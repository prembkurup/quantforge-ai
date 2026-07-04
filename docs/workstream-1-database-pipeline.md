# Workstream 1 Database Pipeline

The Workstream 1 database pipeline schedules and runs the real candle-backed research path end to end.

It sits above `DatabaseBackedStrategyLibraryRunner` and turns the run into explicit operational tasks:

1. Database connection
2. Candle coverage validation
3. Real experiment batch execution
4. Database-backed candidate Strategy Asset generation
5. Optimization for stable parameter regions
6. Event-driven backtesting
7. Strategy validation
8. Immutable Strategy Asset publication
9. Pipeline report archival

## Start Command

Run a small real database batch first:

```powershell
.\.venv\Scripts\python .\scripts\run_workstream1_pipeline.py --pairs EUR_USD --timeframes H1 --from 2025-01-01 --to 2025-02-01 --max-batches 2
```

Scale only after the small run completes cleanly:

```powershell
.\.venv\Scripts\python .\scripts\run_workstream1_pipeline.py --pairs EUR_USD,GBP_USD,USD_JPY --timeframes M15,H1,H4 --from 2015-01-01 --to 2025-01-01 --max-batches 500
```

Run the resumable full-history scheduler:

```powershell
.\.venv\Scripts\python .\scripts\full_history_research_scheduler.py --max-jobs 3
```

The scheduler breaks the historical rollout into controlled jobs:

- full-period candle coverage check
- short smoke window
- rolling yearly windows
- capped full-history run

Each invocation reads `var/full_history_research_state.json`, skips completed jobs, runs the next pending jobs, updates state, and writes process logs to PostgreSQL.
The Windows task `QuantForge Full History Research Scheduler` runs it daily with `--max-jobs 3`.

## Completion Evidence

The pipeline report includes:

- scheduled task count
- completed task count
- failed task count
- stored candle count
- duplicate candle count
- missing candle count
- real experiment batch count
- database-backed candidate asset count
- optimized candidate count
- backtested candidate count
- validated Strategy Asset count
- reproducibility key
- task-level evidence

## Safety Boundary

This pipeline is research-only. It does not place live orders.

Database-backed candidates now pass through optimization, backtesting, validation, and Strategy Asset publication inside the research pipeline.

Published Strategy Assets must still pass paper/shadow trading, operations, and controlled live capital gates before they can influence real trading.
