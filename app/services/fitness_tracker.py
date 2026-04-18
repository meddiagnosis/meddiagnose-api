"""Fitness tracker service for computing goals, streaks, and summaries."""

from __future__ import annotations
from datetime import date, timedelta
from app.models.fitness_log import FitnessLog, FitnessGoal
from app.schemas.fitness_log import (
    DailyProgress,
    WeeklySummary,
    FitnessGoalResponse,
    FitnessLogResponse,
    FitnessDashboard,
)


def _safe_pct(value: float, goal: float) -> float:
    if goal <= 0:
        return 100.0
    return round(min((value / goal) * 100, 100), 1)


def compute_daily_progress(log: FitnessLog | None, goal: FitnessGoal | None, target_date: date) -> DailyProgress | None:
    if log is None:
        return None

    g_steps = (goal.daily_steps or 10000) if goal else 10000
    g_cal = (goal.daily_calories or 500) if goal else 500
    g_active = (goal.daily_active_minutes or 30) if goal else 30
    g_water = (goal.daily_water_ml or 2500) if goal else 2500
    g_sleep = (goal.daily_sleep_hours or 7.5) if goal else 7.5

    steps = log.steps or 0
    calories = log.calories_burned or 0
    active = log.active_minutes or 0
    water = log.water_ml or 0
    sleep = log.sleep_hours or 0.0

    return DailyProgress(
        date=target_date.isoformat(),
        steps=steps,
        steps_goal=g_steps,
        steps_pct=_safe_pct(steps, g_steps),
        calories=calories,
        calories_goal=g_cal,
        calories_pct=_safe_pct(calories, g_cal),
        active_minutes=active,
        active_minutes_goal=g_active,
        active_minutes_pct=_safe_pct(active, g_active),
        water_ml=water,
        water_goal=g_water,
        water_pct=_safe_pct(water, g_water),
        sleep_hours=sleep,
        sleep_goal=g_sleep,
        sleep_pct=_safe_pct(sleep, g_sleep),
        workout_done=bool(log.workout_type),
        mood=log.mood,
        weight_kg=log.weight_kg,
    )


def compute_weekly_summary(logs: list[FitnessLog], goal: FitnessGoal | None) -> WeeklySummary | None:
    if not logs:
        return None

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_logs = [l for l in logs if week_start <= l.log_date <= week_end]
    if not week_logs:
        week_logs = logs[-7:]
        if week_logs:
            week_start = week_logs[0].log_date
            week_end = week_logs[-1].log_date

    days = len(week_logs)

    total_steps = sum(l.steps or 0 for l in week_logs)
    total_cal = sum(l.calories_burned or 0 for l in week_logs)
    total_active = sum(l.active_minutes or 0 for l in week_logs)
    total_water = sum(l.water_ml or 0 for l in week_logs)
    sleep_vals = [l.sleep_hours for l in week_logs if l.sleep_hours is not None]
    mood_vals = [l.mood for l in week_logs if l.mood is not None]
    workout_count = sum(1 for l in week_logs if l.workout_type)

    g_workouts = (goal.weekly_workouts or 4) if goal else 4

    weight_trend = []
    for l in sorted(week_logs, key=lambda x: x.log_date):
        if l.weight_kg is not None:
            weight_trend.append({"date": l.log_date.isoformat(), "weight": l.weight_kg})

    return WeeklySummary(
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        total_steps=total_steps,
        avg_steps=total_steps // max(days, 1),
        total_calories=total_cal,
        avg_calories=total_cal // max(days, 1),
        total_active_minutes=total_active,
        avg_active_minutes=total_active // max(days, 1),
        total_water_ml=total_water,
        avg_water_ml=total_water // max(days, 1),
        avg_sleep_hours=round(sum(sleep_vals) / len(sleep_vals), 1) if sleep_vals else 0,
        workout_count=workout_count,
        workout_goal=g_workouts,
        workout_pct=_safe_pct(workout_count, g_workouts),
        days_logged=days,
        streak=compute_streak(logs),
        avg_mood=round(sum(mood_vals) / len(mood_vals), 1) if mood_vals else None,
        weight_trend=weight_trend,
    )


def compute_streak(logs: list[FitnessLog]) -> int:
    if not logs:
        return 0

    dates_set = {l.log_date for l in logs}
    streak = 0
    current = date.today()
    while current in dates_set:
        streak += 1
        current -= timedelta(days=1)
    return streak


def build_dashboard(
    logs: list[FitnessLog],
    goal: FitnessGoal | None,
    today_log: FitnessLog | None,
) -> FitnessDashboard:
    today_date = date.today()

    today_progress = compute_daily_progress(today_log, goal, today_date)
    weekly = compute_weekly_summary(logs, goal)
    streak = compute_streak(logs)

    recent = sorted(logs, key=lambda l: l.log_date, reverse=True)[:14]

    return FitnessDashboard(
        today=today_progress,
        goals=FitnessGoalResponse.model_validate(goal) if goal else None,
        weekly=weekly,
        recent_logs=[FitnessLogResponse.model_validate(l) for l in recent],
        streak=streak,
        total_logged_days=len({l.log_date for l in logs}),
    )
