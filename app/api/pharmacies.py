from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.diagnosis import PharmacySearchRequest, PharmacySearchResponse
from app.services.audit import log_audit

router = APIRouter(prefix="/pharmacies", tags=["Pharmacies"])


@router.post("/nearby", response_model=PharmacySearchResponse)
async def find_nearby_pharmacies(
    body: PharmacySearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find pharmacies that stock the requested medications, sorted by proximity."""
    from app.services.pharmacy_locator import find_nearby_pharmacies as locate

    cleaned = [m.strip() for m in body.medications if m.strip()]
    results = locate(
        medications=cleaned,
        latitude=body.latitude,
        longitude=body.longitude,
        radius_km=body.radius_km,
    )

    is_fallback = False
    if body.latitude is not None and body.longitude is not None and results:
        is_fallback = all(
            (r.get("distance_km") or 0) > body.radius_km for r in results
        )

    await log_audit(
        db, action="pharmacy_search", resource_type="pharmacy",
        resource_id=",".join(cleaned[:10]),
        user_id=current_user.id, user_email=current_user.email, request=request,
    )
    await db.commit()

    return PharmacySearchResponse(
        pharmacies=results,
        medications_searched=cleaned,
        total_results=len(results),
        is_nationwide_fallback=is_fallback,
    )
