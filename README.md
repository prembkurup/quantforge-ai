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
  experiment-management-system.md
  data-model.md
  roadmap.md
```

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
