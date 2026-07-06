# Milestone 26 - Performance Attribution & Continuous Learning Platform

**Version:** 2.0  
**Phase:** Adaptive Intelligence  
**Status:** Implemented MVP

## 26.1 Vision

QuantForge AI should not only report trading results. It should explain why those results happened and turn that explanation into future research priorities.

## 26.2 Scope

- Performance Attribution Engine
- Continuous Learning Engine
- Research Prioritizer
- Strategy Evolution Manager
- Portfolio Evolution Manager
- Decision Quality Metrics
- Daily Learning Report
- Weekly Research Review
- Monthly Intelligence Review

## 26.3 Runtime Surfaces

- Backend engine: `quantforge.live.performance_learning`
- Dashboard API: `GET /api/performance/learning`
- Dashboard page: `/performance-learning`
- Script: `.\.venv\Scripts\python .\scripts\performance_learning.py`
- Launcher: `.\scripts\start_performance_learning.bat`

## 26.4 Learning Loop

```text
Trading Evidence
  -> Performance Attribution
  -> Knowledge Updates
  -> Research Priorities
  -> Strategy Evolution
  -> Portfolio Evolution
  -> Future Research Campaigns
```

## 26.5 Acceptance Criteria

Milestone 26 is complete when QuantForge AI can explain:

- Why each strategy contributed to portfolio performance.
- Which market regimes generated the highest returns.
- Which sessions produced the best opportunities.
- Which features mattered most.
- Which plugins consistently added value.
- Which portfolio decisions improved overall performance.
- Which research campaigns should run next.

All explanations are deterministic, traceable, and available through tests, scripts, API, and dashboard surfaces.
