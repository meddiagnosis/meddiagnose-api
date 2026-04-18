from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientList
from app.services.audit import log_audit

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.external_id:
        existing = await db.execute(select(Patient).where(Patient.external_id == body.external_id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Patient with this external ID already exists")

    patient = Patient(**body.model_dump(), created_by=current_user.id)
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    await log_audit(db, action="create", resource_type="patient", resource_id=str(patient.id),
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return PatientResponse.model_validate(patient)


@router.get("/", response_model=PatientList)
async def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Patient)
    count_query = select(func.count(Patient.id))

    if search:
        search_filter = (
            Patient.first_name.ilike(f"%{search}%") |
            Patient.last_name.ilike(f"%{search}%") |
            Patient.external_id.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Patient.created_at.desc()).offset(offset).limit(per_page))
    patients = result.scalars().all()

    return PatientList(
        items=[PatientResponse.model_validate(p) for p in patients],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    await log_audit(db, action="read", resource_type="patient", resource_id=str(patient_id),
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return PatientResponse.model_validate(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    body: PatientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    changes = {}
    for field, value in body.model_dump(exclude_unset=True).items():
        old = getattr(patient, field)
        if old != value:
            changes[field] = {"old": str(old), "new": str(value)}
            setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    await log_audit(db, action="update", resource_type="patient", resource_id=str(patient_id),
                    user_id=current_user.id, user_email=current_user.email, request=request, changes=changes)
    await db.commit()

    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    await log_audit(db, action="delete", resource_type="patient", resource_id=str(patient_id),
                    user_id=current_user.id, user_email=current_user.email, request=request)

    await db.delete(patient)
    await db.commit()
