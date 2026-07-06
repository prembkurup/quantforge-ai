# QuantForge AI

AI-powered quantitative Forex strategy discovery, validation, and automated trading platform.

QuantForge AI is designed around permanent raw market data, reproducible research, plugin-driven strategy discovery, and a separate live trading engine for OANDA execution.

## Core Decisions

- PostgreSQL is the source of truth.
- Raw OHLCV candles are stored permanently.
- Derived calculation values are calculated dynamically in Python by default.
- Redis is used only for live cache and short-lived runtime state.
- Parquet is used for research cache and offline experiments.
- Strategy discovery is template-based and plugin-driven.
- Research is organized around experiments, not indicators.
- Every research activity is managed by the Experiment Management System.
- Research and live trading are separate engines.
- OANDA API is used for broker execution.
- CoreUI's `oanda_candles` table is the current live candle source while it remains updated.

## Current App Status

- Version 2.0 / Milestone 23 is now defined as the Intraday Trading Framework design specification.
- Version 2.0 focuses on intraday-only strategies, daily capital rotation, no overnight exposure, session-aware portfolios, daily risk controls, and forced end-of-day exits.
- Version 2.0 daily operations are wired through `GET /api/intraday/daily`, the Intraday dashboard page, and script-driven start/end-of-day automation.
- Before the first trade each day, the platform now produces a 0-100 market readiness score covering regime, volatility, spread, session quality, strategy availability, and portfolio exposure.
- Milestone 24 adds Decision Intelligence through `GET /api/intraday/decision-intelligence`, separating signal generation from the final decision to trade.
- Decision Intelligence now exposes the dashboard decision timeline, daily trading journal, and decision quality metrics for evaluating trades avoided as well as trades executed.
- Milestone 25 adds Portfolio Intelligence through `GET /api/portfolio/intelligence`, scoring portfolio health, allocation, drift, stress, lifecycle, and daily review state.
- Milestone 26 adds Performance Attribution and Continuous Learning through `GET /api/performance/learning`, explaining strategy, regime, session, feature, plugin, risk, and portfolio contribution while generating research priorities.
- Forced end-of-day closes now create execution receipts and Trade Journal evidence.
- Dashboard header now reads live platform health and live trading state from `GET /api/dashboard/overview`.
- Admin includes a `risk.live_trading_enabled` master switch for controlled live trading.
- Workflow shows the live gate reason, full-history workflow progress, tasks, and events.
- Workflow Events are paginated at 30 rows per page.
- Research list views paginate automatically when a list has more than 30 rows.
- Full-history research workers process jobs in controlled batches and can sleep during idle windows.
- Always-on research orchestration and historical validation workers are being added behind script-driven operations.

Live trading enablement is a platform/admin gate only. Actual execution still depends on broker credentials, production certification, and runtime risk checks.

## Project Layout

```text
backend/
  quantforge/
    core/          Configuration and shared domain types
    config/        Runtime settings
    database/      SQLAlchemy models and database sessions
    data/          Repository interfaces
    market_data/   OANDA candle ingestion and OHLCV storage
    instruments/   Tradable instruments, timeframes, broker mappings
    calculations/  Calculation Engine with indicator, statistical, volatility, and plugin calculators
    indicators/    Compatibility exports for indicator calculations
    features/      Reusable market features derived from Calculation Engine outputs
    plugins/       Plugin components and discovery
    experiments/   Experiment definitions and management models
    strategies/    Strategy templates, versions, deployments
    research/      Offline experiments and candidate scoring
    backtesting/   Historical simulations and performance metrics
    validation/    Walk-forward, out-of-sample, robustness gates
    live/          Live trading orchestration
    risk/          Risk checks, limits, kill switches
    execution/     Broker execution adapters, starting with OANDA
    reporting/     Reports, metric snapshots, exports
    admin/         Users, roles, credentials, audit
    infrastructure/ Jobs, health checks, alerts, backups
    storage/       PostgreSQL, Redis, and Parquet adapters
migrations/        Alembic database migrations
docker/            Docker-related support files
scripts/           Operational and ingestion scripts
docs/
  architecture.md
  architecture-decisions.md
  domain-model.md
  logical-database-model.md
  physical-postgresql-schema.md
  research-engine.md
  research-knowledge-base.md
  research-orchestrator.md
  strategy-composer.md
  optimization-laboratory.md
  backtesting-engine.md
  strategy-validation-platform.md
  production-strategy-management.md
  autonomous-research-validation.md
  live-trading-engine.md
  production-engineering-sre.md
  shadow-trading-platform.md
  production-certification-platform.md
  institutional-research-campaign.md
  autonomous-operations-validation.md
  production-acceptance-live-capital.md
  workstream-1-strategy-library.md
  database-backed-workstream-1.md
  workstream-1-database-pipeline.md
  dashboard-mvp.md
  experiment-management-system.md
  data-model.md
  milestone-23-intraday-trading-framework.md
  milestone-24-intraday-decision-intelligence-platform.md
  milestone-25-portfolio-intelligence-platform.md
  milestone-26-performance-attribution-continuous-learning-platform.md
  roadmap.md
```

## Version 2.0 Direction

Milestone 23 moves QuantForge AI toward an institutional intraday trading platform.

Production strategy work must now align with the Intraday Trading Policy:

- Trading style: intraday only
- Overnight positions: not allowed
- Weekend positions: not allowed
- Force close: required
- Daily risk limits: required
- Session awareness: required

The full Version 2.0 design specification is in `docs/milestone-23-intraday-trading-framework.md`.

The Milestone 24 Decision Intelligence specification is in `docs/milestone-24-intraday-decision-intelligence-platform.md`.

The Milestone 25 Portfolio Intelligence specification is in `docs/milestone-25-portfolio-intelligence-platform.md`.

The Milestone 26 Performance Attribution and Continuous Learning specification is in `docs/milestone-26-performance-attribution-continuous-learning-platform.md`.

## Near-Term Milestone

The first milestone is a usable research loop:

1. Ingest and verify OANDA OHLCV candles into PostgreSQL.
2. Load candle windows into Python.
3. Define a reproducible experiment with dataset, feature set, and strategy template.
4. Calculate indicators, statistics, volatility, price action, patterns, and other derived values dynamically inside the experiment pipeline.
5. Convert calculations into FeatureVector payloads and detect the current market regime.
6. Query the Research Knowledge Base so known winners, failures, and risk warnings guide what gets tested next.
7. Use the Research Orchestrator to choose datasets, features, templates, parameters, jobs, and next experiments.
8. Discover compatible strategy plugins from the registry.
9. Assemble candidates through the Strategy Composer.
10. Search parameters, backtest, validate, and score candidates.
11. Publish approved strategies with full experiment lineage.
12. Run autonomous research validation to prove the full lifecycle can publish Strategy Assets without manual intervention.

Generate the first standardized feature vector from CoreUI candles:

```powershell
.\.venv\Scripts\python .\scripts\generate_feature_vector.py --pair EUR_USD --timeframe H1 --candles 300
```

Generate a validated, versioned FeatureVector through the Feature Engine:

```powershell
.\.venv\Scripts\python .\scripts\generate_features.py --pair EUR_USD --timeframe H1 --lookback 300
```

Detect the current rule-based market regime from the latest FeatureVector:

```powershell
.\.venv\Scripts\python .\scripts\detect_regime.py --pair EUR_USD --timeframe H1 --lookback 300
```

Show the Research Knowledge Base demo report:

```powershell
.\.venv\Scripts\python .\scripts\knowledge_report.py --demo
```

Show the Research Orchestrator demo plan:

```powershell
.\.venv\Scripts\python .\scripts\orchestrate_research.py --pair EUR_USD --timeframe H1 --regime TRENDING --session London
```

Run the full research-loop queue demo:

```powershell
.\.venv\Scripts\python .\scripts\run_research.py
```

Run the constraint-based Strategy Composer demo:

```powershell
.\.venv\Scripts\python .\scripts\compose_strategy.py
```

Run the Optimization Laboratory demo:

```powershell
.\.venv\Scripts\python .\scripts\optimize_strategy.py
```

Run the event-driven Backtesting Engine demo:

```powershell
.\.venv\Scripts\python .\scripts\backtest.py
```

Run the Strategy Validation Platform demo:

```powershell
.\.venv\Scripts\python .\scripts\validate_strategy.py
```

Run the Production Strategy Management demo:

```powershell
.\.venv\Scripts\python .\scripts\deploy_strategy.py
```

Run the Autonomous Research Validation demo:

```powershell
.\.venv\Scripts\python .\scripts\autonomous_research.py
```

Run the Live Trading Engine demo:

```powershell
.\.venv\Scripts\python .\scripts\live_trading.py
```

Run the Version 2.0 intraday daily operations snapshot:

```powershell
.\.venv\Scripts\python .\scripts\intraday_daily_operations.py
```

Include explicit morning market readiness inputs when needed:

```powershell
.\.venv\Scripts\python .\scripts\intraday_daily_operations.py --market-regime TRENDING --volatility 0.006 --spread 0.00012 --portfolio-exposure 0.18
```

Or use the Windows launcher:

```powershell
.\scripts\start_intraday_daily_operations.bat
```

Run the Milestone 24 Decision Intelligence snapshot:

```powershell
.\.venv\Scripts\python .\scripts\intraday_decision_intelligence.py
```

Run the Milestone 25 Portfolio Intelligence snapshot:

```powershell
.\.venv\Scripts\python .\scripts\portfolio_intelligence.py
```

Run the Milestone 26 Performance Attribution and Continuous Learning snapshot:

```powershell
.\.venv\Scripts\python .\scripts\performance_learning.py
```

Run start-of-day or end-of-day intraday automation:

```powershell
.\.venv\Scripts\python .\scripts\intraday_daily_scheduler.py --mode start
.\.venv\Scripts\python .\scripts\intraday_daily_scheduler.py --mode end
```

Or use the Windows launcher:

```powershell
.\scripts\start_intraday_daily_scheduler.bat --mode end
```

Run the Production Engineering and SRE demo:

```powershell
.\.venv\Scripts\python .\scripts\production_readiness.py
```

Run the Shadow Trading and Paper Trading demo:

```powershell
.\.venv\Scripts\python .\scripts\shadow_trading.py
```

Run the Production Certification demo:

```powershell
.\.venv\Scripts\python .\scripts\certify_production.py
```

Run the Institutional Research Campaign demo:

```powershell
.\.venv\Scripts\python .\scripts\institutional_campaign.py
```

Run the Autonomous Operations Validation demo:

```powershell
.\.venv\Scripts\python .\scripts\autonomous_operations.py
```

Run the Production Acceptance and Live Capital Qualification demo:

```powershell
.\.venv\Scripts\python .\scripts\production_acceptance.py
```

Run the Workstream 1 Strategy Library demo:

```powershell
.\.venv\Scripts\python .\scripts\strategy_library.py
```

Run Workstream 1 against the real CoreUI/OANDA candle database:

```powershell
.\.venv\Scripts\python .\scripts\database_strategy_library.py --pairs EUR_USD --timeframes H1 --from 2025-01-01 --to 2025-02-01 --max-batches 25
```

Schedule and complete the Workstream 1 database pipeline:

```powershell
.\.venv\Scripts\python .\scripts\run_workstream1_pipeline.py --pairs EUR_USD --timeframes H1 --from 2025-01-01 --to 2025-02-01 --max-batches 2
```

The scheduled pipeline continues from real candle batches into optimization, event-driven backtesting, validation, and Strategy Asset publication. Use `--max-assets-to-validate` to cap how many database-backed candidates move through the expensive gates in one run.

Run the resumable full-history scheduler:

```powershell
.\.venv\Scripts\python .\scripts\full_history_research_scheduler.py --max-jobs 3
```

The scheduler plans candle coverage checks, smoke windows, rolling yearly windows, and full-history jobs for configured pairs/timeframes.
It stores resume state in `var/full_history_research_state.json` and writes output to the database-backed Logs page.
The Windows task `QuantForge Full History Research Scheduler` runs this daily with `--max-jobs 3`, so the 10-year workload progresses in controlled batches.

Run the always-on research orchestrator:

```powershell
.\scripts\start_always_on_research_orchestrator.bat
```

Run the historical validation worker:

```powershell
.\scripts\start_historical_validation_worker.bat
```

Worker notes:

- `full_history.max_parallel_jobs` controls how many full-history jobs a worker claims per loop.
- `full_history.sleep_seconds` controls the active-loop delay.
- `full_history.idle_sleep_seconds` controls how long a worker sleeps when no pending work is found.
- If the dashboard shows idle workers after a new date/window rolls forward, restart the relevant worker so it immediately claims the new jobs instead of waiting for the idle interval.

Run the read-only dashboard API:

```powershell
.\.venv\Scripts\python .\scripts\serve_dashboard_api.py
```

The dashboard API host, port, and browser origins are environment-driven:

```powershell
QUANTFORGE_DASHBOARD_API_HOST=127.0.0.1
QUANTFORGE_DASHBOARD_API_PORT=8000
QUANTFORGE_DASHBOARD_CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174,http://192.168.1.113:5174
```

Run the React dashboard:

```powershell
cd frontend
npm install
npm run dev
```

Open the UI at `http://127.0.0.1:5174` locally or `http://192.168.1.113:5174` from the private LAN.

The dashboard shell uses CoreUI and AdminLTE styling while staying read-only for Version 1.

The `/pipeline` dashboard page shows the current running task, queued pipeline tasks, all engine statuses, and per-engine workload.
It uses `GET /api/pipeline/snapshot` for a faster single-request page load.
The `/indicators` page lists the active indicators, statistical calculators, volatility measures, price-action signals, market-structure signals, and session features used by the platform.
The Strategy Library page paginates results at 30 strategies per page.
The `/logs` page reads database-backed process logs from `GET /api/logs`, with category/process/level filters and 30 logs per page.
Python scripts in `scripts/` are wrapped with the QuantForge log manager so process start, stdout, stderr, exceptions, and process finish events are written to `infrastructure.process_log`.

Production dashboard deployment:

```powershell
Copy-Item .env.production.example .env.production
# Edit .env.production secrets and production database URLs first.
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
docker compose -f docker-compose.production.yml --env-file .env.production exec dashboard-api python -m alembic upgrade head
```

The production stack serves the dashboard at `http://127.0.0.1:5174` and `http://192.168.1.113:5174`, proxies `/api/*` to FastAPI, supports React routes such as `/help`, and exposes `GET /api/health`.

## Foundation Setup

Create and activate the local Python environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

Start local services:

```powershell
docker compose up -d postgres redis
```

Or point QuantForge AI at an existing PostgreSQL server:

```powershell
Copy-Item .env.example .env
# Edit QUANTFORGE_DATABASE_URL in .env:
# postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
.\.venv\Scripts\python .\scripts\check_database.py
```

Use CoreUI's existing candle history as the read-only market-data source:

```powershell
Copy-Item .env.example .env
# Set QUANTFORGE_COREUI_HISTORY_DATABASE_URL to CoreUI_backend\.env HISTORY_DATABASE_URL.
# QuantForge reads the CoreUI oanda_candles table and does not migrate or write to it.
.\.venv\Scripts\python .\scripts\check_coreui_candles.py
.\.venv\Scripts\python .\scripts\validate_coreui_candles.py --pair EUR_USD --timeframe H1 --from 2025-01-01 --to 2025-12-31
```

Apply the first database migration:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
```

Run tests:

```powershell
.\.venv\Scripts\python -m pytest
```

Run the Calculation Engine and Feature Platform coverage gate:

```powershell
.\.venv\Scripts\python -m pytest --cov=quantforge.calculations --cov=quantforge.features --cov-report=term-missing --cov-fail-under=95
```

Optional manual OANDA candle ingestion smoke test:

```powershell
Copy-Item .env.example .env
# Fill QUANTFORGE_OANDA_API_TOKEN if using a real OANDA practice account.
# CoreUI already runs the 24/7 OANDA collector; QuantForge should not run another collector service.
.\.venv\Scripts\python .\scripts\ingest_oanda_candles.py --pair EUR_USD --timeframe H1 --from 2025-01-01 --to 2025-12-31
```

Check Monday.com integration:

```powershell
# Add QUANTFORGE_MONDAY_API_TOKEN to the local .env file. Do not commit it.
.\.venv\Scripts\python .\scripts\check_monday.py
.\.venv\Scripts\python .\scripts\list_monday_boards.py
```

Create or verify the initial QuantForge roadmap tasks:

```powershell
.\.venv\Scripts\python .\scripts\create_monday_roadmap.py
```
