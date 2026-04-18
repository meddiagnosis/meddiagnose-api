"""Seed script: creates dummy users (admin, doctor, patients) and sample diagnoses."""

import asyncio
import random
import secrets
from datetime import date, datetime, timedelta, timezone

import bcrypt as _bcrypt

from app.core.database import engine, Base, AsyncSessionLocal
from app.models.user import User
from app.models.patient import Patient


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
from app.models.diagnosis import Diagnosis
from app.models.symptom_log import SymptomLog
from app.models.chat_message import ChatMessage
from app.models.insurance import InsurancePolicy, InsuranceBill, InsuranceClaim

USERS = [
    {
        "email": "admin@meddiagnose.com",
        "password": "Admin@123",
        "full_name": "Rahul Sharma",
        "role": "admin",
        "gender": "Male",
        "date_of_birth": "1985-03-15",
        "blood_group": "B+",
        "phone": "+91-9876543210",
        "weight_kg": 78.0,
    },
    {
        "email": "doctor@meddiagnose.com",
        "password": "Doctor@123",
        "full_name": "Dr. Priya Mehta",
        "role": "doctor",
        "gender": "Female",
        "date_of_birth": "1980-07-22",
        "blood_group": "A+",
        "phone": "+91-9876543211",
        "weight_kg": 62.0,
    },
    {
        "email": "doctor2@meddiagnose.com",
        "password": "Doctor@123",
        "full_name": "Dr. Arjun Patel",
        "role": "doctor",
        "gender": "Male",
        "date_of_birth": "1978-11-05",
        "blood_group": "O+",
        "phone": "+91-9876543212",
        "weight_kg": 82.0,
    },
    {
        "email": "patient1@gmail.com",
        "password": "Patient@123",
        "full_name": "Ananya Gupta",
        "role": "patient",
        "gender": "Female",
        "date_of_birth": "1995-01-20",
        "blood_group": "O+",
        "allergies": "Penicillin, Sulfa drugs",
        "phone": "+91-9123456780",
        "weight_kg": 55.0,
    },
    {
        "email": "patient2@gmail.com",
        "password": "Patient@123",
        "full_name": "Vikram Singh",
        "role": "patient",
        "gender": "Male",
        "date_of_birth": "1988-06-10",
        "blood_group": "A-",
        "allergies": "Aspirin",
        "phone": "+91-9123456781",
        "weight_kg": 75.0,
    },
    {
        "email": "patient3@gmail.com",
        "password": "Patient@123",
        "full_name": "Meera Krishnan",
        "role": "patient",
        "gender": "Female",
        "date_of_birth": "2000-09-12",
        "blood_group": "B+",
        "phone": "+91-9123456782",
        "weight_kg": 60.0,
    },
    {
        "email": "patient4@gmail.com",
        "password": "Patient@123",
        "full_name": "Rohan Desai",
        "role": "patient",
        "gender": "Male",
        "date_of_birth": "1992-12-03",
        "blood_group": "AB+",
        "allergies": "Ibuprofen",
        "phone": "+91-9123456783",
        "weight_kg": 88.0,
    },
    {
        "email": "patient5@gmail.com",
        "password": "Patient@123",
        "full_name": "Sanya Joshi",
        "role": "patient",
        "gender": "Female",
        "date_of_birth": "1998-04-28",
        "blood_group": "O-",
        "phone": "+91-9123456784",
        "weight_kg": 52.0,
    },
    {
        "email": "patient6@gmail.com",
        "password": "Patient@123",
        "full_name": "Kabir Malhotra",
        "role": "patient",
        "gender": "Male",
        "date_of_birth": "1975-08-14",
        "blood_group": "A+",
        "allergies": "Codeine, Morphine",
        "phone": "+91-9123456785",
        "weight_kg": 95.0,
    },
    {
        "email": "patient7@gmail.com",
        "password": "Patient@123",
        "full_name": "Nisha Reddy",
        "role": "patient",
        "gender": "Female",
        "date_of_birth": "2002-02-17",
        "blood_group": "B-",
        "phone": "+91-9123456786",
        "weight_kg": 48.0,
    },
]

SAMPLE_DIAGNOSES = [
    {
        "ai_diagnosis": "Upper Respiratory Tract Infection",
        "symptoms_text": "fever, runny nose, sore throat, cough for 3 days",
        "ai_severity": "mild",
        "ai_urgency": "routine",
        "ai_confidence": 0.87,
        "ai_reasoning": "Symptoms are consistent with viral URTI. No alarm signs.",
        "ai_findings": ["Nasal congestion", "Mild pharyngeal erythema", "Low-grade fever"],
        "ai_medications": [
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours", "duration": "3 days"},
            {"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily", "duration": "5 days"},
        ],
        "ai_lifestyle": ["Rest and adequate hydration", "Warm salt-water gargles"],
        "ai_precautions": ["Avoid cold beverages", "Wear a mask to prevent spread"],
        "ai_when_to_see_doctor": "If fever persists beyond 5 days or breathing difficulty occurs.",
    },
    {
        "ai_diagnosis": "Type 2 Diabetes Mellitus",
        "symptoms_text": "frequent urination, increased thirst, blurred vision, fatigue",
        "ai_severity": "moderate",
        "ai_urgency": "soon",
        "ai_confidence": 0.82,
        "ai_reasoning": "Classic triad of polyuria, polydipsia, and fatigue suggests hyperglycemia.",
        "ai_findings": ["Elevated random blood glucose suspected", "BMI potentially elevated"],
        "ai_medications": [
            {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "duration": "Ongoing"},
        ],
        "ai_lifestyle": ["Low-carb diet", "Daily 30-minute walk", "Regular blood sugar monitoring"],
        "ai_precautions": ["Avoid sugary foods", "Regular eye exams"],
        "ai_when_to_see_doctor": "If blood sugar exceeds 300 mg/dL or you experience confusion.",
    },
    {
        "ai_diagnosis": "Hypertension",
        "symptoms_text": "headache, dizziness, occasional nosebleeds, chest tightness",
        "ai_severity": "moderate",
        "ai_urgency": "soon",
        "ai_confidence": 0.79,
        "ai_reasoning": "Persistent headaches with dizziness and chest tightness suggest elevated blood pressure.",
        "ai_findings": ["Suspected elevated BP", "Possible target organ involvement"],
        "ai_medications": [
            {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "duration": "Ongoing"},
        ],
        "ai_lifestyle": ["Low-sodium diet (DASH)", "Regular exercise", "Stress management", "Limit alcohol"],
        "ai_precautions": ["Monitor BP at home twice daily", "Avoid sudden position changes"],
        "ai_when_to_see_doctor": "If BP exceeds 180/120 mmHg or severe headache with vision changes.",
    },
    {
        "ai_diagnosis": "Migraine",
        "symptoms_text": "severe headache on one side, nausea, sensitivity to light and sound",
        "ai_severity": "moderate",
        "ai_urgency": "routine",
        "ai_confidence": 0.91,
        "ai_reasoning": "Unilateral throbbing headache with photophobia and nausea is classic migraine presentation.",
        "ai_findings": ["Unilateral cephalalgia", "Photophobia", "Phonophobia", "Nausea"],
        "ai_medications": [
            {"name": "Sumatriptan", "dosage": "50mg", "frequency": "At onset of migraine", "duration": "As needed"},
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Every 8 hours during attack", "duration": "3 days"},
        ],
        "ai_lifestyle": ["Maintain regular sleep schedule", "Avoid known triggers", "Keep a headache diary"],
        "ai_precautions": ["Avoid bright screens during episodes", "Stay in a dark, quiet room"],
        "ai_when_to_see_doctor": "If migraines become more frequent or change in character.",
    },
    {
        "ai_diagnosis": "Gastroesophageal Reflux Disease",
        "symptoms_text": "heartburn after meals, acid regurgitation, chest discomfort, bloating",
        "ai_severity": "mild",
        "ai_urgency": "routine",
        "ai_confidence": 0.85,
        "ai_reasoning": "Postprandial heartburn with acid reflux is characteristic of GERD.",
        "ai_findings": ["Retrosternal burning", "Acid regurgitation", "Epigastric discomfort"],
        "ai_medications": [
            {"name": "Omeprazole", "dosage": "20mg", "frequency": "Once daily before breakfast", "duration": "4 weeks"},
            {"name": "Antacid", "dosage": "10ml", "frequency": "After meals as needed", "duration": "2 weeks"},
        ],
        "ai_lifestyle": ["Eat smaller meals", "Avoid lying down after eating", "Elevate head of bed"],
        "ai_precautions": ["Avoid spicy, fatty foods", "Limit caffeine and alcohol"],
        "ai_when_to_see_doctor": "If symptoms persist after 4 weeks or difficulty swallowing occurs.",
    },
    {
        "ai_diagnosis": "Dengue Fever",
        "symptoms_text": "high fever, severe body aches, rash, pain behind eyes, fatigue",
        "ai_severity": "severe",
        "ai_urgency": "urgent",
        "ai_confidence": 0.88,
        "ai_reasoning": "High fever with retro-orbital pain, myalgia, and rash in endemic area suggests dengue.",
        "ai_findings": ["High-grade fever", "Retro-orbital pain", "Thrombocytopenia suspected", "Maculopapular rash"],
        "ai_medications": [
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours", "duration": "5 days"},
        ],
        "ai_lifestyle": ["Complete bed rest", "Oral rehydration salts", "Platelet count monitoring"],
        "ai_precautions": ["Avoid NSAIDs (Aspirin/Ibuprofen)", "Use mosquito net"],
        "ai_when_to_see_doctor": "Immediately if bleeding, severe abdominal pain, or persistent vomiting.",
    },
    {
        "ai_diagnosis": "Iron Deficiency Anemia",
        "symptoms_text": "extreme fatigue, pale skin, shortness of breath, brittle nails, cold hands",
        "ai_severity": "moderate",
        "ai_urgency": "soon",
        "ai_confidence": 0.83,
        "ai_reasoning": "Fatigue, pallor, and koilonychia point to iron deficiency anemia.",
        "ai_findings": ["Pallor", "Koilonychia", "Tachycardia on exertion", "Fatigue"],
        "ai_medications": [
            {"name": "Ferrous Sulfate", "dosage": "325mg", "frequency": "Twice daily", "duration": "3 months"},
            {"name": "Vitamin C", "dosage": "500mg", "frequency": "With iron supplement", "duration": "3 months"},
        ],
        "ai_lifestyle": ["Iron-rich diet (spinach, red meat, lentils)", "Avoid tea/coffee with meals"],
        "ai_precautions": ["Take iron on empty stomach if tolerated", "May cause dark stools"],
        "ai_when_to_see_doctor": "If symptoms don't improve in 4 weeks or blood in stool.",
    },
    {
        "ai_diagnosis": "Urinary Tract Infection",
        "symptoms_text": "burning urination, frequent urge to urinate, lower abdominal pain, cloudy urine",
        "ai_severity": "mild",
        "ai_urgency": "soon",
        "ai_confidence": 0.90,
        "ai_reasoning": "Dysuria, frequency, and suprapubic pain are classic for uncomplicated UTI.",
        "ai_findings": ["Dysuria", "Urinary frequency", "Suprapubic tenderness"],
        "ai_medications": [
            {"name": "Nitrofurantoin", "dosage": "100mg", "frequency": "Twice daily", "duration": "5 days"},
        ],
        "ai_lifestyle": ["Drink plenty of water", "Cranberry juice may help", "Urinate after intercourse"],
        "ai_precautions": ["Complete the full course of antibiotics", "Avoid irritants like caffeine"],
        "ai_when_to_see_doctor": "If fever develops or symptoms worsen after 48 hours.",
    },
    {
        "ai_diagnosis": "Asthma",
        "symptoms_text": "wheezing, shortness of breath, chest tightness, cough worse at night",
        "ai_severity": "moderate",
        "ai_urgency": "soon",
        "ai_confidence": 0.86,
        "ai_reasoning": "Episodic wheezing with nocturnal cough and chest tightness suggest bronchial asthma.",
        "ai_findings": ["Expiratory wheezing", "Reduced peak flow", "Nocturnal symptoms"],
        "ai_medications": [
            {"name": "Salbutamol Inhaler", "dosage": "2 puffs", "frequency": "As needed for relief", "duration": "Ongoing"},
            {"name": "Budesonide Inhaler", "dosage": "200mcg", "frequency": "Twice daily", "duration": "Ongoing"},
        ],
        "ai_lifestyle": ["Avoid dust and smoke", "Use air purifier indoors", "Regular breathing exercises"],
        "ai_precautions": ["Always carry rescue inhaler", "Avoid known allergens"],
        "ai_when_to_see_doctor": "If rescue inhaler needed more than 3 times per week.",
    },
    {
        "ai_diagnosis": "Lower Back Pain",
        "symptoms_text": "persistent lower back ache, stiffness in morning, pain radiating to legs",
        "ai_severity": "mild",
        "ai_urgency": "routine",
        "ai_confidence": 0.80,
        "ai_reasoning": "Mechanical lower back pain with morning stiffness, likely musculoskeletal origin.",
        "ai_findings": ["Lumbar tenderness", "Reduced range of motion", "Paravertebral muscle spasm"],
        "ai_medications": [
            {"name": "Diclofenac", "dosage": "50mg", "frequency": "Twice daily after food", "duration": "7 days"},
            {"name": "Thiocolchicoside", "dosage": "4mg", "frequency": "Twice daily", "duration": "5 days"},
        ],
        "ai_lifestyle": ["Correct posture while sitting", "Core strengthening exercises", "Hot fomentation"],
        "ai_precautions": ["Avoid heavy lifting", "Use ergonomic chair"],
        "ai_when_to_see_doctor": "If numbness in legs or loss of bladder control occurs.",
    },
    {
        "ai_diagnosis": "Anxiety Disorder",
        "symptoms_text": "restlessness, racing thoughts, difficulty sleeping, palpitations, sweating",
        "ai_severity": "moderate",
        "ai_urgency": "soon",
        "ai_confidence": 0.78,
        "ai_reasoning": "Persistent anxiety with autonomic symptoms and insomnia suggests generalized anxiety disorder.",
        "ai_findings": ["Psychomotor agitation", "Tachycardia", "Sleep disturbance", "Excessive worry"],
        "ai_medications": [
            {"name": "Escitalopram", "dosage": "10mg", "frequency": "Once daily", "duration": "Ongoing"},
        ],
        "ai_lifestyle": ["Mindfulness meditation", "Regular exercise", "Limit caffeine", "Journaling"],
        "ai_precautions": ["Don't stop medication abruptly", "Avoid alcohol"],
        "ai_when_to_see_doctor": "If panic attacks occur or suicidal thoughts emerge.",
    },
    {
        "ai_diagnosis": "Conjunctivitis",
        "symptoms_text": "red eyes, itching, watery discharge, swollen eyelids",
        "ai_severity": "mild",
        "ai_urgency": "routine",
        "ai_confidence": 0.92,
        "ai_reasoning": "Bilateral red eyes with watery discharge and itching suggest allergic conjunctivitis.",
        "ai_findings": ["Conjunctival injection", "Chemosis", "Watery discharge"],
        "ai_medications": [
            {"name": "Olopatadine Eye Drops", "dosage": "1 drop", "frequency": "Twice daily", "duration": "7 days"},
        ],
        "ai_lifestyle": ["Cold compresses on eyes", "Avoid rubbing eyes", "Wear sunglasses outdoors"],
        "ai_precautions": ["Don't share towels", "Wash hands frequently"],
        "ai_when_to_see_doctor": "If vision changes or pain increases.",
    },
]

SYMPTOM_NAMES = [
    "Headache", "Fatigue", "Cough", "Fever", "Nausea", "Back Pain",
    "Joint Pain", "Dizziness", "Chest Tightness", "Insomnia",
    "Stomach Pain", "Shortness of Breath", "Sore Throat", "Muscle Ache",
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            __import__("sqlalchemy").select(User).where(User.email == "admin@meddiagnose.com")
        )).scalar_one_or_none()

        if existing:
            print("Seed data already exists. Skipping.")
            return

        created_users: list[User] = []
        for u in USERS:
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                gender=u.get("gender"),
                date_of_birth=u.get("date_of_birth"),
                blood_group=u.get("blood_group"),
                allergies=u.get("allergies"),
                phone=u.get("phone"),
                weight_kg=u.get("weight_kg"),
                is_active=True,
            )
            db.add(user)
            created_users.append(user)

        await db.flush()
        print(f"Created {len(created_users)} users")

        patient_users = [u for u in created_users if u.role == "patient"]

        # Create matching Patient records for FK requirement
        patient_records: dict[int, Patient] = {}
        for pu in patient_users:
            names = pu.full_name.split(" ", 1)
            pat = Patient(
                first_name=names[0],
                last_name=names[1] if len(names) > 1 else "",
                gender=pu.gender,
                contact_email=pu.email,
                contact_phone=pu.phone,
                created_by=pu.id,
            )
            db.add(pat)
            patient_records[pu.id] = pat

        await db.flush()
        print(f"Created {len(patient_records)} patient records")

        now = datetime.now(timezone.utc)
        diag_count = 0
        for pu in patient_users:
            pat = patient_records[pu.id]
            num_diagnoses = random.randint(2, 5)
            chosen = random.sample(SAMPLE_DIAGNOSES, min(num_diagnoses, len(SAMPLE_DIAGNOSES)))
            for i, diag_data in enumerate(chosen):
                days_ago = random.randint(1, 60)
                created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                diagnosis = Diagnosis(
                    patient_id=pat.id,
                    status="completed",
                    symptoms_text=diag_data["symptoms_text"],
                    ai_diagnosis=diag_data["ai_diagnosis"],
                    ai_reasoning=diag_data["ai_reasoning"],
                    ai_confidence=diag_data["ai_confidence"] + random.uniform(-0.05, 0.05),
                    ai_model_version="medgemma-mock-v1",
                    ai_findings=diag_data.get("ai_findings"),
                    ai_medications=diag_data.get("ai_medications"),
                    ai_lifestyle=diag_data.get("ai_lifestyle"),
                    ai_precautions=diag_data.get("ai_precautions"),
                    ai_severity=diag_data["ai_severity"],
                    ai_urgency=diag_data["ai_urgency"],
                    ai_when_to_see_doctor=diag_data.get("ai_when_to_see_doctor"),
                    ai_raw_response=diag_data,
                    reviewed_by=pu.id,
                    priority="normal",
                    created_at=created_at,
                )
                db.add(diagnosis)
                diag_count += 1

        print(f"Created {diag_count} diagnoses")

        sym_count = 0
        for patient in patient_users:
            for _ in range(random.randint(5, 15)):
                days_ago = random.randint(0, 30)
                ts = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                log = SymptomLog(
                    user_id=patient.id,
                    symptom=random.choice(SYMPTOM_NAMES),
                    severity=random.randint(1, 10),
                    notes=random.choice(["Mild today", "Getting worse", "About the same", "Slightly better", ""]),
                    logged_at=ts,
                    created_at=ts,
                )
                db.add(log)
                sym_count += 1

        print(f"Created {sym_count} symptom logs")

        chat_count = 0
        for patient in patient_users:
            for _ in range(random.randint(2, 8)):
                days_ago = random.randint(0, 30)
                ts = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                q = ChatMessage(
                    user_id=patient.id,
                    role="user",
                    content=random.choice([
                        "What does my diagnosis mean?",
                        "Can I take ibuprofen with my current medication?",
                        "How long will recovery take?",
                        "Are there any side effects?",
                        "Should I get blood tests?",
                        "Is this condition hereditary?",
                    ]),
                    created_at=ts,
                )
                a = ChatMessage(
                    user_id=patient.id,
                    role="assistant",
                    content="Based on your medical history and current diagnosis, I'd recommend discussing this with your doctor for personalized advice.",
                    created_at=ts + timedelta(seconds=2),
                )
                db.add(q)
                db.add(a)
                chat_count += 2

        print(f"Created {chat_count} chat messages")

        # Sample insurance for patient1 (Ananya Gupta)
        p1 = next((u for u in patient_users if u.email == "patient1@gmail.com"), None)
        if p1:
            pol = InsurancePolicy(
                user_id=p1.id,
                provider_type="government",
                provider_name="Ayushman Bharat PM-JAY",
                policy_number="PMJAY" + secrets.token_hex(4).upper(),
                member_id="BEN" + str(p1.id).zfill(6),
                sum_insured=500000.0,
                valid_from=date.today() - timedelta(days=365),
                valid_until=date.today() + timedelta(days=365),
                is_primary=True,
                scheme_name="PM-JAY",
                is_active=True,
            )
            db.add(pol)
            await db.flush()
            bill = InsuranceBill(
                user_id=p1.id,
                policy_id=pol.id,
                bill_date=date.today() - timedelta(days=14),
                hospital_name="City General Hospital",
                treatment_description="Fever and blood tests",
                amount_total=8500.0,
            )
            db.add(bill)
            await db.flush()
            claim = InsuranceClaim(
                user_id=p1.id,
                policy_id=pol.id,
                bill_id=bill.id,
                claim_type="reimbursement",
                status="submitted",
                reference_number="MD-" + secrets.token_hex(4).upper(),
                amount_claimed=8500.0,
                submitted_at=now - timedelta(days=10),
            )
            db.add(claim)
            print("Created sample insurance (policy, bill, claim) for patient1")

        await db.commit()
        print("\nSeed complete!")
        print("\n--- Login Credentials ---")
        print(f"{'Role':<10} {'Email':<30} {'Password'}")
        print("-" * 60)
        for u in USERS:
            if u["role"] != "patient" or u["email"] in ("patient1@gmail.com",):
                print(f"{u['role']:<10} {u['email']:<30} {u['password']}")
        print(f"{'patient':<10} {'patient1@gmail.com - patient7@gmail.com':<30}")
        print(f"{'':10} All patient passwords: Patient@123")


if __name__ == "__main__":
    asyncio.run(seed())
