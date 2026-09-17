from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal, get_session, init_db
from app.models import Alert, AlertStatus, Asset, Check
from app.schemas import AssetCreate, AssetView, AlertView, CheckCreate, TelemetryView
from app.seed import seed_demo_data
from app.services import dashboard_overview, execute_check, list_assets

settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        await seed_demo_data(session)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan, docs_url="/swagger-ui", redoc_url="/redoc")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    overview = await dashboard_overview(session)
    return templates.TemplateResponse(request, "dashboard.html", {"overview": overview})


async def page_context(request: Request, session: AsyncSession) -> dict:
    overview = await dashboard_overview(session)
    return {"request": request, "overview": overview}


@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    context["assets"] = await list_assets(session)
    return templates.TemplateResponse(request, "inventory.html", context)


@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    context["alerts"] = list((await session.scalars(select(Alert).order_by(desc(Alert.created_at)))).all())
    return templates.TemplateResponse(request, "alerts.html", context)


@app.get("/checks", response_class=HTMLResponse)
async def checks_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    context["checks"] = list((await session.scalars(select(Check).order_by(Check.name))).all())
    return templates.TemplateResponse(request, "checks.html", context)


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    return templates.TemplateResponse(request, "reports.html", context)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    return templates.TemplateResponse(request, "settings.html", context)
    
@app.get("/docs", response_class=HTMLResponse)
async def api_reference_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    context["endpoints"] = [
        ("GET", "/health", "Service liveness and environment status."),
        ("GET", "/api/v1/overview", "Dashboard metrics, recent telemetry, and active alerts."),
        ("GET", "/api/v1/assets", "Monitored asset inventory."),
        ("POST", "/api/v1/assets", "Create a monitored asset."),
        ("POST", "/api/v1/assets/{asset_id}/checks", "Attach a monitoring check to an asset."),
        ("POST", "/api/v1/assets/{asset_id}/checks/{check_id}/run", "Execute a check immediately."),
        ("POST", "/api/v1/alerts/{alert_id}/acknowledge", "Acknowledge an active alert."),
        ("POST", "/api/v1/collectors/sync", "Receive buffered collector records."),
    ]
    return templates.TemplateResponse(request, "api_reference.html", context)


@app.get("/swagger", response_class=HTMLResponse)
async def swagger_workspace_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await page_context(request, session)
    context["endpoints"] = [
        ("GET", "/health", "Service liveness and environment status."),
        ("GET", "/api/v1/overview", "Dashboard metrics, recent telemetry, and active alerts."),
        ("GET", "/api/v1/assets", "Monitored asset inventory."),
        ("POST", "/api/v1/assets", "Create a monitored asset."),
        ("POST", "/api/v1/assets/{asset_id}/checks", "Attach a monitoring check to an asset."),
        ("POST", "/api/v1/assets/{asset_id}/checks/{check_id}/run", "Execute a check immediately."),
        ("POST", "/api/v1/alerts/{alert_id}/acknowledge", "Acknowledge an active alert."),
        ("POST", "/api/v1/collectors/sync", "Receive buffered collector records."),
    ]
    return templates.TemplateResponse(request, "swagger_workspace.html", context)


@app.get("/api-view", response_class=HTMLResponse)
async def api_response_view(request: Request, session: AsyncSession = Depends(get_session)):
    path = request.query_params.get("path", "/health")
    if path == "/health":
        payload = {"status": "ok", "service": settings.app_name, "environment": settings.environment}
    elif path == "/api/v1/overview":
        data = await dashboard_overview(session)
        payload = {
            "assets_total": data["assets_total"],
            "assets_healthy": data["assets_healthy"],
            "assets_down": data["assets_down"],
            "alerts_open": data["alerts_open"],
            "average_latency_ms": data["average_latency_ms"],
        }
    elif path == "/api/v1/assets":
        payload = [AssetView.model_validate(asset).model_dump() for asset in await list_assets(session)]
    elif path == "/api/v1/collectors/sync":
        payload = {"accepted": 0, "collector_id": settings.collector_id}
    else:
        path = "/swagger-ui"
        payload = {"message": "This operation requires parameters or a request body."}
    context = await page_context(request, session)
    context.update({"endpoint_path": path, "payload_json": json.dumps(payload, indent=2, default=str)})
    return templates.TemplateResponse(request, "api_response.html", context)


@app.get("/api/v1/overview")
async def overview(session: AsyncSession = Depends(get_session)) -> dict:
    data = await dashboard_overview(session)
    data["telemetry"] = [TelemetryView.model_validate(item) for item in data["telemetry"]]
    data["alerts"] = [AlertView.model_validate(item) for item in data["alerts"]]
    return data


@app.get("/api/v1/assets", response_model=list[AssetView])
async def assets(session: AsyncSession = Depends(get_session)):
    return await list_assets(session)


@app.post("/api/v1/collectors/sync")
async def sync_collector(payload: dict, session: AsyncSession = Depends(get_session)):
    """Receive buffered collector records; normalization can be expanded per check type."""
    records = payload.get("records", [])
    return {"accepted": len(records), "collector_id": settings.collector_id}


@app.post("/api/v1/assets", response_model=AssetView, status_code=201)
async def create_asset(payload: AssetCreate, session: AsyncSession = Depends(get_session)):
    asset = Asset(**payload.model_dump())
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


@app.post("/api/v1/assets/{asset_id}/checks", status_code=201)
async def create_check(asset_id: int, payload: CheckCreate, session: AsyncSession = Depends(get_session)):
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    check = Check(asset_id=asset_id, **payload.model_dump())
    session.add(check)
    await session.commit()
    await session.refresh(check)
    return check


@app.post("/api/v1/assets/{asset_id}/checks/{check_id}/run", response_model=TelemetryView)
async def run_asset_check(asset_id: int, check_id: int, session: AsyncSession = Depends(get_session)):
    check = await session.scalar(select(Check).where(Check.id == check_id, Check.asset_id == asset_id))
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    return await execute_check(session, check)


@app.post("/api/v1/alerts/{alert_id}/acknowledge", response_model=AlertView)
async def acknowledge_alert(alert_id: int, session: AsyncSession = Depends(get_session)):
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.acknowledged.value
    alert.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(alert)
    return alert


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
