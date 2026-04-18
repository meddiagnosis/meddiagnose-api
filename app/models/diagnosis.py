import enum
from datetime import datetime
from sqlalchemy import String, Text, Float, DateTime, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DiagnosisStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patients.id"), nullable=True, index=True)
    batch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("batches.id"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)

    ai_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_layman_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # Plain-language for patients
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_medications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_lifestyle: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_precautions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_when_to_see_doctor: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_recommended_tests: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_differential_diagnoses: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_drug_interactions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_allergy_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_high_risk_drug_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_organ_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_critical_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_dietary_plan: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_routine_plan: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_ayurvedic_medicines: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_extracted_lab_values: Mapped[list | None] = mapped_column(JSON, nullable=True)

    report_files: Mapped[list | None] = mapped_column(JSON, nullable=True)
    symptoms_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    final_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="diagnoses", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Diagnosis {self.id} [{self.status.value}] confidence={self.ai_confidence}>"


from app.models.patient import Patient  # noqa: E402
