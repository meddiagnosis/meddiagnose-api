from datetime import datetime
from pydantic import BaseModel


class HealthAlertResponse(BaseModel):
    id: int
    user_id: int
    metric: str
    metric_label: str | None
    value: float
    unit: str | None
    normal_min: float | None
    normal_max: float | None
    severity: str
    status: str
    message: str | None
    source_type: str | None
    source_id: int | None
    acknowledged_at: datetime | None
    acknowledged_by: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthAlertList(BaseModel):
    items: list[HealthAlertResponse]
    total: int
    unread_count: int
