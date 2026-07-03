import pandas as pd


def true_range(candles: pd.DataFrame) -> pd.Series:
    high = candles["high"]
    low = candles["low"]
    close = candles["close"]
    previous_close = close.shift(1)
    return pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def close_to_close_volatility(close: pd.Series, window: int) -> pd.Series:
    returns = close.pct_change()
    return returns.rolling(window=window, min_periods=window).std()
