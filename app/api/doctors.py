"""Doctor-patient linking API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User

router = APIRouter(prefix="/doctors", tags=["Doctors"])


class DoctorSummary(BaseModel):
    id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


class LinkDoctorBody(BaseModel):
    doctor_id: int


@router.get("", response_model=list[DoctorSummary])
async def list_doctors(
    search: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List doctors for patient selection. Patients use this to find and link to a doctor."""
    query = select(User).where(User.role == "doctor", User.is_active == True)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    result = await db.execute(query.order_by(User.full_name).limit(50))
    doctors = result.scalars().all()
    return [DoctorSummary(id=d.id, email=d.email, full_name=d.full_name) for d in doctors]


@router.get("/linked", response_model=DoctorSummary | None)
async def get_linked_doctor(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("patient")),
):
    """Get the doctor the current patient is linked to."""
    if not current_user.linked_doctor_id:
        return None
    result = await db.execute(
        select(User).where(User.id == current_user.linked_doctor_id, User.role == "doctor")
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        return None
    return DoctorSummary(id=doctor.id, email=doctor.email, full_name=doctor.full_name)


@router.post("/link", status_code=204)
async def link_doctor(
    body: LinkDoctorBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("patient")),
):
    """Link the current patient to a doctor."""
    result = await db.execute(
        select(User).where(User.id == body.doctor_id, User.role == "doctor", User.is_active == True)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    current_user.linked_doctor_id = body.doctor_id
    await db.commit()


@router.delete("/link", status_code=204)
async def unlink_doctor(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("patient")),
):
    """Unlink the current patient from their doctor."""
    current_user.linked_doctor_id = None
    await db.commit()
