import pandas as pd


class MarketRegimeEngine:
    """Classifies broad market regimes from standardized features."""

    def classify(self, features: pd.DataFrame) -> str:
        if features.empty:
            return "no_trade"
        latest = features.iloc[-1]
        if latest.get("atr_percent", 0) > 0.02:
            return "high_volatility"
        trend = latest.get("trend_direction")
        if trend in {"bullish", "bearish"}:
            return "trending"
        return "ranging"

