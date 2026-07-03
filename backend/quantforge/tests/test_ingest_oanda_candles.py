from datetime import datetime, timezone

from scripts.ingest_oanda_candles import chunk_ranges, parse_end, parse_start


def test_parse_end_treats_date_only_as_inclusive_day() -> None:
    assert parse_start("2025-01-01") == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert parse_end("2025-12-31") == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_chunk_ranges_splits_large_oanda_requests() -> None:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 12, 31, tzinfo=timezone.utc)

    chunks = list(chunk_ranges(start, end, timeframe_seconds=3600))

    assert len(chunks) == 2
    assert chunks[0][0] == start
    assert chunks[-1][1] == end
    assert chunks[0][1] == datetime(2025, 7, 7, 12, tzinfo=timezone.utc)
