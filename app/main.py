from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi import Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth import AccountError, AccountService, AuthenticationError, AuthenticationService
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


PUBLIC_PATHS = {
    "/health",
    "/account/login",
    "/account/register",
    "/account/logout",
    "/openapi.json",
    "/swagger-ui",
    "/redoc",
}


@app.middleware("http")
async def authentication_gate(request: Request, call_next):
    path = request.url.path
    is_static = path.startswith("/static/")
    is_public = path in PUBLIC_PATHS or path.startswith("/swagger-ui/") or path.startswith("/redoc")
    requires_auth = not is_static and not is_public and (
        path == "/" or path.startswith(("/inventory", "/alerts", "/checks", "/reports", "/settings", "/docs", "/swagger", "/api/", "/api-view"))
    )
    if requires_auth and not request.session.get("user_id"):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        return RedirectResponse(url=f"/account/login?next={request.url.path}", status_code=303)
    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie=settings.session_cookie_name, https_only=False)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


def current_user_id(request: Request) -> int | None:
    return request.session.get("user_id")


async def auth_context(request: Request, session: AsyncSession) -> dict:
    return await page_context(request, session)


@app.get("/account/register", response_class=HTMLResponse)
async def register_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    context["error"] = None
    return templates.TemplateResponse(request, "register.html", context)


@app.post("/account/register", response_class=HTMLResponse)
async def register_account(request: Request, email: str = Form(...), full_name: str = Form(...), password: str = Form(...), session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    try:
        user = await AccountService(session).create_account(email, full_name, password)
        request.session["user_id"] = user.id
        return RedirectResponse("/account", status_code=303)
    except AccountError as error:
        context["error"] = str(error)
        return templates.TemplateResponse(request, "register.html", context, status_code=400)


@app.get("/account/login", response_class=HTMLResponse)
async def login_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    context["error"] = None
    return templates.TemplateResponse(request, "login.html", context)


@app.post("/account/login", response_class=HTMLResponse)
async def login_account(request: Request, email: str = Form(...), password: str = Form(...), session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    try:
        user = await AuthenticationService(session).authenticate(email, password)
        request.session["user_id"] = user.id
        return RedirectResponse("/account", status_code=303)
    except AuthenticationError as error:
        context["error"] = str(error)
        return templates.TemplateResponse(request, "login.html", context, status_code=401)


@app.get("/account/logout")
async def logout_account(request: Request):
    request.session.clear()
    return RedirectResponse("/account/login", status_code=303)


@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    if not context["current_user"]:
        return RedirectResponse("/account/login", status_code=303)
    context["error"] = None
    return templates.TemplateResponse(request, "account.html", context)


@app.post("/account/profile", response_class=HTMLResponse)
async def update_account(request: Request, full_name: str = Form(...), password: str = Form(""), session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    user = context["current_user"]
    if not user:
        return RedirectResponse("/account/login", status_code=303)
    try:
        await AccountService(session).update_profile(user, full_name, password or None)
        context["message"] = "Account updated successfully"
        context["error"] = None
    except AccountError as error:
        context["message"] = None
        context["error"] = str(error)
    return templates.TemplateResponse(request, "account.html", context)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    context = await auth_context(request, session)
    return templates.TemplateResponse(request, "dashboard.html", context)


async def page_context(request: Request, session: AsyncSession) -> dict:
    overview = await dashboard_overview(session)
    user_id = current_user_id(request)
    current_user = await AccountService(session).get_account(user_id) if user_id else None
    return {"request": request, "overview": overview, "current_user": current_user}


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
