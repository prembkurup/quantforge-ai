import math

import pandas as pd
import pytest

from quantforge.calculations.indicators import (
    atr,
    bollinger_bands,
    cci,
    donchian,
    ema,
    hma,
    ichimoku,
    keltner_channels,
    macd,
    mfi,
    momentum,
    obv,
    roc,
    rsi,
    sma,
    stochastic,
    supertrend,
    true_range,
    vwap,
    wma,
)


def _candles(rows: int = 80) -> pd.DataFrame:
    close = pd.Series([100.0 + (index * 0.5) + ((index % 5) * 0.1) for index in range(rows)])
    return pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=rows, freq="h", tz="UTC"),
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.9,
            "close": close,
            "volume": [1000 + (index * 10) for index in range(rows)],
        }
    )


def test_moving_average_indicators_match_expected_values() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    assert sma(close, 3).iloc[-1] == pytest.approx(4.0)
    assert wma(close, 3).iloc[-1] == pytest.approx((3.0 + 8.0 + 15.0) / 6.0)
    assert ema(close, 3).iloc[-1] == pytest.approx(close.ewm(span=3, adjust=False).mean().iloc[-1])
    assert hma(close, 4).notna().any()


def test_momentum_indicators_return_expected_shapes_and_values() -> None:
    candles = _candles()
    close = candles["close"]

    rsi_values = rsi(close, 14).dropna()
    macd_values = macd(close)
    stochastic_values = stochastic(candles)

    assert rsi_values.between(0, 100).all()
    assert {"macd", "macd_signal", "macd_histogram"} == set(macd_values.columns)
    assert macd_values["macd_histogram"].iloc[-1] == pytest.approx(
        macd_values["macd"].iloc[-1] - macd_values["macd_signal"].iloc[-1]
    )
    assert stochastic_values["stochastic_k"].dropna().between(0, 100).all()
    assert cci(candles, 20).notna().any()
    assert roc(close, 12).iloc[-1] == pytest.approx(close.pct_change(12).iloc[-1] * 100)
    assert momentum(close, 10).iloc[-1] == pytest.approx(close.iloc[-1] - close.iloc[-11])


def test_volatility_and_channel_indicators_are_consistent() -> None:
    candles = _candles()
    close = candles["close"]

    true_ranges = true_range(candles)
    atr_values = atr(candles, 14)
    bands = bollinger_bands(close, 20)
    keltner = keltner_channels(candles, 20, 10)
    donchian_values = donchian(candles, 20)
    supertrend_values = supertrend(candles, 10)

    assert true_ranges.iloc[0] == pytest.approx(candles["high"].iloc[0] - candles["low"].iloc[0])
    assert atr_values.dropna().gt(0).all()
    assert bands["bb_upper"].iloc[-1] > bands["bb_middle"].iloc[-1] > bands["bb_lower"].iloc[-1]
    assert (
        keltner["keltner_upper"].iloc[-1]
        > keltner["keltner_middle"].iloc[-1]
        > keltner["keltner_lower"].iloc[-1]
    )
    assert donchian_values["donchian_upper"].iloc[-1] == candles["high"].tail(20).max()
    assert set(supertrend_values["supertrend_direction"].dropna().unique()).issubset(
        {"flat", "bullish", "bearish"}
    )


def test_ichimoku_and_volume_indicators_return_registered_outputs() -> None:
    candles = _candles()
    ichimoku_values = ichimoku(candles)

    assert {
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_senkou_a",
        "ichimoku_senkou_b",
        "ichimoku_chikou",
    } == set(ichimoku_values.columns)
    assert obv(candles).iloc[-1] > 0
    assert vwap(candles).iloc[-1] == pytest.approx(
        (
            ((candles["high"] + candles["low"] + candles["close"]) / 3)
            * candles["volume"]
        ).cumsum().iloc[-1]
        / candles["volume"].cumsum().iloc[-1]
    )
    assert mfi(candles, 14).dropna().between(0, 100).all()


def test_vwap_handles_zero_cumulative_volume_as_nan_or_infinite() -> None:
    candles = _candles(3)
    candles["volume"] = 0

    result = vwap(candles)

    assert result.isna().all() or math.isinf(result.iloc[-1])
