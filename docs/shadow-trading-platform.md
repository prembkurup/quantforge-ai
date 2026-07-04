# Shadow Trading and Paper Trading Platform

Milestone 16 is the final gate before live capital. It makes QuantForge AI behave like a professional trading desk by placing validated Strategy Assets into paper and shadow trading before any production money is used.

## Pipeline

```text
Market Feed
  -> Live Trading Engine
  -> Trade Decision
  -> Shadow Execution Engine
  -> Paper Portfolio
  -> Performance Comparator
  -> Decision Auditor
  -> Knowledge Base
```

## Components

- `ShadowExecutionEngine` converts live trading signals into virtual exchange orders.
- `VirtualExchange` fills market, limit, and stop order models with spread, slippage, latency, and future partial-fill support.
- `PaperPortfolio` maintains a separate paper account with balance, equity, margin, exposure, portfolio, and history.
- `DecisionAuditor` records the full WHY behind every trade.
- `PredictionAnalyzer` compares research expectations with paper performance.
- `ExecutionAnalyzer` compares expected fill with actual virtual fill, spread, slippage, latency, and execution quality.
- `DriftAnalytics` tracks prediction, execution, market, feature, and decision drift.
- `TradeReplay` reconstructs every paper trade from market event to decision trace to fill.
- `ContinuousValidationEngine` creates daily validation reports.
- `PromotionEngine` performs monthly promotion review and decides whether to continue paper, promote, retire, or return to research.
- `DigitalTwin` runs broker/paper execution and internal simulation exchange paths in parallel and freezes promotion if decisions diverge.
- `ShadowTradingDashboard` summarizes market, orders, portfolio, drift, performance, and promotion status.

## Acceptance Criteria

The paper/shadow gate is designed for a 60-day observation period:

- zero unrecovered failures
- no duplicate orders
- internally consistent portfolio
- decision trace available for 100% of trades
- expected-vs-actual deviation within defined thresholds
- automatic promotion decisions
- full audit trail

## Digital Twin

The Digital Twin compares two trading engines:

- Engine A: broker execution path, live or paper
- Engine B: internal simulation exchange

Both receive the same market events, Strategy Assets, and feature vectors. If decisions diverge, promotion is frozen and an investigation alert is produced.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\shadow_trading.py
```

Expected shape:

```text
System

Receive Live Market
YES

Generate Signals
1

Trade Paper Portfolio
1 orders

Monitor Drift
5 dimensions

Audit Decisions
100%

Generate Reports
Daily + Monthly

Update Knowledge
5 records

Recommend Promotion
PROMOTE

Digital Twin
MATCH
```
