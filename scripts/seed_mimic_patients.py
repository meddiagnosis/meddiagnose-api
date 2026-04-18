#!/usr/bin/env python3
"""
Seed MIMIC patient users and diagnoses for testing patient-centric vs doctor-centric views.

Creates:
- 1 doctor user (doctor@meddiagnose.demo)
- N patient users from MIMIC manifest (default 20 for quick test, use --all for 150)
- 1 diagnosis per patient using books brain (symptoms + clinical_notes from manifest)

Run: python scripts/seed_mimic_patients.py [--all]
"""
import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.diagnosis import Diagnosis


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "real_patients_mimic"
MANIFEST_PATH = DATA_DIR / "manifest.json"
DOCTOR_EMAIL = "doctor@meddiagnose.demo"
DOCTOR_PASSWORD = "Doctor@123"
DOCTOR2_EMAIL = "doctor2@meddiagnose.demo"

# Real patient names, emails, and passwords for testing
PATIENT_CREDENTIALS = [
    ("Sarah Johnson", "sarah.johnson@meddiagnose.demo", "Sarah@2024"),
    ("Michael Chen", "michael.chen@meddiagnose.demo", "Michael@2024"),
    ("Priya Sharma", "priya.sharma@meddiagnose.demo", "Priya@2024"),
    ("James Wilson", "james.wilson@meddiagnose.demo", "James@2024"),
    ("Maria Garcia", "maria.garcia@meddiagnose.demo", "Maria@2024"),
    ("David Kim", "david.kim@meddiagnose.demo", "David@2024"),
    ("Emily Davis", "emily.davis@meddiagnose.demo", "Emily@2024"),
    ("Robert Martinez", "robert.martinez@meddiagnose.demo", "Robert@2024"),
    ("Anita Patel", "anita.patel@meddiagnose.demo", "Anita@2024"),
    ("William Brown", "william.brown@meddiagnose.demo", "William@2024"),
    ("Lisa Anderson", "lisa.anderson@meddiagnose.demo", "Lisa@2024"),
    ("Raj Kumar", "raj.kumar@meddiagnose.demo", "Raj@2024"),
    ("Jennifer Taylor", "jennifer.taylor@meddiagnose.demo", "Jennifer@2024"),
    ("Christopher Lee", "christopher.lee@meddiagnose.demo", "Chris@2024"),
    ("Amanda White", "amanda.white@meddiagnose.demo", "Amanda@2024"),
    ("Daniel Thompson", "daniel.thompson@meddiagnose.demo", "Daniel@2024"),
    ("Sneha Reddy", "sneha.reddy@meddiagnose.demo", "Sneha@2024"),
    ("Thomas Clark", "thomas.clark@meddiagnose.demo", "Thomas@2024"),
    ("Rachel Green", "rachel.green@meddiagnose.demo", "Rachel@2024"),
    ("Kevin Nguyen", "kevin.nguyen@meddiagnose.demo", "Kevin@2024"),
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _diagnosis_from_books(symptoms: str, clinical_notes: str) -> dict | None:
    """Run books brain diagnosis. Returns None if unavailable."""
    try:
        from app.services.books_diagnosis import diagnose as books_diagnose
        result = books_diagnose(symptoms, clinical_notes, medical_history={})
        if result and result.get("diagnosis"):
            return {
                "ai_diagnosis": result.get("diagnosis"),
                "ai_reasoning": result.get("reasoning", ""),
                "ai_confidence": float(result.get("confidence", 0.8)),
                "ai_severity": result.get("severity", "moderate"),
                "ai_urgency": result.get("urgency", "routine"),
                "ai_findings": result.get("findings") or [],
                "ai_medications": result.get("medications") or [],
                "ai_lifestyle": result.get("lifestyle_recommendations") or [],
                "ai_precautions": result.get("precautions") or [],
                "ai_when_to_see_doctor": result.get("when_to_see_doctor") or "",
            }
    except Exception as e:
        print(f"  Books brain failed: {e}")
    return None


SAMPLE_DIAGNOSES = [
    {"ai_diagnosis": "Upper Respiratory Tract Infection", "ai_severity": "mild", "ai_urgency": "routine", "ai_confidence": 0.87,
     "ai_reasoning": "Symptoms consistent with viral URTI.", "ai_findings": ["Nasal congestion", "Low-grade fever"],
     "ai_medications": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours", "duration": "3 days"}],
     "ai_lifestyle": ["Rest", "Hydration"], "ai_precautions": ["Avoid cold beverages"], "ai_when_to_see_doctor": "If fever persists."},
    {"ai_diagnosis": "Type 2 Diabetes Mellitus", "ai_severity": "moderate", "ai_urgency": "soon", "ai_confidence": 0.82,
     "ai_reasoning": "Lab values suggest hyperglycemia.", "ai_findings": ["Elevated glucose"],
     "ai_medications": [{"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "duration": "Ongoing"}],
     "ai_lifestyle": ["Low-carb diet", "Exercise"], "ai_precautions": ["Monitor blood sugar"], "ai_when_to_see_doctor": "If blood sugar exceeds 300."},
    {"ai_diagnosis": "Hypertension", "ai_severity": "moderate", "ai_urgency": "soon", "ai_confidence": 0.79,
     "ai_reasoning": "Elevated BP indicators in lab.", "ai_findings": ["Suspected elevated BP"],
     "ai_medications": [{"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "duration": "Ongoing"}],
     "ai_lifestyle": ["Low-sodium diet", "Exercise"], "ai_precautions": ["Monitor BP"], "ai_when_to_see_doctor": "If BP exceeds 180/120."},
    {"ai_diagnosis": "Chronic Kidney Disease", "ai_severity": "moderate", "ai_urgency": "soon", "ai_confidence": 0.75,
     "ai_reasoning": "Renal function markers abnormal.", "ai_findings": ["Elevated creatinine"],
     "ai_medications": [{"name": "ACE inhibitor", "dosage": "As prescribed", "frequency": "Daily", "duration": "Ongoing"}],
     "ai_lifestyle": ["Low-protein diet", "Fluid management"], "ai_precautions": ["Avoid NSAIDs"], "ai_when_to_see_doctor": "If edema or fatigue worsens."},
    {"ai_diagnosis": "Anemia", "ai_severity": "moderate", "ai_urgency": "soon", "ai_confidence": 0.83,
     "ai_reasoning": "Low hemoglobin/hematocrit.", "ai_findings": ["Low Hb", "Fatigue"],
     "ai_medications": [{"name": "Ferrous Sulfate", "dosage": "325mg", "frequency": "Twice daily", "duration": "3 months"}],
     "ai_lifestyle": ["Iron-rich diet"], "ai_precautions": ["Take with vitamin C"], "ai_when_to_see_doctor": "If no improvement in 4 weeks."},
    {"ai_diagnosis": "Urinary Tract Infection", "ai_severity": "mild", "ai_urgency": "soon", "ai_confidence": 0.90,
     "ai_reasoning": "Urine findings suggest UTI.", "ai_findings": ["Pyuria", "Bacteriuria"],
     "ai_medications": [{"name": "Nitrofurantoin", "dosage": "100mg", "frequency": "Twice daily", "duration": "5 days"}],
     "ai_lifestyle": ["Hydration"], "ai_precautions": ["Complete antibiotic course"], "ai_when_to_see_doctor": "If fever develops."},
    {"ai_diagnosis": "Asthma", "ai_severity": "moderate", "ai_urgency": "soon", "ai_confidence": 0.86,
     "ai_reasoning": "Respiratory findings consistent with asthma.", "ai_findings": ["Wheezing", "Reduced peak flow"],
     "ai_medications": [{"name": "Salbutamol Inhaler", "dosage": "2 puffs", "frequency": "As needed", "duration": "Ongoing"}],
     "ai_lifestyle": ["Avoid triggers"], "ai_precautions": ["Carry rescue inhaler"], "ai_when_to_see_doctor": "If inhaler needed >3x/week."},
    {"ai_diagnosis": "COPD", "ai_severity": "moderate", "ai_urgency": "soon", "ai_confidence": 0.80,
     "ai_reasoning": "Chronic obstructive pattern in labs.", "ai_findings": ["Chronic bronchitis pattern"],
     "ai_medications": [{"name": "Tiotropium", "dosage": "18mcg", "frequency": "Once daily", "duration": "Ongoing"}],
     "ai_lifestyle": ["Smoking cessation", "Pulmonary rehab"], "ai_precautions": ["Avoid irritants"], "ai_when_to_see_doctor": "If dyspnea worsens."},
    {"ai_diagnosis": "Hypothyroidism", "ai_severity": "mild", "ai_urgency": "routine", "ai_confidence": 0.85,
     "ai_reasoning": "Thyroid markers suggest hypothyroidism.", "ai_findings": ["Elevated TSH"],
     "ai_medications": [{"name": "Levothyroxine", "dosage": "50mcg", "frequency": "Once daily", "duration": "Ongoing"}],
     "ai_lifestyle": ["Regular follow-up"], "ai_precautions": ["Take on empty stomach"], "ai_when_to_see_doctor": "If fatigue persists."},
    {"ai_diagnosis": "Acute Kidney Injury", "ai_severity": "severe", "ai_urgency": "urgent", "ai_confidence": 0.78,
     "ai_reasoning": "Acute rise in creatinine.", "ai_findings": ["Elevated creatinine", "Reduced eGFR"],
     "ai_medications": [{"name": "IV fluids", "dosage": "As prescribed", "frequency": "Per protocol", "duration": "Until recovery"}],
     "ai_lifestyle": ["Rest", "Monitor intake"], "ai_precautions": ["Avoid nephrotoxins"], "ai_when_to_see_doctor": "Immediately."},
]


def _fallback_diagnosis(index: int, symptoms: str) -> dict:
    d = SAMPLE_DIAGNOSES[index % len(SAMPLE_DIAGNOSES)].copy()
    d["symptoms_text"] = symptoms
    return d


def _get_patient_credentials(index: int) -> tuple[str, str, str]:
    """Get (full_name, email, password) for patient at index. Cycles through list if needed."""
    creds = PATIENT_CREDENTIALS[index % len(PATIENT_CREDENTIALS)]
    name, base_email, pwd = creds
    if index >= len(PATIENT_CREDENTIALS):
        local, domain = base_email.rsplit("@", 1)
        return (name, f"{local}{index}@{domain}", pwd)
    return creds


async def seed_mimic(limit: int = 20):
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found: {MANIFEST_PATH}")
        print("Run: python scripts/convert_mimic_to_reports.py first")
        return

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    patients = manifest.get("patients", [])[:limit]
    if not patients:
        print("No patients in manifest")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Ensure doctors exist (one-to-many: each doctor has many patients)
        doctors: dict[str, User] = {}
        for email, name in [(DOCTOR_EMAIL, "Dr. Sarah Mitchell"), (DOCTOR2_EMAIL, "Dr. Arjun Patel")]:
            doc_result = await db.execute(select(User).where(User.email == email))
            doctor = doc_result.scalar_one_or_none()
            if not doctor:
                doctor = User(
                    email=email,
                    hashed_password=hash_password(DOCTOR_PASSWORD),
                    full_name=name,
                    role="doctor",
                    gender="Male",
                    is_active=True,
                )
                db.add(doctor)
                await db.flush()
                print(f"Created doctor: {email}")
            else:
                print(f"Doctor exists: {email}")
            doctors[email] = doctor

        created = 0
        skipped = 0
        now = datetime.now(timezone.utc)

        for i, p in enumerate(patients):
            full_name, email, password = _get_patient_credentials(i)
            existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            # Patients 0-9: doctor@meddiagnose.demo; patients 10+: doctor2@meddiagnose.demo
            doctor = doctors[DOCTOR_EMAIL] if i < 10 else doctors[DOCTOR2_EMAIL]
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role="patient",
                gender="F" if " F." in p.get("symptoms", "") else "M",
                is_active=True,
                linked_doctor_id=doctor.id,
            )
            db.add(user)
            await db.flush()
            created += 1

            # Diagnosis: try books brain first
            symptoms = p.get("symptoms", "")
            clinical_notes = p.get("clinical_notes", "")
            diag_data = _diagnosis_from_books(symptoms, clinical_notes)
            if not diag_data:
                diag_data = _fallback_diagnosis(i, symptoms)

            diagnosis = Diagnosis(
                status="completed",
                symptoms_text=symptoms,
                ai_diagnosis=diag_data.get("ai_diagnosis"),
                ai_reasoning=diag_data.get("ai_reasoning"),
                ai_confidence=diag_data.get("ai_confidence", 0.8) + random.uniform(-0.03, 0.03),
                ai_model_version="books-brain-v1",
                ai_findings=diag_data.get("ai_findings"),
                ai_medications=diag_data.get("ai_medications"),
                ai_lifestyle=diag_data.get("ai_lifestyle"),
                ai_precautions=diag_data.get("ai_precautions"),
                ai_severity=diag_data.get("ai_severity", "moderate"),
                ai_urgency=diag_data.get("ai_urgency", "routine"),
                ai_when_to_see_doctor=diag_data.get("ai_when_to_see_doctor"),
                reviewed_by=user.id,
                priority="normal",
                created_at=now - timedelta(days=random.randint(1, 30)),
            )
            db.add(diagnosis)

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(patients)}...")

        await db.commit()
        print(f"\nCreated {created} patient users with diagnoses (skipped {skipped} existing)")
        print("\n--- Test Credentials ---")
        print(f"Doctor 1:  {DOCTOR_EMAIL} / {DOCTOR_PASSWORD}")
        print(f"Doctor 2:  {DOCTOR2_EMAIL} / {DOCTOR_PASSWORD}")
        print("\nPatients (name / email / password):")
        for i in range(min(10, len(PATIENT_CREDENTIALS))):
            name, email, pwd = _get_patient_credentials(i)
            print(f"  {name}: {email} / {pwd}")
        if len(PATIENT_CREDENTIALS) > 10:
            print(f"  ... and {len(PATIENT_CREDENTIALS) - 10} more (see PATIENT_CREDENTIALS in script)")
        print("\nPatient view: Login as patient -> My Diagnoses")
        print("Doctor view:  Login as doctor -> Patients -> click patient -> view diagnoses")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Seed all 150 patients (default: 20)")
    args = parser.parse_args()
    limit = 150 if args.all else 20
    asyncio.run(seed_mimic(limit=limit))
