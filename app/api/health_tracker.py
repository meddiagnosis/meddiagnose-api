from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.health_report import HealthReport
from app.schemas.health_report import (
    HealthReportCreate,
    HealthReportResponse,
    HealthReportList,
    HealthReportComparison,
    HealthReportTrends,
)
from app.services.health_tracker import compare_reports, compute_trends, get_health_status
from app.services.health_alerts import check_health_report_vitals

router = APIRouter(prefix="/health-tracker", tags=["Health Tracker"])


@router.post("/", response_model=HealthReportResponse, status_code=201)
async def create_report(
    body: HealthReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = HealthReport(user_id=current_user.id, **body.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    try:
        await check_health_report_vitals(db, current_user.id, report.id, report)
        await db.commit()
    except Exception:
        pass  # Don't fail report creation if alert check fails
    return HealthReportResponse.model_validate(report)


@router.get("/", response_model=HealthReportList)
async def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count_q = select(func.count()).select_from(HealthReport).where(HealthReport.user_id == current_user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(HealthReport)
        .where(HealthReport.user_id == current_user.id)
        .order_by(HealthReport.report_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    reports = result.scalars().all()
    return HealthReportList(
        items=[HealthReportResponse.model_validate(r) for r in reports],
        total=total,
    )


@router.get("/compare", response_model=HealthReportComparison)
async def compare_two_reports(
    report_id_1: int = Query(..., description="Older report ID"),
    report_id_2: int = Query(..., description="Newer report ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r1 = await db.get(HealthReport, report_id_1)
    r2 = await db.get(HealthReport, report_id_2)
    if not r1 or r1.user_id != current_user.id:
        raise HTTPException(404, "Report 1 not found")
    if not r2 or r2.user_id != current_user.id:
        raise HTTPException(404, "Report 2 not found")

    older, newer = (r1, r2) if r1.report_date <= r2.report_date else (r2, r1)
    return compare_reports(older, newer)


@router.get("/latest-comparison", response_model=HealthReportComparison)
async def latest_comparison(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(HealthReport)
        .where(HealthReport.user_id == current_user.id)
        .order_by(HealthReport.report_date.desc())
        .limit(2)
    )
    result = await db.execute(q)
    reports = result.scalars().all()
    if len(reports) < 2:
        raise HTTPException(400, "Need at least 2 reports to compare. Please add more reports.")
    return compare_reports(reports[1], reports[0])


@router.get("/trends", response_model=HealthReportTrends)
async def get_trends(
    metrics: str = Query("", description="Comma-separated metric field names (empty = all)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(HealthReport)
        .where(HealthReport.user_id == current_user.id)
        .order_by(HealthReport.report_date.asc())
    )
    result = await db.execute(q)
    reports = list(result.scalars().all())
    if not reports:
        return HealthReportTrends(trends=[], report_count=0)

    metric_list = [m.strip() for m in metrics.split(",") if m.strip()] or None
    return compute_trends(reports, metric_list)


@router.get("/{report_id}", response_model=HealthReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = await db.get(HealthReport, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(404, "Report not found")
    return HealthReportResponse.model_validate(report)


@router.get("/{report_id}/status")
async def get_report_status(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = await db.get(HealthReport, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(404, "Report not found")
    return {"report_id": report_id, "metrics": get_health_status(report)}


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = await db.get(HealthReport, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(404, "Report not found")
    await db.delete(report)
    await db.commit()
