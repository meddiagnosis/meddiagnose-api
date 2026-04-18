from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FitnessLog(Base):
    __tablename__ = "fitness_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories_burned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    water_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5

    workout_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    workout_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workout_intensity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # light/moderate/intense

    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Live vitals from wearables (Fitbit, Apple Watch, etc.)
    heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # bpm, resting or avg
    spo2: Mapped[float | None] = mapped_column(Float, nullable=True)  # blood oxygen %

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<FitnessLog {self.id} user={self.user_id} date={self.log_date}>"


class FitnessGoal(Base):
    __tablename__ = "fitness_goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    daily_steps: Mapped[int | None] = mapped_column(Integer, nullable=True, default=10000)
    daily_calories: Mapped[int | None] = mapped_column(Integer, nullable=True, default=500)
    daily_active_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=30)
    daily_water_ml: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2500)
    daily_sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True, default=7.5)
    weekly_workouts: Mapped[int | None] = mapped_column(Integer, nullable=True, default=4)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<FitnessGoal {self.id} user={self.user_id}>"
