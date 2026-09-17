from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Alert, AlertStatus, Asset, AssetStatus, Check, Telemetry
from app.monitoring import CheckResult, run_check


async def execute_check(session: AsyncSession, check: Check) -> Telemetry:
    result: CheckResult = await run_check(check.check_type, check.target)
    telemetry = Telemetry(
        asset_id=check.asset_id,
        check_id=check.id,
        recorded_at=datetime.now(timezone.utc),
        latency_ms=result.latency_ms,
        packet_loss=result.packet_loss,
        availability=100.0 if result.success else 0.0,
        payload={"message": result.message, "success": result.success},
    )
    check.asset.status = AssetStatus.healthy.value if result.success else AssetStatus.down.value
    session.add(telemetry)
    await update_alert(session, check.asset, check, result)
    await session.commit()
    await session.refresh(telemetry)
    return telemetry


async def update_alert(session: AsyncSession, asset: Asset, check: Check, result: CheckResult) -> None:
    open_alert = await session.scalar(
        select(Alert).where(
            Alert.asset_id == asset.id,
            Alert.status.in_([AlertStatus.open.value, AlertStatus.acknowledged.value]),
            Alert.title == f"{check.name} failed",
        )
    )
    if result.success:
        if open_alert:
            open_alert.status = AlertStatus.resolved.value
        return
    if not open_alert:
        session.add(
            Alert(
                asset_id=asset.id,
                severity="critical",
                title=f"{check.name} failed",
                message=result.message,
            )
        )


async def dashboard_overview(session: AsyncSession) -> dict:
    assets = list((await session.scalars(select(Asset))).all())
    alerts = list(
        (
            await session.scalars(
                select(Alert).where(Alert.status != AlertStatus.resolved.value).order_by(desc(Alert.created_at))
            )
        ).all()
    )
    telemetry = list(
        (
            await session.scalars(select(Telemetry).order_by(desc(Telemetry.recorded_at)).limit(24))
        ).all()
    )
    average_latency = await session.scalar(select(func.avg(Telemetry.latency_ms)))
    return {
        "assets_total": len(assets),
        "assets_healthy": sum(asset.status == AssetStatus.healthy.value for asset in assets),
        "assets_down": sum(asset.status == AssetStatus.down.value for asset in assets),
        "alerts_open": len(alerts),
        "average_latency_ms": round(average_latency or 0, 2),
        "telemetry": telemetry,
        "alerts": alerts,
    }


async def list_assets(session: AsyncSession) -> list[Asset]:
    return list((await session.scalars(select(Asset).options(selectinload(Asset.site)))).all())
