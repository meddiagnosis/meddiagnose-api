from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.fitness_log import FitnessLog, FitnessGoal
from app.schemas.fitness_log import (
    FitnessLogCreate,
    FitnessLogResponse,
    FitnessLogList,
    FitnessGoalCreate,
    FitnessGoalResponse,
    FitnessDashboard,
)
from app.services.fitness_tracker import build_dashboard
from app.services.health_alerts import check_fitness_log_vitals

router = APIRouter(prefix="/fitness", tags=["Fitness Tracker"])


@router.get("/dashboard", response_model=FitnessDashboard)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    ninety_days_ago = today - timedelta(days=90)

    logs_q = (
        select(FitnessLog)
        .where(FitnessLog.user_id == current_user.id, FitnessLog.log_date >= ninety_days_ago)
        .order_by(FitnessLog.log_date.asc())
    )
    result = await db.execute(logs_q)
    logs = list(result.scalars().all())

    today_log = next((l for l in logs if l.log_date == today), None)

    goal_q = select(FitnessGoal).where(FitnessGoal.user_id == current_user.id)
    goal_result = await db.execute(goal_q)
    goal = goal_result.scalar_one_or_none()

    return build_dashboard(logs, goal, today_log)


@router.post("/logs", response_model=FitnessLogResponse, status_code=201)
async def create_log(
    body: FitnessLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_q = select(FitnessLog).where(
        FitnessLog.user_id == current_user.id,
        FitnessLog.log_date == body.log_date,
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()
    if existing:
        for field, value in body.model_dump(exclude_unset=True).items():
            if field != "log_date":
                setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        try:
            await check_fitness_log_vitals(db, current_user.id, existing.id, existing.heart_rate, existing.spo2)
            await db.commit()
        except Exception:
            pass
        return FitnessLogResponse.model_validate(existing)

    log = FitnessLog(user_id=current_user.id, **body.model_dump())
    db.add(log)
    await db.commit()
    await db.refresh(log)
    try:
        await check_fitness_log_vitals(db, current_user.id, log.id, log.heart_rate, log.spo2)
        await db.commit()
    except Exception:
        pass
    return FitnessLogResponse.model_validate(log)


@router.get("/logs", response_model=FitnessLogList)
async def list_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = date.today() - timedelta(days=days)

    count_q = (
        select(func.count())
        .select_from(FitnessLog)
        .where(FitnessLog.user_id == current_user.id, FitnessLog.log_date >= since)
    )
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(FitnessLog)
        .where(FitnessLog.user_id == current_user.id, FitnessLog.log_date >= since)
        .order_by(FitnessLog.log_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    logs = result.scalars().all()

    return FitnessLogList(
        items=[FitnessLogResponse.model_validate(l) for l in logs],
        total=total,
    )


@router.get("/logs/{log_id}", response_model=FitnessLogResponse)
async def get_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = await db.get(FitnessLog, log_id)
    if not log or log.user_id != current_user.id:
        raise HTTPException(404, "Fitness log not found")
    return FitnessLogResponse.model_validate(log)


@router.delete("/logs/{log_id}", status_code=204)
async def delete_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = await db.get(FitnessLog, log_id)
    if not log or log.user_id != current_user.id:
        raise HTTPException(404, "Fitness log not found")
    await db.delete(log)
    await db.commit()


@router.get("/goals", response_model=FitnessGoalResponse | None)
async def get_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(FitnessGoal).where(FitnessGoal.user_id == current_user.id)
    result = await db.execute(q)
    goal = result.scalar_one_or_none()
    if not goal:
        return None
    return FitnessGoalResponse.model_validate(goal)


@router.put("/goals", response_model=FitnessGoalResponse)
async def upsert_goals(
    body: FitnessGoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(FitnessGoal).where(FitnessGoal.user_id == current_user.id)
    result = await db.execute(q)
    goal = result.scalar_one_or_none()

    if goal:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(goal, field, value)
    else:
        goal = FitnessGoal(user_id=current_user.id, **body.model_dump())
        db.add(goal)

    await db.commit()
    await db.refresh(goal)
    return FitnessGoalResponse.model_validate(goal)
