from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.symptom_log import SymptomLog
from app.schemas.symptom_log import SymptomLogCreate, SymptomLogResponse, SymptomLogList

router = APIRouter(prefix="/symptoms", tags=["Symptom Tracking"])


@router.post("/", response_model=SymptomLogResponse, status_code=201)
async def log_symptom(
    body: SymptomLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = SymptomLog(
        user_id=current_user.id,
        symptom=body.symptom,
        severity=body.severity,
        notes=body.notes,
        logged_at=body.logged_at or datetime.now(timezone.utc),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return SymptomLogResponse.model_validate(log)


@router.get("/", response_model=SymptomLogList)
async def list_symptoms(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        select(SymptomLog)
        .where(SymptomLog.user_id == current_user.id, SymptomLog.logged_at >= since)
        .order_by(SymptomLog.logged_at.desc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()
    return SymptomLogList(
        items=[SymptomLogResponse.model_validate(l) for l in logs],
        total=len(logs),
    )


@router.get("/summary")
async def symptom_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        select(SymptomLog)
        .where(SymptomLog.user_id == current_user.id, SymptomLog.logged_at >= since)
        .order_by(SymptomLog.logged_at.asc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    by_symptom: dict[str, list[dict]] = {}
    for l in logs:
        name = l.symptom.lower().strip()
        if name not in by_symptom:
            by_symptom[name] = []
        by_symptom[name].append({
            "severity": l.severity,
            "date": l.logged_at.isoformat(),
        })

    trends = []
    for symptom, entries in by_symptom.items():
        severities = [e["severity"] for e in entries]
        trend = "stable"
        if len(severities) >= 2:
            first_half = sum(severities[:len(severities)//2]) / max(len(severities)//2, 1)
            second_half = sum(severities[len(severities)//2:]) / max(len(severities) - len(severities)//2, 1)
            if second_half < first_half - 0.5:
                trend = "improving"
            elif second_half > first_half + 0.5:
                trend = "worsening"
        trends.append({
            "symptom": symptom,
            "entries": entries,
            "avg_severity": round(sum(severities) / len(severities), 1),
            "trend": trend,
            "count": len(entries),
        })

    return {"period_days": days, "symptoms": trends, "total_logs": len(logs)}
