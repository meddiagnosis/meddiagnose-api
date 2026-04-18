"""
Insurance API: policies, bills, claims for government and private insurance.
Includes NHCX callback endpoint for real-time claim responses from insurers.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.insurance import InsurancePolicy, InsuranceBill, InsuranceClaim
from app.schemas.insurance import (
    InsurancePolicyCreate,
    InsurancePolicyResponse,
    InsuranceBillCreate,
    InsuranceBillResponse,
    InsuranceClaimCreate,
    InsuranceClaimResponse,
    InsuranceClaimSubmitResponse,
    InsuranceProviderInfo,
    INSURANCE_PROVIDERS,
)
from app.services.insurance_service import submit_claim_to_provider

router = APIRouter(prefix="/insurance", tags=["Insurance"])


# ─── Providers (for UI dropdown) ───
@router.get("/providers", response_model=list[InsuranceProviderInfo])
async def list_providers():
    """List supported government and private insurance providers."""
    return INSURANCE_PROVIDERS


# ─── Policies ───
@router.get("/policies", response_model=list[InsurancePolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(InsurancePolicy).where(
        InsurancePolicy.user_id == current_user.id,
        InsurancePolicy.is_active == True,
    ).order_by(InsurancePolicy.is_primary.desc(), InsurancePolicy.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/policies", response_model=InsurancePolicyResponse, status_code=201)
async def create_policy(
    body: InsurancePolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = InsurancePolicy(user_id=current_user.id, **body.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/policies/{policy_id}", response_model=InsurancePolicyResponse)
async def get_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(InsurancePolicy).where(
        InsurancePolicy.id == policy_id,
        InsurancePolicy.user_id == current_user.id,
    )
    policy = (await db.execute(q)).scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    return policy


@router.delete("/policies/{policy_id}", status_code=204)
async def deactivate_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(InsurancePolicy).where(
        InsurancePolicy.id == policy_id,
        InsurancePolicy.user_id == current_user.id,
    )
    policy = (await db.execute(q)).scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    policy.is_active = False
    await db.commit()


# ─── Bills ───
@router.get("/bills", response_model=list[InsuranceBillResponse])
async def list_bills(
    policy_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(InsuranceBill).where(InsuranceBill.user_id == current_user.id)
    if policy_id:
        q = q.where(InsuranceBill.policy_id == policy_id)
    q = q.order_by(InsuranceBill.bill_date.desc(), InsuranceBill.created_at.desc())
    result = await db.execute(q)
    bills = list(result.scalars().all())
    out = []
    for b in bills:
        r = InsuranceBillResponse.model_validate(b)
        claim_q = select(InsuranceClaim.id).where(InsuranceClaim.bill_id == b.id)
        claim_ids = [row[0] for row in (await db.execute(claim_q)).all()]
        r.claim_ids = claim_ids
        out.append(r)
    return out


@router.post("/bills", response_model=InsuranceBillResponse, status_code=201)
async def create_bill(
    body: InsuranceBillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.policy_id:
        q = select(InsurancePolicy).where(
            InsurancePolicy.id == body.policy_id,
            InsurancePolicy.user_id == current_user.id,
        )
        if not (await db.execute(q)).scalar_one_or_none():
            raise HTTPException(404, "Policy not found")
    bill = InsuranceBill(user_id=current_user.id, **body.model_dump())
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    return InsuranceBillResponse(
        id=bill.id,
        policy_id=bill.policy_id,
        bill_date=bill.bill_date,
        hospital_name=bill.hospital_name,
        hospital_address=bill.hospital_address,
        treatment_description=bill.treatment_description,
        amount_total=bill.amount_total,
        created_at=bill.created_at,
        claim_ids=[],
    )


# ─── Claims ───
@router.get("/claims", response_model=list[InsuranceClaimResponse])
async def list_claims(
    policy_id: int | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(InsuranceClaim).where(InsuranceClaim.user_id == current_user.id)
    if policy_id:
        q = q.where(InsuranceClaim.policy_id == policy_id)
    if status:
        q = q.where(InsuranceClaim.status == status)
    q = q.order_by(InsuranceClaim.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/claims", response_model=InsuranceClaimResponse, status_code=201)
async def create_claim(
    body: InsuranceClaimCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = (await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.id == body.policy_id,
            InsurancePolicy.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    bill = (await db.execute(
        select(InsuranceBill).where(
            InsuranceBill.id == body.bill_id,
            InsuranceBill.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not bill:
        raise HTTPException(404, "Bill not found")
    claim = InsuranceClaim(
        user_id=current_user.id,
        policy_id=body.policy_id,
        bill_id=body.bill_id,
        claim_type=body.claim_type,
        amount_claimed=bill.amount_total,
        status="draft",
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


@router.get("/policies/{policy_id}/eligibility")
async def check_eligibility(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check coverage eligibility with insurer (real when ABDM configured)."""
    from app.services.nhcx_client import get_nhcx_client

    policy = (await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.id == policy_id,
            InsurancePolicy.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    client = get_nhcx_client()
    result = await client.check_eligibility(
        policy_number=policy.policy_number,
        member_id=policy.member_id or policy.policy_number,
    )
    return {"eligible": result.eligible, "success": result.success, "details": result.coverage_details, "error": result.error_message}


@router.post("/claims/{claim_id}/submit", response_model=InsuranceClaimSubmitResponse)
async def submit_claim(
    claim_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claim = (await db.execute(
        select(InsuranceClaim).where(
            InsuranceClaim.id == claim_id,
            InsuranceClaim.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.status != "draft":
        raise HTTPException(400, f"Claim already {claim.status}")

    policy = (await db.execute(select(InsurancePolicy).where(InsurancePolicy.id == claim.policy_id))).scalar_one_or_none()
    bill = (await db.execute(select(InsuranceBill).where(InsuranceBill.id == claim.bill_id))).scalar_one_or_none()
    if not policy or not bill:
        raise HTTPException(404, "Policy or bill not found")

    status, ref, rejection_reason = await submit_claim_to_provider(db, claim, policy, bill)
    claim.status = status
    claim.reference_number = ref
    if rejection_reason:
        claim.rejection_reason = rejection_reason
    claim.submitted_at = datetime.now(timezone.utc)
    await db.commit()

    return InsuranceClaimSubmitResponse(
        claim_id=claim.id,
        status=status,
        reference_number=ref,
        message=f"Claim submitted successfully. Reference: {ref}" if status == "submitted" else (rejection_reason or f"Claim {status}"),
    )


# ─── NHCX callback (for real-time responses from insurers) ───
@router.post("/hcx/callback")
async def nhcx_callback(request: Request):
    """
    Webhook for NHCX claim/eligibility responses. HCX calls this when payor responds.
    Configure NHCX_CALLBACK_URL during NHCX registration: https://yourdomain.com/api/v1/insurance/hcx/callback
    Payload is JWE-encrypted; full implementation requires decryption with our private key.
    """
    try:
        body = await request.json()
        logger.info("NHCX callback received: keys=%s", list(body.keys()) if isinstance(body, dict) else "non-dict")
        # TODO: Decrypt JWE, extract ClaimResponse, update claim status in DB
        return {"status": "received"}
    except Exception as e:
        logger.warning("NHCX callback error: %s", e)
        return {"status": "error", "message": str(e)[:200]}
