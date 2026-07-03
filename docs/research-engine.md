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
8. Strategy Template Selection
9. Strategy Factory
10. Parameter Generation
11. Optimization
12. Backtesting
13. Validation
14. Ranking
15. Research Analytics
16. Strategy Publishing

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

### Strategy Template Engine

Provides reusable blueprints such as trend pullback, breakout, mean reversion, volatility expansion, and momentum continuation.

### Strategy Factory

Generates candidate strategies by selecting a template, selecting compatible plugins, and generating candidate structure. It never performs optimization.

### Parameter Generator

Generates valid parameter combinations and rejects invalid combinations before optimization.

### Optimization Engine

Searches parameter space with grid search, random search, Bayesian optimization, genetic algorithms, or Optuna. The optimization objective is configurable.

### Backtesting Engine

Evaluates historical performance with realistic spread, slippage, commission, position sizing, partial close, trailing stop, multiple positions, and execution rules.

### Validation Engine

Runs walk-forward testing, out-of-sample testing, Monte Carlo simulation, cross-pair testing, cross-timeframe testing, and stability analysis.

### Strategy Ranking Engine

Ranks validated strategies with configurable weighted metrics such as profit factor, Sharpe ratio, max drawdown, walk-forward score, Monte Carlo score, trade count, and cross-pair stability.

### Research Analytics Engine

Compares templates, plugins, feature importance, robust parameter ranges, overfitting risk, and recommends future experiments.

### Strategy Repository

Stores approved strategy versions with template, plugins, parameters, validation results, ranking score, and deployment status.
