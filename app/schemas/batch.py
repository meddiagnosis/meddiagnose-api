from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BatchCreate(BaseModel):
    name: str


class BatchResponse(BaseModel):
    id: int
    name: str
    status: str
    total_patients: int
    processed_count: int
    failed_count: int
    flagged_count: int
    source_file: Optional[str] = None
    error_log: Optional[str] = None
    airflow_dag_run_id: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchList(BaseModel):
    items: list[BatchResponse]
    total: int
    page: int
    per_page: int


class BatchItemResponse(BaseModel):
    id: int
    batch_id: int
    patient_id: Optional[int] = None
    diagnosis_id: Optional[int] = None
    row_number: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
