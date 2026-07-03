import numpy as np
import pandas as pd


def rolling_mean(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).mean()


def rolling_median(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).median()


def rolling_std(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).std()


def zscore(values: pd.Series, window: int) -> pd.Series:
    mean = rolling_mean(values, window)
    standard_deviation = rolling_std(values, window)
    return (values - mean) / standard_deviation.replace(0, pd.NA)


def variance(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).var()


def percentile(values: pd.Series, window: int, percentile_value: float = 0.5) -> pd.Series:
    return values.rolling(window=window, min_periods=window).quantile(percentile_value)


def skewness(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).skew()


def kurtosis(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).kurt()


def simple_returns(values: pd.Series) -> pd.Series:
    return values.pct_change()


def log_returns(values: pd.Series) -> pd.Series:
    return np.log(values / values.shift(1))
