from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.config.settings import get_settings  # noqa: E402
from quantforge.live import (  # noqa: E402
    HistoricalCandleReplayStream,
    PaperTradingReplayRunner,
    ReplayCursor,
    ReplayProgressStore,
    ReplaySession,
    ReplayStatus,
    infer_replay_mode,
)
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine  # noqa: E402
from quantforge.research.full_history_scheduler import (  # noqa: E402
    FULL_HISTORY_RESEARCH_PAIRS,
    FULL_HISTORY_RESEARCH_START,
    FULL_HISTORY_RESEARCH_TIMEFRAMES,
)
from quantforge.research.strategy_assets import default_strategy_asset_repository  # noqa: E402


STATE_FILE = PROJECT_ROOT / "var" / "paper_replay_campaign_status.json"
DASHBOARD_PROGRESS_FILE = PROJECT_ROOT / "var" / "paper_replay_progress.json"
JOB_DIR = PROJECT_ROOT / "var" / "paper_replay" / "jobs"
LOCK_FILE = PROJECT_ROOT / "var" / "paper_replay_campaign.lock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automatically complete full-history Replay Paper Trading in parallel batches."
    )
    parser.add_argument("--from", dest="start", default=FULL_HISTORY_RESEARCH_START.date().isoformat())
    parser.add_argument("--to", dest="end", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--pairs", default=",".join(FULL_HISTORY_RESEARCH_PAIRS))
    parser.add_argument("--timeframes", default=",".join(FULL_HISTORY_RESEARCH_TIMEFRAMES))
    parser.add_argument("--max-workers", type=int, default=_env_int("QUANTFORGE_REPLAY_MAX_WORKERS", 6))
    parser.add_argument("--max-jobs-per-run", type=int, default=_env_int("QUANTFORGE_REPLAY_MAX_JOBS_PER_RUN", 24))
    parser.add_argument("--progress-interval-events", type=int, default=_env_int("QUANTFORGE_REPLAY_PROGRESS_INTERVAL_EVENTS", 1000))
    parser.add_argument("--strategy-asset-id", default="")
    parser.add_argument("--reset", action="store_true", help="Clear the replay campaign state before running.")
    return parser.parse_args()


def main() -> None:
    if not _acquire_lock():
        print("Replay Paper Trading automation is already running.")
        return
    args = parse_args()
    try:
        start = _parse_datetime(args.start)
        end = _parse_datetime(args.end, end_of_date=True)
        pairs = _csv_tuple(args.pairs)
        timeframes = _csv_tuple(args.timeframes)
        workers = max(1, int(args.max_workers or 1))
        max_jobs = max(0, int(args.max_jobs_per_run or 0))
        campaign_id = f"AUTO-REPLAY-{start.date().isoformat()}-{end.date().isoformat()}"

        if args.reset and STATE_FILE.exists():
            STATE_FILE.unlink()

        all_jobs = _build_jobs(campaign_id, pairs, timeframes, start, end)
        state = _load_state(campaign_id, pairs, timeframes, start, end, workers, all_jobs)
        _merge_missing_jobs(state, all_jobs)
        strategy_asset_id = _strategy_asset_id(args.strategy_asset_id)

        pending = _claim_pending_jobs(state, max_jobs=max_jobs)
        _save_state_and_progress(state, pairs, timeframes, start, end)
        if not pending:
            _save_state_and_progress(state, pairs, timeframes, start, end)
            print("Replay Paper Trading automation")
            print(f"Status: {_campaign_status(state)}")
            print(f"Completed: {state['completed_jobs']}/{state['total_jobs']}")
            print("No pending replay jobs.")
            return

        print("Replay Paper Trading automation")
        print(f"Campaign: {campaign_id}")
        print(f"Workers: {workers}")
        print(f"Claimed Jobs: {len(pending)}")
        print(f"Strategy Asset: {strategy_asset_id}")
        print()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _run_replay_job,
                    job,
                    strategy_asset_id=strategy_asset_id,
                    progress_interval_events=max(1, int(args.progress_interval_events or 1)),
                ): job
                for job in pending
            }
            for future in as_completed(futures):
                job = futures[future]
                try:
                    result = future.result()
                    _mark_complete(state, job["job_id"], result)
                    print(
                        f"COMPLETE {job['job_id']} events={result['processed_events']} "
                        f"signals={result['generated_signals']} orders={result['paper_orders']}"
                    )
                except Exception as exc:
                    _mark_failed(state, job["job_id"], str(exc))
                    print(f"FAILED {job['job_id']} {exc}")
                _save_state_and_progress(state, pairs, timeframes, start, end)

        _save_state_and_progress(state, pairs, timeframes, start, end)
        print()
        print(f"Status: {_campaign_status(state)}")
        print(f"Completed: {state['completed_jobs']}/{state['total_jobs']}")
        print(f"Failed: {state['failed_jobs']}")
        print(f"Events: {state['processed_events']}")
        print(f"Signals: {state['generated_signals']}")
        print(f"Paper Orders: {state['paper_orders']}")
    finally:
        _release_lock()


def _build_jobs(
    campaign_id: str,
    pairs: tuple[str, ...],
    timeframes: tuple[str, ...],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for pair in pairs:
        for timeframe in timeframes:
            for window_start, window_end in _year_windows(start, end):
                job_id = f"{campaign_id}-{pair}-{timeframe}-{window_start:%Y%m%d}-{window_end:%Y%m%d}"
                jobs.append(
                    {
                        "job_id": job_id,
                        "replay_id": f"REPLAY-{pair}-{timeframe}-{window_start:%Y%m%d}-{window_end:%Y%m%d}",
                        "pair": pair,
                        "timeframe": timeframe,
                        "start_time": window_start.isoformat(),
                        "end_time": window_end.isoformat(),
                        "status": ReplayStatus.PENDING.value,
                        "attempts": 0,
                        "processed_events": 0,
                        "generated_signals": 0,
                        "paper_orders": 0,
                        "current_candle_time": "",
                        "last_error": "",
                    }
                )
    return jobs


def _run_replay_job(job: dict[str, Any], *, strategy_asset_id: str, progress_interval_events: int) -> dict[str, Any]:
    pair = str(job["pair"])
    timeframe = str(job["timeframe"])
    session = ReplaySession(
        replay_id=str(job["replay_id"]),
        pairs=(pair,),
        timeframes=(timeframe,),
        start_time=_parse_datetime(str(job["start_time"])),
        end_time=_parse_datetime(str(job["end_time"])),
        mode=infer_replay_mode((pair,), (timeframe,)),
        status=ReplayStatus.RUNNING,
    )
    safe_id = _safe_filename(str(job["job_id"]))
    progress_store = ReplayProgressStore(JOB_DIR / f"{safe_id}.progress.json")
    report_path = JOB_DIR / f"{safe_id}.report.json"
    improvements_path = JOB_DIR / f"{safe_id}.improvements.json"
    trade_journal_path = JOB_DIR / f"{safe_id}.trade-journal.json"

    settings = get_settings()
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        candle_repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        runner = PaperTradingReplayRunner(
            HistoricalCandleReplayStream(candle_repository),
            progress_store,
            report_path=report_path,
            improvement_requests_path=improvements_path,
            trade_journal_path=trade_journal_path,
        )
        result = runner.run(
            session,
            strategy_asset_id=strategy_asset_id,
            replay_speed="MAXIMUM",
            progress_interval_events=progress_interval_events,
        )

    cursor = result.replay_cursor
    return {
        "processed_events": int(cursor.processed_events if cursor else 0),
        "generated_signals": int(result.signals_generated),
        "paper_orders": len(result.paper_orders),
        "current_candle_time": cursor.current_candle_time if cursor else "",
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _load_state(
    campaign_id: str,
    pairs: tuple[str, ...],
    timeframes: tuple[str, ...],
    start: datetime,
    end: datetime,
    workers: int,
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if state.get("campaign_id") == campaign_id:
            for item in state.get("jobs", {}).values():
                if item.get("status") == ReplayStatus.RUNNING.value:
                    item["status"] = ReplayStatus.PENDING.value
            return _refresh_totals(state)

    return _refresh_totals(
        {
            "version": 1,
            "campaign_id": campaign_id,
            "mode": "AUTOMATIC_10_YEAR_REPLAY",
            "started_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "pairs": list(pairs),
            "timeframes": list(timeframes),
            "max_workers": workers,
            "jobs": {job["job_id"]: job for job in jobs},
        }
    )


def _merge_missing_jobs(state: dict[str, Any], jobs: list[dict[str, Any]]) -> None:
    existing = state.setdefault("jobs", {})
    for job in jobs:
        existing.setdefault(job["job_id"], job)
    _refresh_totals(state)


def _claim_pending_jobs(state: dict[str, Any], *, max_jobs: int) -> list[dict[str, Any]]:
    claimed: list[dict[str, Any]] = []
    for job in state.get("jobs", {}).values():
        if job.get("status") == ReplayStatus.COMPLETE.value:
            continue
        if job.get("status") == ReplayStatus.FAILED.value and int(job.get("attempts", 0) or 0) >= 3:
            continue
        claimed.append(job)
        if max_jobs and len(claimed) >= max_jobs:
            break
    for job in claimed:
        job["status"] = ReplayStatus.RUNNING.value
        job["attempts"] = int(job.get("attempts", 0) or 0) + 1
        job["started_at"] = datetime.now(UTC).isoformat()
        job["last_error"] = ""
    _refresh_totals(state)
    return claimed


def _mark_complete(state: dict[str, Any], job_id: str, result: dict[str, Any]) -> None:
    job = state["jobs"][job_id]
    job.update(result)
    job["status"] = ReplayStatus.COMPLETE.value
    job["completed_at"] = datetime.now(UTC).isoformat()
    job["last_error"] = ""
    _refresh_totals(state)


def _mark_failed(state: dict[str, Any], job_id: str, error: str) -> None:
    job = state["jobs"][job_id]
    job["status"] = ReplayStatus.FAILED.value
    job["failed_at"] = datetime.now(UTC).isoformat()
    job["last_error"] = error
    _refresh_totals(state)


def _refresh_totals(state: dict[str, Any]) -> dict[str, Any]:
    jobs = list(state.get("jobs", {}).values())
    completed = [job for job in jobs if job.get("status") == ReplayStatus.COMPLETE.value]
    running = [job for job in jobs if job.get("status") == ReplayStatus.RUNNING.value]
    failed = [job for job in jobs if job.get("status") == ReplayStatus.FAILED.value]
    state["updated_at"] = datetime.now(UTC).isoformat()
    state["total_jobs"] = len(jobs)
    state["completed_jobs"] = len(completed)
    state["running_jobs"] = len(running)
    state["failed_jobs"] = len(failed)
    state["pending_jobs"] = max(0, len(jobs) - len(completed) - len(running) - len(failed))
    state["processed_events"] = sum(int(job.get("processed_events", 0) or 0) for job in completed)
    state["generated_signals"] = sum(int(job.get("generated_signals", 0) or 0) for job in completed)
    state["paper_orders"] = sum(int(job.get("paper_orders", 0) or 0) for job in completed)
    return state


def _save_state_and_progress(
    state: dict[str, Any],
    pairs: tuple[str, ...],
    timeframes: tuple[str, ...],
    start: datetime,
    end: datetime,
) -> None:
    _refresh_totals(state)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    total = max(1, int(state.get("total_jobs", 0) or 0))
    completed = int(state.get("completed_jobs", 0) or 0)
    progress_percent = round((completed / total) * 100.0, 2)
    status = _campaign_status(state)
    current_candle_time = _latest_completed_candle(state)
    cursor = ReplayCursor(
        replay_id=str(state["campaign_id"]),
        pair=",".join(pairs),
        timeframe=",".join(timeframes),
        current_candle_time=current_candle_time,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        processed_events=int(state.get("processed_events", 0) or 0),
        generated_signals=int(state.get("generated_signals", 0) or 0),
        paper_orders=int(state.get("paper_orders", 0) or 0),
        status=status,
        last_error=_latest_error(state),
        replay_mode=infer_replay_mode(pairs, timeframes).value,
        replay_speed="MAXIMUM",
        progress_percent=progress_percent,
        control="AUTOMATIC_10_YEAR_REPLAY",
        updated_at=datetime.now(UTC).isoformat(),
    )
    ReplayProgressStore(DASHBOARD_PROGRESS_FILE).save(cursor)


def _campaign_status(state: dict[str, Any]) -> ReplayStatus:
    if int(state.get("running_jobs", 0) or 0) > 0:
        return ReplayStatus.RUNNING
    if int(state.get("completed_jobs", 0) or 0) >= int(state.get("total_jobs", 0) or 0):
        return ReplayStatus.COMPLETE
    if int(state.get("failed_jobs", 0) or 0) > 0 and int(state.get("pending_jobs", 0) or 0) == 0:
        return ReplayStatus.FAILED
    return ReplayStatus.RUNNING


def _latest_completed_candle(state: dict[str, Any]) -> str:
    completed = [
        str(job.get("current_candle_time", ""))
        for job in state.get("jobs", {}).values()
        if job.get("status") == ReplayStatus.COMPLETE.value and job.get("current_candle_time")
    ]
    return max(completed, default="")


def _latest_error(state: dict[str, Any]) -> str:
    errors = [
        str(job.get("last_error", ""))
        for job in state.get("jobs", {}).values()
        if job.get("last_error")
    ]
    return errors[-1] if errors else ""


def _year_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    current = start
    while current < end:
        next_year = datetime(current.year + 1, 1, 1, tzinfo=UTC)
        window_end = min(next_year, end)
        windows.append((current, window_end))
        current = window_end
    return windows


def _strategy_asset_id(value: str) -> str:
    if value:
        return value
    assets = tuple(asset for asset in default_strategy_asset_repository().list() if asset.deployable)
    if not assets:
        raise SystemExit("No deployable Strategy Asset is available. Run autonomous research first.")
    return assets[0].strategy_asset_id


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip().upper() for item in str(value).split(",") if item.strip())


def _parse_datetime(value: str, *, end_of_date: bool = False) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    if end_of_date and "T" not in str(value):
        return parsed.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return parsed


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _acquire_lock() -> bool:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            locked_at = datetime.fromisoformat(str(payload.get("locked_at", "")).replace("Z", "+00:00"))
            if (datetime.now(UTC) - locked_at.astimezone(UTC)).total_seconds() > 6 * 3600:
                LOCK_FILE.unlink()
        except Exception:
            LOCK_FILE.unlink(missing_ok=True)
    try:
        handle = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        file.write(json.dumps({"pid": os.getpid(), "locked_at": datetime.now(UTC).isoformat()}))
    return True


def _release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
