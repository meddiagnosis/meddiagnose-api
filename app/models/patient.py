from datetime import datetime, date
from sqlalchemy import String, Text, Date, DateTime, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    medical_history: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    medications: Mapped[list | None] = mapped_column(JSON, nullable=True)

    media_files: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="patient", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Patient {self.first_name} {self.last_name}>"


from app.models.diagnosis import Diagnosis  # noqa: E402
