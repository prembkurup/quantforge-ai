from datetime import datetime, timezone

from scripts.validate_coreui_candles import parse_end, parse_start


def test_coreui_validation_date_only_end_is_inclusive_day() -> None:
    assert parse_start("2025-01-01") == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert parse_end("2025-12-31") == datetime(2026, 1, 1, tzinfo=timezone.utc)
