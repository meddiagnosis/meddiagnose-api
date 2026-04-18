from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class PatientCreate(BaseModel):
    external_id: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    clinical_notes: Optional[str] = None
    symptoms: Optional[list[str]] = None
    medical_history: Optional[dict] = None
    medications: Optional[list[str]] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    clinical_notes: Optional[str] = None
    symptoms: Optional[list[str]] = None
    medical_history: Optional[dict] = None
    medications: Optional[list[str]] = None


class PatientResponse(BaseModel):
    id: int
    external_id: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    clinical_notes: Optional[str] = None
    symptoms: Optional[list[str]] = None
    medical_history: Optional[dict] = None
    medications: Optional[list[str]] = None
    media_files: Optional[list] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientList(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    per_page: int
