# Milestone 23 - Intraday Trading Framework

**Version:** 2.0  
**Phase:** Intraday Trading Platform  
**Status:** Design Specification

## 23.1 Vision

QuantForge AI Version 2.0 transforms the platform from a general quantitative trading system into an institutional intraday trading platform.

Version 2.0 focuses on:

- Intraday trading only
- Daily capital rotation
- No overnight exposure
- Session-aware trading
- Daily risk control
- Consistent long-term daily performance

## 23.2 Primary Objective

The objective is not to maximize historical profit.

The objective is to build a portfolio of robust intraday strategies that:

- Open positions during the trading day.
- Close every position before the configured end-of-day cutoff.
- Protect capital through strict daily risk controls.
- Produce consistent performance over long periods.

## 23.3 Trading Policy

Every production strategy must follow the Intraday Trading Policy.

Mandatory rules:

```text
Trading Style:      INTRADAY
Overnight Positions: NOT ALLOWED
Weekend Positions:   NOT ALLOWED
Force Close:         REQUIRED
Daily Risk Limits:   REQUIRED
Session Awareness:   REQUIRED
```

Strategies violating these rules cannot be deployed.

## 23.4 Intraday Strategy Asset

A new Strategy Asset type is introduced.

```text
Strategy Asset
|-- Swing
|-- Position
`-- Intraday
```

The production portfolio uses only Intraday Strategy Assets.

Each asset contains:

- Trading Style
- Preferred Session
- Maximum Trade Duration
- Force Close Time
- Latest Entry Time
- Daily Risk Profile
- Intraday Score
- Session Compatibility

## 23.5 Daily Trading Lifecycle

Every trading day follows the same lifecycle.

```text
Trading Day Starts
  |
  v
Load Approved Intraday Strategies
  |
  v
Determine Current Trading Session
  |
  v
Activate Session Portfolio
  |
  v
Receive Live Market Events
  |
  v
Generate Trade Opportunities
  |
  v
Risk Evaluation
  |
  v
Execute Approved Trades
  |
  v
Monitor Open Positions
  |
  v
Force Close Before End Of Day
  |
  v
Generate Daily Reports
  |
  v
Update Knowledge Base
```

## 23.6 Session Engine

The Session Engine becomes a production-critical module.

Supported sessions:

- Asian
- London Open
- London
- London-New York Overlap
- New York
- Late New York

Every Strategy Asset declares:

- Preferred Session
- Allowed Sessions
- Blocked Sessions

Strategies remain inactive outside their approved sessions.

## 23.7 Session Portfolio

Instead of one portfolio for the whole day, the platform maintains session portfolios.

Example:

- Asian Portfolio
- London Portfolio
- New York Portfolio

The Portfolio Manager activates the appropriate portfolio automatically.

## 23.8 Daily Risk Engine

Version 2.0 introduces dedicated daily controls.

Examples:

- Maximum Daily Loss
- Maximum Daily Drawdown
- Maximum Trades Per Day
- Maximum Consecutive Losses
- Maximum Daily Exposure
- Maximum Strategy Allocation
- Maximum Currency Exposure

If any mandatory rule is violated:

```text
Stop Opening New Trades
Continue Managing Existing Positions
Force Close At End Of Day
```

## 23.9 Entry Window Rules

Strategies must define:

- Earliest Entry Time
- Latest Entry Time

Example:

```text
Earliest Entry: 07:00 UTC
Latest Entry:   19:30 UTC
```

No new positions may be opened after the latest entry time.

## 23.10 Forced End-of-Day Exit

Every open position must be closed before the configured cutoff.

Example:

```text
Force Close Time: 21:45 UTC
```

The Execution Manager automatically closes remaining positions.

Reasons are recorded in the Trade Journal.

## 23.11 Intraday Metrics

Version 2.0 introduces new research metrics. These metrics supplement, not replace, the existing validation metrics.

Performance metrics:

- Average Daily Profit
- Winning Days
- Losing Days
- Average Trades Per Day
- Average Trade Duration
- Profit Per Trading Hour
- Daily Expectancy

Risk metrics:

- Maximum Daily Drawdown
- Average Daily Drawdown
- Daily Risk Utilization

Operational metrics:

- Average Daily Signals
- Average Daily Executions
- Average Daily Exposure
- Average Daily Slippage

## 23.12 Intraday Strategy Certification

Every intraday strategy must satisfy additional requirements before deployment.

Examples:

| Requirement | Target |
| --- | --- |
| No overnight positions | 100% |
| Trades closed before cutoff | 100% |
| Session compatibility | Pass |
| Daily drawdown | Below configured limit |
| Average trade duration | Within policy |

Certification is required before deployment.

## 23.13 Intraday Portfolio Construction

Portfolio optimization should consider:

- Session diversification
- Strategy family diversification
- Currency diversification
- Expected daily correlation
- Expected daily drawdown
- Capital utilization

The objective is balanced daily performance rather than concentrating capital in one strategy.

## 23.14 Daily Operations Dashboard

The dashboard displays:

- Current Session
- Today's P/L
- Today's Trades
- Open Positions
- Remaining Daily Risk
- Daily Drawdown
- Session Portfolio
- Active Strategies
- Trading Status

Possible trading statuses:

- ACTIVE
- PAUSED (Risk Limit)
- FINISHED (End Of Day)
- NO TRADING

## 23.15 Daily Report

A daily report is automatically generated after market close.

It includes:

- Daily Performance
- Strategy Performance
- Session Performance
- Risk Utilization
- Trade Summary
- Execution Summary
- Drift Summary
- Knowledge Updates
- Improvement Recommendations

Reports become part of the Knowledge Base.

## 23.16 Daily Learning Loop

At the end of every trading day:

```text
Trades
  |
  v
Performance Analysis
  |
  v
Knowledge Base
  |
  v
Research Priorities
  |
  v
Future Campaigns
```

Every day improves future research.

## 23.17 Acceptance Criteria

Version 2.0 Intraday Framework is complete when:

- Every production strategy is certified as intraday.
- No overnight positions remain.
- No weekend positions remain.
- Session activation works automatically.
- Daily risk limits are enforced.
- Forced end-of-day exits execute correctly.
- Daily reports are generated automatically.
- Daily learning updates the Knowledge Base.
- Dashboard accurately reflects daily operational status.

## 23.18 Deliverables

Software deliverables:

- Intraday Policy Engine
- Session Engine
- Session Portfolio Manager
- Daily Risk Controller
- Forced Close Manager
- Intraday Certification Engine
- Daily Report Generator

Dashboard deliverables:

- Session Dashboard
- Daily Trading Dashboard
- Daily Risk Dashboard

Documentation deliverables:

- Intraday Trading Policy
- Session Rules
- Daily Risk Policy
- End-of-Day Procedures

## 23.19 Exit Criteria

Milestone 23 is complete when QuantForge AI consistently operates as an institutional intraday trading platform, automatically selecting session-appropriate strategies, enforcing daily risk policies, closing all positions before the configured end-of-day cutoff, and producing complete daily operational evidence.

## 23.20 Guiding Principle

Version 2.0 is based on one core principle:

**The goal is not to trade every day. The goal is to trade only when high-quality intraday opportunities exist, while ensuring that every trading day ends with zero open positions and well-controlled risk.**

The platform should always be willing to end the day with no trades rather than force low-quality entries simply to generate daily activity.

**End of Milestone 23 - Intraday Trading Framework**
