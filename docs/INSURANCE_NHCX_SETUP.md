# Real Insurance Connection via ABDM NHCX

This guide explains how to enable **real** insurance integration so claims are submitted to actual insurers (PM-JAY, Star Health, etc.) via the National Health Claims Exchange (NHCX).

## Prerequisites

- MedDiagnose deployed with a **public URL** (for NHCX callbacks)
- Organization/entity capable of NHCX registration

## Step 1: Register on NHCX Sandbox

1. Go to **https://sbxhcx.abdm.gov.in**
2. Submit the online registration form
3. Provide:
   - Organization details
   - Contact information
   - Callback URL: `https://your-domain.com/api/v1/insurance/hcx/callback`
4. Wait for approval (typically 3–4 days)
5. You will receive:
   - **Client ID** (Participant ID)
   - **Client Secret**
   - Sandbox credentials

## Step 2: Configure Environment

Add to your `.env`:

```env
# ABDM NHCX (from registration)
ABDM_CLIENT_ID=your-participant-id
ABDM_CLIENT_SECRET=your-secret
ABDM_BASE_URL=https://sbxhcx.abdm.gov.in

# Callback URL (must match what you registered)
NHCX_CALLBACK_URL=https://your-domain.com/api/v1/insurance/hcx/callback
```

## Step 3: Restart the Application

Restart the backend so it picks up the new credentials. Claims for **government schemes** (PM-JAY, CGHS, ESIC) and **Star Health** will now be sent to NHCX.

## What Works Now

| Feature | Status |
|---------|--------|
| Claim submission to NHCX | ✅ Real API call when credentials set |
| Eligibility check | ✅ Real API call |

## Payload Format

The NHCX protocol expects:
- **JWE**-encrypted payloads (RFC 7516)
- **FHIR R4** ClaimRequestBundle
- Protocol headers for routing

The current implementation uses a simplified payload for sandbox testing. Production use requires:
- Full FHIR ClaimRequestBundle per [HCX Implementation Guide](https://ig.hcxprotocol.io/)
- JWE encryption with payor's public key (from registry lookup)
- Proper protocol headers

## Sandbox vs Production

- **Sandbox:** `ABDM_BASE_URL=https://sbxhcx.abdm.gov.in`
- **Production:** Register at production NHCX, then use `ABDM_BASE_URL=https://hcx.abdm.gov.in`

## Private Insurers (HDFC, Max Bupa, Axis)

- **Star Health:** Uses NHCX when ABDM is configured (Star Health is on NHCX)
- **HDFC Ergo, Max Bupa, Axis:** Set partner API credentials when available:
  - `HDFC_ERGO_API_URL`, `HDFC_ERGO_API_KEY`
  - `MAX_BUPA_API_URL`, `MAX_BUPA_API_KEY`
  - `AXIS_HEALTH_API_URL`, `AXIS_HEALTH_API_KEY`

## Troubleshooting

- **"NHCX authentication failed"** – Check Client ID and Secret are correct
- **401/403** – Token may have expired; session is refreshed automatically
- **404** – Verify `ABDM_BASE_URL` and API paths match your NHCX environment
- **Callback not received** – Ensure NHCX_CALLBACK_URL is publicly reachable and matches registration

## References

- [HCX Protocol Spec](https://docs.hcxprotocol.io/)
- [NHCX FHIR IG](https://ig.hcxprotocol.io/)
- [ABDM Sandbox](https://sbxhcx.abdm.gov.in)
