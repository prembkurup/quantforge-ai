# Milestone 24 - Intraday Decision Intelligence Platform

**Version:** 2.0  
**Phase:** Intelligent Intraday Trading  
**Status:** Design Specification

## 24.1 Vision

The Decision Intelligence Platform decides whether QuantForge AI should participate in today's market.

It sits between the Research Platform and the Live Trading Platform.

Its purpose is not to generate trading signals. Its purpose is to determine whether trading is justified.

## 24.2 Primary Principle

A trading signal does not automatically become a trade.

Every potential trade must satisfy:

```text
Strategy
  -> Market Conditions
  -> Portfolio Conditions
  -> Risk Conditions
  -> Operational Conditions
  -> Decision Intelligence
  -> Trade
```

If any layer rejects the trade, no trade is executed.

## 24.3 Decision Architecture

```text
Market Data
  -> Calculation Engine
  -> Feature Engine
  -> Market Regime Engine
  -> Daily Opportunity Engine
  -> Market Quality Engine
  -> Strategy Selector
  -> Trade Eligibility Engine
  -> Trade Decision Engine
  -> Risk Engine
  -> Execution Manager
```

## 24.4 Daily Opportunity Engine

Purpose: estimate whether today's market is worth trading.

Inputs:

- Market regime
- Volatility
- Session
- Spread
- Portfolio
- Risk
- Knowledge Base

Outputs:

- Opportunity score from 0 to 100
- Explainable factors and rejection reasons

Suggested interpretation:

- 90-100: Excellent
- 70-89: Good
- 40-69: Selective
- Below 40: Avoid new trades

## 24.5 Market Quality Engine

Purpose: evaluate the current trading environment independently of strategy signals.

Inputs:

- Spread
- Liquidity
- Volatility
- Price stability
- Session
- Market structure

Outputs:

- Market quality score
- Rating: Poor, Fair, Good, or Excellent

## 24.6 News & Event Filter

Purpose: prevent low-quality entries around scheduled market events.

Supported event types include:

- Interest rate decisions
- CPI
- PPI
- GDP
- Employment reports
- Central bank speeches
- NFP
- PMI

Policy:

- Pause new entries before configurable events.
- Resume after configurable cooldown.
- Existing positions continue to be managed.

## 24.7 Trade Eligibility Engine

Purpose: determine whether a strategy is eligible to trade.

Checks:

- Strategy active
- Session allowed
- Opportunity score
- Market quality
- Portfolio exposure
- Daily risk remaining
- News filter
- Manual trading suspension
- Broker health

Every rejection records a reason.

## 24.8 Trade Decision Engine

Purpose: produce the final trading decision.

Possible outcomes:

- BUY
- SELL
- EXIT
- HOLD
- NO TRADE

Each decision includes confidence, reason, supporting evidence, and a decision trace.

## 24.9 Decision Trace

Every decision records:

- Timestamp
- Instrument
- Strategy Asset
- Feature Vector
- Market regime
- Opportunity score
- Market quality
- Risk state
- Portfolio state
- News state
- Final decision
- Decision confidence
- Reason codes

The decision trace becomes part of the permanent audit record.

## 24.10 Daily Trading Plan

At the beginning of each trading day the platform generates a plan.

Contents:

- Preferred sessions
- Preferred strategy families
- Daily risk budget
- Capital allocation
- Expected regimes
- Maximum trades
- Trading objectives

The plan guides intraday behavior.

## 24.11 Intraday Session Management

Supported sessions:

- Asian
- London Open
- London
- London/New York Overlap
- New York
- Late New York

Each session has expected volatility, expected liquidity, preferred strategies, and preferred risk.

## 24.12 Dynamic Daily Risk Budget

The Daily Risk Budget adapts to market conditions:

- Excellent opportunity: normal risk
- Moderate opportunity: reduced risk
- Poor opportunity: minimal risk
- No opportunity: no new trades

The budget resets each trading day.

## 24.13 Intraday Trading Status

Possible values:

- ACTIVE
- WAITING
- PAUSED
- NO TRADING
- FINISHED

Reasons are displayed for every non-active state.
