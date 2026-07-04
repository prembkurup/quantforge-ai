# QuantForge AI Dashboard MVP

The dashboard MVP is a read-only internal UI for monitoring QuantForge AI research progress, strategy library status, portfolio readiness, paper trading status, operations health, and Knowledge Base evidence.

## Scope

Version 1 is read-only:

- no live trading actions
- no strategy deployment actions
- no credential display
- local/private network use only

## Backend API

Run the FastAPI service:

```powershell
.\.venv\Scripts\python .\scripts\serve_dashboard_api.py
```

Primary endpoints:

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

Run the React dashboard:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

Routes:

- `/` Executive Overview
- `/research` Research Progress
- `/strategies` Strategy Library
- `/strategies/:id` Strategy Detail
- `/portfolio` Portfolio Readiness
- `/paper` Paper Trading
- `/operations` Operations Health
- `/knowledge` Knowledge Base

## Success Criteria

- Executive overview loads correctly.
- Research metrics display correctly.
- Strategy library is filterable.
- Strategy detail is traceable.
- Portfolio readiness is visible.
- Operations health is visible.
- Dashboard refreshes API data automatically.
- Write actions are unavailable.
