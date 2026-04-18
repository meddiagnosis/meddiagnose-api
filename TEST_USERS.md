# Test Users for Live Case Testing

Run the seed script to create dummy users:

```bash
cd backend && source venv/bin/activate && python seed_data.py
```

**Ensure PostgreSQL is running** before running the seed.

---

## Login Credentials

| Role   | Email                  | Password   | Profile |
|--------|------------------------|------------|---------|
| Admin  | admin@meddiagnose.com  | Admin@123  | Rahul Sharma |
| Doctor | doctor@meddiagnose.com | Doctor@123 | Dr. Priya Mehta |
| Doctor | doctor2@meddiagnose.com | Doctor@123 | Dr. Arjun Patel |
| Patient | patient1@gmail.com    | Patient@123 | Ananya Gupta — **Penicillin, Sulfa drugs** allergy |
| Patient | patient2@gmail.com    | Patient@123 | Vikram Singh — **Aspirin** allergy |
| Patient | patient3@gmail.com    | Patient@123 | Meera Krishnan — No allergies |
| Patient | patient4@gmail.com    | Patient@123 | Rohan Desai — **Ibuprofen** allergy |
| Patient | patient5@gmail.com    | Patient@123 | Sanya Joshi — No allergies |
| Patient | patient6@gmail.com    | Patient@123 | Kabir Malhotra — **Codeine, Morphine** allergy |
| Patient | patient7@gmail.com    | Patient@123 | Nisha Reddy — No allergies |

---

## Live Testing Flow

1. **Login** as any patient (e.g. `patient1@gmail.com` / `Patient@123`)
2. Go to **New Diagnosis**
3. Enter symptoms (e.g. "fever, sore throat, cough for 3 days")
4. **Upload** lab reports, X-rays, or skin photos (PDF, JPG, PNG, DICOM)
5. Click **Get AI Diagnosis**
6. Review diagnosis, medications, and extracted lab values
7. **Allergy check**: Patient1 is allergic to Penicillin — verify AI avoids it

---

## Patient Profiles (for medication testing)

| Patient | Allergies | Blood Group | Weight | Use Case |
|---------|-----------|-------------|--------|----------|
| patient1 | Penicillin, Sulfa | O+ | 55 kg | Test allergy avoidance |
| patient2 | Aspirin | A- | 75 kg | Test NSAID avoidance |
| patient4 | Ibuprofen | AB+ | 88 kg | Test painkiller alternatives |
| patient6 | Codeine, Morphine | A+ | 95 kg | Test opioid avoidance |
