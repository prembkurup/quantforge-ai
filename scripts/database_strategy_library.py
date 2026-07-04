from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone

from quantforge.config.settings import get_settings
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.research import DatabaseBackedStrategyLibraryRunner, DatabaseResearchScope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Workstream 1 experiment batches from the real CoreUI/OANDA candle database."
    )
    parser.add_argument("--pairs", default="EUR_USD", help="Comma-separated pairs, for example EUR_USD,GBP_USD.")
    parser.add_argument("--timeframes", default="H1", help="Comma-separated timeframes, for example M15,H1,H4.")
    parser.add_argument("--from", dest="start", required=True, help="UTC start date/time.")
    parser.add_argument("--to", dest="end", required=True, help="UTC end date/time; date-only is inclusive.")
    parser.add_argument("--window-candles", type=int, default=300)
    parser.add_argument("--stride-candles", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=25)
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
    )
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        result = DatabaseBackedStrategyLibraryRunner(repository).run(scope)

    print("Database-Backed Workstream 1")
    print()
    print(f"Source: {result.report.source}")
    print(f"Pairs: {', '.join(result.scope.pairs)}")
    print(f"Timeframes: {', '.join(result.scope.timeframes)}")
    print(f"From: {result.scope.start.isoformat()}")
    print(f"To: {result.scope.end.isoformat()}")
    print(f"Coverage Slices: {len(result.coverage)}")
    print(f"Stored Candles: {sum(item.stored_candles for item in result.coverage):,}")
    print(f"Duplicate Candles: {sum(item.duplicate_candles for item in result.coverage):,}")
    print(f"Missing Candles: {sum(item.missing_candle_count for item in result.coverage):,}")
    print(f"Real Experiment Batches: {len(result.experiment_batches):,}")
    print(f"Database-Backed Candidate Assets: {len(result.candidate_assets):,}")
    print(f"Reproducibility Key: {result.reproducibility_key}")
    print(f"Successful: {'YES' if result.successful else 'NO'}")


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
