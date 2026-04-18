"""
Insurance provider adapters for Star Health, HDFC Ergo, Max Bupa, Axis, and government schemes.

Real connection via ABDM NHCX when ABDM_CLIENT_ID and ABDM_CLIENT_SECRET are set.
Register at https://sbxhcx.abdm.gov.in
"""

import logging
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from app.models.insurance import InsuranceClaim, InsurancePolicy, InsuranceBill
from app.services.nhcx_client import get_nhcx_client, NHCXClaimResult

logger = logging.getLogger(__name__)


@dataclass
class ClaimSubmitResult:
    status: str  # submitted, approved, rejected
    reference_number: Optional[str] = None
    message: Optional[str] = None


class InsuranceProviderAdapter(ABC):
    """Base adapter for insurance provider integration."""

    @abstractmethod
    def can_handle(self, policy: InsurancePolicy) -> bool:
        """Return True if this adapter handles the given policy."""
        pass

    @abstractmethod
    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        """Submit claim to provider. Returns result with status and reference."""
        pass


class ABDMGovernmentAdapter(InsuranceProviderAdapter):
    """Government schemes via ABDM NHCX (PM-JAY, CGHS, ESIC)."""

    GOV_PROVIDERS = ("pm-jay", "ayushman", "pmjay", "cghs", "esic")

    def can_handle(self, policy: InsurancePolicy) -> bool:
        if policy.provider_type != "government":
            return False
        name = policy.provider_name.lower()
        return any(p in name for p in self.GOV_PROVIDERS)

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        client = get_nhcx_client()
        if client.is_configured():
            result = await client.submit_claim(
                policy_number=policy.policy_number,
                member_id=policy.member_id or policy.policy_number,
                bill_amount=bill.amount_total,
                hospital_name=bill.hospital_name,
                treatment=bill.treatment_description or "Medical treatment",
                claim_type=claim.claim_type,
            )
            if result.success:
                return ClaimSubmitResult(status="submitted", reference_number=result.reference_number)
            return ClaimSubmitResult(status="rejected", reference_number=result.reference_number, message=result.error_message)
        ref = f"NHCX-{secrets.token_hex(4).upper()}"
        logger.info("ABDM government claim (mock): %s for %s", ref, policy.provider_name)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


class LICAdapter(InsuranceProviderAdapter):
    """LIC India - Jeevan Arogya and other health plans. Majority of Indians use LIC."""

    def can_handle(self, policy: InsurancePolicy) -> bool:
        name = policy.provider_name.lower()
        return "lic" in name or "jeevan arogya" in name or "life insurance corporation" in name

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        # LIC may join NHCX; use NHCX when configured
        client = get_nhcx_client()
        if client.is_configured():
            result = await client.submit_claim(
                policy_number=policy.policy_number,
                member_id=policy.member_id or policy.policy_number,
                bill_amount=bill.amount_total,
                hospital_name=bill.hospital_name,
                treatment=bill.treatment_description or "Medical treatment",
                claim_type=claim.claim_type,
            )
            if result.success:
                return ClaimSubmitResult(status="submitted", reference_number=result.reference_number)
            return ClaimSubmitResult(status="rejected", reference_number=result.reference_number, message=result.error_message)
        ref = f"LIC-{secrets.token_hex(4).upper()}"
        logger.info("LIC claim (mock): %s", ref)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


class StarHealthAdapter(InsuranceProviderAdapter):
    """Star Health and Allied Insurance. NHCX participant."""

    def can_handle(self, policy: InsurancePolicy) -> bool:
        name = policy.provider_name.lower()
        return "star health" in name or "starhealth" in name

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        settings = get_settings()
        if settings.STAR_HEALTH_API_URL and settings.STAR_HEALTH_API_KEY:
            # TODO: Call Star Health partner API when available
            ref = f"STAR-{secrets.token_hex(4).upper()}"
            logger.info("Star Health API claim submission: %s", ref)
            return ClaimSubmitResult(status="submitted", reference_number=ref)
        # Star Health is on NHCX - use real NHCX when ABDM configured
        client = get_nhcx_client()
        if client.is_configured():
            result = await client.submit_claim(
                policy_number=policy.policy_number,
                member_id=policy.member_id or policy.policy_number,
                bill_amount=bill.amount_total,
                hospital_name=bill.hospital_name,
                treatment=bill.treatment_description or "Medical treatment",
                claim_type=claim.claim_type,
            )
            if result.success:
                return ClaimSubmitResult(status="submitted", reference_number=result.reference_number)
            return ClaimSubmitResult(status="rejected", reference_number=result.reference_number, message=result.error_message)
        ref = f"STAR-{secrets.token_hex(4).upper()}"
        logger.info("Star Health claim (mock): %s", ref)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


class HDFCErgoAdapter(InsuranceProviderAdapter):
    """HDFC Ergo General Insurance."""

    def can_handle(self, policy: InsurancePolicy) -> bool:
        name = policy.provider_name.lower()
        return "hdfc ergo" in name or "hdfc" in name

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        settings = get_settings()
        ref = f"HDFC-{secrets.token_hex(4).upper()}"

        if settings.HDFC_ERGO_API_URL and settings.HDFC_ERGO_API_KEY:
            # TODO: Call HDFC Ergo partner API
            logger.info("HDFC Ergo API claim submission: %s", ref)
            return ClaimSubmitResult(status="submitted", reference_number=ref)
        logger.info("HDFC Ergo claim (mock): %s", ref)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


class MaxBupaAdapter(InsuranceProviderAdapter):
    """Max Bupa Health Insurance."""

    def can_handle(self, policy: InsurancePolicy) -> bool:
        name = policy.provider_name.lower()
        return "max bupa" in name or "maxbupa" in name

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        settings = get_settings()
        ref = f"MAX-{secrets.token_hex(4).upper()}"

        if settings.MAX_BUPA_API_URL and settings.MAX_BUPA_API_KEY:
            # TODO: Call Max Bupa partner API
            logger.info("Max Bupa API claim submission: %s", ref)
            return ClaimSubmitResult(status="submitted", reference_number=ref)
        logger.info("Max Bupa claim (mock): %s", ref)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


class AxisHealthAdapter(InsuranceProviderAdapter):
    """Axis Health Insurance (partnered with Max Bupa)."""

    def can_handle(self, policy: InsurancePolicy) -> bool:
        name = policy.provider_name.lower()
        return "axis" in name

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        settings = get_settings()
        ref = f"AXIS-{secrets.token_hex(4).upper()}"

        if settings.AXIS_HEALTH_API_URL and settings.AXIS_HEALTH_API_KEY:
            # TODO: Call Axis Health partner API (or Max Bupa if shared)
            logger.info("Axis Health API claim submission: %s", ref)
            return ClaimSubmitResult(status="submitted", reference_number=ref)
        logger.info("Axis Health claim (mock): %s", ref)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


class GenericPrivateAdapter(InsuranceProviderAdapter):
    """Fallback for other private insurers."""

    def can_handle(self, policy: InsurancePolicy) -> bool:
        return policy.provider_type == "private"

    async def submit_claim(
        self,
        claim: InsuranceClaim,
        policy: InsurancePolicy,
        bill: InsuranceBill,
    ) -> ClaimSubmitResult:
        ref = f"MD-{secrets.token_hex(4).upper()}"
        logger.info("Generic private claim (mock): %s for %s", ref, policy.provider_name)
        return ClaimSubmitResult(status="submitted", reference_number=ref)


ADAPTERS: list[InsuranceProviderAdapter] = [
    ABDMGovernmentAdapter(),
    LICAdapter(),
    StarHealthAdapter(),
    HDFCErgoAdapter(),
    MaxBupaAdapter(),
    AxisHealthAdapter(),
    GenericPrivateAdapter(),
]


def get_adapter_for_policy(policy: InsurancePolicy) -> InsuranceProviderAdapter:
    """Return the first adapter that can handle the policy."""
    for adapter in ADAPTERS:
        if adapter.can_handle(policy):
            return adapter
    return GenericPrivateAdapter()
