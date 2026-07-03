import pandas as pd

from quantforge.indicators import atr, ema, rsi


def test_dynamic_indicators_return_series() -> None:
    candles = pd.DataFrame(
        {
            "high": [2.0, 3.0, 4.0, 5.0, 6.0],
            "low": [1.0, 1.5, 2.0, 3.0, 4.0],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5],
        }
    )

    assert len(ema(candles["close"], 3)) == len(candles)
    assert len(rsi(candles["close"], 3)) == len(candles)
    assert len(atr(candles, 3)) == len(candles)
