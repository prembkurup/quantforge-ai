# Backtesting Engine 2.0

The Backtesting Engine answers the only question that matters after composition and optimization:

```text
Would this strategy have made money under realistic trading conditions?
```

It is event-driven. It does not simply loop over candles and book idealized profit.

## Architecture

```text
Strategy
  -> Market Simulator
  -> Execution Simulator
  -> Position Manager
  -> Portfolio Manager
  -> Performance Engine
  -> Trade Journal
  -> Backtest Report
```

## Event Core

Backtesting and future live trading should process the same event concepts:

- new candle
- order submitted
- order filled
- stop loss modified
- take profit hit
- position closed
- session open
- session close
- risk rule triggered

This reduces drift between simulated and live behaviour.

## Components

- `MarketSimulator` emits session and candle events, with room for intrabar movement, weekend gaps, and market closures.
- `ExecutionSimulator` models order type, spread, slippage, and latency.
- `PositionManager` tracks open positions, entry data, floating P/L, margin, and closed trades.
- `PortfolioManager` tracks balance, equity, free margin, exposure, strategy allocation, and portfolio-ready state.
- `TradeJournal` records every completed trade as an auditable object.
- `PerformanceEngine` computes return, risk, statistical, distribution, and behaviour metrics.
- `ReplayEngine` builds frames for watching the strategy think through events.
- `TimeMachine` freezes market data to a pretend date so research cannot use future knowledge.
- `BacktestReport` combines strategy summary, trade statistics, risk metrics, equity curve, drawdown curve, monthly returns, decision trace summary, and recommendations.

## Trade Audit

Every trade records:

- entry reason
- decision trace
- feature vector
- market regime
- strategy version
- parameters
- exit reason

Years later, the platform can explain exactly why a trade happened.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\backtest.py
```

Expected shape:

```text
Strategy
Trend Pullback

Trades
843

Profit Factor
2.21

Max DD
8.2%

Sharpe
1.78

Validation Ready
YES
```
