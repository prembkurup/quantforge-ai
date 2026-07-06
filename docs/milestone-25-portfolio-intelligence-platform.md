# Milestone 25 - Portfolio Intelligence Platform

**Version:** 2.0  
**Phase:** Intelligent Intraday Trading  
**Status:** Implemented MVP

## 25.1 Vision

Portfolio Intelligence decides whether the current strategy portfolio is healthy enough to trade, remain in paper review, rebalance, or pause.

It extends the Milestone 24 decision layer from single-trade eligibility into portfolio-level supervision.

## 25.2 Scope

- Portfolio policy and acceptance criteria
- Portfolio health score
- Correlation profile and clusters
- Allocation decision trace
- Drift detection against validation evidence
- Stress-test scenarios
- Portfolio KPIs
- Daily portfolio review
- Lifecycle status and retirement candidates

## 25.3 Runtime Surfaces

- Backend engine: `quantforge.live.portfolio_intelligence`
- Dashboard API: `GET /api/portfolio/intelligence`
- Dashboard page: `/portfolio-intelligence`
- Script: `.\.venv\Scripts\python .\scripts\portfolio_intelligence.py`
- Launcher: `.\scripts\start_portfolio_intelligence.bat`

## 25.4 Acceptance Criteria

Milestone 25 is complete when QuantForge AI can:

- Score portfolio health from deterministic policy checks.
- Detect allocation, correlation, stress, and live-vs-validation drift issues.
- Produce an auditable allocation decision trace.
- Generate a daily portfolio review with watchlist and next actions.
- Expose portfolio KPIs and lifecycle status through the read-only dashboard API.
- Surface the same information in the React dashboard and operational script.
