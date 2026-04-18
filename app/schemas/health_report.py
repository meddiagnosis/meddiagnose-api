from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class HealthReportCreate(BaseModel):
    report_date: date
    title: Optional[str] = None
    notes: Optional[str] = None

    systolic_bp: Optional[float] = Field(None, ge=50, le=300)
    diastolic_bp: Optional[float] = Field(None, ge=30, le=200)
    heart_rate: Optional[float] = Field(None, ge=30, le=250)
    spo2: Optional[float] = Field(None, ge=50, le=100)
    temperature: Optional[float] = Field(None, ge=90, le=110)
    weight: Optional[float] = Field(None, ge=1, le=500)

    fasting_blood_sugar: Optional[float] = Field(None, ge=20, le=600)
    post_prandial_blood_sugar: Optional[float] = Field(None, ge=20, le=600)
    hba1c: Optional[float] = Field(None, ge=3, le=20)

    total_cholesterol: Optional[float] = Field(None, ge=50, le=500)
    hdl_cholesterol: Optional[float] = Field(None, ge=10, le=150)
    ldl_cholesterol: Optional[float] = Field(None, ge=20, le=400)
    triglycerides: Optional[float] = Field(None, ge=20, le=1000)

    hemoglobin: Optional[float] = Field(None, ge=3, le=25)

    serum_creatinine: Optional[float] = Field(None, ge=0.1, le=20)
    tsh: Optional[float] = Field(None, ge=0.01, le=100)
    vitamin_d: Optional[float] = Field(None, ge=1, le=200)
    uric_acid: Optional[float] = Field(None, ge=1, le=20)


class HealthReportResponse(BaseModel):
    id: int
    user_id: int
    report_date: date
    title: Optional[str] = None
    notes: Optional[str] = None

    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    weight: Optional[float] = None

    fasting_blood_sugar: Optional[float] = None
    post_prandial_blood_sugar: Optional[float] = None
    hba1c: Optional[float] = None

    total_cholesterol: Optional[float] = None
    hdl_cholesterol: Optional[float] = None
    ldl_cholesterol: Optional[float] = None
    triglycerides: Optional[float] = None

    hemoglobin: Optional[float] = None

    serum_creatinine: Optional[float] = None
    tsh: Optional[float] = None
    vitamin_d: Optional[float] = None
    uric_acid: Optional[float] = None

    created_at: datetime

    model_config = {"from_attributes": True}


class MetricChange(BaseModel):
    metric: str
    label: str
    unit: str
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    change: Optional[float] = None
    percent_change: Optional[float] = None
    status: str  # "improved", "worsened", "stable", "new", "removed"
    old_status: Optional[str] = None  # "normal", "borderline", "high", "low"
    new_status: Optional[str] = None


class HealthReportComparison(BaseModel):
    older_report: HealthReportResponse
    newer_report: HealthReportResponse
    changes: list[MetricChange]
    summary: str
    improved_count: int
    worsened_count: int
    stable_count: int


class TrendDataPoint(BaseModel):
    date: str
    value: float


class MetricTrend(BaseModel):
    metric: str
    label: str
    unit: str
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    data: list[TrendDataPoint]


class HealthReportTrends(BaseModel):
    trends: list[MetricTrend]
    report_count: int


class HealthReportList(BaseModel):
    items: list[HealthReportResponse]
    total: int
