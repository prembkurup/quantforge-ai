import numpy as np
import pandas as pd
import pytest

from quantforge.calculations.statistics import (
    kurtosis,
    log_returns,
    percentile,
    rolling_mean,
    rolling_median,
    rolling_std,
    simple_returns,
    skewness,
    variance,
    zscore,
)


def test_rolling_statistics_match_pandas_reference() -> None:
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    assert rolling_mean(values, 3).iloc[-1] == pytest.approx(4.0)
    assert rolling_median(values, 3).iloc[-1] == pytest.approx(4.0)
    assert rolling_std(values, 3).iloc[-1] == pytest.approx(values.tail(3).std())
    assert variance(values, 3).iloc[-1] == pytest.approx(values.tail(3).var())
    assert percentile(values, 3, 0.5).iloc[-1] == pytest.approx(4.0)


def test_distribution_statistics_and_returns_are_consistent() -> None:
    values = pd.Series([10.0, 11.0, 13.0, 12.0, 15.0, 18.0])

    assert zscore(values, 3).iloc[-1] == pytest.approx(
        (values.iloc[-1] - values.tail(3).mean()) / values.tail(3).std()
    )
    assert skewness(values, 4).iloc[-1] == pytest.approx(values.tail(4).skew())
    assert kurtosis(values, 4).iloc[-1] == pytest.approx(values.tail(4).kurt())
    assert simple_returns(values).iloc[-1] == pytest.approx(0.2)
    assert log_returns(values).iloc[-1] == pytest.approx(np.log(18.0 / 15.0))


def test_zscore_zero_volatility_returns_missing_values() -> None:
    values = pd.Series([5.0, 5.0, 5.0, 5.0])

    assert zscore(values, 3).dropna().empty
