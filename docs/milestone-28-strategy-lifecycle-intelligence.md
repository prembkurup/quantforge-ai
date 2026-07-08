# Milestone 28 - Strategy Lifecycle Intelligence and Self-Healing Platform

Version: 2.0
Phase: Autonomous Strategy Evolution
Status: Implemented foundation

## Vision

Every strategy asset has a lifecycle. It is born, learns, improves, degrades, and can eventually be retired. QuantForge AI should not treat strategies as static profitable/not-profitable objects. It should continuously ask whether each strategy is still healthy, suitable for the current market, correctly allocated, research-worthy, replaceable, or retirement-ready.

## Lifecycle Model

The implemented lifecycle engine supports these stages:

- Research Candidate
- Validated
- Paper Trading
- Production
- Healthy
- Watch
- Degraded
- Paused
- Research Required
- Improved Version
- Retired

The first production implementation is read-only and policy-driven. It recommends actions and produces reports without mutating the strategy asset store.

## Health Engine

Every strategy receives a `health_score` from 0 to 100.

Inputs:

- Performance: rolling profit factor, Sharpe, expectancy
- Risk: rolling drawdown, daily loss
- Market: regime match, opportunity score, market quality
- Operations: execution quality, slippage, latency, data quality
- Portfolio: correlation and allocation pressure
- Research: knowledge confidence and validation confidence

Health bands:

- 90-100: Excellent
- 75-89: Healthy
- 60-74: Watch
- 40-59: Degraded
- 20-39: Critical
- 0-19: Retire

## Root Cause Engine

Every degradation is classified into one or more categories:

- Market: regime drift, market quality, opportunity changes
- Strategy: edge drift, parameter/logic decay, expectancy failure
- Portfolio: concentration, correlation, over-allocation
- Risk: drawdown, daily loss, exposure pressure
- Execution: slippage, latency, execution quality
- Operations: missing candles, data quality, service interruption
- Research: validation confidence and knowledge confidence gaps

## Policy Actions

The engine can recommend:

- Continue
- Reduce Allocation
- Increase Allocation
- Pause
- Resume
- Send Back To Research
- Retire

Actions are generated from `StrategyLifecyclePolicy` thresholds and root-cause evidence.

## Research Feedback

When a strategy falls into Watch, Degraded, Critical, or Retire bands, the engine can produce a research goal:

- research goal id
- strategy asset id
- hypothesis
- experiment campaign
- priority

This closes the feedback loop from strategy health back into autonomous research.

## Version Evolution and Replacement

The dashboard payload includes:

- active version
- archived previous version
- candidate replacement version
- replacement process
- expected replacement health score

Old versions remain visible in `version_history`.

## Portfolio Impact

Before recommending a lifecycle action, the engine estimates:

- current allocation
- target allocation
- allocation delta
- expected profit-factor delta
- correlation effect
- risk effect
- expected return effect

This ensures strategy-level actions are evaluated against portfolio impact.

## Reports

Milestone 28 exposes these reports from `/api/strategy-lifecycle`:

- Daily Strategy Health Report
- Weekly Lifecycle Report
- Monthly Strategy Evolution Report
- Research Recommendation Report
- Portfolio Impact Report

## Dashboard

The Strategy Lifecycle page shows:

- strategy health summary
- per-strategy health score and status
- health timeline
- version history
- allocation history
- root cause analysis
- policy actions and recommendations
- research links and goals
- retirement status and evidence
- replacement candidates
- portfolio impact analysis
- report views
- acceptance criteria coverage

## Acceptance Criteria Mapping

The milestone is complete when:

- Every strategy has a health score.
- Every degradation has a classified root cause.
- Automatic actions are policy-driven.
- Research requests are generated automatically.
- Version replacement is supported.
- Retirement is evidence-based.
- Dashboard shows full lifecycle history.
- Portfolio impact is evaluated before changes.

The API exposes these checks under `acceptance_criteria`.

## Exit Criteria

Milestone 28 is complete when QuantForge AI no longer treats strategies as static objects. Every strategy asset becomes a living entity that is continuously monitored, evaluated, improved, replaced, or retired based on objective evidence.

Guiding principle: a strategy is never finished. Its value depends on how well it continues to perform under changing market conditions.
