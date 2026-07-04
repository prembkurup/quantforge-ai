# QuantForge AI Dashboard MVP

The dashboard MVP is a read-only internal UI for monitoring QuantForge AI research progress, strategy library status, portfolio readiness, paper trading status, operations health, and Knowledge Base evidence.

## Scope

Version 1 is read-only:

- no live trading actions
- no strategy deployment actions
- no credential display
- local/private network use only

## Production Deployment

Use the production deployment when the dashboard should run as a stable internal service instead of a Vite development server.

1. Create a real production environment file from the template:

```powershell
Copy-Item .env.production.example .env.production
```

2. Edit `.env.production`:

- Change `POSTGRES_PASSWORD`.
- Keep `QUANTFORGE_DATABASE_URL` aligned with the production PostgreSQL host and password.
- Set `QUANTFORGE_COREUI_HISTORY_DATABASE_URL` to the real CoreUI history database.
- Set `QUANTFORGE_DASHBOARD_CORS_ORIGINS` to the exact internal URLs that should load the dashboard.
- Add Monday/OANDA tokens only if the production service needs them.

3. Build and start the production stack:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

4. Apply database migrations when the production database is ready:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production exec dashboard-api python -m alembic upgrade head
```

5. Open the production dashboard:

- `http://127.0.0.1:5174`
- `http://192.168.1.113:5174`

The production frontend is served by Nginx. It proxies `/api/*` to the FastAPI dashboard API container and serves React routes like `/help` through the SPA fallback.

Production health check:

```powershell
Invoke-WebRequest http://127.0.0.1:5174/api/health -UseBasicParsing
```

Stop the production stack:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production down
```

## Backend API

Run the FastAPI service:

```powershell
.\.venv\Scripts\python .\scripts\serve_dashboard_api.py
```

Primary endpoints:

- `GET /api/health`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/research/progress`
- `GET /api/dashboard/research/programs`
- `GET /api/strategies`
- `GET /api/strategies/{strategy_id}`
- `GET /api/portfolio/readiness`
- `GET /api/paper/summary`
- `GET /api/ops/health`
- `GET /api/knowledge/summary`

The API currently exposes dashboard DTOs from existing QuantForge evidence modules: Workstream 1 Strategy Library, Shadow Trading, Operations Validation, and Knowledge evidence.

## Frontend

The React dashboard uses Tailwind for local layout polish and imports CoreUI plus AdminLTE for the internal operations-console theme:

- `@coreui/coreui`
- `@coreui/react`
- `admin-lte`
- `bootstrap`

Run the React dashboard:

```powershell
cd frontend
npm install
npm run dev
```

Open locally at `http://127.0.0.1:5174` or from the private LAN at `http://192.168.1.113:5174`.

For production, use `docker-compose.production.yml` or build with `npm run build` and serve `frontend/dist` behind an internal reverse proxy.

Routes:

- `/` Executive Overview
- `/research` Research Progress
- `/strategies` Strategy Library
- `/strategies/:id` Strategy Detail
- `/portfolio` Portfolio Readiness
- `/paper` Paper Trading
- `/operations` Operations Health
- `/knowledge` Knowledge Base
- `/help` Manual / Help

## Success Criteria

- Executive overview loads correctly.
- Research metrics display correctly.
- Strategy library is filterable.
- Strategy detail is traceable.
- Portfolio readiness is visible.
- Operations health is visible.
- Dashboard refreshes API data automatically.
- Write actions are unavailable.
