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
- `calculations.indicators` contains EMA, RSI, and ATR.
- `calculations.statistical` starts rolling mean, rolling standard deviation, and z-score.
- `calculations.volatility` starts true range and close-to-close volatility.

The legacy `quantforge.indicators` package remains as compatibility exports while newer code moves to the Calculation Engine.
