from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WearableConnectionResponse(BaseModel):
    id: int
    provider: str
    is_active: bool
    device_name: Optional[str] = None
    external_user_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    connected: bool = True

    model_config = {"from_attributes": True}


class WearableConnectionList(BaseModel):
    connections: list[WearableConnectionResponse]
    available_providers: list[dict]


class OAuthStartResponse(BaseModel):
    auth_url: str
    provider: str
    state: str


class SyncResult(BaseModel):
    provider: str
    days_synced: int
    records_created: int
    records_updated: int
    last_synced_at: datetime
    message: str


class WearableDeviceInfo(BaseModel):
    provider: str
    device_name: Optional[str] = None
    battery: Optional[str] = None
    last_sync_time: Optional[str] = None


class SyncAllResult(BaseModel):
    synced_providers: list[str]
    total_created: int
    total_updated: int
    results: list[SyncResult]
    message: str


class LiveVitals(BaseModel):
    """Latest vitals from connected devices for live patient monitoring."""
    heart_rate: Optional[float] = None  # bpm
    spo2: Optional[float] = None  # %
    steps_today: Optional[int] = None
    active_minutes_today: Optional[int] = None
    sleep_last_night: Optional[float] = None
    weight_kg: Optional[float] = None
    last_synced_at: Optional[datetime] = None
    source_provider: Optional[str] = None
