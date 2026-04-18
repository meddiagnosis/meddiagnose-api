from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SymptomLogCreate(BaseModel):
    symptom: str
    severity: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None
    logged_at: Optional[datetime] = None


class SymptomLogResponse(BaseModel):
    id: int
    user_id: int
    symptom: str
    severity: int
    notes: Optional[str] = None
    logged_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SymptomLogList(BaseModel):
    items: list[SymptomLogResponse]
    total: int
