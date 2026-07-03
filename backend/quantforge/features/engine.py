import pandas as pd


class FeatureEngine:
    """Compatibility helper for tabular features.

    New downstream modules should consume standardized FeatureVector payloads from
    StandardFeatureVectorGenerator instead of calling individual indicators.
    """

    def add_trend_features(self, candles: pd.DataFrame) -> pd.DataFrame:
        frame = candles.copy()
        if "ema_fast" in frame and "ema_slow" in frame:
            frame["trend_direction"] = "flat"
            frame.loc[frame["ema_fast"] > frame["ema_slow"], "trend_direction"] = "bullish"
            frame.loc[frame["ema_fast"] < frame["ema_slow"], "trend_direction"] = "bearish"
        return frame

    def add_volatility_features(self, candles: pd.DataFrame) -> pd.DataFrame:
        frame = candles.copy()
        if "atr" in frame and "close" in frame:
            frame["atr_percent"] = frame["atr"] / frame["close"]
        return frame
