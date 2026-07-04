# Live Trading Engine

Milestone 14 turns QuantForge AI from a research platform into a production trading platform.

The Live Trading Engine is not just an OANDA order sender. It is an event-driven runtime that evaluates market events, selects approved Strategy Assets, decides whether trading conditions are acceptable, checks risk, executes, monitors, stores state, recovers, and synchronizes with the broker.

## Pipeline

```text
Market Stream
  -> Event Bus
  -> Feature Engine
  -> Market Regime
  -> Strategy Selector
  -> Trade Decision Engine
  -> Signal Generator
  -> Risk Engine
  -> Execution Manager
  -> OANDA
```

## Components

- `LiveEventBus` receives live events such as candles, price updates, session changes, order fills, heartbeats, connection loss, and spread changes.
- `MarketStream` seeds broker and market events for the demo runtime.
- `LiveFeatureEngine` converts market events into live feature vectors.
- `LiveMarketRegimeEngine` classifies the active market regime.
- `StrategySelector` chooses the best active Strategy Asset from the catalog, regime, portfolio, and capital allocation context.
- `TradeDecisionEngine` asks whether the platform should trade right now before any actionable signal is emitted.
- `SignalGenerator` produces `BUY`, `SELL`, `EXIT`, or `HOLD`.
- `LiveRiskController` checks risk limits, exposure, drawdown, daily loss, and order size before execution.
- `ExecutionManager` creates paper-safe OANDA orders in the demo and can use `OandaExecutionClient` when real credentials are supplied.
- `PositionMonitor` tracks open positions, floating P/L, margin, and exposure.
- `PortfolioController` manages Strategy Assets as a portfolio rather than one strategy at a time.
- `LiveStateStore` keeps live orders, positions, signals, regimes, portfolio, and risk state in memory with snapshots.
- `RecoveryManager` restores state after restart.
- `SynchronizationManager` compares internal state with broker state and repairs mismatches.

## Trade Decision Engine

The Trade Decision Engine keeps strategy logic clean. It centralizes execution-time decisions that should block trading even when a strategy has a valid signal:

- spread too high
- high-impact news window active
- portfolio exposure too high
- daily loss limit breached
- broker health degraded
- connection unhealthy

Only when this layer allows trading can the Signal Generator emit an actionable order signal.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\live_trading.py
```

Expected shape:

```text
System

Connect
YES

Receive Market
6 events

Generate Signals
1

Execute
1 orders

Monitor
1 open positions

Recover
YES

Synchronize
YES

Run
24/7 READY
```

## Production Note

The demo path uses paper OANDA execution by default and does not require real credentials. Real order placement should only be enabled with explicit OANDA credentials, deployment controls, monitoring, and operational runbooks.
