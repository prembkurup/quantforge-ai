from datetime import datetime, timezone

import pytest

from quantforge.market_data.validation import detect_missing_candle_gaps


def test_detect_missing_candle_gaps_reports_skipped_slots() -> None:
    times = [
        datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 4, tzinfo=timezone.utc),
    ]

    gaps = detect_missing_candle_gaps(times, timeframe_seconds=3600)

    assert len(gaps) == 1
    assert gaps[0].previous_time == times[1]
    assert gaps[0].next_time == times[2]
    assert gaps[0].missing_count == 2


def test_detect_missing_candle_gaps_ignores_duplicates_and_unsorted_input() -> None:
    times = [
        datetime(2025, 1, 1, 2, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
    ]

    assert detect_missing_candle_gaps(times, timeframe_seconds=3600) == []


def test_detect_missing_candle_gaps_rejects_invalid_timeframe() -> None:
    with pytest.raises(ValueError, match="timeframe_seconds"):
        detect_missing_candle_gaps([], timeframe_seconds=0)
