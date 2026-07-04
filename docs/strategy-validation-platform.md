# Strategy Validation Platform

The Strategy Validation Platform is the QA department for QuantForge AI.

Nothing reaches live trading unless every validation gate passes or the Deployment Board explicitly routes it to paper trading or review.

## Pipeline

```text
Optimized Strategy
  -> Walk Forward
  -> Out-of-Sample
  -> Monte Carlo
  -> Cross Pair
  -> Cross Timeframe
  -> Parameter Stability
  -> Stress Testing
  -> Confidence Score
  -> Deployment Decision
```

## Components

- `WalkForwardValidator` stores every train/test window.
- `OutOfSampleValidator` checks the permanently hidden validation period.
- `MonteCarloLab` randomizes spread, slippage, entry delay, exit delay, and missing trades.
- `CrossPairValidator` checks whether behavior remains stable across related instruments.
- `CrossTimeframeValidator` checks M15, H1, and H4 behavior.
- `ParameterStabilityValidator` uses Optimization Laboratory regions to reject fragile strategies.
- `StressTestingLab` simulates high spread, network delay, market gaps, volatility spikes, and low liquidity.
- `ConfidenceEngine` produces a confidence percentage and deployment grade.
- `DeploymentBoard` decides approved, paper trade, reject, or needs review.
- `StrategyPassport` gives each validated strategy a permanent identity.
- `StrategyAsset` packages the complete immutable lifecycle record.

## Strategy Passport

Example:

```text
Strategy ID: QF-2026-00431
Created: 2026-08-01
Template: Trend Pullback
Market Regime: Trending
Validation Grade: A
Confidence: 93%
Production: YES
Version: 3.2
```

## Strategy Assets

QuantForge AI should treat strategies as immutable, versioned Strategy Assets.

A Strategy Asset includes:

- strategy definition
- plugin versions
- parameters
- feature versions
- decision trace
- optimization report
- validation report
- strategy passport
- deployment history
- live performance history

This makes promotion, rollback, auditing, and long-term maintenance safer.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\validate_strategy.py
```

Expected shape:

```text
Strategy
QF-2026-00431

Walk Forward
PASS

Monte Carlo
PASS

Cross Pair
PASS

Stress
PASS

Confidence
93%

Deployment
APPROVED
```
