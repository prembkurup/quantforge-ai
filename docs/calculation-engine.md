# Calculation Engine

The Calculation Engine is the shared layer for all derived market values used by research, backtesting, validation, and live signal evaluation.

It replaces the narrower idea of a standalone Indicator Engine. Indicators remain important, but they are only one calculator family.

## Calculator Families

- Indicator Calculator
- Statistical Calculator
- Price Action Calculator
- Pattern Calculator
- Market Structure Calculator
- Volatility Calculator
- Session Calculator
- Liquidity Calculator
- Custom Calculator Plugins

## Design Rules

- Raw candles remain the source of truth.
- Calculation outputs are derived data.
- Calculation outputs are dynamic by default and are not permanently stored unless a cache is explicitly useful.
- Every calculator must be deterministic for the same input data and parameters.
- Every calculator should declare a stable key, category, parameters, and version when it becomes production-grade.
- Research features consume Calculation Engine outputs; they should not call ad hoc calculation code directly.

## Initial Code Boundary

The initial package is `quantforge.calculations`.

- `CalculationEngine` provides registry-backed execution.
- `CalculationCategory` defines calculator families.
- `CalculationSpec` defines a registered calculation.
- `calculations.indicators` contains Version 1 indicator calculators.
- `calculations.statistics` contains rolling and return statistics.
- `calculations.price_action` contains candle anatomy and candle patterns.
- `calculations.market_structure` contains swing and structure calculations.
- `calculations.sessions` contains session flags.
- `calculations.volatility` starts true range and close-to-close volatility.
- `features.registry` stores versioned, dependency-aware feature definitions.
- `features.generators` creates standardized feature vectors for downstream systems.

The legacy `quantforge.indicators` package remains as compatibility exports while newer code moves to the Calculation Engine.

## Completion Gate

Milestone 3 is gated by:

- A live feature-vector command using CoreUI candles.
- Unit tests for indicator, statistics, price action, market structure, session, feature registry, custom plugin, cache, and multi-timeframe paths.
- Coverage target of at least 95% across `quantforge.calculations` and `quantforge.features`.

```powershell
.\.venv\Scripts\python .\scripts\generate_feature_vector.py --pair EUR_USD --timeframe H1 --candles 300
.\.venv\Scripts\python -m pytest --cov=quantforge.calculations --cov=quantforge.features --cov-report=term-missing --cov-fail-under=95
```

## Downstream Contract

Strategy, experiment, backtesting, and validation modules should consume standardized feature vectors instead of calling individual indicator plugins directly.

```text
OHLCV
  -> Calculation Engine
  -> Feature Vector
  -> Experiment Engine
  -> Strategy Factory
  -> Backtesting
  -> Validation
```
