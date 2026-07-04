from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone

from quantforge.config.settings import get_settings
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.research import DatabaseResearchScope, Workstream1PipelineRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Schedule and run Workstream 1 against the real CoreUI/OANDA candle database."
    )
    parser.add_argument("--pairs", default="EUR_USD", help="Comma-separated pairs, for example EUR_USD,GBP_USD.")
    parser.add_argument("--timeframes", default="H1", help="Comma-separated timeframes, for example M15,H1,H4.")
    parser.add_argument("--from", dest="start", required=True, help="UTC start date/time.")
    parser.add_argument("--to", dest="end", required=True, help="UTC end date/time; date-only is inclusive.")
    parser.add_argument("--window-candles", type=int, default=300)
    parser.add_argument("--stride-candles", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=25)
    parser.add_argument("--max-assets-to-validate", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    scope = DatabaseResearchScope(
        pairs=tuple(item.strip().upper() for item in args.pairs.split(",") if item.strip()),
        timeframes=tuple(item.strip().upper() for item in args.timeframes.split(",") if item.strip()),
        start=parse_datetime(args.start, end_of_date=False),
        end=parse_datetime(args.end, end_of_date=True),
        window_candles=args.window_candles,
        stride_candles=args.stride_candles,
        max_batches=args.max_batches,
        max_assets_to_validate=args.max_assets_to_validate,
    )
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        result = Workstream1PipelineRunner(repository).run(scope)

    print("Workstream 1 Database Pipeline")
    print()
    print(f"Schedule: {result.schedule.schedule_id}")
    print(f"Source: {result.database_result.report.source}")
    print(f"Pairs: {', '.join(result.schedule.scope.pairs)}")
    print(f"Timeframes: {', '.join(result.schedule.scope.timeframes)}")
    print(f"From: {result.schedule.scope.start.isoformat()}")
    print(f"To: {result.schedule.scope.end.isoformat()}")
    print(f"Scheduled Tasks: {len(result.schedule.tasks)}")
    print(f"Completed Tasks: {len(result.completed_tasks)}")
    print(f"Failed Tasks: {len(result.failed_tasks)}")
    print(f"Stored Candles: {result.report.stored_candles:,}")
    print(f"Duplicate Candles: {result.report.duplicate_candles:,}")
    print(f"Missing Candles: {result.report.missing_candles:,}")
    print(f"Real Experiment Batches: {result.report.real_experiment_batches:,}")
    print(f"Database-Backed Candidate Assets: {result.report.database_backed_candidate_assets:,}")
    print(f"Optimized Candidates: {result.report.optimized_candidates:,}")
    print(f"Backtested Candidates: {result.report.backtested_candidates:,}")
    print(f"Validated Strategy Assets: {result.report.validated_strategy_assets:,}")
    print(f"Reproducibility Key: {result.database_result.reproducibility_key}")
    print(f"Successful: {'YES' if result.successful else 'NO'}")
    print()
    print("Task Report")
    for task in result.schedule.tasks:
        print(f"- {task.task_id} {task.task_type}: {task.status} - {task.evidence}")


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
    main()
