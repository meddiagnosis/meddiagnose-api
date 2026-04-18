"""
Insurance models for government and private health insurance.

Supports policies, medical bills, and claims for reimbursement/cashless.
"""

from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class InsurancePolicy(Base):
    """Patient's insurance policy (government or private)."""
    __tablename__ = "insurance_policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    provider_type: Mapped[str] = mapped_column(String(30), nullable=False)  # government, private
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)  # PM-JAY, Star Health, etc.
    policy_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Beneficiary/member ID
    group_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    sum_insured: Mapped[float | None] = mapped_column(Float, nullable=True)  # Total coverage in INR
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=True, nullable=False)  # Primary policy for claims

    # For government schemes (PM-JAY, CGHS, etc.)
    scheme_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    abha_number: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Ayushman Bharat Health Account

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    claims: Mapped[list["InsuranceClaim"]] = relationship(back_populates="policy", lazy="selectin")
    bills: Mapped[list["InsuranceBill"]] = relationship(back_populates="policy", lazy="selectin")

    def __repr__(self) -> str:
        return f"<InsurancePolicy {self.provider_name} {self.policy_number}>"


class InsuranceBill(Base):
    """Medical bill for insurance claim."""
    __tablename__ = "insurance_bills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    policy_id: Mapped[int | None] = mapped_column(ForeignKey("insurance_policies.id"), nullable=True, index=True)

    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    hospital_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hospital_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    treatment_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis_id: Mapped[int | None] = mapped_column(ForeignKey("diagnoses.id"), nullable=True)

    amount_total: Mapped[float] = mapped_column(Float, nullable=False)  # Total bill amount INR
    amount_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: room, surgery, meds, etc.
    document_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Uploaded bill PDF path

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    policy: Mapped["InsurancePolicy | None"] = relationship(back_populates="bills")
    claims: Mapped[list["InsuranceClaim"]] = relationship(back_populates="bill", lazy="selectin")

    def __repr__(self) -> str:
        return f"<InsuranceBill {self.hospital_name} {self.amount_total}>"


class InsuranceClaim(Base):
    """Insurance claim for a bill (reimbursement or cashless)."""
    __tablename__ = "insurance_claims"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("insurance_policies.id"), nullable=False, index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("insurance_bills.id"), nullable=False, index=True)

    claim_type: Mapped[str] = mapped_column(String(20), nullable=False)  # reimbursement, cashless
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")  # draft, submitted, approved, rejected, paid
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Insurer's claim ref

    amount_claimed: Mapped[float] = mapped_column(Float, nullable=False)
    amount_approved: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_paid: Mapped[float | None] = mapped_column(Float, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    policy: Mapped["InsurancePolicy"] = relationship(back_populates="claims")
    bill: Mapped["InsuranceBill"] = relationship(back_populates="claims")

    def __repr__(self) -> str:
        return f"<InsuranceClaim {self.id} {self.status} {self.amount_claimed}>"
