from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    site_id: int
    name: str = Field(min_length=2, max_length=160)
    hostname: str
    asset_type: str = "network-device"
    tags: list[str] = []


class CheckCreate(BaseModel):
    name: str
    check_type: str
    target: str
    interval_seconds: int = Field(default=60, ge=10)


class AssetView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    asset_type: str
    status: str
    site_id: int
    tags: list[str]


class TelemetryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recorded_at: datetime
    latency_ms: float | None
    packet_loss: float
    availability: float
    cpu_percent: float | None
    memory_percent: float | None


class AlertView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    severity: str
    status: str
    title: str
    message: str
    created_at: datetime
