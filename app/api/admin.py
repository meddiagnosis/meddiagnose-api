"""Dashboard API endpoints for the web application."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User
from app.models.diagnosis import Diagnosis
from app.models.symptom_log import SymptomLog
from app.models.chat_message import ChatMessage

router = APIRouter(prefix="/admin", tags=["Dashboard"])


def _is_admin(user: User) -> bool:
    return user.role in ("admin", "doctor")


@router.get("/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    is_admin = _is_admin(current_user)

    if is_admin:
        diag_filter = True
        symptom_filter = True
        chat_filter = True
    else:
        diag_filter = Diagnosis.reviewed_by == current_user.id
        symptom_filter = SymptomLog.user_id == current_user.id
        chat_filter = ChatMessage.user_id == current_user.id

    if is_admin:
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        new_users_week = (await db.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )).scalar() or 0
        active_users = (await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )).scalar() or 0
    else:
        total_users = 1
        new_users_week = 0
        active_users = 1

    total_diagnoses = (await db.execute(
        select(func.count(Diagnosis.id)).where(diag_filter)
    )).scalar() or 0
    diagnoses_week = (await db.execute(
        select(func.count(Diagnosis.id)).where(diag_filter, Diagnosis.created_at >= week_ago)
    )).scalar() or 0
    diagnoses_month = (await db.execute(
        select(func.count(Diagnosis.id)).where(diag_filter, Diagnosis.created_at >= month_ago)
    )).scalar() or 0

    severity_q = await db.execute(
        select(Diagnosis.ai_severity, func.count(Diagnosis.id))
        .where(diag_filter, Diagnosis.ai_severity.isnot(None))
        .group_by(Diagnosis.ai_severity)
    )
    severity_dist = {row[0]: row[1] for row in severity_q.all()}

    avg_confidence = (await db.execute(
        select(func.avg(Diagnosis.ai_confidence)).where(diag_filter, Diagnosis.ai_confidence.isnot(None))
    )).scalar()

    total_symptoms = (await db.execute(
        select(func.count(SymptomLog.id)).where(symptom_filter)
    )).scalar() or 0
    total_chats = (await db.execute(
        select(func.count(ChatMessage.id)).where(chat_filter)
    )).scalar() or 0

    return {
        "role": current_user.role,
        "users": {
            "total": total_users,
            "active": active_users,
            "new_this_week": new_users_week,
        },
        "diagnoses": {
            "total": total_diagnoses,
            "this_week": diagnoses_week,
            "this_month": diagnoses_month,
            "avg_confidence": round(avg_confidence, 3) if avg_confidence else 0,
            "severity_distribution": severity_dist,
        },
        "engagement": {
            "symptom_logs": total_symptoms,
            "chat_messages": total_chats,
        },
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    role: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_filter = User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(per_page))
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": u.id, "email": u.email, "full_name": u.full_name,
                "role": u.role, "gender": u.gender, "date_of_birth": u.date_of_birth,
                "blood_group": u.blood_group, "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/patients")
async def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    """List patient-role users. Doctors see only patients linked to them; admins see all."""
    query = select(User).where(User.role == "patient")
    count_query = select(func.count(User.id)).where(User.role == "patient")

    if current_user.role == "doctor":
        query = query.where(User.linked_doctor_id == current_user.id)
        count_query = count_query.where(User.linked_doctor_id == current_user.id)

    if search:
        search_filter = User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(per_page))
    users = result.scalars().all()

    items = []
    for u in users:
        diag_count = (await db.execute(
            select(func.count(Diagnosis.id)).where(Diagnosis.reviewed_by == u.id)
        )).scalar() or 0
        last_diag_row = (await db.execute(
            select(Diagnosis.created_at)
            .where(Diagnosis.reviewed_by == u.id)
            .order_by(Diagnosis.created_at.desc())
            .limit(1)
        )).scalar()
        items.append({
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "gender": u.gender, "date_of_birth": u.date_of_birth,
            "blood_group": u.blood_group, "allergies": u.allergies,
            "phone": u.phone, "weight_kg": u.weight_kg,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "diagnosis_count": diag_count,
            "last_diagnosis_at": last_diag_row.isoformat() if last_diag_row else None,
        })

    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/patients/{patient_id}")
async def get_patient_detail(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    """Get a single patient's full profile. Doctors can only access patients linked to them."""
    result = await db.execute(select(User).where(User.id == patient_id, User.role == "patient"))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if current_user.role == "doctor" and patient.linked_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: patient is not linked to you")

    diag_count = (await db.execute(
        select(func.count(Diagnosis.id)).where(Diagnosis.reviewed_by == patient.id)
    )).scalar() or 0
    symptom_count = (await db.execute(
        select(func.count(SymptomLog.id)).where(SymptomLog.user_id == patient.id)
    )).scalar() or 0

    return {
        "id": patient.id, "email": patient.email, "full_name": patient.full_name,
        "gender": patient.gender, "date_of_birth": patient.date_of_birth,
        "blood_group": patient.blood_group, "allergies": patient.allergies,
        "phone": patient.phone, "weight_kg": patient.weight_kg,
        "is_active": patient.is_active,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "diagnosis_count": diag_count,
        "symptom_log_count": symptom_count,
    }


@router.get("/patients/{patient_id}/diagnoses")
async def get_patient_diagnoses(
    patient_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    """Get all diagnoses belonging to a specific patient. Doctors can only access linked patients."""
    result = await db.execute(select(User).where(User.id == patient_id, User.role == "patient"))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if current_user.role == "doctor" and patient.linked_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: patient is not linked to you")

    query = select(Diagnosis).where(Diagnosis.reviewed_by == patient_id)
    count_query = select(func.count(Diagnosis.id)).where(Diagnosis.reviewed_by == patient_id)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Diagnosis.created_at.desc()).offset(offset).limit(per_page))
    diagnoses = result.scalars().all()

    return {
        "items": [
            {
                "id": d.id, "status": d.status, "ai_diagnosis": d.ai_diagnosis,
                "ai_layman_summary": d.ai_layman_summary,
                "ai_severity": d.ai_severity, "ai_urgency": d.ai_urgency,
                "ai_confidence": d.ai_confidence, "symptoms_text": d.symptoms_text,
                "ai_medications": d.ai_medications, "ai_findings": d.ai_findings,
                "ai_reasoning": d.ai_reasoning, "ai_lifestyle": d.ai_lifestyle,
                "ai_precautions": d.ai_precautions, "ai_recommended_tests": d.ai_recommended_tests,
                "ai_when_to_see_doctor": d.ai_when_to_see_doctor,
                "ai_drug_interactions": d.ai_drug_interactions,
                "reviewed_by": d.reviewed_by, "priority": d.priority,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in diagnoses
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = not user.is_active
    await db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    role: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    if role not in ("patient", "doctor", "admin", "reviewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    await db.commit()
    return {"id": user.id, "role": user.role}


@router.get("/diagnoses")
async def list_all_diagnoses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    severity: str = Query(""),
    status: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Diagnosis)
    count_query = select(func.count(Diagnosis.id))

    if not _is_admin(current_user):
        query = query.where(Diagnosis.reviewed_by == current_user.id)
        count_query = count_query.where(Diagnosis.reviewed_by == current_user.id)

    if severity:
        query = query.where(Diagnosis.ai_severity == severity)
        count_query = count_query.where(Diagnosis.ai_severity == severity)
    if status:
        query = query.where(Diagnosis.status == status)
        count_query = count_query.where(Diagnosis.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Diagnosis.created_at.desc()).offset(offset).limit(per_page))
    diagnoses = result.scalars().all()

    return {
        "items": [
            {
                "id": d.id, "status": d.status, "ai_diagnosis": d.ai_diagnosis,
                "ai_layman_summary": d.ai_layman_summary,
                "ai_severity": d.ai_severity, "ai_urgency": d.ai_urgency,
                "ai_confidence": d.ai_confidence, "symptoms_text": d.symptoms_text,
                "ai_medications": d.ai_medications, "ai_findings": d.ai_findings,
                "ai_reasoning": d.ai_reasoning, "ai_lifestyle": d.ai_lifestyle,
                "ai_precautions": d.ai_precautions, "ai_recommended_tests": d.ai_recommended_tests,
                "ai_when_to_see_doctor": d.ai_when_to_see_doctor,
                "ai_drug_interactions": d.ai_drug_interactions,
                "reviewed_by": d.reviewed_by, "priority": d.priority,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in diagnoses
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/analytics/disease-distribution")
async def disease_distribution(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        select(Diagnosis.ai_diagnosis, func.count(Diagnosis.id))
        .where(Diagnosis.ai_diagnosis.isnot(None), Diagnosis.created_at >= since)
    )
    if not _is_admin(current_user):
        query = query.where(Diagnosis.reviewed_by == current_user.id)
    result = await db.execute(
        query.group_by(Diagnosis.ai_diagnosis)
        .order_by(func.count(Diagnosis.id).desc())
        .limit(20)
    )
    return {"period_days": days, "diseases": [{"name": r[0], "count": r[1]} for r in result.all()]}


@router.get("/analytics/daily-trend")
async def daily_trend(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = select(
        func.date(Diagnosis.created_at).label("date"),
        func.count(Diagnosis.id).label("count"),
    ).where(Diagnosis.created_at >= since)
    if not _is_admin(current_user):
        query = query.where(Diagnosis.reviewed_by == current_user.id)
    result = await db.execute(
        query.group_by(func.date(Diagnosis.created_at))
        .order_by(func.date(Diagnosis.created_at))
    )
    return {"period_days": days, "trend": [{"date": str(r[0]), "count": r[1]} for r in result.all()]}


@router.get("/analytics/confidence-distribution")
async def confidence_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(
        case(
            (Diagnosis.ai_confidence < 0.5, "Low (<50%)"),
            (Diagnosis.ai_confidence < 0.7, "Medium (50-70%)"),
            (Diagnosis.ai_confidence < 0.85, "High (70-85%)"),
            else_="Very High (>85%)",
        ).label("bucket"),
        func.count(Diagnosis.id),
    ).where(Diagnosis.ai_confidence.isnot(None))
    if not _is_admin(current_user):
        query = query.where(Diagnosis.reviewed_by == current_user.id)
    result = await db.execute(query.group_by("bucket"))
    return {"buckets": [{"range": r[0], "count": r[1]} for r in result.all()]}


@router.get("/analytics/gender-disease")
async def gender_disease_distribution(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    """Disease distribution broken down by patient gender."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            func.coalesce(User.gender, "Unknown").label("gender"),
            Diagnosis.ai_diagnosis,
            func.count(Diagnosis.id).label("cnt"),
        )
        .join(User, Diagnosis.reviewed_by == User.id)
        .where(Diagnosis.ai_diagnosis.isnot(None), Diagnosis.created_at >= since)
        .group_by("gender", Diagnosis.ai_diagnosis)
        .order_by(func.count(Diagnosis.id).desc())
    )
    rows = (await db.execute(query)).all()

    gender_totals: dict[str, int] = {}
    disease_by_gender: dict[str, list] = {}
    for gender, disease, cnt in rows:
        g = gender.capitalize() if gender else "Unknown"
        gender_totals[g] = gender_totals.get(g, 0) + cnt
        disease_by_gender.setdefault(g, []).append({"disease": disease, "count": cnt})

    return {
        "period_days": days,
        "gender_totals": [{"gender": g, "count": c} for g, c in gender_totals.items()],
        "disease_by_gender": disease_by_gender,
    }


@router.get("/analytics/top-medications")
async def top_medications(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    """Most frequently prescribed medications across all diagnoses."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Diagnosis.ai_medications)
        .where(Diagnosis.ai_medications.isnot(None), Diagnosis.created_at >= since)
    )
    all_meds = result.scalars().all()

    med_counts: dict[str, int] = {}
    med_diseases: dict[str, dict[str, int]] = {}
    for meds_list in all_meds:
        if not isinstance(meds_list, list):
            continue
        for m in meds_list:
            if isinstance(m, dict) and "name" in m:
                name = m["name"]
                med_counts[name] = med_counts.get(name, 0) + 1

    result2 = await db.execute(
        select(Diagnosis.ai_diagnosis, Diagnosis.ai_medications)
        .where(Diagnosis.ai_medications.isnot(None), Diagnosis.created_at >= since)
    )
    for disease, meds_list in result2.all():
        if not isinstance(meds_list, list) or not disease:
            continue
        for m in meds_list:
            if isinstance(m, dict) and "name" in m:
                name = m["name"]
                med_diseases.setdefault(name, {})
                med_diseases[name][disease] = med_diseases[name].get(disease, 0) + 1

    sorted_meds = sorted(med_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "period_days": days,
        "medications": [
            {
                "name": name,
                "count": count,
                "top_diseases": sorted(
                    [{"disease": d, "count": c} for d, c in med_diseases.get(name, {}).items()],
                    key=lambda x: x["count"], reverse=True,
                )[:5],
            }
            for name, count in sorted_meds
        ],
    }


@router.get("/analytics/severity-by-gender")
async def severity_by_gender(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    """Severity distribution broken down by patient gender."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            func.coalesce(User.gender, "Unknown").label("gender"),
            Diagnosis.ai_severity,
            func.count(Diagnosis.id).label("cnt"),
        )
        .join(User, Diagnosis.reviewed_by == User.id)
        .where(Diagnosis.ai_severity.isnot(None), Diagnosis.created_at >= since)
        .group_by("gender", Diagnosis.ai_severity)
    )
    rows = (await db.execute(query)).all()

    data: dict[str, dict[str, int]] = {}
    for gender, severity, cnt in rows:
        g = gender.capitalize() if gender else "Unknown"
        data.setdefault(g, {})
        data[g][severity] = cnt

    return {
        "period_days": days,
        "genders": [
            {"gender": g, **counts}
            for g, counts in data.items()
        ],
    }
