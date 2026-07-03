import numpy as np
import pandas as pd


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period, min_periods=period).mean()


def wma(close: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1)
    return close.rolling(window=period, min_periods=period).apply(
        lambda values: float(np.dot(values, weights) / weights.sum()),
        raw=True,
    )


def hma(close: pd.Series, period: int) -> pd.Series:
    half_period = max(1, period // 2)
    sqrt_period = max(1, int(np.sqrt(period)))
    return wma((2 * wma(close, half_period)) - wma(close, period), sqrt_period)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    macd_line = ema(close, fast_period) - ema(close, slow_period)
    signal = ema(macd_line, signal_period)
    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal,
            "macd_histogram": macd_line - signal,
        }
    )


def stochastic(candles: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    lowest_low = candles["low"].rolling(k_period, min_periods=k_period).min()
    highest_high = candles["high"].rolling(k_period, min_periods=k_period).max()
    percent_k = 100 * ((candles["close"] - lowest_low) / (highest_high - lowest_low))
    percent_d = percent_k.rolling(d_period, min_periods=d_period).mean()
    return pd.DataFrame({"stochastic_k": percent_k, "stochastic_d": percent_d})


def cci(candles: pd.DataFrame, period: int = 20) -> pd.Series:
    typical_price = (candles["high"] + candles["low"] + candles["close"]) / 3
    average = typical_price.rolling(period, min_periods=period).mean()
    mean_deviation = (typical_price - average).abs().rolling(period, min_periods=period).mean()
    return (typical_price - average) / (0.015 * mean_deviation)


def roc(close: pd.Series, period: int = 12) -> pd.Series:
    return close.pct_change(periods=period) * 100


def momentum(close: pd.Series, period: int = 10) -> pd.Series:
    return close - close.shift(period)


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


def atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(candles).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def bollinger_bands(close: pd.Series, period: int = 20, deviations: float = 2.0) -> pd.DataFrame:
    middle = sma(close, period)
    std = close.rolling(period, min_periods=period).std()
    return pd.DataFrame(
        {
            "bb_lower": middle - (deviations * std),
            "bb_middle": middle,
            "bb_upper": middle + (deviations * std),
        }
    )


def keltner_channels(
    candles: pd.DataFrame,
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
) -> pd.DataFrame:
    middle = ema(candles["close"], ema_period)
    average_true_range = atr(candles, atr_period)
    return pd.DataFrame(
        {
            "keltner_lower": middle - (multiplier * average_true_range),
            "keltner_middle": middle,
            "keltner_upper": middle + (multiplier * average_true_range),
        }
    )


def donchian(candles: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    upper = candles["high"].rolling(period, min_periods=period).max()
    lower = candles["low"].rolling(period, min_periods=period).min()
    return pd.DataFrame({"donchian_lower": lower, "donchian_middle": (upper + lower) / 2, "donchian_upper": upper})


def ichimoku(candles: pd.DataFrame) -> pd.DataFrame:
    high = candles["high"]
    low = candles["low"]
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    chikou = candles["close"].shift(-26)
    return pd.DataFrame(
        {
            "ichimoku_tenkan": tenkan,
            "ichimoku_kijun": kijun,
            "ichimoku_senkou_a": senkou_a,
            "ichimoku_senkou_b": senkou_b,
            "ichimoku_chikou": chikou,
        }
    )


def supertrend(candles: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    average_true_range = atr(candles, period)
    hl2 = (candles["high"] + candles["low"]) / 2
    upper_band = hl2 + (multiplier * average_true_range)
    lower_band = hl2 - (multiplier * average_true_range)
    direction = pd.Series("flat", index=candles.index, dtype="object")
    direction.loc[candles["close"] > upper_band.shift(1)] = "bullish"
    direction.loc[candles["close"] < lower_band.shift(1)] = "bearish"
    direction = direction.replace("flat", pd.NA).ffill().fillna("flat")
    return pd.DataFrame({"supertrend_upper": upper_band, "supertrend_lower": lower_band, "supertrend_direction": direction})


def obv(candles: pd.DataFrame) -> pd.Series:
    direction = np.sign(candles["close"].diff()).fillna(0)
    return (direction * candles["volume"]).cumsum()


def vwap(candles: pd.DataFrame) -> pd.Series:
    typical_price = (candles["high"] + candles["low"] + candles["close"]) / 3
    cumulative_volume = candles["volume"].cumsum()
    return (typical_price * candles["volume"]).cumsum() / cumulative_volume


def mfi(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    typical_price = (candles["high"] + candles["low"] + candles["close"]) / 3
    money_flow = typical_price * candles["volume"]
    direction = typical_price.diff()
    positive_flow = money_flow.where(direction > 0, 0).rolling(period, min_periods=period).sum()
    negative_flow = money_flow.where(direction < 0, 0).rolling(period, min_periods=period).sum()
    money_ratio = positive_flow / negative_flow.replace(0, pd.NA)
    return 100 - (100 / (1 + money_ratio))
