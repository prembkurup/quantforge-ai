import pandas as pd


def rolling_mean(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).mean()


def rolling_std(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).std()


def zscore(values: pd.Series, window: int) -> pd.Series:
    mean = rolling_mean(values, window)
    standard_deviation = rolling_std(values, window)
    return (values - mean) / standard_deviation.replace(0, pd.NA)
