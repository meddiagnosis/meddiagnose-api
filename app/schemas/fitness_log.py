from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class FitnessLogCreate(BaseModel):
    log_date: date
    steps: Optional[int] = Field(None, ge=0, le=200000)
    calories_burned: Optional[int] = Field(None, ge=0, le=10000)
    active_minutes: Optional[int] = Field(None, ge=0, le=1440)
    distance_km: Optional[float] = Field(None, ge=0, le=200)

    water_ml: Optional[int] = Field(None, ge=0, le=20000)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    sleep_quality: Optional[int] = Field(None, ge=1, le=5)

    workout_type: Optional[str] = Field(None, max_length=100)
    workout_duration_min: Optional[int] = Field(None, ge=0, le=600)
    workout_intensity: Optional[str] = Field(None, pattern=r"^(light|moderate|intense)$")

    weight_kg: Optional[float] = Field(None, ge=10, le=500)
    mood: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class FitnessLogResponse(BaseModel):
    id: int
    user_id: int
    log_date: date
    steps: Optional[int] = None
    calories_burned: Optional[int] = None
    active_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    water_ml: Optional[int] = None
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    workout_type: Optional[str] = None
    workout_duration_min: Optional[int] = None
    workout_intensity: Optional[str] = None
    weight_kg: Optional[float] = None
    mood: Optional[int] = None
    notes: Optional[str] = None
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FitnessLogList(BaseModel):
    items: list[FitnessLogResponse]
    total: int


class FitnessGoalCreate(BaseModel):
    daily_steps: Optional[int] = Field(10000, ge=0, le=100000)
    daily_calories: Optional[int] = Field(500, ge=0, le=10000)
    daily_active_minutes: Optional[int] = Field(30, ge=0, le=600)
    daily_water_ml: Optional[int] = Field(2500, ge=0, le=20000)
    daily_sleep_hours: Optional[float] = Field(7.5, ge=0, le=24)
    weekly_workouts: Optional[int] = Field(4, ge=0, le=14)
    target_weight_kg: Optional[float] = Field(None, ge=10, le=500)


class FitnessGoalResponse(BaseModel):
    id: int
    user_id: int
    daily_steps: Optional[int] = None
    daily_calories: Optional[int] = None
    daily_active_minutes: Optional[int] = None
    daily_water_ml: Optional[int] = None
    daily_sleep_hours: Optional[float] = None
    weekly_workouts: Optional[int] = None
    target_weight_kg: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DailyProgress(BaseModel):
    date: str
    steps: int
    steps_goal: int
    steps_pct: float
    calories: int
    calories_goal: int
    calories_pct: float
    active_minutes: int
    active_minutes_goal: int
    active_minutes_pct: float
    water_ml: int
    water_goal: int
    water_pct: float
    sleep_hours: float
    sleep_goal: float
    sleep_pct: float
    workout_done: bool
    mood: Optional[int] = None
    weight_kg: Optional[float] = None


class WeeklySummary(BaseModel):
    week_start: str
    week_end: str
    total_steps: int
    avg_steps: int
    total_calories: int
    avg_calories: int
    total_active_minutes: int
    avg_active_minutes: int
    total_water_ml: int
    avg_water_ml: int
    avg_sleep_hours: float
    workout_count: int
    workout_goal: int
    workout_pct: float
    days_logged: int
    streak: int
    avg_mood: Optional[float] = None
    weight_trend: list[dict]


class FitnessDashboard(BaseModel):
    today: Optional[DailyProgress] = None
    goals: Optional[FitnessGoalResponse] = None
    weekly: Optional[WeeklySummary] = None
    recent_logs: list[FitnessLogResponse]
    streak: int
    total_logged_days: int
