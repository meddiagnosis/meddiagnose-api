"""
Wearable device integration API.

Handles OAuth connect/disconnect flows for Fitbit, Google Fit, and Apple Health,
plus manual and automatic data sync.
"""

import secrets
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.fitness_log import FitnessLog
from app.models.wearable_integration import WearableIntegration
from app.core.config import get_settings
from app.schemas.wearable_integration import (
    WearableConnectionResponse,
    WearableConnectionList,
    OAuthStartResponse,
    SyncResult,
    SyncAllResult,
    LiveVitals,
)
from app.services.wearable_sync import (
    PROVIDER_INFO,
    get_fitbit_auth_url,
    get_google_fit_auth_url,
    exchange_fitbit_code,
    exchange_google_fit_code,
    sync_fitbit_data,
    sync_google_fit_data,
    records_to_fitness_logs,
)
from app.services.health_alerts import check_fitness_log_vitals
from app.core.cache import oauth_state_set, oauth_state_get

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wearables", tags=["Wearable Integrations"])


@router.get("/connections", response_model=WearableConnectionList)
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(WearableIntegration).where(WearableIntegration.user_id == current_user.id)
    result = await db.execute(q)
    integrations = result.scalars().all()

    connected_providers = {i.provider for i in integrations if i.is_active}

    connections = []
    for integration in integrations:
        if integration.is_active:
            connections.append(WearableConnectionResponse(
                id=integration.id,
                provider=integration.provider,
                is_active=integration.is_active,
                device_name=integration.device_name,
                external_user_id=integration.external_user_id,
                last_synced_at=integration.last_synced_at,
                created_at=integration.created_at,
                connected=True,
            ))

    available = []
    for provider, info in PROVIDER_INFO.items():
        available.append({
            "provider": provider,
            "name": info["name"],
            "description": info["description"],
            "icon": info["icon"],
            "capabilities": info["capabilities"],
            "connected": provider in connected_providers,
            "requires_mobile": info.get("requires_mobile", False),
        })

    return WearableConnectionList(connections=connections, available_providers=available)


@router.post("/connect/{provider}", response_model=OAuthStartResponse)
async def start_oauth(
    provider: str,
    current_user: User = Depends(get_current_user),
):
    if provider not in ("fitbit", "google_fit"):
        raise HTTPException(
            400,
            f"Connect {provider} via the MedDiagnose mobile app. Web OAuth is available for Fitbit and Google Fit.",
        )

    state = secrets.token_urlsafe(32)
    await oauth_state_set(state, {
        "user_id": current_user.id,
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    if provider == "fitbit":
        auth_url = get_fitbit_auth_url(state)
    else:
        auth_url = get_google_fit_auth_url(state)

    return OAuthStartResponse(auth_url=auth_url, provider=provider, state=state)


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    state_data = await oauth_state_get(state)
    if not state_data:
        raise HTTPException(400, "Invalid or expired OAuth state")

    if state_data["provider"] != provider:
        raise HTTPException(400, "Provider mismatch")

    user_id = state_data["user_id"]

    try:
        if provider == "fitbit":
            tokens = await exchange_fitbit_code(code)
        elif provider == "google_fit":
            tokens = await exchange_google_fit_code(code)
        else:
            raise HTTPException(400, f"Unsupported provider: {provider}")
    except Exception as e:
        logger.error(f"OAuth token exchange failed for {provider}: {e}")
        raise HTTPException(400, f"Failed to authenticate with {provider}: {str(e)}")

    expires_in = tokens.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    existing_q = select(WearableIntegration).where(
        WearableIntegration.user_id == user_id,
        WearableIntegration.provider == provider,
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()

    if existing:
        existing.access_token = tokens["access_token"]
        existing.refresh_token = tokens.get("refresh_token", existing.refresh_token)
        existing.token_type = tokens.get("token_type", "Bearer")
        existing.scope = tokens.get("scope", "")
        existing.expires_at = expires_at
        existing.is_active = True
        existing.external_user_id = tokens.get("user_id", "")
    else:
        integration = WearableIntegration(
            user_id=user_id,
            provider=provider,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_type=tokens.get("token_type", "Bearer"),
            scope=tokens.get("scope", ""),
            expires_at=expires_at,
            external_user_id=tokens.get("user_id", ""),
            is_active=True,
        )
        db.add(integration)

    await db.commit()

    # Auto-sync data immediately after connection — import 30 days for rich first-time experience
    synced = False
    integration = (await db.execute(
        select(WearableIntegration).where(
            WearableIntegration.user_id == user_id,
            WearableIntegration.provider == provider,
        )
    )).scalar_one_or_none()
    if integration:
        try:
            if provider == "fitbit":
                raw_data = await sync_fitbit_data(integration, days=30)
            elif provider == "google_fit":
                raw_data = await sync_google_fit_data(integration, days=30)
            else:
                raw_data = {"records": []}
            if raw_data.get("records"):
                if raw_data.get("device_name"):
                    integration.device_name = raw_data["device_name"]
                since = date.today() - timedelta(days=30)
                existing_q = select(FitnessLog).where(
                    FitnessLog.user_id == user_id,
                    FitnessLog.log_date >= since,
                )
                existing_map = {l.log_date: l for l in (await db.execute(existing_q)).scalars().all()}
                new_logs, created, updated = records_to_fitness_logs(
                    raw_data["records"], user_id, existing_map
                )
                for log in new_logs:
                    if log.id is None:
                        db.add(log)
                integration.last_synced_at = datetime.now(timezone.utc)
                await db.commit()
                synced = True
        except Exception as e:
            logger.warning(f"Auto-sync after OAuth failed for {provider}: {e}")

    frontend_url = getattr(get_settings(), "FRONTEND_URL", "http://localhost:5173")
    qs = f"connected={provider}" + ("&synced=1" if synced else "")
    return RedirectResponse(url=f"{frontend_url.rstrip('/')}/fitness-tracker?{qs}")


@router.post("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(WearableIntegration).where(
        WearableIntegration.user_id == current_user.id,
        WearableIntegration.provider == provider,
    )
    integration = (await db.execute(q)).scalar_one_or_none()
    if not integration:
        raise HTTPException(404, f"No {provider} connection found")

    integration.is_active = False
    integration.access_token = None
    integration.refresh_token = None
    await db.commit()

    return {"message": f"Disconnected from {PROVIDER_INFO.get(provider, {}).get('name', provider)}"}


@router.post("/sync/{provider}", response_model=SyncResult)
async def sync_provider(
    provider: str,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(WearableIntegration).where(
        WearableIntegration.user_id == current_user.id,
        WearableIntegration.provider == provider,
        WearableIntegration.is_active == True,
    )
    integration = (await db.execute(q)).scalar_one_or_none()
    if not integration:
        raise HTTPException(404, f"No active {provider} connection found. Please connect first.")

    try:
        if provider == "fitbit":
            raw_data = await sync_fitbit_data(integration, days)
        elif provider == "google_fit":
            raw_data = await sync_google_fit_data(integration, days)
        else:
            raise HTTPException(400, f"Sync not supported for {provider}")
    except Exception as e:
        logger.error(f"Sync failed for {provider}: {e}")
        raise HTTPException(502, f"Failed to fetch data from {provider}: {str(e)}")

    if raw_data.get("device_name"):
        integration.device_name = raw_data["device_name"]

    since = date.today() - timedelta(days=days)
    existing_q = select(FitnessLog).where(
        FitnessLog.user_id == current_user.id,
        FitnessLog.log_date >= since,
    )
    existing_logs_result = await db.execute(existing_q)
    existing_map = {l.log_date: l for l in existing_logs_result.scalars().all()}

    new_logs, created, updated = records_to_fitness_logs(
        raw_data["records"], current_user.id, existing_map
    )

    for log in new_logs:
        if log.id is None:
            db.add(log)

    now = datetime.now(timezone.utc)
    integration.last_synced_at = now
    await db.commit()

    for log in new_logs:
        if (log.heart_rate is not None or log.spo2 is not None) and log.id:
            try:
                await check_fitness_log_vitals(db, current_user.id, log.id, log.heart_rate, log.spo2)
            except Exception:
                pass
    await db.commit()

    return SyncResult(
        provider=provider,
        days_synced=days,
        records_created=created,
        records_updated=updated,
        last_synced_at=now,
        message=f"Synced {created + updated} records from {PROVIDER_INFO[provider]['name']} ({created} new, {updated} updated)",
    )


@router.post("/sync-apple-health")
async def sync_apple_health_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Receive Apple Health data pushed from the mobile app."""
    body = await request.json()
    records = body.get("records", [])

    if not records:
        raise HTTPException(400, "No records provided")

    q = select(WearableIntegration).where(
        WearableIntegration.user_id == current_user.id,
        WearableIntegration.provider == "apple_health",
    )
    integration = (await db.execute(q)).scalar_one_or_none()

    if not integration:
        integration = WearableIntegration(
            user_id=current_user.id,
            provider="apple_health",
            is_active=True,
            device_name=body.get("device_name", "Apple Watch"),
        )
        db.add(integration)

    parsed_records = []
    for r in records:
        try:
            d = date.fromisoformat(r["date"])
            parsed_records.append({
                "date": d,
                "steps": r.get("steps"),
                "calories_burned": r.get("calories_burned") or r.get("active_calories"),
                "active_minutes": r.get("active_minutes") or r.get("exercise_minutes"),
                "distance_km": r.get("distance_km"),
                "sleep_hours": r.get("sleep_hours"),
                "weight_kg": r.get("weight_kg"),
                "heart_rate": r.get("heart_rate"),
                "spo2": r.get("spo2"),
            })
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping invalid Apple Health record: {e}")

    dates = [r["date"] for r in parsed_records]
    if dates:
        min_date = min(dates)
        existing_q = select(FitnessLog).where(
            FitnessLog.user_id == current_user.id,
            FitnessLog.log_date >= min_date,
        )
        existing_map = {l.log_date: l for l in (await db.execute(existing_q)).scalars().all()}
    else:
        existing_map = {}

    new_logs, created, updated = records_to_fitness_logs(
        parsed_records, current_user.id, existing_map
    )

    for log in new_logs:
        if log.id is None:
            db.add(log)

    now = datetime.now(timezone.utc)
    integration.last_synced_at = now
    integration.device_name = body.get("device_name", integration.device_name or "Apple Watch")
    await db.commit()

    for log in new_logs:
        if (log.heart_rate is not None or log.spo2 is not None) and log.id:
            try:
                await check_fitness_log_vitals(db, current_user.id, log.id, log.heart_rate, log.spo2)
            except Exception:
                pass
    await db.commit()

    return SyncResult(
        provider="apple_health",
        days_synced=len(parsed_records),
        records_created=created,
        records_updated=updated,
        last_synced_at=now,
        message=f"Synced {created + updated} records from Apple Health ({created} new, {updated} updated)",
    )


@router.post("/sync-all", response_model=SyncAllResult)
async def sync_all_connected(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync data from all connected wearable devices at once for live tracking."""
    q = select(WearableIntegration).where(
        WearableIntegration.user_id == current_user.id,
        WearableIntegration.is_active == True,
        WearableIntegration.provider.in_(["fitbit", "google_fit"]),
    )
    result = await db.execute(q)
    integrations = result.scalars().all()

    if not integrations:
        raise HTTPException(404, "No connected devices. Connect Fitbit or Google Fit first.")

    results_list: list[SyncResult] = []
    total_created = 0
    total_updated = 0
    synced_providers: list[str] = []
    all_new_logs: list = []

    for integration in integrations:
        try:
            if integration.provider == "fitbit":
                raw_data = await sync_fitbit_data(integration, days)
            elif integration.provider == "google_fit":
                raw_data = await sync_google_fit_data(integration, days)
            else:
                continue

            if raw_data.get("device_name"):
                integration.device_name = raw_data["device_name"]

            since = date.today() - timedelta(days=days)
            existing_q = select(FitnessLog).where(
                FitnessLog.user_id == current_user.id,
                FitnessLog.log_date >= since,
            )
            existing_map = {l.log_date: l for l in (await db.execute(existing_q)).scalars().all()}

            new_logs, created, updated = records_to_fitness_logs(
                raw_data["records"], current_user.id, existing_map
            )
            all_new_logs.extend(new_logs)
            for log in new_logs:
                if log.id is None:
                    db.add(log)

            now = datetime.now(timezone.utc)
            integration.last_synced_at = now
            synced_providers.append(integration.provider)
            total_created += created
            total_updated += updated
            results_list.append(SyncResult(
                provider=integration.provider,
                days_synced=days,
                records_created=created,
                records_updated=updated,
                last_synced_at=now,
                message=f"{PROVIDER_INFO.get(integration.provider, {}).get('name', integration.provider)}: {created + updated} records",
            ))
        except Exception as e:
            logger.error(f"Sync failed for {integration.provider}: {e}")

    await db.commit()

    for log in all_new_logs:
        if (log.heart_rate is not None or log.spo2 is not None) and log.id:
            try:
                await check_fitness_log_vitals(db, current_user.id, log.id, log.heart_rate, log.spo2)
            except Exception:
                pass
    await db.commit()

    return SyncAllResult(
        synced_providers=synced_providers,
        total_created=total_created,
        total_updated=total_updated,
        results=results_list,
        message=f"Synced {total_created + total_updated} records from {len(synced_providers)} device(s)",
    )


@router.get("/live", response_model=LiveVitals)
async def get_live_vitals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest vitals from connected devices for live patient monitoring."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Latest fitness log with vitals (today or yesterday)
    latest_q = (
        select(FitnessLog)
        .where(
            FitnessLog.user_id == current_user.id,
            FitnessLog.log_date.in_([today, yesterday]),
        )
        .order_by(FitnessLog.log_date.desc(), FitnessLog.created_at.desc())
    )
    logs_result = await db.execute(latest_q)
    logs = list(logs_result.scalars().all())

    today_log = next((l for l in logs if l.log_date == today), None)
    yesterday_log = next((l for l in logs if l.log_date == yesterday), None)

    # Latest integration for last_synced_at
    int_q = select(WearableIntegration).where(
        WearableIntegration.user_id == current_user.id,
        WearableIntegration.is_active == True,
    ).order_by(WearableIntegration.last_synced_at.desc().nullslast())
    int_result = await db.execute(int_q)
    latest_int = int_result.scalars().first()

    return LiveVitals(
        heart_rate=today_log.heart_rate if today_log else (yesterday_log.heart_rate if yesterday_log else None),
        spo2=today_log.spo2 if today_log else (yesterday_log.spo2 if yesterday_log else None),
        steps_today=today_log.steps if today_log else None,
        active_minutes_today=today_log.active_minutes if today_log else None,
        sleep_last_night=yesterday_log.sleep_hours if yesterday_log else None,
        weight_kg=(today_log or yesterday_log).weight_kg if (today_log or yesterday_log) else None,
        last_synced_at=latest_int.last_synced_at if latest_int else None,
        source_provider=latest_int.provider if latest_int else None,
    )
