import argparse
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone

from quantforge.config.settings import get_settings
from quantforge.database.session import get_engine
from quantforge.market_data.oanda import OandaCandleClient
from quantforge.market_data.repository import PostgresCandleRepository, _timeframe_seconds
from quantforge.market_data.validation import detect_missing_candle_gaps

MAX_CANDLES_PER_REQUEST = 4500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest OANDA candles into QuantForge PostgreSQL.")
    parser.add_argument("--pair", default="EUR_USD", help="OANDA instrument, for example EUR_USD.")
    parser.add_argument("--timeframe", default="H1", help="OANDA granularity, for example H1.")
    parser.add_argument("--from", dest="start", required=True, help="UTC start date/time.")
    parser.add_argument("--to", dest="end", required=True, help="UTC end date/time; date-only is inclusive.")
    return parser.parse_args()


def parse_start(value: str) -> datetime:
    return _parse_datetime(value, end_of_date=False)


def parse_end(value: str) -> datetime:
    return _parse_datetime(value, end_of_date=True)


def chunk_ranges(start: datetime, end: datetime, timeframe_seconds: int) -> Iterable[tuple[datetime, datetime]]:
    if timeframe_seconds <= 0:
        raise ValueError("Unsupported timeframe; cannot calculate request chunks.")
    step = timedelta(seconds=timeframe_seconds * MAX_CANDLES_PER_REQUEST)
    current = start
    while current < end:
        next_end = min(current + step, end)
        yield current, next_end
        current = next_end


def main() -> None:
    args = parse_args()
    settings = get_settings()
    if not settings.oanda_api_token:
        raise RuntimeError("QUANTFORGE_OANDA_API_TOKEN is not configured in the local .env file.")
    client = OandaCandleClient(settings.oanda_api_url, settings.oanda_api_token)

    instrument = args.pair.upper()
    granularity = args.timeframe.upper()
    start = parse_start(args.start)
    end = parse_end(args.end)
    timeframe_seconds = _timeframe_seconds(granularity)
    if start >= end:
        raise ValueError("--from must be earlier than --to.")
    if timeframe_seconds <= 0:
        raise ValueError(f"Unsupported timeframe: {granularity}")

    fetched = []
    for chunk_start, chunk_end in chunk_ranges(start, end, timeframe_seconds):
        fetched.extend(client.fetch_candles(instrument, granularity, chunk_start, chunk_end))

    engine = get_engine()
    with engine.begin() as connection:
        repository = PostgresCandleRepository(connection)
        saved = repository.upsert_candles(fetched)
        stored = repository.count_window(instrument, granularity, start, end)
        duplicates = repository.duplicate_count(instrument, granularity, start, end)
        stored_rows = repository.load_window(instrument, granularity, start, end)

    gaps = detect_missing_candle_gaps(
        [row["candle_time"] for row in stored_rows],
        timeframe_seconds,
    )
    missing_total = sum(gap.missing_count for gap in gaps)

    print(f"instrument={instrument}")
    print(f"timeframe={granularity}")
    print(f"from={start.isoformat()}")
    print(f"to={end.isoformat()}")
    print(f"fetched={len(fetched)}")
    print(f"saved_or_updated={saved}")
    print(f"stored={stored}")
    print(f"duplicates={duplicates}")
    print(f"missing_gap_count={len(gaps)}")
    print(f"missing_candle_count={missing_total}")
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
        parsed_time = time.min
        parsed = datetime.combine(parsed_date, parsed_time, tzinfo=timezone.utc)
        if end_of_date:
            parsed += timedelta(days=1)
        return parsed

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    main()
