# Roadmap

## Phase 1: Foundation

- Create backend project skeleton.
- Define configuration model.
- Add PostgreSQL, Redis, Parquet, and OANDA boundaries.
- Add Chapter 4 enterprise domain boundaries.
- Add Chapter 5 logical database ownership, lifecycle, and access rules.
- Add plugin registry decision with type-specific metadata tables.
- Add Chapter 6 physical PostgreSQL schema standards.
- Add Chapter 7 Research Engine pipeline.
- Adopt experiment-centric research as the primary platform model.
- Add Chapter 8 Experiment Management System.
- Define candle repository interface.
- Define strategy plugin contract.
- Document initial data model.

## Phase 2: Data Ingestion

- Implement OANDA candle downloader.
- Persist raw OHLCV candles to PostgreSQL.
- Add idempotent upsert by instrument, granularity, and time.
- Add data quality checks for missing and duplicate candles.

## Phase 3: Research Engine

- Load historical candles from PostgreSQL.
- Define experiments with dataset, feature set, strategy template, and objective.
- Add experiment lifecycle, scheduling, resource tracking, comparison, and publication controls.
- Calculate derived values dynamically through the Calculation Engine.
- Convert calculations into standardized FeatureVector payloads.
- Detect current market regime from FeatureVector payloads.
- Add Research Knowledge Base to remember validated findings, failed setups, and research evidence before plugin and template selection.
- Add Research Orchestrator to coordinate hypotheses, datasets, features, regimes, knowledge, template/plugin selection, parameter planning, job scheduling, result collection, and next experiment planning before strategy composition.
- Discover strategy plugins.
- Add Constraint-Based Strategy Composer with constraint building, compatibility checks, dependency checks, strategy graphs, validation, complexity scoring, diversity filtering, and decision traceability.
- Add Optimization Laboratory for stable parameter regions, sensitivity analysis, parameter landscapes, robustness estimates, optimization knowledge writing, reports, and Research Review Board gates.
- Run backtests and validation only after strategy structure and parameter regions pass review.
- Add Backtesting Engine 2.0 with event-driven market simulation, execution simulation, position and portfolio management, trade journal, performance reports, replay mode, and time machine.
- Add Autonomous Research Validation to run the complete research lifecycle, execute 100+ experiments, publish validated Strategy Assets, update the Knowledge Base, and preserve audit trails.
- Store experiment lineage, analytics, and final metrics.
- Export research cache to Parquet.

## Phase 4: Validation

- Add walk-forward validation.
- Add out-of-sample testing.
- Add spread and slippage modeling.
- Add robustness scoring.
- Add Strategy Validation Platform with Monte Carlo, cross-pair, cross-timeframe, parameter stability, stress testing, confidence scoring, Deployment Board, Strategy Passport, and Strategy Assets.
- Promote validated candidates.

## Phase 5: Live Engine

- Load approved strategy candidates only.
- Add Production Strategy Management Platform with Strategy Catalog, Strategy Registry, Deployment Manager, Portfolio Manager, Capital Allocator, Scheduler, Drift Detector, Live Performance Monitor, Retirement Manager, Strategy Marketplace, and Production Dashboard.
- Add Live Trading Engine with event bus, strategy selector, Trade Decision Engine, signal generator, risk controller, execution manager, position monitor, state store, recovery, and broker synchronization.
- Add Shadow Trading and Paper Trading Platform with virtual exchange, paper portfolio, decision audit, expected-vs-actual analysis, drift analytics, Digital Twin comparison, and promotion gate before live capital.
- Use Redis for latest live cache.
- Evaluate signals on completed candles.
- Enforce risk checks before execution.
- Execute through OANDA adapter.
- Persist live orders and audit logs.

## Phase 6: Operations

- Deploy on in-house Linux servers.
- Add process supervision.
- Add health checks and alerts.
- Add Production Engineering and SRE layer with health, heartbeats, Prometheus metrics, structured JSON logs, distributed tracing, classified alerts, and automatic recovery actions.
- Connect project tasks to Monday.com.
- Push private repository to GitHub.
