from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from quantforge.admin.settings import admin_setting_value
from quantforge.research.full_history_scheduler import (
    FULL_HISTORY_RESEARCH_PAIRS,
    FULL_HISTORY_RESEARCH_START,
    FULL_HISTORY_RESEARCH_TIMEFRAMES,
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
)
from quantforge.research.orchestrator import (
    AlwaysOnAutonomousResearchOrchestrator,
    AlwaysOnResearchThresholds,
    default_always_on_orchestrator_paths,
)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    admin_file = repo_root / "var" / "admin_settings.json"
    parser = argparse.ArgumentParser(description="Run the always-on autonomous research orchestrator.")
    parser.add_argument("--once", action="store_true", help="Run one orchestration pass and exit.")
    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=_env_int("RESEARCH_ORCHESTRATOR_INTERVAL_SECONDS", int(admin_setting_value(admin_file, "research_orchestrator.sleep_seconds", 900))),
    )
    parser.add_argument("--max-jobs-per-pass", type=int, default=_env_int("RESEARCH_ORCHESTRATOR_MAX_JOBS_PER_CYCLE", 12))
    parser.add_argument("--max-in-flight", type=int, default=_env_int("RESEARCH_ORCHESTRATOR_MAX_IN_FLIGHT", 24))
    parser.add_argument("--stale-after-hours", type=int, default=_env_int("RESEARCH_ORCHESTRATOR_STALE_AFTER_HOURS", 6))
    parser.add_argument("--min-assets-per-program", type=int, default=_env_int("RESEARCH_ORCHESTRATOR_MIN_ASSETS_PER_PROGRAM", 1))
    parser.add_argument("--state-file", default="var/full_history_research_state.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    state_file = repo_root / args.state_file
    scheduler = FullHistoryResearchScheduler(
        config=_full_history_config(),
        state_file=state_file,
        repository_factory=lambda: None,
    )
    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=scheduler.plan(),
        full_history_state_file=state_file,
        paths=default_always_on_orchestrator_paths(repo_root),
        thresholds=AlwaysOnResearchThresholds(
            schedule_seconds=args.sleep_seconds,
            max_jobs_per_pass=args.max_jobs_per_pass,
            max_jobs_in_flight=args.max_in_flight,
            stale_after_hours=args.stale_after_hours,
            min_assets_per_program=args.min_assets_per_program,
        ),
    )
    if args.once:
        record = orchestrator.run_once(trigger="manual")
        print(f"{record.run_id} {record.state.value} jobs={record.jobs_launched}")
        if record.idle_reason_code:
            print(f"idle_reason={record.idle_reason_code}")
        return
    print("Always-On Autonomous Research Orchestrator")
    print(f"Started At: {datetime.now(UTC).isoformat(timespec='seconds')}")
    print(f"Sleep Seconds: {args.sleep_seconds}")
    print(f"State File: {args.state_file}")
    orchestrator.run_forever()


def _full_history_config() -> FullHistorySchedulerConfig:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return FullHistorySchedulerConfig(
        pairs=FULL_HISTORY_RESEARCH_PAIRS,
        timeframes=FULL_HISTORY_RESEARCH_TIMEFRAMES,
        start=FULL_HISTORY_RESEARCH_START,
        end=today_start + timedelta(days=1),
        smoke_window_candles_by_timeframe={"M5": 300, "M15": 300, "H1": 300, "H4": 120},
    )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


if __name__ == "__main__":
    main()
