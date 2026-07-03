# QuantForge AI Architecture

## Purpose

QuantForge AI discovers, validates, and runs quantitative Forex strategies. The platform must support long-term research without compromising live trading safety.

## System Boundaries

QuantForge AI has two main engines:

- Research engine: offline strategy discovery, backtesting, validation, walk-forward tests, and candidate ranking.
- Live trading engine: real-time signal evaluation, risk checks, order execution, monitoring, and audit logs.

These engines share market data and strategy definitions, but they do not share runtime state.

## Data Architecture

PostgreSQL is the source of truth for all durable records:

- raw OHLCV candles
- instruments
- strategy definitions
- experiments and research runs
- backtest results
- selected strategy candidates
- live orders, positions, executions, and audit logs

Raw OHLCV candles are stored permanently. Calculation outputs are not stored by default because they are derived data and can explode storage requirements. Indicators, statistics, volatility measures, price action, patterns, market structure, sessions, liquidity, and custom plugin calculations are calculated dynamically in Python when research or live signal evaluation needs them.

Redis is only for live cache:

- latest candle snapshots
- current spread snapshots
- temporary signal state
- live engine heartbeats

Parquet is only for research cache:

- local experiment datasets
- feature matrices for repeatable research
- large intermediate outputs that can be regenerated from PostgreSQL

## Strategy Discovery

Strategies are template-based and plugin-driven. Research is organized around experiments, not indicators. An experiment binds the dataset, feature set, strategy template, plugin versions, parameter search, validation results, analytics, and any published strategy versions.

A strategy plugin declares:

- metadata
- required candle granularities
- required calculations
- parameter search space
- signal generation logic
- risk model hooks
- validation constraints

The research engine defines experiments, discovers plugins, expands parameter templates, runs backtests, validates results, compares experiment analytics, and ranks candidates. The live engine only runs approved strategy versions.

## Live Execution

OANDA is the execution adapter for live orders.

The live engine flow is:

1. Load approved strategy version.
2. Read latest candles from PostgreSQL and live cache.
3. Calculate derived values dynamically through the Calculation Engine.
4. Generate signal.
5. Apply risk checks.
6. Send order through OANDA adapter.
7. Persist order, execution, and audit records in PostgreSQL.

## Safety Rules

- Research code must not place live orders.
- Live engine must not mutate strategy research results.
- OANDA credentials must not be hard-coded.
- Every live order must have an audit trail.
- Raw candle history must never be pruned by log retention jobs.
