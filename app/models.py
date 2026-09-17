from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AssetStatus(StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    down = "down"
    unknown = "unknown"


class CheckType(StrEnum):
    ping = "ping"
    tcp = "tcp"
    http = "http"
    dns = "dns"


class AlertStatus(StrEnum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class UserRole(StrEnum):
    administrator = "administrator"
    operator = "operator"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default=UserRole.viewer.value)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    location: Mapped[str] = mapped_column(String(160), default="Unknown")
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    assets: Mapped[list["Asset"]] = relationship(back_populates="site", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    name: Mapped[str] = mapped_column(String(160))
    hostname: Mapped[str] = mapped_column(String(255))
    asset_type: Mapped[str] = mapped_column(String(80), default="network-device")
    status: Mapped[str] = mapped_column(String(30), default=AssetStatus.unknown.value)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    site: Mapped[Site] = relationship(back_populates="assets")
    checks: Mapped[list["Check"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    telemetry: Mapped[list["Telemetry"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    name: Mapped[str] = mapped_column(String(160))
    check_type: Mapped[str] = mapped_column(String(30))
    target: Mapped[str] = mapped_column(String(255))
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(default=True)
    asset: Mapped[Asset] = relationship(back_populates="checks")


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    check_id: Mapped[int | None] = mapped_column(ForeignKey("checks.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss: Mapped[float] = mapped_column(Float, default=0)
    availability: Mapped[float] = mapped_column(Float, default=100)
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    asset: Mapped[Asset] = relationship(back_populates="telemetry")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    status: Mapped[str] = mapped_column(String(30), default=AlertStatus.open.value)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
