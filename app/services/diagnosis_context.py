"""
Build prior patient context for diagnosis — previous diagnoses, fitness vitals, symptom history.

Used to give the AI a fuller picture when making a new diagnosis.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnosis import Diagnosis
from app.models.fitness_log import FitnessLog
from app.models.symptom_log import SymptomLog
from app.models.patient import Patient


async def build_prior_context(
    db: AsyncSession,
    *,
    user_id: int,
    patient_id: int | None = None,
    max_prior_diagnoses: int = 5,
    fitness_days: int = 14,
    symptom_days: int = 14,
) -> dict:
    """
    Fetch prior diagnoses, fitness vitals, and symptom logs for context.

    When patient_id is set: use that patient's prior diagnoses + patient record (symptoms, medical_history).
    When patient_id is None: use current user's prior diagnoses, fitness logs, symptom logs.

    Returns a dict with keys: prior_diagnoses, fitness_vitals, symptom_history, patient_context.
    """
    out: dict = {
        "prior_diagnoses": [],
        "fitness_vitals": None,
        "symptom_history": [],
        "patient_context": None,
    }

    # --- Prior diagnoses ---
    if patient_id:
        diag_q = (
            select(Diagnosis)
            .where(
                Diagnosis.patient_id == patient_id,
                Diagnosis.status == "completed",
                Diagnosis.ai_diagnosis.isnot(None),
            )
            .order_by(Diagnosis.created_at.desc())
            .limit(max_prior_diagnoses)
        )
    else:
        diag_q = (
            select(Diagnosis)
            .where(
                Diagnosis.patient_id.is_(None),
                Diagnosis.reviewed_by == user_id,
                Diagnosis.status == "completed",
                Diagnosis.ai_diagnosis.isnot(None),
            )
            .order_by(Diagnosis.created_at.desc())
            .limit(max_prior_diagnoses)
        )

    diag_result = await db.execute(diag_q)
    diagnoses = diag_result.scalars().all()
    for d in diagnoses:
        created = d.created_at.strftime("%Y-%m-%d") if d.created_at else "unknown"
        out["prior_diagnoses"].append({
            "diagnosis": d.ai_diagnosis or "Unknown",
            "date": created,
            "severity": d.ai_severity,
            "urgency": d.ai_urgency,
        })

    # --- Fitness vitals (user only — fitness logs are user-scoped) ---
    if not patient_id:
        since = date.today() - timedelta(days=fitness_days)
        fit_q = (
            select(FitnessLog)
            .where(
                FitnessLog.user_id == user_id,
                FitnessLog.log_date >= since,
            )
            .order_by(FitnessLog.log_date.desc())
            .limit(60)
        )
        fit_result = await db.execute(fit_q)
        logs = fit_result.scalars().all()
        if logs:
            hr_vals = [l.heart_rate for l in logs if l.heart_rate is not None]
            spo2_vals = [l.spo2 for l in logs if l.spo2 is not None]
            out["fitness_vitals"] = {
                "heart_rate_avg": round(sum(hr_vals) / len(hr_vals), 0) if hr_vals else None,
                "heart_rate_recent": hr_vals[0] if hr_vals else None,
                "spo2_avg": round(sum(spo2_vals) / len(spo2_vals), 0) if spo2_vals else None,
                "spo2_recent": spo2_vals[0] if spo2_vals else None,
                "days_with_data": len(set(l.log_date for l in logs)),
            }

    # --- Symptom history (user only) ---
    if not patient_id:
        since_dt = datetime.now(timezone.utc) - timedelta(days=symptom_days)
        sym_q = (
            select(SymptomLog)
            .where(
                SymptomLog.user_id == user_id,
                SymptomLog.logged_at >= since_dt,
            )
            .order_by(SymptomLog.logged_at.desc())
            .limit(50)
        )
        sym_result = await db.execute(sym_q)
        sym_logs = sym_result.scalars().all()
        if sym_logs:
            by_symptom: dict[str, list[int]] = {}
            for s in sym_logs:
                key = s.symptom.strip().lower()
                if key not in by_symptom:
                    by_symptom[key] = []
                by_symptom[key].append(s.severity)
            out["symptom_history"] = [
                {"symptom": k, "count": len(v), "avg_severity": round(sum(v) / len(v), 1)}
                for k, v in sorted(by_symptom.items(), key=lambda x: -len(x[1]))[:15]
            ]

    # --- Patient context (when diagnosing a patient) ---
    if patient_id:
        pat_result = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = pat_result.scalar_one_or_none()
        if patient:
            out["patient_context"] = {
                "name": f"{patient.first_name} {patient.last_name}",
                "symptoms": patient.symptoms,
                "medical_history": patient.medical_history,
                "medications": patient.medications,
                "clinical_notes": patient.clinical_notes,
            }

    return out


def format_prior_context_for_prompt(ctx: dict) -> str:
    """Build a human-readable string for the AI prompt from prior context."""
    parts: list[str] = []

    if ctx.get("prior_diagnoses"):
        lines = []
        for d in ctx["prior_diagnoses"]:
            s = f"- {d['diagnosis']} ({d['date']})"
            if d.get("severity"):
                s += f", severity: {d['severity']}"
            if d.get("urgency"):
                s += f", urgency: {d['urgency']}"
            lines.append(s)
        parts.append("Prior diagnoses (recent):\n" + "\n".join(lines))

    if ctx.get("fitness_vitals"):
        f = ctx["fitness_vitals"]
        fparts = []
        if f.get("heart_rate_recent") is not None:
            fparts.append(f"recent HR {f['heart_rate_recent']} bpm")
        if f.get("heart_rate_avg") is not None and f.get("heart_rate_avg") != f.get("heart_rate_recent"):
            fparts.append(f"avg HR {f['heart_rate_avg']} bpm")
        if f.get("spo2_recent") is not None:
            fparts.append(f"recent SpO2 {f['spo2_recent']}%")
        if f.get("spo2_avg") is not None:
            fparts.append(f"avg SpO2 {f['spo2_avg']}%")
        if fparts:
            parts.append(f"Wearable/fitness vitals (last {f.get('days_with_data', 0)} days): " + "; ".join(fparts))

    if ctx.get("symptom_history"):
        lines = [f"- {s['symptom']} (logged {s['count']}x, avg severity {s['avg_severity']}/5)" for s in ctx["symptom_history"][:10]]
        parts.append("Symptom history (recent):\n" + "\n".join(lines))

    if ctx.get("patient_context"):
        p = ctx["patient_context"]
        pparts = []
        if p.get("symptoms"):
            syms = p["symptoms"] if isinstance(p["symptoms"], list) else [str(p["symptoms"])]
            pparts.append(f"reported symptoms: {', '.join(str(s) for s in syms)}")
        if p.get("medications"):
            meds = p["medications"] if isinstance(p["medications"], list) else [str(p["medications"])]
            pparts.append(f"current medications: {', '.join(str(m) for m in meds)}")
        if p.get("medical_history"):
            mh = p["medical_history"]
            if isinstance(mh, dict):
                pparts.append("medical history: " + "; ".join(f"{k}: {v}" for k, v in mh.items()))
            else:
                pparts.append(f"medical history: {mh}")
        if p.get("clinical_notes"):
            pparts.append(f"clinical notes: {p['clinical_notes']}")
        if pparts:
            parts.append(f"Patient record ({p.get('name', 'unknown')}):\n" + "\n".join(pparts))

    if not parts:
        return ""
    return "\n\nPatient prior context (use for differentials and continuity):\n" + "\n".join(parts)
