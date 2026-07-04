# Autonomous Research Validation

Milestone 13 proves that QuantForge AI can run the full research lifecycle as one autonomous system.

The goal is not to prove that a strategy is profitable. The goal is to prove that the platform follows a reproducible scientific process and only publishes high-quality Strategy Assets after every gate has run.

## Pipeline

```text
Research Goal
  -> Hypothesis Generator
  -> Research Orchestrator
  -> Dataset Selection
  -> Calculation Engine
  -> Feature Engine
  -> Market Regime Engine
  -> Knowledge Base
  -> Strategy Composer
  -> Optimization Laboratory
  -> Backtesting Engine
  -> Validation Platform
  -> Research Review Board
  -> Strategy Asset
  -> Strategy Catalog
```

## Components

- `AutonomousResearchPipeline` coordinates the end-to-end run.
- `HypothesisGenerator` creates versioned, evidence-backed hypotheses from a research goal.
- `DatasetSelector` chooses pairs, timeframes, training, walk-forward, out-of-sample, and reserved test periods.
- `ExperimentScheduler` creates a reproducible queue of autonomous experiments.
- `ExperimentRunner` records each experiment's composition, optimization, backtest, validation, publication, and rejection outcome.
- `StrategyAssetPublisher` publishes approved Strategy Assets into the Strategy Catalog.
- `KnowledgeBaseUpdater` writes feature importance, plugin performance, parameter stability, template success, regime statistics, and hypothesis confidence.
- `ResearchReportGenerator` produces JSON and PDF-ready report payloads.
- `ResearchDashboard` summarizes throughput, assets, catalog state, reproducibility, exports, and autonomous operation.

## Reproducibility

Every run creates an immutable experiment plan with a plan hash. Running the same research goal with the same inputs produces the same schedule, Strategy Asset IDs, KPI totals, and reproducibility key.

The reserved test period is explicitly excluded from optimization periods so future knowledge cannot leak into the research process.

## Failure Handling

Each experiment preserves audit events and a rejection reason. Invalid or statistically weak experiments are rejected and never published as partial Strategy Assets.

Independent experiments continue even when other experiments are rejected.

## Reports

The pipeline produces:

- experiment summary
- validation summary
- strategy ranking report
- knowledge update report
- JSON payload
- PDF-ready text payload
- full research audit trail

## Demo

```powershell
.\.venv\Scripts\python .\scripts\autonomous_research.py
```

Expected shape:

```text
Research Goal
Improve trend-following strategies on major Forex pairs.

Hypotheses
3

Experiments
100

Candidates Generated
284,000

Approved Strategy Assets
12

Knowledge Base Updated
YES

Reports
JSON, PDF

Audit Trail
503 events

Autonomous
YES
```

## Exit Criteria

Milestone 13 is complete when the system can execute at least 100 experiments automatically, publish validated Strategy Assets without manual intervention, reject weak candidates, update the Knowledge Base, produce complete reports, and maintain a full audit trail.
