from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.diagnosis import MedicationLookupRequest, MedicationLookupResponse
from app.services.audit import log_audit

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.post("/identify", response_model=MedicationLookupResponse)
async def identify_diseases_from_medications(
    body: MedicationLookupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Given a list of medications a patient is taking, plus optional symptoms
    and vital signs, identify possible diseases."""
    from app.services.mock_diagnosis import identify_diseases_by_medications

    cleaned = [m.strip() for m in body.medications if m.strip()]
    vitals = {}
    if body.temperature_f is not None:
        vitals["temperature_f"] = body.temperature_f
    if body.systolic_bp is not None:
        vitals["systolic_bp"] = body.systolic_bp
    if body.diastolic_bp is not None:
        vitals["diastolic_bp"] = body.diastolic_bp
    if body.heart_rate is not None:
        vitals["heart_rate"] = body.heart_rate
    if body.spo2 is not None:
        vitals["spo2"] = body.spo2
    if body.blood_sugar is not None:
        vitals["blood_sugar"] = body.blood_sugar
    if body.respiratory_rate is not None:
        vitals["respiratory_rate"] = body.respiratory_rate

    results = identify_diseases_by_medications(
        cleaned,
        symptoms=body.symptoms or "",
        vitals=vitals if vitals else None,
    )

    await log_audit(
        db, action="medication_lookup", resource_type="medication",
        resource_id=",".join(cleaned[:10]),
        user_id=current_user.id, user_email=current_user.email, request=request,
    )
    await db.commit()

    return MedicationLookupResponse(
        matches=results,
        medications_searched=cleaned,
        total_matches=len(results),
    )
