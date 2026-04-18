"""
Wearable device sync service.

Pulls fitness data from Fitbit, Google Fit, and Apple Health (via mobile relay)
and upserts into FitnessLog records.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from app.models.fitness_log import FitnessLog
from app.models.wearable_integration import WearableIntegration
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API_BASE = "https://api.fitbit.com"

GOOGLE_FIT_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_FIT_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_FIT_API_BASE = "https://www.googleapis.com/fitness/v1"

PROVIDER_INFO = {
    "fitbit": {
        "name": "Fitbit",
        "description": "Sync steps, heart rate, SpO2, sleep, and activity from Fitbit trackers & watches",
        "icon": "fitbit",
        "capabilities": ["steps", "heart_rate", "spo2", "sleep", "calories", "distance", "active_minutes", "weight"],
    },
    "google_fit": {
        "name": "Google Fit",
        "description": "Sync steps, heart rate, and activity from Google Fit (Pixel Watch, Wear OS)",
        "icon": "google_fit",
        "capabilities": ["steps", "calories", "distance", "active_minutes", "weight", "heart_rate"],
    },
    "apple_health": {
        "name": "Apple Health / Apple Watch",
        "description": "Sync heart rate, SpO2, steps, and sleep from Apple Watch via the MedDiagnose mobile app",
        "icon": "apple_health",
        "capabilities": ["steps", "heart_rate", "spo2", "sleep", "calories", "distance", "active_minutes", "weight"],
        "requires_mobile": True,
    },
    "samsung_health": {
        "name": "Samsung Health",
        "description": "Sync from Galaxy Watch and Samsung Health app — connect via mobile app",
        "icon": "samsung_health",
        "capabilities": ["steps", "heart_rate", "spo2", "sleep", "calories", "distance", "weight"],
        "requires_mobile": True,
    },
    "garmin": {
        "name": "Garmin Connect",
        "description": "Sync from Garmin watches — connect via Garmin Connect mobile app",
        "icon": "garmin",
        "capabilities": ["steps", "heart_rate", "spo2", "sleep", "calories", "distance", "active_minutes", "weight"],
        "requires_mobile": True,
    },
}


def get_fitbit_auth_url(state: str) -> str:
    client_id = getattr(settings, "FITBIT_CLIENT_ID", "")
    redirect_uri = getattr(settings, "FITBIT_REDIRECT_URI", "")
    scopes = "activity heartrate sleep weight profile oxygen_saturation"
    return (
        f"{FITBIT_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&state={state}"
        f"&prompt=login consent"
    )


def get_google_fit_auth_url(state: str) -> str:
    client_id = getattr(settings, "GOOGLE_FIT_CLIENT_ID", "")
    redirect_uri = getattr(settings, "GOOGLE_FIT_REDIRECT_URI", "")
    scopes = (
        "https://www.googleapis.com/auth/fitness.activity.read "
        "https://www.googleapis.com/auth/fitness.body.read "
        "https://www.googleapis.com/auth/fitness.sleep.read "
        "https://www.googleapis.com/auth/fitness.heart_rate.read"
    )
    return (
        f"{GOOGLE_FIT_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent"
    )


async def exchange_fitbit_code(code: str) -> dict:
    client_id = getattr(settings, "FITBIT_CLIENT_ID", "")
    client_secret = getattr(settings, "FITBIT_CLIENT_SECRET", "")
    redirect_uri = getattr(settings, "FITBIT_REDIRECT_URI", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def exchange_google_fit_code(code: str) -> dict:
    client_id = getattr(settings, "GOOGLE_FIT_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_FIT_CLIENT_SECRET", "")
    redirect_uri = getattr(settings, "GOOGLE_FIT_REDIRECT_URI", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_FIT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_fitbit_token(integration: WearableIntegration) -> dict:
    client_id = getattr(settings, "FITBIT_CLIENT_ID", "")
    client_secret = getattr(settings, "FITBIT_CLIENT_SECRET", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": integration.refresh_token,
            },
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_google_fit_token(integration: WearableIntegration) -> dict:
    client_id = getattr(settings, "GOOGLE_FIT_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_FIT_CLIENT_SECRET", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_FIT_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": integration.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def _ensure_valid_token(integration: WearableIntegration) -> str:
    """Refresh token if expired, return the current access token."""
    now = datetime.now(timezone.utc)
    if integration.expires_at and integration.expires_at < now:
        logger.info(f"Refreshing {integration.provider} token for user {integration.user_id}")
        if integration.provider == "fitbit":
            tokens = await refresh_fitbit_token(integration)
        elif integration.provider == "google_fit":
            tokens = await refresh_google_fit_token(integration)
        else:
            raise ValueError(f"Cannot refresh token for {integration.provider}")

        integration.access_token = tokens["access_token"]
        if "refresh_token" in tokens:
            integration.refresh_token = tokens["refresh_token"]
        integration.expires_at = now + timedelta(seconds=tokens.get("expires_in", 3600))

    return integration.access_token


async def sync_fitbit_data(
    integration: WearableIntegration, days: int = 7
) -> dict:
    """Pull activity, sleep, and weight data from Fitbit for the last N days."""
    token = await _ensure_valid_token(integration)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    start = today - timedelta(days=days - 1)
    results = {"records": [], "device_name": None}

    async with httpx.AsyncClient(base_url=FITBIT_API_BASE, headers=headers, timeout=30) as client:
        # Device info
        try:
            dev_resp = await client.get("/1/user/-/devices.json")
            if dev_resp.status_code == 200:
                devices = dev_resp.json()
                if devices:
                    results["device_name"] = f"{devices[0].get('deviceVersion', 'Fitbit')} ({devices[0].get('type', '')})"
        except Exception as e:
            logger.warning(f"Failed to fetch Fitbit devices: {e}")

        for day_offset in range(days):
            d = start + timedelta(days=day_offset)
            ds = d.strftime("%Y-%m-%d")
            record: dict = {"date": d}

            # Activity summary
            try:
                resp = await client.get(f"/1/user/-/activities/date/{ds}.json")
                if resp.status_code == 200:
                    summary = resp.json().get("summary", {})
                    record["steps"] = summary.get("steps")
                    record["calories_burned"] = summary.get("caloriesOut")
                    record["active_minutes"] = (
                        summary.get("fairlyActiveMinutes", 0) +
                        summary.get("veryActiveMinutes", 0)
                    )
                    distances = summary.get("distances", [])
                    total_dist = next((d["distance"] for d in distances if d.get("activity") == "total"), None)
                    if total_dist is not None:
                        record["distance_km"] = round(total_dist, 2)
            except Exception as e:
                logger.warning(f"Fitbit activity fetch failed for {ds}: {e}")

            # Sleep
            try:
                resp = await client.get(f"/1.2/user/-/sleep/date/{ds}.json")
                if resp.status_code == 200:
                    sleep_data = resp.json()
                    sleep_summary = sleep_data.get("summary", {})
                    total_min = sleep_summary.get("totalMinutesAsleep", 0)
                    if total_min:
                        record["sleep_hours"] = round(total_min / 60, 1)
            except Exception as e:
                logger.warning(f"Fitbit sleep fetch failed for {ds}: {e}")

            # Weight (body)
            try:
                resp = await client.get(f"/1/user/-/body/log/weight/date/{ds}.json")
                if resp.status_code == 200:
                    weights = resp.json().get("weight", [])
                    if weights:
                        record["weight_kg"] = weights[-1].get("weight")
            except Exception as e:
                logger.warning(f"Fitbit weight fetch failed for {ds}: {e}")

            # Resting heart rate
            try:
                resp = await client.get(f"/1/user/-/activities/heart/date/{ds}/1d.json")
                if resp.status_code == 200:
                    hr_data = resp.json().get("activities-heart", [])
                    if hr_data:
                        rhr = hr_data[0].get("value", {}).get("restingHeartRate")
                        if rhr:
                            record["heart_rate"] = float(rhr)
            except Exception as e:
                logger.warning(f"Fitbit heart rate fetch failed for {ds}: {e}")

            # SpO2 (blood oxygen) — available on Fitbit Sense, Versa 3, Charge 5+
            try:
                resp = await client.get(f"/1/user/-/spo2/date/{ds}/{ds}.json")
                if resp.status_code == 200:
                    spo2_list = resp.json() if isinstance(resp.json(), list) else []
                    for item in spo2_list:
                        if item.get("dateTime") == ds:
                            val = item.get("value") or {}
                            avg_spo2 = val.get("avg")
                            if avg_spo2 is not None:
                                record["spo2"] = float(avg_spo2)
                            break
            except Exception as e:
                logger.warning(f"Fitbit SpO2 fetch failed for {ds}: {e}")

            if any(v is not None for k, v in record.items() if k != "date"):
                results["records"].append(record)

    return results


async def sync_google_fit_data(
    integration: WearableIntegration, days: int = 7
) -> dict:
    """Pull activity and body data from Google Fit for the last N days."""
    token = await _ensure_valid_token(integration)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    start = today - timedelta(days=days - 1)
    results = {"records": [], "device_name": "Google Fit / Wear OS"}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        for day_offset in range(days):
            d = start + timedelta(days=day_offset)
            record: dict = {"date": d}

            start_ns = int(datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1e9)
            end_ns = int(datetime.combine(d + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1e9)

            # Steps
            try:
                resp = await client.post(
                    f"{GOOGLE_FIT_API_BASE}/users/me/dataset:aggregate",
                    json={
                        "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
                        "bucketByTime": {"durationMillis": 86400000},
                        "startTimeMillis": start_ns // 1000000,
                        "endTimeMillis": end_ns // 1000000,
                    },
                )
                if resp.status_code == 200:
                    buckets = resp.json().get("bucket", [])
                    for bucket in buckets:
                        for dataset in bucket.get("dataset", []):
                            for point in dataset.get("point", []):
                                for val in point.get("value", []):
                                    record["steps"] = val.get("intVal", 0)
            except Exception as e:
                logger.warning(f"Google Fit steps fetch failed for {d}: {e}")

            # Calories
            try:
                resp = await client.post(
                    f"{GOOGLE_FIT_API_BASE}/users/me/dataset:aggregate",
                    json={
                        "aggregateBy": [{"dataTypeName": "com.google.calories.expended"}],
                        "bucketByTime": {"durationMillis": 86400000},
                        "startTimeMillis": start_ns // 1000000,
                        "endTimeMillis": end_ns // 1000000,
                    },
                )
                if resp.status_code == 200:
                    buckets = resp.json().get("bucket", [])
                    for bucket in buckets:
                        for dataset in bucket.get("dataset", []):
                            for point in dataset.get("point", []):
                                for val in point.get("value", []):
                                    record["calories_burned"] = int(val.get("fpVal", 0))
            except Exception as e:
                logger.warning(f"Google Fit calories fetch failed for {d}: {e}")

            # Distance
            try:
                resp = await client.post(
                    f"{GOOGLE_FIT_API_BASE}/users/me/dataset:aggregate",
                    json={
                        "aggregateBy": [{"dataTypeName": "com.google.distance.delta"}],
                        "bucketByTime": {"durationMillis": 86400000},
                        "startTimeMillis": start_ns // 1000000,
                        "endTimeMillis": end_ns // 1000000,
                    },
                )
                if resp.status_code == 200:
                    buckets = resp.json().get("bucket", [])
                    for bucket in buckets:
                        for dataset in bucket.get("dataset", []):
                            for point in dataset.get("point", []):
                                for val in point.get("value", []):
                                    record["distance_km"] = round(val.get("fpVal", 0) / 1000, 2)
            except Exception as e:
                logger.warning(f"Google Fit distance fetch failed for {d}: {e}")

            # Weight
            try:
                resp = await client.post(
                    f"{GOOGLE_FIT_API_BASE}/users/me/dataset:aggregate",
                    json={
                        "aggregateBy": [{"dataTypeName": "com.google.weight"}],
                        "bucketByTime": {"durationMillis": 86400000},
                        "startTimeMillis": start_ns // 1000000,
                        "endTimeMillis": end_ns // 1000000,
                    },
                )
                if resp.status_code == 200:
                    buckets = resp.json().get("bucket", [])
                    for bucket in buckets:
                        for dataset in bucket.get("dataset", []):
                            for point in dataset.get("point", []):
                                for val in point.get("value", []):
                                    record["weight_kg"] = round(val.get("fpVal", 0), 1)
            except Exception as e:
                logger.warning(f"Google Fit weight fetch failed for {d}: {e}")

            # Heart rate
            try:
                resp = await client.post(
                    f"{GOOGLE_FIT_API_BASE}/users/me/dataset:aggregate",
                    json={
                        "aggregateBy": [{"dataTypeName": "com.google.heart_rate.bpm"}],
                        "bucketByTime": {"durationMillis": 86400000},
                        "startTimeMillis": start_ns // 1000000,
                        "endTimeMillis": end_ns // 1000000,
                    },
                )
                if resp.status_code == 200:
                    buckets = resp.json().get("bucket", [])
                    for bucket in buckets:
                        for dataset in bucket.get("dataset", []):
                            for point in dataset.get("point", []):
                                for val in point.get("value", []):
                                    record["heart_rate"] = float(val.get("fpVal", 0))
            except Exception as e:
                logger.warning(f"Google Fit heart rate fetch failed for {d}: {e}")

            if any(v is not None for k, v in record.items() if k != "date"):
                results["records"].append(record)

    return results


def records_to_fitness_logs(
    records: list[dict], user_id: int, existing_logs: dict[date, FitnessLog]
) -> tuple[list[FitnessLog], int, int]:
    """Convert raw wearable records into FitnessLog objects, merging with existing data."""
    created = 0
    updated = 0
    result_logs: list[FitnessLog] = []
    vitals_fields = ["heart_rate", "spo2"]
    activity_fields = ["steps", "calories_burned", "active_minutes", "distance_km",
                       "sleep_hours", "weight_kg"]
    all_fields = activity_fields + vitals_fields

    for record in records:
        d = record["date"]
        existing = existing_logs.get(d)

        # Normalize heart_rate from heart_rate_resting for backward compat
        if "heart_rate_resting" in record and "heart_rate" not in record:
            record["heart_rate"] = record["heart_rate_resting"]

        if existing:
            changed = False
            for field in all_fields:
                new_val = record.get(field)
                if new_val is not None:
                    old_val = getattr(existing, field, None)
                    if old_val is None or (field in ("steps", "calories_burned", "active_minutes") and new_val > old_val):
                        setattr(existing, field, new_val)
                        changed = True
            if changed:
                updated += 1
                result_logs.append(existing)
        else:
            log = FitnessLog(
                user_id=user_id,
                log_date=d,
                steps=record.get("steps"),
                calories_burned=record.get("calories_burned"),
                active_minutes=record.get("active_minutes"),
                distance_km=record.get("distance_km"),
                sleep_hours=record.get("sleep_hours"),
                weight_kg=record.get("weight_kg"),
                heart_rate=record.get("heart_rate"),
                spo2=record.get("spo2"),
            )
            created += 1
            result_logs.append(log)

    return result_logs, created, updated
