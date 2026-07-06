# Operations Runbook

## Dashboard

- Start the FastAPI dashboard API with `.\.venv\Scripts\python .\scripts\serve_dashboard_api.py`.
- Start the React dashboard from `frontend/` with `npm run dev`.
- The header reads platform health and live trading status from `GET /api/dashboard/overview`.
- The Admin page owns the `risk.live_trading_enabled` setting.
- The Intraday page reads `GET /api/intraday/daily` for market readiness, session, daily P/L, open positions, daily risk, certification, report, learning-loop, and Trade Journal evidence.
- The Decision Intel page reads `GET /api/intraday/decision-intelligence` for opportunity score, market quality, news state, trade eligibility, final decision, decision trace, daily plan, dynamic risk budget, and status reasons.
- The Decision Intel page also displays the decision timeline, Daily Trading Journal, and Decision Quality Metrics so avoided trades are auditable.

## Intraday Operations

- Run the daily operations snapshot with `.\.venv\Scripts\python .\scripts\intraday_daily_operations.py`.
- Run the Decision Intelligence snapshot with `.\.venv\Scripts\python .\scripts\intraday_decision_intelligence.py`.
- The first start-of-day decision is the market readiness score. Scores of 90-100 mean excellent conditions, 70-89 normal trading, 40-69 selective trading, and below 40 no new trades unless exceptional conditions arise.
- A strategy signal is not executable until Decision Intelligence marks the strategy eligible and the Trade Decision Engine returns a final BUY, SELL, EXIT, HOLD, or NO TRADE decision with trace evidence.
- Record start-of-day activation with `.\.venv\Scripts\python .\scripts\intraday_daily_scheduler.py --mode start`.
- Record end-of-day report and learning updates with `.\.venv\Scripts\python .\scripts\intraday_daily_scheduler.py --mode end`.
- Forced end-of-day position closes are written to `var/intraday_trade_journal.json` as Trade Journal evidence.
- Daily report automation writes `var/intraday_daily_reports.json` and learning updates to `var/intraday_knowledge_updates.json`.

## Research Workers

- Full-history research runs in controlled batches, commonly with `--max-jobs 3`.
- The worker sleeps for `full_history.sleep_seconds` between active loops.
- When no work exists, it sleeps for `full_history.idle_sleep_seconds`.
- If a new full-history window appears while a worker is in the idle interval, restarting the worker lets it claim work immediately.

## Live Trading Gate

Live trading requires all of these to line up:

- Admin switch: `risk.live_trading_enabled = true`.
- Workflow policy: live trading must not be blocked by policy.
- Production certification must pass.
- Broker credentials must be configured.
- Runtime risk checks must allow execution.

The dashboard can show Live Trading as enabled at the admin/platform level before real broker execution is allowed.
