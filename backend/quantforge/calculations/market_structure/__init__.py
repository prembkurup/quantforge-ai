import pandas as pd


def structure_points(candles: pd.DataFrame, swing_window: int = 2) -> pd.DataFrame:
    high = candles["high"]
    low = candles["low"]
    swing_high = high == high.rolling((swing_window * 2) + 1, center=True).max()
    swing_low = low == low.rolling((swing_window * 2) + 1, center=True).min()
    previous_swing_high = high.where(swing_high).ffill().shift(1)
    previous_swing_low = low.where(swing_low).ffill().shift(1)

    higher_high = swing_high & (high > previous_swing_high)
    lower_high = swing_high & (high < previous_swing_high)
    higher_low = swing_low & (low > previous_swing_low)
    lower_low = swing_low & (low < previous_swing_low)

    bos = (candles["close"] > previous_swing_high) | (candles["close"] < previous_swing_low)
    trend_direction = pd.Series("flat", index=candles.index, dtype="object")
    trend_direction.loc[higher_high | higher_low] = "bullish"
    trend_direction.loc[lower_high | lower_low] = "bearish"
    trend_direction = trend_direction.replace("flat", pd.NA).ffill().fillna("flat")
    choch = trend_direction != trend_direction.shift(1)

    return pd.DataFrame(
        {
            "higher_high": higher_high.fillna(False),
            "higher_low": higher_low.fillna(False),
            "lower_high": lower_high.fillna(False),
            "lower_low": lower_low.fillna(False),
            "swing_high": swing_high.fillna(False),
            "swing_low": swing_low.fillna(False),
            "bos": bos.fillna(False),
            "choch": choch.fillna(False),
            "support_distance": candles["close"] - previous_swing_low,
            "resistance_distance": previous_swing_high - candles["close"],
            "trend_direction": trend_direction,
        }
    )
