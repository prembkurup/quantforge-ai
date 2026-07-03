from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from quantforge.calculations import CalculationEngine


@dataclass(frozen=True, slots=True)
class FeatureVector:
    instrument: str
    timeframe: str
    candle_time: str
    features: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "candle_time": self.candle_time,
            "features": self.features,
        }


class StandardFeatureVectorGenerator:
    def __init__(self, calculation_engine: CalculationEngine | None = None) -> None:
        self._calculation_engine = calculation_engine or CalculationEngine()

    def generate(self, candles: pd.DataFrame, instrument: str, timeframe: str) -> FeatureVector:
        if candles.empty:
            raise ValueError("Cannot generate a feature vector from an empty candle frame.")

        frame = candles.copy().reset_index(drop=True)
        frame["ema_fast"] = self._calculation_engine.calculate("indicator.ema", frame["close"], period=12)
        frame["ema_slow"] = self._calculation_engine.calculate("indicator.ema", frame["close"], period=26)
        frame["rsi"] = self._calculation_engine.calculate("indicator.rsi", frame["close"], period=14)
        frame["atr"] = self._calculation_engine.calculate("indicator.atr", frame, period=14)
        frame["zscore"] = self._calculation_engine.calculate("statistical.zscore", frame["close"], window=20)
        frame["return_1"] = self._calculation_engine.calculate("statistical.simple_returns", frame["close"])

        price_action = self._calculation_engine.calculate("price_action.candle_parts", frame)
        patterns = self._calculation_engine.calculate("price_action.candle_patterns", frame)
        structure = self._calculation_engine.calculate("market_structure.structure_points", frame)
        sessions = self._calculation_engine.calculate("session.flags", frame)

        latest = frame.iloc[-1]
        latest_price_action = price_action.iloc[-1]
        latest_patterns = patterns.iloc[-1]
        latest_structure = structure.iloc[-1]
        latest_session = sessions.iloc[-1]

        ema_distance = _safe_float((latest["ema_fast"] - latest["ema_slow"]) / latest["close"])
        atr_percent = _safe_float(latest["atr"] / latest["close"])
        trend = _trend(latest["ema_fast"], latest["ema_slow"])

        features = {
            "trend": trend,
            "trend_strength": min(abs(ema_distance) * 100, 1.0),
            "momentum": _momentum(frame["rsi"]),
            "volatility": _volatility_bucket(atr_percent),
            "pullback": bool(_is_pullback(trend, latest["close"], latest["ema_fast"])),
            "breakout": bool(latest_structure["bos"]),
            "session": latest_session["session"],
            "ema_distance": ema_distance,
            "support_distance": _safe_float(latest_structure["support_distance"]),
            "resistance_distance": _safe_float(latest_structure["resistance_distance"]),
            "bos": bool(latest_structure["bos"]),
            "choch": bool(latest_structure["choch"]),
            "body_percent": _safe_float(latest_price_action["body_percent"]),
            "inside_bar": bool(latest_patterns["inside_bar"]),
            "outside_bar": bool(latest_patterns["outside_bar"]),
            "pin_bar": bool(latest_patterns["pin_bar"]),
            "zscore": _safe_float(latest["zscore"]),
            "return_1": _safe_float(latest["return_1"]),
        }
        return FeatureVector(
            instrument=instrument,
            timeframe=timeframe,
            candle_time=str(latest["time"]),
            features=features,
        )


def _trend(ema_fast: Any, ema_slow: Any) -> str:
    if pd.isna(ema_fast) or pd.isna(ema_slow):
        return "unknown"
    if ema_fast > ema_slow:
        return "bullish"
    if ema_fast < ema_slow:
        return "bearish"
    return "flat"


def _momentum(rsi: pd.Series) -> str:
    latest = rsi.iloc[-1]
    previous = rsi.iloc[-2] if len(rsi) > 1 else pd.NA
    if pd.isna(latest) or pd.isna(previous):
        return "unknown"
    if latest > previous:
        return "increasing"
    if latest < previous:
        return "decreasing"
    return "flat"


def _volatility_bucket(atr_percent: float | None) -> str:
    if atr_percent is None:
        return "unknown"
    if atr_percent < 0.001:
        return "low"
    if atr_percent < 0.003:
        return "medium"
    return "high"


def _is_pullback(trend: str, close: Any, ema_fast: Any) -> bool:
    if pd.isna(close) or pd.isna(ema_fast):
        return False
    return (trend == "bullish" and close < ema_fast) or (trend == "bearish" and close > ema_fast)


def _safe_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)
