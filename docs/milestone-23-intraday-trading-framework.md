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

