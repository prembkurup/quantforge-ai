from datetime import datetime, timezone
from decimal import Decimal

from quantforge.market_data.coreui_repository import _normalize_datetime_for_coreui, _normalize_row


def test_coreui_datetime_normalization_matches_coreui_queries() -> None:
    value = datetime(2026, 7, 4, 1, 0, tzinfo=timezone.utc)

    normalized = _normalize_datetime_for_coreui(value)

    assert normalized.tzinfo == timezone.utc
    assert normalized == value


def test_coreui_row_is_normalized_to_quantforge_candle_shape() -> None:
    row = {
        "time": datetime(2026, 7, 4, 1, 0),
        "pair_name": "EUR_USD",
        "granularity": "M5",
        "volume": 123,
        "mid_o": 1.1,
        "mid_h": 1.2,
        "mid_l": 1.0,
        "mid_c": 1.15,
        "complete": True,
    }

    normalized = _normalize_row(row)

    assert normalized["pair_name"] == "EUR_USD"
    assert normalized["granularity"] == "M5"
    assert normalized["time"] == datetime(2026, 7, 4, 1, 0, tzinfo=timezone.utc)
    assert normalized["open_price"] == Decimal("1.1")
    assert normalized["high_price"] == Decimal("1.2")
    assert normalized["low_price"] == Decimal("1.0")
    assert normalized["close_price"] == Decimal("1.15")
    assert normalized["source"] == "coreui.oanda_candles"
