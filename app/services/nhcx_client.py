"""
ABDM NHCX (National Health Claims Exchange) client for real insurance integration.

When ABDM_CLIENT_ID and ABDM_CLIENT_SECRET are set, makes real API calls to NHCX.
Register at https://sbxhcx.abdm.gov.in to get credentials (typically 3-4 days).

APIs: /claim/submit, /coverageeligibility/check, /preauth/submit
Payload: JWE-encrypted FHIR ClaimRequestBundle per HCX protocol.
"""

import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class NHCXClaimResult:
    success: bool
    status: str  # submitted, error
    reference_number: Optional[str] = None
    correlation_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class NHCXEligibilityResult:
    success: bool
    eligible: bool
    coverage_details: Optional[dict] = None
    error_message: Optional[str] = None


class NHCXClient:
    """Client for ABDM NHCX APIs."""

    def __init__(self):
        self.settings = get_settings()
        self._token: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.settings.ABDM_CLIENT_ID and self.settings.ABDM_CLIENT_SECRET)

    async def _get_token(self) -> Optional[str]:
        """Fetch session token from ABDM gateway."""
        if not self.is_configured():
            return None
        auth_url = self.settings.ABDM_AUTH_URL or f"{self.settings.ABDM_BASE_URL.rstrip('/')}/api/v1/sessions"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    auth_url,
                    json={
                        "clientId": self.settings.ABDM_CLIENT_ID,
                        "clientSecret": self.settings.ABDM_CLIENT_SECRET,
                    },
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
                self._token = data.get("accessToken") or data.get("token")
                return self._token
        except Exception as e:
            logger.warning("NHCX auth failed: %s", e)
            return None

    def _build_claim_payload(
        self,
        policy_number: str,
        member_id: str,
        bill_amount: float,
        hospital_name: str,
        treatment: str,
        claim_type: str,
    ) -> dict:
        """Build FHIR ClaimRequestBundle (simplified). Full HCX compliance requires JWE encryption."""
        correlation_id = f"meddiagnose-{secrets.token_hex(8)}"
        # Minimal structure - production needs full FHIR R4 ClaimRequestBundle per HCX IG
        return {
            "protocol": {
                "sender": {"participantCode": "meddiagnose"},
                "recipient": {"participantCode": "payor"},
                "timestamp": "",
                "correlation_id": correlation_id,
                "workflow_id": "claim",
            },
            "payload": {
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Claim",
                            "id": correlation_id,
                            "status": "active",
                            "type": {"coding": [{"code": "institutional"}]},
                            "use": "claim" if claim_type == "reimbursement" else "preauthorization",
                            "patient": {"reference": f"Patient/{member_id}"},
                            "insurance": [{"sequence": 1, "focal": True, "identifier": {"value": policy_number}}],
                            "item": [
                                {
                                    "sequence": 1,
                                    "productOrService": {"coding": [{"display": treatment}]},
                                    "quantity": {"value": 1},
                                    "unitPrice": {"value": bill_amount, "currency": "INR"},
                                }
                            ],
                            "supportingInfo": [{"sequence": 1, "category": {"coding": [{"code": "info"}]}, "valueString": hospital_name}],
                        }
                    }
                ],
            },
        }

    async def submit_claim(
        self,
        policy_number: str,
        member_id: str,
        bill_amount: float,
        hospital_name: str,
        treatment: str,
        claim_type: str = "reimbursement",
        payor_code: Optional[str] = None,
    ) -> NHCXClaimResult:
        """
        Submit claim to NHCX. Routes to insurer (PM-JAY, Star Health, etc.).
        Returns 202 Accepted on success; actual response comes via callback.
        """
        if not self.is_configured():
            ref = f"NHCX-MOCK-{secrets.token_hex(4).upper()}"
            logger.info("NHCX not configured, returning mock: %s", ref)
            return NHCXClaimResult(success=True, status="submitted", reference_number=ref)

        token = await self._get_token()
        if not token:
            return NHCXClaimResult(success=False, status="error", error_message="NHCX authentication failed")

        payload = self._build_claim_payload(
            policy_number, member_id, bill_amount, hospital_name, treatment, claim_type
        )
        correlation_id = payload["protocol"]["correlation_id"]

        try:
            # HCX requires JWE-encrypted payload. For sandbox/testing, some gateways accept
            # unencrypted JSON. Production MUST use JWE per HCX spec.
            # TODO: Encrypt with payor's public key from registry lookup
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{self.settings.ABDM_BASE_URL.rstrip('/')}/api/v1/claim/submit",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code == 202:
                    ref = f"NHCX-{secrets.token_hex(4).upper()}"
                    logger.info("NHCX claim submitted: %s", correlation_id)
                    return NHCXClaimResult(
                        success=True,
                        status="submitted",
                        reference_number=ref,
                        correlation_id=correlation_id,
                    )
                err = r.text
                try:
                    err_json = r.json()
                    err = err_json.get("message", err_json.get("error", err))
                except Exception:
                    pass
                logger.warning("NHCX claim submit failed %s: %s", r.status_code, err)
                return NHCXClaimResult(
                    success=False,
                    status="error",
                    correlation_id=correlation_id,
                    error_message=str(err)[:500],
                )
        except Exception as e:
            logger.exception("NHCX claim submit error")
            return NHCXClaimResult(
                success=False,
                status="error",
                error_message=str(e)[:500],
            )

    async def check_eligibility(
        self,
        policy_number: str,
        member_id: str,
    ) -> NHCXEligibilityResult:
        """Check coverage eligibility with payor via NHCX."""
        if not self.is_configured():
            return NHCXEligibilityResult(success=True, eligible=True, coverage_details={"mock": True})

        token = await self._get_token()
        if not token:
            return NHCXEligibilityResult(success=False, eligible=False, error_message="NHCX auth failed")

        try:
            payload = {
                "protocol": {"sender": {"participantCode": "meddiagnose"}, "recipient": {"participantCode": "payor"}},
                "payload": {
                    "resourceType": "CoverageEligibilityRequest",
                    "patient": {"reference": f"Patient/{member_id}"},
                    "insurance": [{"coverage": {"reference": f"Coverage/{policy_number}"}}],
                },
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.settings.ABDM_BASE_URL.rstrip('/')}/api/v1/coverageeligibility/check",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                if r.status_code == 202:
                    return NHCXEligibilityResult(success=True, eligible=True)
                return NHCXEligibilityResult(
                    success=False,
                    eligible=False,
                    error_message=r.text[:500] if r.text else f"HTTP {r.status_code}",
                )
        except Exception as e:
            return NHCXEligibilityResult(success=False, eligible=False, error_message=str(e)[:500])


_nhcx_client: Optional[NHCXClient] = None


def get_nhcx_client() -> NHCXClient:
    global _nhcx_client
    if _nhcx_client is None:
        _nhcx_client = NHCXClient()
    return _nhcx_client
