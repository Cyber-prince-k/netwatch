# NetWatch Enterprise

NetWatch Enterprise is a browser-based infrastructure monitoring platform for network and application operations teams. It provides one operational view of sites, assets, reachability checks, telemetry, alert state, and collector data.

## Purpose and scope

NetWatch is intended to help administrators, network engineers, NOC technicians, auditors, and executive viewers answer three questions quickly:

1. Which monitored assets are healthy, degraded, or unavailable?
2. What changed recently in latency, packet loss, and availability?
3. Which alerts need acknowledgement or investigation?

The current repository is an MVP foundation. It includes the web dashboard, REST API, persistence model, check execution primitives, alert lifecycle, collector buffering contract, and local/production deployment paths. Authentication, RBAC, full SNMPv3 polling, advanced reports, and production migrations are intentionally next-stage work.

## Functional capabilities

- Site and asset inventory with tags and health status
- Ping, TCP, HTTP/HTTPS, and DNS checks
- Normalized telemetry for latency, packet loss, availability, CPU, and memory fields
- Alert creation, acknowledgement, and resolution flow
- Dashboard summary cards, telemetry visualization, inventory table, and active-alert queue
- Animated refresh state, live connection indicator, toast feedback, responsive layout, and reduced-motion support
- REST API with OpenAPI documentation at `/docs`
- Collector local JSONL buffering and central synchronization endpoint
- SQLite for local development
- PostgreSQL with TimescaleDB bootstrap for production time-series storage
- Docker Compose deployment and PowerShell/Bash backup scripts

## Application pages

Every page uses the same NetWatch shell: fixed top navigation, fixed side navigation, animated grid background, dark glass panels, live status indicators, and responsive layouts.

### Overview - `/`

The main operations dashboard. It summarizes healthy assets, open alerts, average latency, and assets currently down. It also displays the recent latency chart, active alert queue, and a live inventory table. The refresh control updates asset and telemetry data without leaving the page, and the dashboard automatically refreshes periodically.

### Inventory - `/inventory`

The asset register for all monitored sites and services. It shows each asset name, hostname, type, site association, health status, and tags. This page is intended for administrators and engineers who need to inspect the monitoring scope and confirm that assets are represented correctly.

### Alerts - `/alerts`

The incident and alert review page. It lists alert severity, title, message, lifecycle status, and creation time. It is intended for operators who need to investigate active signals and acknowledge incidents. Alert creation and resolution are driven by check results; acknowledgement is available through the API operation console.

### Checks - `/checks`

The monitoring probe registry. It shows configured ping, TCP, HTTP/HTTPS, and DNS checks, their targets, polling interval, enabled state, and associated asset. This page is intended for understanding what the platform is actively testing. Check creation and immediate execution are available in the API console.

### Reports - `/reports`

The reporting workspace for availability, SLA, capacity, and audit outputs. The current page presents the planned reporting functions and their operational purpose. Report generation, historical SLA calculations, and capacity forecasting are next-stage functionality in this MVP.

### Settings - `/settings`

The runtime configuration view. It displays the current environment, collector identity, and monitoring cadence. This page is currently informational; production configuration should be managed through environment variables and deployment configuration rather than browser-side edits.

### API Reference - `/docs`

The branded endpoint catalog. It lists available routes, HTTP methods, and the purpose of each operation while keeping users inside the NetWatch interface. Safe GET operations open a themed response viewer instead of displaying raw JSON in the browser.

### API Console - `/swagger`

The interactive API workspace. Administrators and developers can execute GET and POST operations directly inside the NetWatch interface, enter IDs and request values, submit JSON payloads, and inspect formatted responses without being redirected to another visual system.

### Technical Swagger UI - `/swagger-ui`

The underlying FastAPI-generated OpenAPI tool. It remains available for schema inspection and low-level request testing, but it is optional. Normal user workflows should use `/docs` and `/swagger` so they remain inside the NetWatch interface.

### Health endpoint - `/health`

The liveness endpoint used by operators, deployment checks, and container probes. It returns the service status, application name, and current environment.

## Account creation, login, and management

Account workflows are available through the shared interface:

- `/account/register` - create an account with a name, email, and password
- `/account/login` - authenticate with a signed session cookie
- `/account` - view account details and update the display name or password
- `/account/logout` - clear the active session

The dashboard, workspace pages, API console, response viewer, and protected API data require an authenticated session. Anonymous browser requests are redirected to `/account/login`; anonymous API requests return HTTP 401. Registration, login, logout, health checks, and static assets remain available without an authenticated session.

Passwords are never stored directly. `PasswordHasher` encapsulates salted PBKDF2-SHA256 hashing and constant-time verification. `AccountService` owns account creation, profile updates, lookup, and account listing. `AuthenticationService` owns credential verification and login timestamps. Custom `AccountError` and `AuthenticationError` exceptions are caught at the HTTP boundary and converted into user-facing form errors.

## Object-oriented design conventions

NetWatch uses an object-oriented service boundary as the system grows:

- **Encapsulation:** domain operations and sensitive password behavior live inside classes rather than being scattered through routes.
- **Reuse:** services receive an `AsyncSession` and can be reused by HTML routes, REST endpoints, background jobs, and collectors.
- **Separation of concerns:** ORM models represent persisted state, schemas validate input, services perform operations, and routes translate HTTP requests and errors.
- **Inheritance and polymorphism:** use them where a shared monitoring or integration contract genuinely reduces duplication; avoid inheritance only for ceremony.
- **Error handling:** service operations use explicit `try/except` handling at persistence and integration boundaries, chaining original exceptions where useful. Routes present safe, actionable errors without exposing secrets or internal stack traces.
- **Testability:** class operations should be small enough to test independently from the browser layer.

New features should follow this structure: model/entity, validated schema, service class, route/controller, template or API response, and focused tests.

## Technologies used

### Backend and application runtime

- **Python 3.11+** - primary language for the web application, monitoring logic, collector workflows, alert processing, and reporting foundations.
- **FastAPI** - asynchronous web framework providing HTML routes, REST endpoints, OpenAPI generation, dependency injection, and application startup handling.
- **Uvicorn** - ASGI server used to run NetWatch locally and in containers.
- **Jinja2** - server-side template engine used for the shared application shell, dashboard, inventory, alerts, checks, reports, settings, API console, and response viewer.
- **Pydantic Settings** - environment-based configuration through `.env` and deployment variables.

### Persistence and time-series data

- **SQLAlchemy 2** - asynchronous ORM and database abstraction for sites, assets, checks, telemetry, and alerts.
- **SQLite with `aiosqlite`** - zero-setup local development database.
- **PostgreSQL with `asyncpg`** - production relational database backend.
- **TimescaleDB** - production time-series extension intended for high-volume telemetry retention, aggregation, partitioning, and historical graphing.
- **JSON/JSONL** - JSON is used for API payloads and collector synchronization; JSON Lines provides durable local collector buffering.

### Monitoring and automation

- **Python sockets and `httpx`** - current ping-style hostname, TCP, HTTP/HTTPS, and DNS check primitives.
- **APScheduler compatibility** - planned scheduling foundation for recurring checks and maintenance jobs.
- **Collector buffering** - local JSONL buffering allows site collectors to retain records while central synchronization is unavailable.
- **scikit-learn** - dependency reserved for Isolation Forest anomaly detection and future telemetry anomaly models.
- **SNMPv3, database, VPN, SSL, API, and flow protocols** - part of the target monitoring scope; full production pollers are planned beyond the current MVP primitives.

### Frontend and user interface

- **HTML5** - semantic page structure and accessible application markup.
- **CSS3** - dark operations workspace, glass surfaces, responsive layouts, animated grid background, fixed navigation, hover states, and reduced-motion support.
- **JavaScript ES6+** - dashboard refresh, animated counters, native canvas telemetry chart, API console execution, response rendering, and copy-to-clipboard behavior.
- **Native HTML Canvas** - lightweight latency visualization without requiring an external chart runtime.
- **DM Mono and Space Grotesk** - interface typography loaded by the stylesheet.

### API and integration formats

- **REST/HTTP** - application and collector communication model.
- **OpenAPI 3** - generated API schema available through `/openapi.json`.
- **JSON** - request and response format for REST APIs, collector synchronization, and future webhook integrations.
- **Teams, Slack, and ITSM webhooks** - planned notification integrations.

### Deployment and operations

- **Docker** - container image for the NetWatch application.
- **Docker Compose** - local multi-service orchestration for the FastAPI application and TimescaleDB.
- **YAML** - Compose configuration and future Kubernetes/CI/CD configuration format.
- **PowerShell** - Windows launcher and backup automation.
- **Bash** - Unix-like backup and maintenance automation.
- **PostgreSQL SQL and PL/pgSQL** - database bootstrap, indexes, future retention policies, partitioning, and stored procedures.

### Quality and documentation

- **pytest and pytest-asyncio** - asynchronous monitoring and application tests.
- **Ruff** - Python linting and formatting configuration.
- **Markdown** - architecture, API, deployment, configuration, and operational documentation.

## Run locally on Windows

### Option A: one command

From the repository root:

```powershell
.\scripts\run.ps1
```

The script creates or uses `.venv`, installs the project, starts Uvicorn on `http://127.0.0.1:8000`, and keeps the server in the foreground. Leave that terminal open while using the dashboard.

### Option B: manual setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. Do not open the Jinja template or generated HTML directly from the file system; the FastAPI server must serve `/static/app.css` and `/static/dashboard.js`.

The first startup creates the local `netwatch.db` database and seeds three demonstration assets. The seed is skipped when data already exists.

## Run with Docker and TimescaleDB

```powershell
docker compose up --build
```

Open `http://127.0.0.1:8000/`. The Compose database uses PostgreSQL/TimescaleDB and persists data in the `timescale_data` volume.

## API reference

- `GET /health` - service liveness
- `GET /api/v1/overview` - dashboard summary, alerts, and recent telemetry
- `GET /api/v1/assets` - monitored inventory
- `POST /api/v1/assets` - create an asset
- `POST /api/v1/assets/{asset_id}/checks` - attach a check to an asset
- `POST /api/v1/assets/{asset_id}/checks/{check_id}/run` - execute a check immediately
- `POST /api/v1/alerts/{alert_id}/acknowledge` - acknowledge an alert
- `POST /api/v1/collectors/sync` - accept buffered collector records
- `GET /docs` - branded API reference
- `GET /swagger` - branded interactive API console
- `GET /swagger-ui` - technical FastAPI Swagger UI

## Configuration

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL` - defaults to local SQLite; use `postgresql+asyncpg://...` in production
- `SECRET_KEY` - replace the development value before deployment
- `COLLECTOR_ID` - identifies the local collector
- `MONITOR_INTERVAL_SECONDS` - intended polling interval configuration

## Tests and checks

```powershell
python -m pytest -q
node --check app/static/dashboard.js
```

## Operations and backups

```powershell
.\scripts\backup.ps1
```

For Bash-based environments:

```bash
bash scripts/backup.sh
```

Production deployments should add authentication, TLS termination, secret management, database migrations, scheduled monitoring workers, retention policies, and structured audit logging before exposure outside a trusted network.
