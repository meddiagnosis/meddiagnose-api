"""Health alerts API — list and acknowledge automated vitals alerts."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User
from app.models.health_alert import HealthAlert
from app.schemas.health_alert import HealthAlertResponse, HealthAlertList

router = APIRouter(prefix="/health-alerts", tags=["Health Alerts"])


@router.get("/", response_model=HealthAlertList)
async def list_alerts(
    status: str | None = Query(None, description="Filter: active, acknowledged, resolved"),
    severity: str | None = Query(None, description="Filter: critical, warning, info"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List health alerts for the current user."""
    q = select(HealthAlert).where(HealthAlert.user_id == current_user.id)
    if status:
        q = q.where(HealthAlert.status == status)
    if severity:
        q = q.where(HealthAlert.severity == severity)
    q = q.order_by(HealthAlert.created_at.desc()).limit(limit)

    result = await db.execute(q)
    alerts = result.scalars().all()

    unread_q = select(func.count()).select_from(HealthAlert).where(
        HealthAlert.user_id == current_user.id,
        HealthAlert.status == "active",
    )
    unread = (await db.execute(unread_q)).scalar() or 0

    return HealthAlertList(
        items=[HealthAlertResponse.model_validate(a) for a in alerts],
        total=len(alerts),
        unread_count=unread,
    )


@router.post("/{alert_id}/acknowledge", response_model=HealthAlertResponse)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as acknowledged."""
    alert = await db.get(HealthAlert, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(404, "Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_user.id
    await db.commit()
    await db.refresh(alert)
    return HealthAlertResponse.model_validate(alert)


@router.post("/acknowledge-all")
async def acknowledge_all_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all active alerts as acknowledged."""
    q = select(HealthAlert).where(
        HealthAlert.user_id == current_user.id,
        HealthAlert.status == "active",
    )
    result = await db.execute(q)
    alerts = result.scalars().all()
    now = datetime.now(timezone.utc)
    for a in alerts:
        a.status = "acknowledged"
        a.acknowledged_at = now
        a.acknowledged_by = current_user.id
    await db.commit()
    return {"acknowledged": len(alerts)}


@router.get("/summary")
async def alerts_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get counts of active alerts by severity."""
    q = (
        select(HealthAlert.severity, func.count(HealthAlert.id))
        .where(HealthAlert.user_id == current_user.id, HealthAlert.status == "active")
        .group_by(HealthAlert.severity)
    )
    result = await db.execute(q)
    by_severity = {row[0]: row[1] for row in result.all()}
    total = sum(by_severity.values())
    return {
        "total_active": total,
        "critical": by_severity.get("critical", 0),
        "warning": by_severity.get("warning", 0),
        "info": by_severity.get("info", 0),
    }
