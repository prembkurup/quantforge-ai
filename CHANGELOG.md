# Changelog

## Unreleased

- Added Version 2.0 / Milestone 23 Intraday Trading Framework design specification.
- Extended Milestone 23 with intraday metrics, certification, portfolio construction, daily dashboard, reporting, learning loop, deliverables, and exit criteria.
- Started Milestone 23 implementation with intraday policy, session, daily risk, forced-close, session portfolio, and certification primitives.
- Added intraday daily metrics, daily report, learning-loop, and dashboard API snapshot support.
- Added script and Windows launcher for the Version 2 intraday daily operations snapshot.
- Wired forced end-of-day intraday close receipts into live execution and Trade Journal evidence.
- Added approved-asset intraday certification and real session portfolio selection to the daily operations API.
- Added React Intraday dashboard page for daily trading, daily risk, certification, report, learning-loop, and journal evidence.
- Added start/end-of-day intraday scheduler script and Windows launcher.
- Added the daily market readiness gate that scores pre-trade conditions from 0-100 before any new intraday trades are considered.
- Added Milestone 24 Decision Intelligence Platform primitives, API, dashboard page, scripts, tests, and specification.
- Extended Milestone 24 with dashboard decision fields, daily trading journal, decision timeline, and decision quality metrics.
- Added Milestone 25 Portfolio Intelligence primitives, API, dashboard page, scripts, tests, and specification.
- Restored QuantForge AI repo-facing metadata and documented the intraday-only strategy policy.
- Added Admin live trading master switch through `risk.live_trading_enabled`.
- Connected the dashboard header to live platform health and live trading status.
- Added 30-row pagination to Workflow Events.
- Added automatic 30-row pagination to large Research page lists.
- Improved Workflow live-gate wording so policy, certification, and full-history blockers are clearer.
- Added always-on research orchestration and historical validation worker entry points.
- Added dashboard/API test coverage for live trading status, workflow state, research orchestration, and history validation.
