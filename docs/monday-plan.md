# Monday.com Project Plan

Use this as the first Monday.com board structure for QuantForge AI.

## Groups

- Foundation
- Data Ingestion
- Research Engine
- Validation
- Live Trading
- Operations

## Suggested Columns

- Owner
- Status
- Priority
- Target Date
- Component
- GitHub PR
- Notes

## Initial Items

- Create private GitHub repository.
- Configure backend Python environment.
- Create PostgreSQL schema for instruments, candles, experiments, research runs, and live orders.
- Implement OANDA candle ingestion.
- Add candle data quality report.
- Implement Calculation Engine with indicator, statistical, volatility, and custom calculator modules.
- Implement Feature Engine and Feature Registry.
- Implement Market Regime Engine.
- Build Research Knowledge Base for validated findings, failed setups, and experiment evidence.
- Build Research Orchestrator to coordinate hypotheses, datasets, regimes, knowledge, experiment planning, job scheduling, result collection, and progress monitoring.
- Implement strategy plugin discovery.
- Implement experiment definition workflow.
- Build Strategy Composer to assemble candidates from market-regime, entry, confirmation, exit, risk, and trade-management plugins.
- Build first template strategy plugin.
- Implement basic backtest runner.
- Store experiment lineage, research run metrics, validation results, and analytics.
- Add Parquet research cache.
- Define live trading risk checks.
- Implement OANDA execution adapter dry-run mode.
- Add Linux server deployment plan.
