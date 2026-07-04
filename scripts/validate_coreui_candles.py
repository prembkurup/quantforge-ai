import argparse
from datetime import date, datetime, time, timedelta, timezone

from quantforge.config.settings import get_settings
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.market_data.repository import _timeframe_seconds
from quantforge.market_data.validation import detect_missing_candle_gaps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate CoreUI's read-only candle table for QuantForge market data."
    )
    parser.add_argument("--pair", default="EUR_USD", help="Instrument, for example EUR_USD.")
    parser.add_argument("--timeframe", default="H1", help="Granularity, for example H1.")
    parser.add_argument("--from", dest="start", required=True, help="UTC start date/time.")
    parser.add_argument("--to", dest="end", required=True, help="UTC end date/time; date-only is inclusive.")
    parser.add_argument("--limit", type=int, default=100_000, help="Maximum candle rows to load for gap checks.")
    return parser.parse_args()


def parse_start(value: str) -> datetime:
    return _parse_datetime(value, end_of_date=False)


def parse_end(value: str) -> datetime:
    return _parse_datetime(value, end_of_date=True)


def main() -> None:
    args = parse_args()
    settings = get_settings()

    pair_name = args.pair.upper()
    granularity = args.timeframe.upper()
    start = parse_start(args.start)
    end = parse_end(args.end)
    timeframe_seconds = _timeframe_seconds(granularity)
    if timeframe_seconds <= 0:
        raise ValueError(f"Unsupported timeframe: {granularity}")
    if start >= end:
        raise ValueError("--from must be earlier than --to.")

    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        stored = repository.count_window(pair_name, granularity, start, end)
        duplicates = repository.duplicate_count(pair_name, granularity, start, end)
        rows = repository.load_window(pair_name, granularity, start, end, limit=args.limit)
        latest = repository.latest_candle_time(pair_name, granularity)

    gaps = detect_missing_candle_gaps([row["time"] for row in rows], timeframe_seconds)
    missing_total = sum(gap.missing_count for gap in gaps)

    print("source=coreui")
    print(f"table={settings.coreui_candle_table}")
    print(f"pair={pair_name}")
    print(f"timeframe={granularity}")
    print(f"from={start.isoformat()}")
    print(f"to={end.isoformat()}")
    print(f"stored={stored}")
    print(f"loaded_for_gap_check={len(rows)}")
    print(f"duplicates={duplicates}")
    print(f"missing_gap_count={len(gaps)}")
    print(f"missing_candle_count={missing_total}")
    print(f"latest_complete={latest}")
    if stored > len(rows):
        print(f"gap_check_truncated=true limit={args.limit}")
    for gap in gaps[:10]:
        print(
            "missing_gap="
            f"{gap.previous_time.isoformat()}..{gap.next_time.isoformat()} "
            f"missing={gap.missing_count}"
        )
    if len(gaps) > 10:
        print(f"missing_gap_more={len(gaps) - 10}")


def _parse_datetime(value: str, *, end_of_date: bool) -> datetime:
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
