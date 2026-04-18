import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.models.diagnosis import Diagnosis
from app.models.batch import Batch, BatchItem
from app.schemas.batch import BatchResponse, BatchList, BatchItemResponse
from app.services.audit import log_audit
from app.services.airflow import trigger_diagnosis_dag
from app.services.kafka_producer import publish_batch_jobs
from app.core.config import get_settings

router = APIRouter(prefix="/batches", tags=["Batches"])

REQUIRED_COLUMNS = {"first_name", "last_name"}


@router.post("/upload", response_model=BatchResponse, status_code=201)
async def upload_batch(
    request: Request,
    file: UploadFile = File(...),
    batch_name: str = Query("Untitled Batch"),
    priority: str = Query("normal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "json"):
        raise HTTPException(status_code=400, detail="File must be CSV, XLSX, or JSON")

    content = await file.read()
    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif ext == "xlsx":
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_json(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    batch = Batch(
        name=batch_name,
        status="validating",
        total_patients=len(df),
        source_file=file.filename,
        created_by=current_user.id,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    for idx, row in df.iterrows():
        row_dict = row.where(pd.notna(row), None).to_dict()

        patient = Patient(
            external_id=str(row_dict.get("external_id")) if row_dict.get("external_id") else None,
            first_name=str(row_dict.get("first_name", "")),
            last_name=str(row_dict.get("last_name", "")),
            gender=str(row_dict.get("gender")) if row_dict.get("gender") else None,
            clinical_notes=str(row_dict.get("clinical_notes")) if row_dict.get("clinical_notes") else None,
            symptoms=row_dict.get("symptoms").split(",") if isinstance(row_dict.get("symptoms"), str) else None,
            created_by=current_user.id,
        )
        db.add(patient)
        await db.flush()

        diagnosis = Diagnosis(
            patient_id=patient.id,
            batch_id=batch.id,
            status="queued",
            specialty=str(row_dict.get("specialty")) if row_dict.get("specialty") else None,
            priority=priority,
        )
        db.add(diagnosis)
        await db.flush()

        batch_item = BatchItem(
            batch_id=batch.id,
            patient_id=patient.id,
            diagnosis_id=diagnosis.id,
            row_number=idx + 1,
            raw_data=row_dict,
            status="created",
        )
        db.add(batch_item)

    batch.status = "queued"
    await db.commit()

    settings = get_settings()
    if getattr(settings, "KAFKA_ENABLED", False):
        # Kafka path: publish jobs for parallel consumer workers
        result = await db.execute(
            select(BatchItem).where(BatchItem.batch_id == batch.id)
        )
        items = result.scalars().all()
        # Load patients and diagnoses
        patient_ids = [i.patient_id for i in items if i.patient_id]
        diag_ids = [i.diagnosis_id for i in items if i.diagnosis_id]
        patients_result = await db.execute(select(Patient).where(Patient.id.in_(patient_ids)))
        patients = {p.id: p for p in patients_result.scalars().all()}
        diag_result = await db.execute(select(Diagnosis).where(Diagnosis.id.in_(diag_ids)))
        diagnoses = {d.id: d for d in diag_result.scalars().all()}
        jobs = []
        for item in items:
            patient = patients.get(item.patient_id) if item.patient_id else None
            diag = diagnoses.get(item.diagnosis_id) if item.diagnosis_id else None
            if not patient or not diag:
                continue
            symptoms = patient.symptoms
            if isinstance(symptoms, list):
                symptoms_str = ", ".join(str(s) for s in symptoms if s)
            else:
                symptoms_str = str(symptoms or "")
            medical_history = patient.medical_history or {}
            if not medical_history and item.raw_data:
                rd = item.raw_data or {}
                medical_history = {
                    k: rd.get(k) for k in ("gender", "date_of_birth", "blood_group", "allergies")
                    if rd.get(k)
                }
            jobs.append({
                "diagnosis_id": diag.id,
                "patient_id": patient.id,
                "batch_id": batch.id,
                "symptoms": symptoms_str or (patient.clinical_notes or ""),
                "clinical_notes": patient.clinical_notes or "",
                "medical_history": medical_history,
                "priority": priority,
            })
        published = await publish_batch_jobs(jobs)
        if published > 0:
            batch.status = "processing"
            await db.commit()
    else:
        try:
            airflow_result = await trigger_diagnosis_dag(batch.id, priority)
            batch.airflow_dag_run_id = airflow_result["dag_run_id"]
            batch.status = "processing"
            await db.commit()
        except Exception:
            pass

    await db.refresh(batch)
    await log_audit(db, action="upload_batch", resource_type="batch", resource_id=str(batch.id),
                    detail=f"Uploaded {len(df)} patients from {file.filename}",
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return BatchResponse.model_validate(batch)


@router.get("/", response_model=BatchList)
async def list_batches(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Batch)
    count_query = select(func.count(Batch.id))

    if status:
        query = query.where(Batch.status == status)
        count_query = count_query.where(Batch.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Batch.created_at.desc()).offset(offset).limit(per_page))
    batches = result.scalars().all()

    return BatchList(
        items=[BatchResponse.model_validate(b) for b in batches],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return BatchResponse.model_validate(batch)


@router.get("/{batch_id}/items", response_model=list[BatchItemResponse])
async def get_batch_items(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BatchItem).where(BatchItem.batch_id == batch_id).order_by(BatchItem.row_number)
    )
    items = result.scalars().all()
    return [BatchItemResponse.model_validate(item) for item in items]
