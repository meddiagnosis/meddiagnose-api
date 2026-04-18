"""
Automated health monitoring and alerting.

Checks vitals against thresholds and creates alerts when values are out of range.
Uses METRIC_SPECS from health_tracker for normal ranges; adds critical thresholds
for severe deviations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_alert import HealthAlert
from app.services.health_tracker import METRIC_SPECS, _SPEC_BY_FIELD, classify_value

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CriticalThreshold:
    """Thresholds for critical (urgent) alerts — beyond normal range."""
    metric: str
    critical_low: float | None  # Below this = critical
    critical_high: float | None  # Above this = critical


# Metrics we monitor from fitness logs and health reports
CRITICAL_THRESHOLDS: dict[str, CriticalThreshold] = {
    "systolic_bp": CriticalThreshold("systolic_bp", None, 180),
    "diastolic_bp": CriticalThreshold("diastolic_bp", None, 120),
    "heart_rate": CriticalThreshold("heart_rate", 40, 150),
    "spo2": CriticalThreshold("spo2", 90, None),
    "temperature": CriticalThreshold("temperature", 95.0, 103.0),
    "fasting_blood_sugar": CriticalThreshold("fasting_blood_sugar", 54, 400),
    "post_prandial_blood_sugar": CriticalThreshold("post_prandial_blood_sugar", 54, 400),
}


def _get_severity(metric: str, value: float, status: str) -> str:
    """Determine severity: critical for severe deviation, warning for out-of-range."""
    if status == "normal":
        return "info"
    thresh = CRITICAL_THRESHOLDS.get(metric)
    if not thresh:
        return "warning"
    if thresh.critical_low is not None and value < thresh.critical_low:
        return "critical"
    if thresh.critical_high is not None and value > thresh.critical_high:
        return "critical"
    return "warning"


def _build_message(metric: str, value: float, status: str, spec) -> str:
    if status == "low":
        return f"{spec.label} is low ({value} {spec.unit}). Normal range: {spec.normal_min}-{spec.normal_max} {spec.unit}."
    if status == "high":
        return f"{spec.label} is high ({value} {spec.unit}). Normal range: {spec.normal_min}-{spec.normal_max} {spec.unit}."
    return f"{spec.label}: {value} {spec.unit} (normal)"


async def _recent_alert_exists(
    db: AsyncSession,
    user_id: int,
    metric: str,
    source_type: str,
    source_id: int | None,
    within_hours: int = 24,
) -> bool:
    """Check if we already raised an alert for this metric/source recently."""
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    q = select(HealthAlert).where(
        HealthAlert.user_id == user_id,
        HealthAlert.metric == metric,
        HealthAlert.source_type == source_type,
        HealthAlert.created_at >= since,
    )
    if source_id is not None:
        q = q.where(HealthAlert.source_id == source_id)
    result = await db.execute(q.limit(1))
    return result.scalar_one_or_none() is not None


async def check_and_create_alert(
    db: AsyncSession,
    user_id: int,
    metric: str,
    value: float,
    source_type: str,
    source_id: int | None = None,
    skip_if_recent: bool = True,
) -> HealthAlert | None:
    """
    Check a single metric value against thresholds. Create alert if out of range.
    Returns the created alert or None.
    """
    spec = _SPEC_BY_FIELD.get(metric)
    if not spec:
        return None

    status = classify_value(spec, value)
    if status == "normal":
        return None

    severity = _get_severity(metric, value, status)
    if severity != "critical":
        return None  # Only alert on critical values, not warnings

    if skip_if_recent:
        exists = await _recent_alert_exists(db, user_id, metric, source_type, source_id)
        if exists:
            return None

    message = _build_message(metric, value, status, spec)
    alert = HealthAlert(
        user_id=user_id,
        metric=metric,
        metric_label=spec.label,
        value=value,
        unit=spec.unit,
        normal_min=spec.normal_min,
        normal_max=spec.normal_max,
        severity=severity,
        status="active",
        message=message,
        source_type=source_type,
        source_id=source_id,
    )
    db.add(alert)
    logger.info("Health alert created: user=%s metric=%s value=%s severity=%s", user_id, metric, value, severity)
    return alert


async def check_fitness_log_vitals(
    db: AsyncSession,
    user_id: int,
    log_id: int,
    heart_rate: float | None,
    spo2: float | None,
) -> list[HealthAlert]:
    """Check fitness log vitals and create alerts if needed."""
    created: list[HealthAlert] = []
    if heart_rate is not None:
        a = await check_and_create_alert(
            db, user_id, "heart_rate", heart_rate,
            source_type="fitness_log", source_id=log_id,
        )
        if a:
            created.append(a)
    if spo2 is not None:
        a = await check_and_create_alert(
            db, user_id, "spo2", spo2,
            source_type="fitness_log", source_id=log_id,
        )
        if a:
            created.append(a)
    return created


async def check_health_report_vitals(
    db: AsyncSession,
    user_id: int,
    report_id: int,
    report: object,
) -> list[HealthAlert]:
    """Check health report vitals and create alerts for any out-of-range values."""
    created: list[HealthAlert] = []
    for spec in METRIC_SPECS:
        val = getattr(report, spec.field, None)
        if val is None:
            continue
        a = await check_and_create_alert(
            db, user_id, spec.field, val,
            source_type="health_report", source_id=report_id,
        )
        if a:
            created.append(a)
    return created
