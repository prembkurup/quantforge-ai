import pandas as pd


def candle_parts(candles: pd.DataFrame) -> pd.DataFrame:
    body_size = (candles["close"] - candles["open"]).abs()
    candle_range = candles["high"] - candles["low"]
    upper_wick = candles["high"] - candles[["open", "close"]].max(axis=1)
    lower_wick = candles[["open", "close"]].min(axis=1) - candles["low"]
    return pd.DataFrame(
        {
            "body_size": body_size,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "range": candle_range,
            "body_percent": body_size / candle_range.replace(0, pd.NA),
            "gap": candles["open"] - candles["close"].shift(1),
            "bullish_candle": candles["close"] > candles["open"],
            "bearish_candle": candles["close"] < candles["open"],
        }
    )


def candle_patterns(candles: pd.DataFrame) -> pd.DataFrame:
    parts = candle_parts(candles)
    previous_high = candles["high"].shift(1)
    previous_low = candles["low"].shift(1)
    previous_open = candles["open"].shift(1)
    previous_close = candles["close"].shift(1)

    inside_bar = (candles["high"] < previous_high) & (candles["low"] > previous_low)
    outside_bar = (candles["high"] > previous_high) & (candles["low"] < previous_low)
    pin_bar = (
        (parts["upper_wick"] > parts["body_size"] * 2)
        | (parts["lower_wick"] > parts["body_size"] * 2)
    ) & (parts["body_percent"] < 0.35)
    bullish_engulfing = (
        (candles["close"] > candles["open"])
        & (previous_close < previous_open)
        & (candles["close"] >= previous_open)
        & (candles["open"] <= previous_close)
    )
    bearish_engulfing = (
        (candles["close"] < candles["open"])
        & (previous_close > previous_open)
        & (candles["open"] >= previous_close)
        & (candles["close"] <= previous_open)
    )
    return pd.DataFrame(
        {
            "inside_bar": inside_bar,
            "outside_bar": outside_bar,
            "pin_bar": pin_bar,
            "engulfing": bullish_engulfing | bearish_engulfing,
        }
    )
