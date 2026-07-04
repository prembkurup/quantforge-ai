# Research Engine

Source: `QuantForge AI - Chapter 7.pdf` and `QuantForge AI - Chapter 8.pdf`.

The Research Engine is the intelligence core of QuantForge AI. It transforms historical market data into validated, production-ready trading strategies through a structured quantitative research pipeline.

The Research Engine never executes live trades. Its responsibility ends when an approved strategy is published for the Strategy Service and later consumed by the live trading platform.

Chapter 8 adds the Experiment Management System as the control layer around the Research Engine. The EMS plans, schedules, monitors, compares, reproduces, and publishes experiments.

## Primary Unit: Experiment

QuantForge AI is experiment-centric. The platform is organized around research experiments, not indicators.

An experiment binds together the complete research record:

- experiment definition
- dataset
- feature set
- strategy template
- parameter search
- optimization runs
- backtest runs
- validation results
- analytics
- published strategy versions

Calculations are derived inputs used inside features and templates. Indicators are one calculator family inside the broader Calculation Engine. A research run is an execution attempt inside an experiment. The experiment is the durable unit used for reproducibility, comparison, audit, and publishing.

## Principles

- Research must be reproducible.
- Every experiment is traceable.
- Every strategy is explainable.
- Every strategy must be statistically validated.
- Research and production remain isolated.
- Calculation outputs are derived.
- Features are standardized.
- Strategies are assembled from reusable components.
- Optimization is independent from strategy generation.
- Validation is mandatory before deployment.

## Pipeline

1. Experiment Definition
2. Dataset Selection
3. Data Preparation
4. Calculation
5. Feature Engineering
6. Feature Store
7. Market Regime Detection
8. Research Knowledge Base Lookup
9. Research Orchestration
10. Plugin Framework
11. Strategy Template Selection
12. Strategy Composer
13. Structural Validation
14. Complexity and Diversity Filtering
15. Parameter Generation
16. Optimization Laboratory
17. Research Review Board
18. Backtesting
19. Validation
20. Ranking
21. Research Analytics
22. Strategy Publishing
23. Autonomous Research Validation

## Engine Responsibilities

### Data Preparation Engine

Loads historical OHLCV data, verifies quality, removes duplicates, detects missing candles, normalizes timestamps to UTC, applies trading calendars, and prepares research datasets.

### Experiment Service

Creates and owns experiment definitions, attaches datasets and feature sets, records strategy templates and plugin versions, tracks parameter search, and links all downstream validation and publishing artifacts back to the experiment.

### Experiment Manager

Manages lifecycle, scheduling, priority, resource usage, reproducibility metadata, results, comparison, and controlled publication. Failed experiments retain metadata and results for future analysis.

### Calculation Engine

Calculates derived market values on demand. It supports parameterized calculators, parallel computation, incremental calculation, and caching when beneficial. Calculation outputs are not stored permanently by default.

The Indicator Calculator is one module inside the Calculation Engine. The engine also owns statistical, price action, pattern, market structure, volatility, session, liquidity, and custom plugin calculators.

### Feature Engineering Engine

Transforms Calculation Engine outputs into standardized market features such as trend direction, trend strength, pullback, breakout, momentum, volatility regime, support/resistance distance, candle structure, session, liquidity, and spread category.

### Feature Store

Provides standardized feature vectors for research consistency, live trading consistency, reuse, and reproducibility. It may use memory, Redis, Parquet, or PostgreSQL cache depending on workload.

### Market Regime Engine

Classifies market conditions such as trending, ranging, breakout, high volatility, low volatility, recovery, and no-trade. Every strategy declares compatible regimes.

The first implementation is rule-based and consumes standardized FeatureVector payloads:

```text
Feature Vector
  -> Market Regime Engine
  -> Current market state
```

Supported V1 regimes:

- `TRENDING`
- `RANGING`
- `HIGH_VOLATILITY`
- `LOW_VOLATILITY`
- `BREAKOUT`
- `NO_TRADE`

Run the current detector:

```powershell
.\.venv\Scripts\python .\scripts\detect_regime.py --pair EUR_USD --timeframe H1 --lookback 300
```

### Research Knowledge Base

Stores durable research findings so QuantForge AI can accumulate knowledge across experiments. It records what worked, what failed, where it worked, under which feature conditions, in which market regime, and how much evidence supports the conclusion.

The Knowledge Base sits before plugin and strategy template selection:

```text
Feature Vector
  -> Market Regime Engine
  -> Research Knowledge Base
  -> Research Orchestrator
  -> Plugin Framework
  -> Strategy Template Engine
```

It should remember examples such as a trend-pullback setup working on `EUR_USD` `H1` during `TRENDING` London sessions, or `RSI < 30` failing on `USD_JPY` `M1`. These records guide future experiment selection and reduce wasted research cycles.

### Research Orchestrator

Coordinates hypothesis, market context, FeatureVector meaning, market regime, and Knowledge Base evidence before any strategy generation starts.

The orchestrator is intentionally upstream of Strategy Composer:

```text
Hypothesis
  -> Dataset Planner
  -> Feature Planner
  -> Market Regime Context
  -> Knowledge Base Lookup
  -> Research Orchestrator
  -> Experiment Queue
  -> Plugin Framework
  -> Strategy Template Engine
  -> Strategy Composer
```

It returns a research plan containing the decision, dataset plan, recommended features, recommended plugins, recommended regimes, selected templates, blocked plugins, Strategy Composer constraints, narrowed parameter search, scheduled jobs, progress snapshot, next experiments, and reasons.

Run the demo:

```powershell
.\.venv\Scripts\python .\scripts\orchestrate_research.py --pair EUR_USD --timeframe H1 --regime TRENDING --session London
```

Run the full research-loop queue demo:

```powershell
.\.venv\Scripts\python .\scripts\run_research.py
```

### Strategy Template Engine

Provides reusable blueprints such as trend pullback, breakout, mean reversion, volatility expansion, and momentum continuation.

### Strategy Composer

Assembles candidate strategies by satisfying research constraints with compatible market-regime, entry, confirmation, exit, risk, and trade-management plugins. It never performs optimization and never sends invalid strategies downstream. The orchestrator decides what should be built; the composer decides which reusable parts satisfy the constraints.

The composer pipeline is:

```text
Research Goal
  -> Constraint Builder
  -> Knowledge Base
  -> Compatibility Engine
  -> Dependency Engine
  -> Strategy Graph Builder
  -> Complexity Scoring
  -> Diversity Filter
  -> Candidate Strategies
```

Every candidate has a decision trace that records which hypothesis, constraints, knowledge, plugin selections, rejection reasons, complexity estimate, and diversity decision produced it.

### Parameter Generator

Generates valid parameter combinations and rejects invalid combinations before optimization.

### Optimization Laboratory

Finds stable parameter regions instead of single best historical-profit points. It supports grid search, random search, Bayesian optimization, Optuna, genetic algorithms, particle swarm, and future ML search surfaces, but its primary objective is parameter stability.

The lab rejects sharp peaks such as one high-profit EMA value surrounded by weak results. It produces parameter candidates, stable regions, sensitivity scores, parameter landscapes, robustness labels, and Knowledge Base updates.

### Research Review Board

Automated gate before expensive validation. It checks parameter stability, complexity score, diversity score, decision trace, and Knowledge Base alignment. Human approval is not required in normal operation, but the gate protects the research pipeline from overfit or low-quality outputs.

### Backtesting Engine

Evaluates historical performance through an event-driven market simulator. It processes new candles, session changes, order submissions, fills, stop updates, take-profit hits, position closes, and risk events instead of treating candles as direct profit calculations.

Backtesting Engine 2.0 contains a market simulator, execution simulator, position manager, portfolio manager, trade journal, performance engine, replay engine, time machine, and report generator. The same event model should later be shared with the live trading engine to reduce simulation/live drift.

Every trade records the entry reason, decision trace, feature vector, market regime, strategy version, parameters, and exit reason.

### Validation Engine

The Strategy Validation Platform is the QA department for QuantForge AI. It runs walk-forward testing, out-of-sample testing, Monte Carlo simulation, cross-pair testing, cross-timeframe testing, parameter stability checks, stress testing, confidence scoring, and deployment board decisions.

Validated strategies receive a permanent Strategy Passport and become immutable Strategy Assets containing the strategy definition, plugin versions, parameters, feature versions, decision trace, optimization report, validation report, passport, deployment history, and live performance history.

### Production Strategy Management

Production treats Strategy Assets like installable apps. The Strategy Catalog stores every asset and version; the Strategy Registry tracks active, inactive, paper, production, deprecated, and retired states; the Deployment Manager installs, upgrades, rolls back, disables, promotes, and archives assets.

The Portfolio Manager activates groups of strategies, the Capital Allocator assigns portfolio weights, the Strategy Scheduler controls sessions and timeframes, the Live Performance Monitor compares research versus live behavior, and the Retirement Manager removes degraded strategies automatically.

### Autonomous Research Validation

Autonomous Research Validation runs the full research lifecycle as one reproducible system. It accepts a research objective, creates hypotheses, plans immutable experiments, selects datasets, composes valid candidate strategies, optimizes stable parameter regions, backtests, validates, ranks, publishes approved Strategy Assets, updates the Knowledge Base, and writes audit-ready reports.

This stage measures platform process quality rather than trading profitability. It proves that QuantForge AI can complete at least 100 experiments without manual intervention, reject invalid or statistically weak candidates, preserve every decision trace, and publish only fully validated Strategy Assets to the catalog.

### Strategy Ranking Engine

Ranks validated strategies with configurable weighted metrics such as profit factor, Sharpe ratio, max drawdown, walk-forward score, Monte Carlo score, trade count, and cross-pair stability.

### Research Analytics Engine

Compares templates, plugins, feature importance, robust parameter ranges, overfitting risk, and recommends future experiments.

### Strategy Repository

Stores approved strategy versions with template, plugins, parameters, validation results, ranking score, and deployment status.
