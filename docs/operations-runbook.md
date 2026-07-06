# Operations Runbook

## Dashboard

- Start the FastAPI dashboard API with `.\.venv\Scripts\python .\scripts\serve_dashboard_api.py`.
- Start the React dashboard from `frontend/` with `npm run dev`.
- The header reads platform health and live trading status from `GET /api/dashboard/overview`.
- The Admin page owns the `risk.live_trading_enabled` setting.

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
