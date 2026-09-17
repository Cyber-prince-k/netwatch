from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, Check, Site


async def seed_demo_data(session: AsyncSession) -> None:
    if await session.scalar(select(Site.id).limit(1)):
        return
    hq = Site(name="North America HQ", location="New York", timezone="America/New_York")
    branch = Site(name="London Branch", location="London", timezone="Europe/London")
    session.add_all([hq, branch])
    await session.flush()
    assets = [
        Asset(name="Core Router", hostname="10.10.0.1", asset_type="router", site=hq, status="unknown", tags=["core", "snmpv3"]),
        Asset(name="Web Cluster", hostname="https://example.com", asset_type="service", site=hq, status="unknown", tags=["production", "http"]),
        Asset(name="London Firewall", hostname="192.168.40.1", asset_type="firewall", site=branch, status="unknown", tags=["edge", "security"]),
    ]
    session.add_all(assets)
    await session.flush()
    session.add_all([
        Check(name="Core router reachability", check_type="ping", target="127.0.0.1", asset_id=assets[0].id),
        Check(name="Public web availability", check_type="http", target="https://example.com", asset_id=assets[1].id),
        Check(name="Firewall reachability", check_type="ping", target="127.0.0.1", asset_id=assets[2].id),
    ])
    await session.commit()
