"""Health alert model for automated vitals monitoring."""

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class HealthAlert(Base):
    __tablename__ = "health_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    metric: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    metric_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    normal_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")  # critical, warning, info
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, acknowledged, resolved
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # fitness_log, health_report, wearable
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<HealthAlert {self.id} user={self.user_id} {self.metric}={self.value} {self.severity}>"
