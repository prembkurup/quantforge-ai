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
- Discover strategy plugins.
- Run parameter searches, optimization, backtests, and validation inside experiments.
- Store experiment lineage, analytics, and final metrics.
- Export research cache to Parquet.

## Phase 4: Validation

- Add walk-forward validation.
- Add out-of-sample testing.
- Add spread and slippage modeling.
- Add robustness scoring.
- Promote validated candidates.

## Phase 5: Live Engine

- Load approved strategy candidates only.
- Use Redis for latest live cache.
- Evaluate signals on completed candles.
- Enforce risk checks before execution.
- Execute through OANDA adapter.
- Persist live orders and audit logs.

## Phase 6: Operations

- Deploy on in-house Linux servers.
- Add process supervision.
- Add health checks and alerts.
- Connect project tasks to Monday.com.
- Push private repository to GitHub.
