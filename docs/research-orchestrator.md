# Research Orchestrator

The Research Orchestrator is the coordinator that sits between institutional knowledge and strategy generation.

It exists because QuantForge AI now has strong components:

- market data
- Calculation Engine
- Feature Engine
- Market Regime Engine
- Research Knowledge Base
- Hypothesis Management

The orchestrator decides how those pieces should be used before the Strategy Composer assembles anything.

```text
Hypothesis
  -> Dataset Planner
  -> Feature Planner
  -> Market Regime Context
  -> Knowledge Base Lookup
  -> Research Orchestrator
  -> Experiment Queue
  -> Plugin Framework
  -> Strategy Templates
  -> Strategy Composer
  -> Backtest and Validation
  -> Knowledge Base Update
```

## Responsibilities

- Ensure every experiment has a hypothesis.
- Choose the dataset, instruments, timeframe, date range, training period, and validation period.
- Select required and knowledge-guided features for the hypothesis and regime.
- Query Knowledge Base scores and recommendations.
- Select strategy templates and plugins to explore.
- Narrow parameter ranges using prior knowledge instead of sweeping broad spaces.
- Block known weak combinations.
- Convert evidence into experiment constraints.
- Schedule research, optimization, backtest, validation, and knowledge-update jobs.
- Track queued, running, completed, and failed jobs.
- Collect results and update the Knowledge Base.
- Decide whether to run, refine, skip, or collect more evidence.

## Decisions

The V1 orchestrator returns one of:

- `run_experiment`
- `refine_hypothesis`
- `skip_known_failure`
- `collect_more_evidence`

This means the Strategy Composer should not receive raw random requests. It should receive a constrained research plan from the orchestrator.

## Components

- `DatasetPlanner` chooses instruments, timeframes, date range, training period, and validation period.
- `FeaturePlanner` combines required features, Knowledge Base recommendations, and regime defaults.
- `TemplatePlanner` selects candidate strategy templates and plugins while blocking known failures.
- `ParameterPlanner` narrows search spaces, such as EMA 20-50 instead of a broad 5-200 sweep.
- `JobScheduler` creates research, optimization, backtest, validation, and knowledge-update jobs.
- `ProgressMonitor` summarizes queue progress.
- `ResearchOrchestrator.collect_results()` forwards completed experiment evidence into the Knowledge Base.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\orchestrate_research.py --pair EUR_USD --timeframe H1 --regime TRENDING --session London
```

Run the full research-loop demo:

```powershell
.\.venv\Scripts\python .\scripts\run_research.py
```

Example output includes:

- decision
- hypothesis status
- confidence
- recommended features
- recommended plugins
- recommended regimes
- blocked plugins
- constraints for Strategy Composer
- next experiment recommendations
- dataset, feature, template, parameter, queue, and progress plans
- reasons
