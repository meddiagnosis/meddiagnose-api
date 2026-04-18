import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user, require_roles
from app.core.storage import get_storage
from app.core.cache import cache_get, cache_set, cache_delete_pattern, make_cache_key
from app.models.user import User
from app.models.diagnosis import Diagnosis
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisReview, DiagnosisResponse, DiagnosisList
from app.services.audit import log_audit
from app.services.image_extraction import extract_images_from_file, images_to_base64_data_urls
from app.services.diagnosis_context import build_prior_context, format_prior_context_for_prompt

router = APIRouter(prefix="/diagnoses", tags=["Diagnoses"])


def _parse_optional_int(val: str | None) -> int | None:
    """Parse optional form int; return None if empty or invalid."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _parse_optional_float(val: str | None) -> float | None:
    """Parse optional form float; return None if empty or invalid."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    try:
        return float(str(val).strip())
    except ValueError:
        return None


# Sample cases for testing (no auth required for demo)
SAMPLE_CASES = [
    {
        "name": "Fever & fatigue (blood report)",
        "symptoms": "Fever for 3 days, fatigue, body ache, mild headache. No cough or cold.",
        "clinical_notes": "Blood sugar slightly elevated in recent checkup. No known allergies.",
        "report_content": """Complete Blood Count (CBC) - Sample Report
Patient: Demo Patient | Date: 2025-03-15
Lab: City Diagnostics

Hemoglobin (Hb): 12.5 g/dL (Ref: 12-16)
RBC: 4.8 M/uL (Ref: 4.5-5.5)
WBC: 7500 /uL (Ref: 4000-11000)
Platelets: 250000 /uL (Ref: 150000-400000)
FBS (Fasting Blood Sugar): 98 mg/dL (Ref: 70-100)
ESR: 18 mm/hr (Ref: 0-20)

Impression: Mild leukocytosis. FBS at upper limit of normal.""",
    },
    {
        "name": "Upper respiratory symptoms",
        "symptoms": "Sore throat, runny nose, mild fever (99.5°F), cough for 4 days.",
        "clinical_notes": "Started after travel. No chest pain or breathing difficulty.",
        "report_content": """Throat Swab - Rapid Strep Test
Result: Negative
Date: 2025-03-14

CBC:
WBC: 11000 /uL (slightly elevated)
Neutrophils: 72%
Lymphocytes: 24%

Clinical: Viral upper respiratory infection likely.""",
    },
    {
        "name": "Hypertension follow-up",
        "symptoms": "Routine BP check. Occasional headache. On amlodipine 5mg.",
        "clinical_notes": "History of hypertension. Kidney function normal last year.",
        "report_content": """Lipid Profile & Renal Function
Date: 2025-03-10

Total Cholesterol: 198 mg/dL (Ref: <200)
LDL: 120 mg/dL (Ref: <100)
HDL: 45 mg/dL (Ref: >40)
Triglycerides: 165 mg/dL (Ref: <150)
Creatinine: 1.0 mg/dL (Ref: 0.7-1.3)
eGFR: 92 mL/min/1.73m2

BP today: 138/88 mmHg""",
    },
]


def _load_patient_lab_reports():
    """Load patient lab reports from data/sample_patients/ (synthetic)."""
    cases = []
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "sample_patients"
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        return cases
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    for p in manifest.get("patients", []):
        lab_path = data_dir / p["lab_report"]
        report_content = ""
        if lab_path.exists():
            report_content = lab_path.read_text(encoding="utf-8")
        cases.append({
            "name": p["user_email"],
            "symptoms": p["symptoms"],
            "clinical_notes": p.get("clinical_notes", ""),
            "report_content": report_content,
            "expected_diagnosis": p.get("expected_diagnosis", ""),
        })
    return cases


def _load_mimic_reports():
    """Load real patient lab reports from MIMIC-IV Demo (data/real_patients_mimic/)."""
    cases = []
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "real_patients_mimic"
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        return cases
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    for p in manifest.get("patients", []):
        lab_path = data_dir / p["lab_report"]
        report_content = ""
        if lab_path.exists():
            report_content = lab_path.read_text(encoding="utf-8")
        cases.append({
            "name": p["user_email"],
            "symptoms": p["symptoms"],
            "clinical_notes": p.get("clinical_notes", ""),
            "report_content": report_content,
            "expected_diagnosis": p.get("expected_diagnosis", ""),
        })
    return cases


@router.get("/sample")
async def get_sample_cases():
    """Return built-in + real MIMIC patient reports + synthetic samples for testing."""
    mimic_cases = _load_mimic_reports()
    patient_cases = _load_patient_lab_reports()
    all_cases = SAMPLE_CASES + mimic_cases + patient_cases
    return {"cases": all_cases}


@router.get("/sample/{index:int}")
async def get_sample_case(index: int):
    """Get a specific sample case by index (0-based). Includes real MIMIC + synthetic."""
    mimic_cases = _load_mimic_reports()
    patient_cases = _load_patient_lab_reports()
    all_cases = SAMPLE_CASES + mimic_cases + patient_cases
    if index < 0 or index >= len(all_cases):
        raise HTTPException(status_code=404, detail="Sample case not found")
    return all_cases[index]


@router.get("/sample/fetch-url")
async def fetch_sample_from_url(url: str = Query(...)):
    """Fetch sample report content from a URL (for testing with external data)."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Valid URL required")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.text
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")
    return {
        "symptoms": "Symptoms from fetched report - please review and edit",
        "clinical_notes": "",
        "report_content": content[:50000],
    }


@router.post("/analyze", response_model=DiagnosisResponse, status_code=201)
async def analyze_report(
    request: Request,
    symptoms: str = Form(...),
    clinical_notes: str = Form(""),
    brain: str = Form(""),  # "books", "medgemma", or "medgemma-27b"
    model_size: str = Form(""),  # "4b" or "27b" (overrides brain for MedGemma)
    files: list[UploadFile] = File(default=[]),
    vitals_systolic: str = Form(""),  # BP systolic (mmHg)
    vitals_diastolic: str = Form(""),  # BP diastolic (mmHg)
    vitals_spo2: str = Form(""),  # SpO2 from oximeter (%)
    vitals_heart_rate: str = Form(""),  # Heart rate (bpm)
    vitals_temperature: str = Form(""),  # Body temp (°F)
    vitals_respiratory_rate: str = Form(""),  # Breaths per minute
    vitals_blood_sugar: str = Form(""),  # Blood glucose (mg/dL)
    vitals_weight_kg: str = Form(""),  # Weight (kg)
    vitals_pain_level: str = Form(""),  # Pain 0-10
    vitals_ecg_notes: str = Form(""),  # ECG interpretation / report text
    patient_id: str = Form(""),  # Optional: link diagnosis to patient (for clinician workflow)
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient uploads medical reports + describes symptoms and gets AI diagnosis with medications."""
    settings = get_settings()
    storage = get_storage()
    saved_files = []
    all_image_bytes: list[tuple[bytes, str]] = []

    for f in files:
        content = await f.read()
        file_path = await storage.upload(content, f.filename or "report", current_user.id)
        saved_files.append(file_path)
        all_image_bytes.extend(extract_images_from_file(content, f.filename or "report"))

    # Cap at 6 images to avoid overwhelming the model and long request times
    MAX_IMAGES = 6
    capped = all_image_bytes[:MAX_IMAGES] if all_image_bytes else []
    image_data_urls = images_to_base64_data_urls(capped) if capped else None

    # Build file hints for modality-specific prompts (radiology, lab report, dermatology)
    file_hints: list[tuple[str, str]] = []
    for f in files:
        fn = f.filename or "report"
        ext = Path(fn).suffix.lower()
        if ext in (".dcm", ".dicom"):
            file_hints.append(("radiology", fn))
        elif ext == ".pdf":
            file_hints.append(("document", fn))
        elif ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            file_hints.append(("image", fn))

    use_27b = (model_size or "").lower() == "27b" or (brain or "").lower() == "medgemma-27b"

    medical_history = {
        "allergies": current_user.allergies or "None reported",
        "blood_group": current_user.blood_group or "Unknown",
        "gender": current_user.gender or "Not specified",
        "date_of_birth": current_user.date_of_birth or "Unknown",
    }

    # Optional vitals from BP machine, oximeter, thermometer, glucometer, ECG, etc.
    vitals = {}
    if (s := _parse_optional_int(vitals_systolic)) is not None:
        vitals["systolic_bp"] = s
    if (d := _parse_optional_int(vitals_diastolic)) is not None:
        vitals["diastolic_bp"] = d
    if (o := _parse_optional_int(vitals_spo2)) is not None:
        vitals["spo2"] = o
    if (hr := _parse_optional_int(vitals_heart_rate)) is not None:
        vitals["heart_rate"] = hr
    if (t := _parse_optional_float(vitals_temperature)) is not None:
        vitals["temperature_f"] = t
    if (rr := _parse_optional_int(vitals_respiratory_rate)) is not None:
        vitals["respiratory_rate"] = rr
    if (bs := _parse_optional_float(vitals_blood_sugar)) is not None:
        vitals["blood_sugar_mg_dl"] = bs
    if (w := _parse_optional_float(vitals_weight_kg)) is not None:
        vitals["weight_kg"] = w
    if (p := _parse_optional_int(vitals_pain_level)) is not None:
        vitals["pain_level"] = p
    if vitals_ecg_notes and vitals_ecg_notes.strip():
        vitals["ecg_notes"] = vitals_ecg_notes.strip()
    if vitals:
        medical_history["vitals"] = vitals

    # Parse patient_id for clinician workflow
    parsed_patient_id: int | None = None
    if patient_id and str(patient_id).strip():
        try:
            parsed_patient_id = int(str(patient_id).strip())
        except ValueError:
            pass

    # Build prior context: previous diagnoses, fitness vitals, symptom history
    prior_ctx = await build_prior_context(
        db,
        user_id=current_user.id,
        patient_id=parsed_patient_id,
        max_prior_diagnoses=5,
        fitness_days=14,
        symptom_days=14,
    )
    prior_context_str = format_prior_context_for_prompt(prior_ctx)
    if prior_context_str:
        medical_history["prior_context"] = prior_context_str

    brain = (brain or settings.DIAGNOSIS_BRAIN or "medgemma").lower()
    if brain == "books":
        from app.services.books_diagnosis import diagnose as books_diagnose
        ai_result = await asyncio.to_thread(books_diagnose, symptoms, clinical_notes, medical_history)
    else:
        from app.services.medgemma_diagnosis import diagnose as medgemma_diagnose
        ai_result = await medgemma_diagnose(
            symptoms,
            clinical_notes,
            medical_history=medical_history,
            image_data_urls=image_data_urls,
            file_hints=file_hints,
            use_27b=use_27b,
        )

    from app.services.drug_interactions import check_within_prescription, check_interactions
    from app.services.dosage_calculator import adjust_dosages, _calculate_age
    from app.services.prescription_safety import apply_prescription_safety

    age = _calculate_age(current_user.date_of_birth) if current_user.date_of_birth else None
    weight = current_user.weight_kg
    if ai_result.get("medications"):
        ai_result["medications"] = adjust_dosages(ai_result["medications"], age, weight)

    # Prescription safety: critical conditions, allergy, pregnancy, organ/breastfeeding/QT, pediatric, Beers
    clinical_context = f"{symptoms} {clinical_notes}".strip()
    ai_result["medications"], safety = apply_prescription_safety(
        ai_result.get("medications") or [],
        allergies=current_user.allergies,
        clinical_context=clinical_context,
        age=age,
        diagnosis=ai_result.get("diagnosis"),
        severity=ai_result.get("severity"),
        urgency=ai_result.get("urgency"),
    )
    ai_result["allergy_warnings"] = safety.get("allergy_warnings") or None
    ai_result["critical_warnings"] = safety.get("critical_warnings") or None
    organ_warns = list(safety.get("organ_warnings") or [])
    organ_warns.extend(safety.get("pediatric_warnings") or [])
    organ_warns.extend(safety.get("beers_warnings") or [])
    ai_result["organ_warnings"] = organ_warns if organ_warns else None
    ai_result["prescription_safety_warnings"] = (
        safety.get("duplicate_warnings") or safety.get("high_risk_warnings") or []
    )
    if safety.get("pregnancy_warnings"):
        ai_result["pregnancy_warnings"] = safety["pregnancy_warnings"]
    if safety.get("high_risk_warnings"):
        ai_result["high_risk_drug_warnings"] = safety["high_risk_warnings"]

    interaction_warnings = []
    if ai_result.get("medications"):
        interaction_warnings = check_within_prescription(ai_result["medications"])
    # Add duplicate-therapy warnings to interaction list
    for dup in safety.get("duplicate_warnings") or []:
        interaction_warnings.append({
            "drug_a": dup.get("drug_a", ""),
            "drug_b": dup.get("drug_b", ""),
            "severity": dup.get("severity", "moderate"),
            "description": dup.get("message", ""),
            "recommendation": dup.get("message", ""),
        })

    if parsed_patient_id:
        prev_diag_filter = Diagnosis.patient_id == parsed_patient_id
    else:
        prev_diag_filter = Diagnosis.patient_id.is_(None) & (Diagnosis.reviewed_by == current_user.id)
    prev_result = await db.execute(
        select(Diagnosis)
        .where(prev_diag_filter, Diagnosis.status == "completed")
        .order_by(Diagnosis.created_at.desc())
        .limit(5)
    )
    prev_diagnoses = prev_result.scalars().all()
    existing_meds = []
    for pd in prev_diagnoses:
        if pd.ai_medications:
            existing_meds.extend(pd.ai_medications)
    if existing_meds and ai_result.get("medications"):
        cross_warnings = check_interactions(ai_result["medications"], existing_meds)
        interaction_warnings.extend(cross_warnings)

    ai_result["drug_interactions"] = interaction_warnings if interaction_warnings else None

    diagnosis = Diagnosis(
        patient_id=parsed_patient_id,
        status="completed",
        symptoms_text=symptoms,
        report_files=saved_files if saved_files else None,
        ai_diagnosis=ai_result.get("diagnosis"),
        ai_layman_summary=ai_result.get("layman_summary"),
        ai_reasoning=ai_result.get("reasoning"),
        ai_confidence=ai_result.get("confidence", 0.0),
        ai_model_version=ai_result.get("model_version", "medgemma-mock"),
        ai_findings=ai_result.get("findings"),
        ai_medications=ai_result.get("medications"),
        ai_lifestyle=ai_result.get("lifestyle_recommendations"),
        ai_precautions=ai_result.get("precautions"),
        ai_severity=ai_result.get("severity"),
        ai_urgency=ai_result.get("urgency"),
        ai_when_to_see_doctor=ai_result.get("when_to_see_doctor"),
        ai_recommended_tests=ai_result.get("recommended_tests"),
        ai_differential_diagnoses=ai_result.get("differential_diagnoses"),
        ai_drug_interactions=ai_result.get("drug_interactions"),
        ai_allergy_warnings=ai_result.get("allergy_warnings"),
        ai_high_risk_drug_warnings=ai_result.get("high_risk_drug_warnings"),
        ai_organ_warnings=ai_result.get("organ_warnings"),
        ai_critical_warnings=ai_result.get("critical_warnings"),
        ai_dietary_plan=ai_result.get("dietary_plan"),
        ai_routine_plan=ai_result.get("routine_plan"),
        ai_ayurvedic_medicines=ai_result.get("ayurvedic_medicines"),
        ai_extracted_lab_values=ai_result.get("extracted_lab_values"),
        ai_raw_response=ai_result,
        reviewed_by=current_user.id,
        priority="normal",
    )
    db.add(diagnosis)
    await db.commit()
    await db.refresh(diagnosis)

    await log_audit(db, action="create", resource_type="diagnosis", resource_id=str(diagnosis.id),
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    await cache_delete_pattern(f"meddiagnose:diag_list:{current_user.id}:*")

    return DiagnosisResponse.model_validate(diagnosis)


@router.post("/", response_model=DiagnosisResponse, status_code=201)
async def create_diagnosis(
    body: DiagnosisCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diagnosis = Diagnosis(
        patient_id=None,
        symptoms_text=body.symptoms,
        status="queued",
        priority=body.priority,
        report_files=body.report_files,
        reviewed_by=current_user.id,
    )
    db.add(diagnosis)
    await db.commit()
    await db.refresh(diagnosis)

    await log_audit(db, action="create", resource_type="diagnosis", resource_id=str(diagnosis.id),
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return DiagnosisResponse.model_validate(diagnosis)


@router.get("/", response_model=DiagnosisList)
async def list_diagnoses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    patient_id: int | None = Query(None),
    batch_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = f"meddiagnose:diag_list:{current_user.id}:{page}:{per_page}:{status}"
    cached = await cache_get(cache_key)
    if cached:
        return DiagnosisList(**cached)

    query = select(Diagnosis).where(Diagnosis.reviewed_by == current_user.id)
    count_query = select(func.count(Diagnosis.id)).where(Diagnosis.reviewed_by == current_user.id)

    if status:
        query = query.where(Diagnosis.status == status)
        count_query = count_query.where(Diagnosis.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Diagnosis.created_at.desc()).offset(offset).limit(per_page))
    diagnoses = result.scalars().all()

    response = DiagnosisList(
        items=[DiagnosisResponse.model_validate(d) for d in diagnoses],
        total=total, page=page, per_page=per_page,
    )
    await cache_set(cache_key, response.model_dump(), ttl=60)
    return response


@router.get("/{diagnosis_id}", response_model=DiagnosisResponse)
async def get_diagnosis(
    diagnosis_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Diagnosis).where(Diagnosis.id == diagnosis_id))
    diagnosis = result.scalar_one_or_none()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    await log_audit(db, action="read", resource_type="diagnosis", resource_id=str(diagnosis_id),
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return DiagnosisResponse.model_validate(diagnosis)


@router.put("/{diagnosis_id}/review", response_model=DiagnosisResponse)
async def review_diagnosis(
    diagnosis_id: int,
    body: DiagnosisReview,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "reviewer", "admin")),
):
    result = await db.execute(select(Diagnosis).where(Diagnosis.id == diagnosis_id))
    diagnosis = result.scalar_one_or_none()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    if diagnosis.status not in ("pending_review", "approved"):
        raise HTTPException(status_code=400, detail=f"Cannot review diagnosis in '{diagnosis.status.value}' status")

    valid_statuses = {"approved", "rejected", "overridden"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Review status must be one of: {', '.join(valid_statuses)}")

    diagnosis.status = body.status
    diagnosis.final_diagnosis = body.final_diagnosis or diagnosis.ai_diagnosis
    diagnosis.reviewer_notes = body.reviewer_notes
    diagnosis.reviewed_by = current_user.id
    diagnosis.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(diagnosis)

    await log_audit(
        db, action="review", resource_type="diagnosis", resource_id=str(diagnosis_id),
        user_id=current_user.id, user_email=current_user.email, request=request,
        changes={"status": body.status, "final_diagnosis": body.final_diagnosis},
    )
    await db.commit()

    return DiagnosisResponse.model_validate(diagnosis)
