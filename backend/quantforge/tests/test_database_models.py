from quantforge.database.models import candle, instrument, timeframe


def test_first_market_tables_are_schema_qualified() -> None:
    assert instrument.schema == "instrument"
    assert timeframe.schema == "instrument"
    assert candle.schema == "market"


def test_candle_has_expected_ohlcv_columns() -> None:
    expected = {
        "instrument_id",
        "timeframe_id",
        "candle_time",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "is_complete",
        "source",
    }
    assert expected.issubset(set(candle.c.keys()))


def test_candle_has_duplicate_prevention_constraint() -> None:
    constraints = {constraint.name for constraint in candle.constraints}

    assert "uq_candle_instrument_timeframe_time" in constraints


def test_candle_has_lookup_index() -> None:
    indexes = {index.name for index in candle.indexes}

    assert "idx_candle_instrument_timeframe_time" in indexes
