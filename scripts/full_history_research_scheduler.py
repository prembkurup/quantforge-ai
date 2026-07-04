from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from quantforge.config.settings import get_settings
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.research.full_history_scheduler import (
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run resumable staged research over the full CoreUI/OANDA candle history."
    )
    parser.add_argument("--pairs", default="EUR_USD,GBP_USD,USD_JPY")
    parser.add_argument("--timeframes", default="M15,H1,H4")
    parser.add_argument("--from", dest="start", default="2016-01-04")
    parser.add_argument("--to", dest="end", default=date.today().isoformat())
    parser.add_argument("--state-file", default="var/full_history_research_state.json")
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--window-candles", type=int, default=300)
    parser.add_argument("--stride-candles", type=int, default=100)
    parser.add_argument("--smoke-days", type=int, default=31)
    parser.add_argument("--smoke-max-batches", type=int, default=2)
    parser.add_argument("--rolling-max-batches", type=int, default=25)
    parser.add_argument("--full-history-max-batches", type=int, default=100)
    parser.add_argument("--max-assets-to-validate", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    config = FullHistorySchedulerConfig(
        pairs=tuple(item.strip().upper() for item in args.pairs.split(",") if item.strip()),
        timeframes=tuple(item.strip().upper() for item in args.timeframes.split(",") if item.strip()),
        start=parse_datetime(args.start, end_of_date=False),
        end=parse_datetime(args.end, end_of_date=True),
        window_candles=args.window_candles,
        stride_candles=args.stride_candles,
        smoke_days=args.smoke_days,
        smoke_max_batches=args.smoke_max_batches,
        rolling_max_batches=args.rolling_max_batches,
        full_history_max_batches=args.full_history_max_batches,
        max_assets_to_validate=args.max_assets_to_validate,
    )
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        scheduler = FullHistoryResearchScheduler(
            config=config,
            state_file=Path(args.state_file),
            repository_factory=lambda: repository,
        )
        result = scheduler.run_pending(max_jobs=args.max_jobs, dry_run=args.dry_run)

    print("Full History Research Scheduler")
    print()
    print(f"Pairs: {', '.join(config.pairs)}")
    print(f"Timeframes: {', '.join(config.timeframes)}")
    print(f"From: {config.start.isoformat()}")
    print(f"To: {config.end.isoformat()}")
    print(f"State File: {result.state_file}")
    print(f"Planned Jobs: {result.planned_jobs}")
    print(f"Completed Jobs: {result.completed_jobs}")
    print(f"Failed Jobs: {result.failed_jobs}")
    print(f"Skipped Pending Jobs: {result.skipped_jobs}")
    print(f"Executed This Run: {len(result.executed_jobs)}")
    print(f"Dry Run: {'YES' if args.dry_run else 'NO'}")
    print()
    print("Executed Jobs")
    for job in result.executed_jobs:
        print(
            f"- {job.stage.value} {job.pair} {job.timeframe} "
            f"{job.start.date()}->{job.end.date()} {job.status.value}: {job.evidence}"
        )


def parse_datetime(value: str, *, end_of_date: bool) -> datetime:
    if "T" not in value and len(value) == 10:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
        if end_of_date:
            parsed += timedelta(days=1)
        return parsed

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
