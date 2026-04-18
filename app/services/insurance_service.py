"""
Insurance service for claim submission and provider integration.

Connected to: Star Health, HDFC Ergo, Max Bupa, Axis Health, and government schemes
(PM-JAY, CGHS, ESIC) via ABDM NHCX.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance import InsuranceClaim, InsurancePolicy, InsuranceBill
from app.services.insurance_providers import get_adapter_for_policy

logger = logging.getLogger(__name__)


async def submit_claim_to_provider(
    db: AsyncSession,
    claim: InsuranceClaim,
    policy: InsurancePolicy,
    bill: InsuranceBill,
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Submit claim to insurance provider. Routes to Star Health, HDFC Ergo,
    Max Bupa, Axis, or government (ABDM NHCX) adapter.
    Returns (status, reference_number, rejection_reason).
    """
    adapter = get_adapter_for_policy(policy)
    result = await adapter.submit_claim(claim, policy, bill)
    return result.status, result.reference_number, result.message


async def fetch_claims_from_provider(
    db: AsyncSession,
    user_id: int,
    policy: InsurancePolicy,
) -> list[dict]:
    """
    Fetch claim status from provider. Returns list of claim status updates.
    Real integration: Poll insurer API or ABDM HCX.
    """
    # Mock: Return empty - in production would fetch from insurer
    return []
