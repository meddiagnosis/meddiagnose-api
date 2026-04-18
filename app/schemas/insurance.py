"""Pydantic schemas for insurance API."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─── Policy ───
class InsurancePolicyCreate(BaseModel):
    provider_type: str = Field(..., pattern="^(government|private)$")
    provider_name: str
    policy_number: str
    member_id: Optional[str] = None
    group_id: Optional[str] = None
    sum_insured: Optional[float] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_primary: bool = True
    scheme_name: Optional[str] = None
    abha_number: Optional[str] = None


class InsurancePolicyResponse(BaseModel):
    id: int
    provider_type: str
    provider_name: str
    policy_number: str
    member_id: Optional[str] = None
    sum_insured: Optional[float] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_primary: bool
    scheme_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Bill ───
class InsuranceBillCreate(BaseModel):
    policy_id: Optional[int] = None
    bill_date: date
    hospital_name: str
    hospital_address: Optional[str] = None
    treatment_description: Optional[str] = None
    diagnosis_id: Optional[int] = None
    amount_total: float = Field(..., gt=0)
    amount_breakdown: Optional[str] = None


class InsuranceBillResponse(BaseModel):
    id: int
    policy_id: Optional[int] = None
    bill_date: date
    hospital_name: str
    hospital_address: Optional[str] = None
    treatment_description: Optional[str] = None
    amount_total: float
    created_at: datetime
    claim_ids: list[int] = []

    model_config = {"from_attributes": True}


# ─── Claim ───
class InsuranceClaimCreate(BaseModel):
    policy_id: int
    bill_id: int
    claim_type: str = Field(..., pattern="^(reimbursement|cashless)$")


class InsuranceClaimResponse(BaseModel):
    id: int
    policy_id: int
    bill_id: int
    claim_type: str
    status: str
    reference_number: Optional[str] = None
    amount_claimed: float
    amount_approved: Optional[float] = None
    amount_paid: Optional[float] = None
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InsuranceClaimSubmitResponse(BaseModel):
    claim_id: int
    status: str
    reference_number: Optional[str] = None
    message: str


# ─── Provider list (for UI dropdown) ───
class InsuranceProviderInfo(BaseModel):
    id: str
    name: str
    type: str  # government, private
    description: str


INSURANCE_PROVIDERS: list[InsuranceProviderInfo] = [
    # Government (ABDM NHCX)
    InsuranceProviderInfo(id="pmjay", name="Ayushman Bharat PM-JAY", type="government", description="Government health scheme for eligible families (ABDM NHCX)"),
    InsuranceProviderInfo(id="cghs", name="CGHS", type="government", description="Central Government Health Scheme (ABDM NHCX)"),
    InsuranceProviderInfo(id="esic", name="ESIC", type="government", description="Employees' State Insurance Corporation (ABDM NHCX)"),
    # Private - Connected insurers
    InsuranceProviderInfo(id="lic", name="LIC (Jeevan Arogya)", type="private", description="LIC India - Jeevan Arogya health plan (widely used)"),
    InsuranceProviderInfo(id="star_health", name="Star Health", type="private", description="Star Health and Allied Insurance (NHCX participant)"),
    InsuranceProviderInfo(id="hdfc_ergo", name="HDFC Ergo", type="private", description="HDFC Ergo General Insurance"),
    InsuranceProviderInfo(id="max_bupa", name="Max Bupa", type="private", description="Max Bupa Health Insurance"),
    InsuranceProviderInfo(id="axis_health", name="Axis Health Insurance", type="private", description="Axis Bank health insurance (Max Bupa partnership)"),
    # Other private
    InsuranceProviderInfo(id="icici_lombard", name="ICICI Lombard", type="private", description="ICICI Lombard General Insurance"),
    InsuranceProviderInfo(id="bajaj_allianz", name="Bajaj Allianz", type="private", description="Bajaj Allianz General Insurance"),
    InsuranceProviderInfo(id="oriental", name="Oriental Insurance", type="private", description="The Oriental Insurance Company"),
    InsuranceProviderInfo(id="new_india", name="New India Assurance", type="private", description="The New India Assurance Co."),
    InsuranceProviderInfo(id="other", name="Other", type="private", description="Other insurance provider"),
]
