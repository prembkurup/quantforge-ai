from typing import Any

import pandas as pd

from quantforge.calculations import CalculationEngine
from quantforge.features.generators import (
    FeatureVector,
    _iso_timestamp,
    _is_pullback,
    _momentum,
    _safe_float,
    _trend,
    _volatility_bucket,
)
from quantforge.features.registry import (
    FeatureRegistry,
    FeatureValue,
    default_feature_registry,
)


REQUIRED_CANDLE_COLUMNS = {"time", "open", "high", "low", "close", "volume"}
REQUIRED_FEATURE_IDS = (
    "trend_direction",
    "trend_strength",
    "momentum_state",
    "volatility_regime",
    "candle_body_ratio",
    "wick_ratio",
    "range_expansion",
    "ema_distance",
    "pullback_state",
    "breakout_state",
)


class FeatureEngine:
    """Converts Calculation Engine outputs into standardized feature vectors.

    Downstream experiment and strategy modules consume FeatureVector payloads
    instead of individual indicator outputs.
    """

    def __init__(
        self,
        calculation_engine: CalculationEngine | None = None,
        registry: FeatureRegistry | None = None,
    ) -> None:
        self._calculation_engine = calculation_engine or CalculationEngine()
        self._registry = registry or default_feature_registry()

    def generate(self, candles: pd.DataFrame, instrument: str, timeframe: str) -> FeatureVector:
        if candles.empty:
            raise ValueError("Cannot generate a feature vector from an empty candle frame.")
        self._validate_candle_inputs(candles)

        calculations = self._calculate(candles)
        features = self._generate_features(calculations)
        available = set(calculations).union(features)
        values = []
        for feature_id in REQUIRED_FEATURE_IDS:
            self._registry.validate_dependencies(feature_id, available)
            spec = self._registry.get(feature_id)
            values.append(FeatureValue(spec=spec, value=features[feature_id]))

        latest = calculations["frame"].iloc[-1]
        return FeatureVector(
            instrument=instrument,
            timeframe=timeframe,
            timestamp=_iso_timestamp(latest["time"]),
            features={value.spec.feature_id: value.value for value in values},
            values=tuple(values),
        )

    def _validate_candle_inputs(self, candles: pd.DataFrame) -> None:
        missing = REQUIRED_CANDLE_COLUMNS.difference(candles.columns)
        if missing:
            raise ValueError(f"Candle frame is missing required columns: {sorted(missing)}")

    def _calculate(self, candles: pd.DataFrame) -> dict[str, Any]:
        frame = candles.copy().reset_index(drop=True)
        frame["ema_fast"] = self._calculation_engine.calculate("indicator.ema", frame["close"], period=12)
        frame["ema_slow"] = self._calculation_engine.calculate("indicator.ema", frame["close"], period=26)
        frame["rsi"] = self._calculation_engine.calculate("indicator.rsi", frame["close"], period=14)
        frame["atr"] = self._calculation_engine.calculate("indicator.atr", frame, period=14)
        price_action = self._calculation_engine.calculate("price_action.candle_parts", frame)
        structure = self._calculation_engine.calculate("market_structure.structure_points", frame)
        frame["range_mean_20"] = price_action["range"].rolling(20, min_periods=1).mean()
        return {
            "frame": frame,
            "ema_fast": frame["ema_fast"].iloc[-1],
            "ema_slow": frame["ema_slow"].iloc[-1],
            "rsi": frame["rsi"],
            "atr": frame["atr"].iloc[-1],
            "close": frame["close"].iloc[-1],
            "body_percent": price_action["body_percent"].iloc[-1],
            "upper_wick": price_action["upper_wick"].iloc[-1],
            "lower_wick": price_action["lower_wick"].iloc[-1],
            "range": price_action["range"].iloc[-1],
            "range_mean_20": frame["range_mean_20"].iloc[-1],
            "bos": structure["bos"].iloc[-1],
        }

    def _generate_features(self, calculations: dict[str, Any]) -> dict[str, Any]:
        trend_direction = _trend(calculations["ema_fast"], calculations["ema_slow"])
        ema_distance = _safe_float(
            (calculations["ema_fast"] - calculations["ema_slow"]) / calculations["close"]
        )
        range_value = calculations["range"]
        range_mean = calculations["range_mean_20"]
        wick_ratio = _safe_float(
            (calculations["upper_wick"] + calculations["lower_wick"]) / range_value
        )
        atr_percent = _safe_float(calculations["atr"] / calculations["close"])
        return {
            "trend_direction": trend_direction,
            "trend_strength": min(abs(ema_distance or 0) * 100, 1.0),
            "momentum_state": _momentum(calculations["rsi"]),
            "volatility_regime": _volatility_bucket(atr_percent),
            "candle_body_ratio": _safe_float(calculations["body_percent"]),
            "wick_ratio": wick_ratio,
            "range_expansion": bool(
                pd.notna(range_value) and pd.notna(range_mean) and range_value > (range_mean * 1.25)
            ),
            "ema_distance": ema_distance,
            "pullback_state": bool(
                _is_pullback(
                    trend_direction,
                    calculations["close"],
                    calculations["ema_fast"],
                )
            ),
            "breakout_state": bool(calculations["bos"]),
        }

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
