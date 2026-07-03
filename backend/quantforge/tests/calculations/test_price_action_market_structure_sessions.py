import pandas as pd
import pytest

from quantforge.calculations.market_structure import structure_points
from quantforge.calculations.price_action import candle_parts, candle_patterns
from quantforge.calculations.sessions import session_flags


def test_price_action_parts_and_patterns_detect_edge_cases() -> None:
    candles = pd.DataFrame(
        {
            "open": [10.0, 10.5, 10.8, 10.0, 11.0],
            "high": [11.0, 10.8, 11.5, 10.9, 11.2],
            "low": [9.5, 10.0, 8.0, 9.8, 9.7],
            "close": [10.4, 10.2, 10.1, 10.9, 9.8],
        }
    )

    parts = candle_parts(candles)
    patterns = candle_patterns(candles)

    assert parts["body_size"].iloc[0] == pytest.approx(0.4)
    assert parts["upper_wick"].iloc[0] == pytest.approx(0.6)
    assert parts["lower_wick"].iloc[0] == pytest.approx(0.5)
    assert parts["bullish_candle"].iloc[0]
    assert parts["bearish_candle"].iloc[-1]
    assert patterns["inside_bar"].iloc[1]
    assert patterns["outside_bar"].iloc[2]
    assert patterns["pin_bar"].iloc[2]
    assert patterns["engulfing"].iloc[3]
    assert patterns["engulfing"].iloc[4]


def test_market_structure_reports_swings_breaks_and_distances() -> None:
    candles = pd.DataFrame(
        {
            "high": [10, 11, 13, 11, 10, 12, 15, 12, 11, 9, 8, 10, 16],
            "low": [8, 9, 10, 8, 7, 9, 11, 9, 6, 5, 4, 6, 12],
            "close": [9, 10, 12, 9, 8, 11, 14, 10, 7, 6, 5, 9, 16],
        }
    )

    structure = structure_points(candles, swing_window=1)

    assert structure["swing_high"].any()
    assert structure["swing_low"].any()
    assert structure["bos"].iloc[-1]
    assert structure["choch"].any()
    assert structure["support_distance"].notna().any()
    assert structure["resistance_distance"].notna().any()
    assert set(structure["trend_direction"].unique()).issubset({"flat", "bullish", "bearish"})


def test_session_flags_cover_sessions_overlap_weekend_and_boundaries() -> None:
    candles = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2025-01-03T00:00:00Z",
                    "2025-01-03T07:00:00Z",
                    "2025-01-03T13:00:00Z",
                    "2025-01-04T21:00:00Z",
                ],
                utc=True,
            )
        }
    )

    sessions = session_flags(candles)

    assert sessions["asian_session"].iloc[0]
    assert sessions["london_session"].iloc[1]
    assert sessions["new_york_session"].iloc[2]
    assert sessions["session_overlap"].iloc[2]
    assert sessions["weekend"].iloc[3]
    assert sessions["session_open"].iloc[0]
    assert sessions["session_close"].iloc[3]
    assert sessions["session"].iloc[2] == "London/New York"
