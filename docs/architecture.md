# QuantForge AI Architecture

## Purpose

QuantForge AI discovers, validates, and runs quantitative Forex strategies. The platform must support long-term research without compromising live trading safety.

## System Boundaries

QuantForge AI has two main engines:

- Research engine: offline strategy discovery, backtesting, validation, walk-forward tests, and candidate ranking.
- Live trading engine: real-time signal evaluation, risk checks, order execution, monitoring, and audit logs.

These engines share market data and strategy definitions, but they do not share runtime state.

## Data Architecture

PostgreSQL is the source of truth for all durable records:

- raw OHLCV candles
- instruments
- strategy definitions
- experiments and research runs
- research knowledge findings
- backtest results
- selected strategy candidates
- live orders, positions, executions, and audit logs

Raw OHLCV candles are stored permanently. Calculation outputs are not stored by default because they are derived data and can explode storage requirements. Indicators, statistics, volatility measures, price action, patterns, market structure, sessions, liquidity, and custom plugin calculations are calculated dynamically in Python when research or live signal evaluation needs them.

Redis is only for live cache:

- latest candle snapshots
- current spread snapshots
- temporary signal state
- live engine heartbeats

Parquet is only for research cache:

- local experiment datasets
- feature matrices for repeatable research
- large intermediate outputs that can be regenerated from PostgreSQL

## Research Memory

QuantForge AI includes a Research Knowledge Base between market regime detection and plugin/template selection:

```text
OHLCV
  -> Calculation Engine
  -> Feature Engine
  -> Market Regime Engine
  -> Research Knowledge Base
  -> Research Orchestrator
  -> Plugin Framework
  -> Strategy Templates
  -> Strategy Composer
```

The Knowledge Base stores durable research findings such as positive edges, failed setups, neutral results, and risk warnings. It links each finding to experiment lineage, instrument, timeframe, market regime, session, feature conditions, metrics, confidence, evidence count, and dependency versions.

The platform should query this memory before launching expensive experiments or generating new strategy candidates.

The Research Orchestrator turns that memory into an experiment plan. It chooses the dataset, features, templates, parameters, job queue, and result update path. It decides whether to run a new experiment, refine the hypothesis, skip a known failure, or collect more evidence before strategy generation.

## Strategy Discovery

Strategies are template-based and plugin-driven. Research is organized around experiments, not indicators. An experiment binds the dataset, feature set, strategy template, plugin versions, parameter search, validation results, analytics, and any published strategy versions.

The Strategy Composer is a constraint-based assembly layer. The orchestrator decides what should be built; the composer asks which reusable market-regime, entry, confirmation, exit, risk, and trade-management plugins satisfy the research constraints. It validates structure, estimates complexity, removes near-duplicates, and only then sends candidates to the Optimization Laboratory.

Every composer decision must be traceable: the hypothesis, applied constraints, knowledge influence, selected plugins, rejection reasons, complexity estimate, and diversity decision are recorded before optimization begins.

The Optimization Laboratory looks for stable parameter regions rather than the highest historical profit. It produces recommended parameter spaces, parameter landscapes, robustness estimates, and Research Knowledge Base updates. A Research Review Board checks parameter stability, complexity, diversity, decision traceability, and Knowledge Base alignment before candidates move to expensive backtesting and validation.

A strategy plugin declares:

- metadata
- required candle granularities
- required calculations
- parameter search space
- signal generation logic
- risk model hooks
- validation constraints

The research engine defines experiments, discovers plugins, expands parameter templates, identifies stable parameter regions, runs review gates, backtests, validates results, compares experiment analytics, and ranks candidates. Backtesting is event-driven: the simulator processes market, order, execution, position, portfolio, risk, and journal events rather than idealized candle outcomes. Validation is a QA platform with walk-forward, out-of-sample, Monte Carlo, cross-pair, cross-timeframe, parameter stability, stress, confidence, and deployment gates. The live engine should consume the same event concepts and only runs approved Strategy Assets.

QuantForge AI treats promoted strategies as immutable Strategy Assets. A Strategy Asset includes the definition, plugin versions, parameters, feature versions, decision trace, optimization report, validation report, Strategy Passport, deployment history, and live performance history.

Production Strategy Management is the bridge from research to live trading. Approved Strategy Assets enter a Strategy Catalog, move through the Strategy Registry and Deployment Manager, are assembled into portfolios, receive capital allocations and schedules, then progress from paper trading to production. Live performance is compared with research performance to detect drift, update the Knowledge Base, and retire degraded strategies automatically.

Autonomous Research Validation is the final research-side integration harness. It accepts a research objective, generates hypotheses, plans immutable experiments, selects datasets, composes valid strategies, optimizes stable parameter regions, backtests, validates, ranks, publishes Strategy Assets, updates the Knowledge Base, and emits reports and audit trails without manual intervention. Its purpose is scientific process validation, not a profitability claim.

## Live Execution

OANDA is the execution adapter for live orders.

The live engine flow is:

1. Load approved strategy version.
2. Read latest candles from PostgreSQL and live cache.
3. Calculate derived values dynamically through the Calculation Engine.
4. Generate signal.
5. Apply risk checks.
6. Send order through OANDA adapter.
7. Persist order, execution, and audit records in PostgreSQL.

Live Trading Engine 2.0 is event-driven. Market stream events flow through a Live Event Bus, live feature generation, market regime detection, Strategy Selector, Trade Decision Engine, Signal Generator, Live Risk Controller, Execution Manager, Position Monitor, State Store, Recovery Manager, and Synchronization Manager.

The Trade Decision Engine sits between strategy selection and signal generation. It asks whether QuantForge should trade right now based on spread, news windows, portfolio exposure, correlated positions, daily loss limits, market quality, broker health, and connection status. This keeps strategy logic clean while centralizing production trading permissions.

## Production Reliability

QuantForge AI includes an SRE layer for production readiness. Services report heartbeat, readiness, liveness, version, build, uptime, and dependency status. Health states are Healthy, Warning, Critical, and Offline.

The production platform emits Prometheus-style metrics, structured JSON logs, distributed trace spans, classified alerts, and automatic recovery actions. This protects against lost trading state, duplicate orders, silent service failures, and capital-risk events such as emergency daily-loss kill switches.

## Shadow Trading

Before live capital, approved Strategy Assets pass through Shadow Trading and Paper Trading. The live engine receives market events and produces decisions, but orders are routed to a Virtual Exchange and isolated Paper Portfolio. The platform audits every decision, compares expected research behavior with paper results, tracks prediction, execution, market, feature, and decision drift, and generates daily validation reports plus monthly promotion reviews.

A Digital Twin runs the broker execution path and internal simulation exchange path in parallel against the same market events, Strategy Assets, and feature vectors. If decisions diverge, promotion is frozen for investigation.

## Production Certification

Production Certification is the final quality gate before controlled live trading. The certification engine consumes evidence from Autonomous Research Validation, Strategy Validation, Production Engineering/SRE, and Shadow Trading.

Certification covers research, strategy, infrastructure, operations, security, risk, performance, and governance, with supporting checks for disaster recovery, data integrity, audit completeness, and Knowledge Base consistency. The weighted readiness score must meet the configured threshold, all mandatory domains must pass, and critical findings must be zero before live trading can be authorized.

Only a `CERTIFIED` decision from the Production Approval Manager allows controlled live trading. Provisionally certified, remediation-required, and rejected systems remain blocked from real capital.

## Institutional Research Campaigns

Institutional Research Campaigns run the complete research ecosystem as an autonomous quantitative research organization. Campaigns are divided into independent programs such as trend following, mean reversion, breakout, momentum, and volatility. Each program starts with hypotheses, plans experiments, composes strategies, optimizes stable regions, backtests, validates, ranks, updates the Knowledge Base, and publishes Strategy Assets.

Campaign results measure research outcomes rather than new software capability: experiments completed, candidate strategies generated, optimized and validated strategies, approved Strategy Assets, production candidates, Knowledge Base growth, and portfolio diversification. Portfolio construction intentionally balances strategy family, market regime, currency exposure, timeframe, and correlation instead of selecting only the highest-profit strategy.

## Autonomous Operations Validation

Autonomous Operations Validation proves the platform can run as a production trading organization over a 90-day simulation. The operations layer continuously monitors infrastructure, trading state, research activity, and service health; converts issues into incidents; executes self-healing recovery; synchronizes broker state every 60 seconds; evaluates operational drift; schedules non-interrupting maintenance; forecasts capacity; and archives daily, weekly, monthly, and capacity reports.

The validation gate fails if duplicate orders are created, broker mismatches remain unreconciled, recovery exceeds configured objectives, compliance evidence is incomplete, or reliability and trading KPIs miss their targets. Operational metrics feed the Knowledge Base and research priorities so production experience improves future Strategy Assets.

## Production Acceptance

Production Acceptance is the Version 1.0 release gate. It does not add trading functionality; it evaluates whether the complete platform is ready for controlled live capital under governance.

The acceptance manager combines evidence from production certification, institutional research campaigns, autonomous operations validation, SRE recovery, shadow trading, paper trading, risk controls, and compliance checks. Engineering, research, strategy, risk, operations, infrastructure, security, and business domains contribute to the final qualification score. Only a clean `APPROVED_FOR_PRODUCTION` decision with all signoffs recorded allows Stage A capital allocation.

Capital scaling is deliberately gradual. Stage A starts at small controlled capital, and progression to later stages requires successful trading days, risk compliance, operational reliability, and no critical incidents. Profitability alone never authorizes scaling.

## Safety Rules

- Research code must not place live orders.
- Live engine must not mutate strategy research results.
- OANDA credentials must not be hard-coded.
- Every live order must have an audit trail.
- Raw candle history must never be pruned by log retention jobs.
