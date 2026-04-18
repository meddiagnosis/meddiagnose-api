from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DiagnosisCreate(BaseModel):
    symptoms: str
    clinical_notes: Optional[str] = None
    report_files: Optional[list[str]] = None
    priority: str = "normal"


class DiagnosisReview(BaseModel):
    status: str
    final_diagnosis: Optional[str] = None
    reviewer_notes: Optional[str] = None


class DiagnosisResponse(BaseModel):
    id: int
    patient_id: Optional[int] = None
    batch_id: Optional[int] = None
    status: str
    ai_diagnosis: Optional[str] = None
    ai_layman_summary: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_model_version: Optional[str] = None
    ai_findings: Optional[list] = None
    ai_medications: Optional[list] = None
    ai_lifestyle: Optional[list] = None
    ai_precautions: Optional[list] = None
    ai_severity: Optional[str] = None
    ai_urgency: Optional[str] = None
    ai_when_to_see_doctor: Optional[str] = None
    ai_recommended_tests: Optional[list] = None
    ai_differential_diagnoses: Optional[list] = None
    ai_drug_interactions: Optional[list] = None
    ai_allergy_warnings: Optional[list] = None
    ai_high_risk_drug_warnings: Optional[list] = None
    ai_organ_warnings: Optional[list] = None
    ai_critical_warnings: Optional[list] = None
    ai_dietary_plan: Optional[list] = None
    ai_routine_plan: Optional[list] = None
    ai_ayurvedic_medicines: Optional[list] = None
    ai_extracted_lab_values: Optional[list] = None
    report_files: Optional[list] = None
    symptoms_text: Optional[str] = None
    final_diagnosis: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    specialty: Optional[str] = None
    priority: str = "normal"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiagnosisList(BaseModel):
    items: list[DiagnosisResponse]
    total: int
    page: int
    per_page: int


class MedicationLookupRequest(BaseModel):
    medications: list[str]
    symptoms: Optional[str] = None
    temperature_f: Optional[float] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    spo2: Optional[int] = None
    blood_sugar: Optional[int] = None
    respiratory_rate: Optional[int] = None


class MedicationDiseaseMatch(BaseModel):
    disease: str
    matched_medications: list[str]
    total_disease_medications: int
    severity: str
    urgency: str
    confidence: float
    reasoning: str
    recommended_tests: list[str]
    when_to_see_doctor: str
    all_medications: list[dict]
    lifestyle_recommendations: list[str]
    precautions: list[str]


class MedicationLookupResponse(BaseModel):
    matches: list[MedicationDiseaseMatch]
    medications_searched: list[str]
    total_matches: int


class PharmacySearchRequest(BaseModel):
    medications: list[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 50.0


class PharmacyResult(BaseModel):
    id: int
    name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    phone: str
    hours: str
    is_24hr: bool
    distance_km: Optional[float] = None
    available_medications: list[str]
    unavailable_medications: list[str]
    availability_ratio: float
    photo_url: str = ""


class PharmacySearchResponse(BaseModel):
    pharmacies: list[PharmacyResult]
    medications_searched: list[str]
    total_results: int
    is_nationwide_fallback: bool = False
