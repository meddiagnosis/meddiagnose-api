"""
Health Tracker comparison and trend analysis service.

Provides normal reference ranges for common health metrics and logic to
compare two reports, classify metric status, and build time-series data
for frontend charting.
"""

from __future__ import annotations
from dataclasses import dataclass
from app.models.health_report import HealthReport
from app.schemas.health_report import (
    MetricChange,
    HealthReportComparison,
    HealthReportResponse,
    TrendDataPoint,
    MetricTrend,
    HealthReportTrends,
)


@dataclass(frozen=True)
class MetricSpec:
    field: str
    label: str
    unit: str
    normal_min: float
    normal_max: float
    lower_is_better_above_normal: bool = True


METRIC_SPECS: list[MetricSpec] = [
    MetricSpec("systolic_bp", "Systolic BP", "mmHg", 90, 120),
    MetricSpec("diastolic_bp", "Diastolic BP", "mmHg", 60, 80),
    MetricSpec("heart_rate", "Heart Rate", "bpm", 60, 100),
    MetricSpec("spo2", "SpO2", "%", 95, 100, lower_is_better_above_normal=False),
    MetricSpec("temperature", "Temperature", "°F", 97.0, 99.0),
    MetricSpec("weight", "Weight", "kg", 0, 999),
    MetricSpec("fasting_blood_sugar", "Fasting Blood Sugar", "mg/dL", 70, 100),
    MetricSpec("post_prandial_blood_sugar", "Post-Prandial Blood Sugar", "mg/dL", 70, 140),
    MetricSpec("hba1c", "HbA1c", "%", 4.0, 5.7),
    MetricSpec("total_cholesterol", "Total Cholesterol", "mg/dL", 100, 200),
    MetricSpec("hdl_cholesterol", "HDL Cholesterol", "mg/dL", 40, 60, lower_is_better_above_normal=False),
    MetricSpec("ldl_cholesterol", "LDL Cholesterol", "mg/dL", 0, 100),
    MetricSpec("triglycerides", "Triglycerides", "mg/dL", 0, 150),
    MetricSpec("hemoglobin", "Hemoglobin", "g/dL", 12.0, 17.0),
    MetricSpec("serum_creatinine", "Serum Creatinine", "mg/dL", 0.6, 1.2),
    MetricSpec("tsh", "TSH", "mIU/L", 0.4, 4.0),
    MetricSpec("vitamin_d", "Vitamin D", "ng/mL", 30, 100, lower_is_better_above_normal=False),
    MetricSpec("uric_acid", "Uric Acid", "mg/dL", 3.5, 7.0),
]

_SPEC_BY_FIELD: dict[str, MetricSpec] = {s.field: s for s in METRIC_SPECS}


def classify_value(spec: MetricSpec, value: float) -> str:
    if value < spec.normal_min:
        return "low"
    if value > spec.normal_max:
        return "high"
    return "normal"


def _is_improvement(spec: MetricSpec, old_val: float, new_val: float) -> str | None:
    """Determine whether moving from old_val to new_val is an improvement."""
    if spec.field == "weight":
        return "stable"

    old_status = classify_value(spec, old_val)
    new_status = classify_value(spec, new_val)

    if old_status == "normal" and new_status == "normal":
        return "stable"

    if old_status == new_status:
        diff = abs(new_val - _nearest_normal_bound(spec, new_val)) - abs(old_val - _nearest_normal_bound(spec, old_val))
        if abs(diff) < 0.01:
            return "stable"
        return "improved" if diff < 0 else "worsened"

    normal_priorities = {"normal": 0, "low": 1, "high": 1}
    if normal_priorities.get(new_status, 1) < normal_priorities.get(old_status, 1):
        return "improved"
    if normal_priorities.get(new_status, 1) > normal_priorities.get(old_status, 1):
        return "worsened"
    return "stable"


def _nearest_normal_bound(spec: MetricSpec, value: float) -> float:
    if value < spec.normal_min:
        return spec.normal_min
    if value > spec.normal_max:
        return spec.normal_max
    return value


def compare_reports(older: HealthReport, newer: HealthReport) -> HealthReportComparison:
    older_resp = HealthReportResponse.model_validate(older)
    newer_resp = HealthReportResponse.model_validate(newer)

    changes: list[MetricChange] = []
    improved = worsened = stable = 0

    for spec in METRIC_SPECS:
        old_val = getattr(older, spec.field)
        new_val = getattr(newer, spec.field)

        if old_val is None and new_val is None:
            continue

        if old_val is not None and new_val is None:
            changes.append(MetricChange(
                metric=spec.field, label=spec.label, unit=spec.unit,
                old_value=old_val, new_value=None,
                status="removed",
                old_status=classify_value(spec, old_val),
            ))
            continue

        if old_val is None and new_val is not None:
            changes.append(MetricChange(
                metric=spec.field, label=spec.label, unit=spec.unit,
                old_value=None, new_value=new_val,
                status="new",
                new_status=classify_value(spec, new_val),
            ))
            continue

        change = round(new_val - old_val, 2)
        pct = round((change / old_val) * 100, 1) if old_val != 0 else 0.0
        status = _is_improvement(spec, old_val, new_val) or "stable"

        if status == "improved":
            improved += 1
        elif status == "worsened":
            worsened += 1
        else:
            stable += 1

        changes.append(MetricChange(
            metric=spec.field, label=spec.label, unit=spec.unit,
            old_value=old_val, new_value=new_val,
            change=change, percent_change=pct,
            status=status,
            old_status=classify_value(spec, old_val),
            new_status=classify_value(spec, new_val),
        ))

    total_compared = improved + worsened + stable
    if total_compared == 0:
        summary = "No comparable metrics between the two reports."
    elif worsened == 0 and improved > 0:
        summary = f"Great progress! {improved} metric{'s' if improved != 1 else ''} improved with {stable} stable."
    elif improved == 0 and worsened > 0:
        summary = f"Attention needed: {worsened} metric{'s' if worsened != 1 else ''} worsened. Consider consulting your doctor."
    else:
        summary = f"{improved} improved, {worsened} need attention, {stable} stable."

    return HealthReportComparison(
        older_report=older_resp,
        newer_report=newer_resp,
        changes=changes,
        summary=summary,
        improved_count=improved,
        worsened_count=worsened,
        stable_count=stable,
    )


def compute_trends(reports: list[HealthReport], metrics: list[str] | None = None) -> HealthReportTrends:
    if metrics is None:
        metrics = [s.field for s in METRIC_SPECS]

    sorted_reports = sorted(reports, key=lambda r: r.report_date)
    trend_list: list[MetricTrend] = []

    for field in metrics:
        spec = _SPEC_BY_FIELD.get(field)
        if spec is None:
            continue

        data_points: list[TrendDataPoint] = []
        for report in sorted_reports:
            val = getattr(report, field, None)
            if val is not None:
                data_points.append(TrendDataPoint(
                    date=report.report_date.isoformat(),
                    value=val,
                ))

        if data_points:
            trend_list.append(MetricTrend(
                metric=spec.field,
                label=spec.label,
                unit=spec.unit,
                normal_min=spec.normal_min if spec.normal_min > 0 else None,
                normal_max=spec.normal_max if spec.normal_max < 999 else None,
                data=data_points,
            ))

    return HealthReportTrends(trends=trend_list, report_count=len(sorted_reports))


def get_health_status(report: HealthReport) -> list[dict]:
    """Return per-metric status for a single report."""
    results: list[dict] = []
    for spec in METRIC_SPECS:
        val = getattr(report, spec.field)
        if val is None:
            continue
        status = classify_value(spec, val)
        results.append({
            "metric": spec.field,
            "label": spec.label,
            "value": val,
            "unit": spec.unit,
            "status": status,
            "normal_range": f"{spec.normal_min} - {spec.normal_max}",
        })
    return results
