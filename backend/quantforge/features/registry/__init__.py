from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FeatureCategory(StrEnum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    PRICE_ACTION = "price_action"
    MARKET_STRUCTURE = "market_structure"
    SESSION = "session"
    RISK_CONTEXT = "risk_context"


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    feature_id: str
    name: str
    category: FeatureCategory
    version: str
    dependencies: tuple[str, ...]
    output_type: str
    description: str
    calculator: str = "feature.engine"


@dataclass(frozen=True, slots=True)
class FeatureValue:
    spec: FeatureSpec
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.spec.feature_id,
            "name": self.spec.name,
            "category": self.spec.category.value,
            "version": self.spec.version,
            "value": self.value,
            "output_type": self.spec.output_type,
        }


FeatureDefinition = FeatureSpec


class FeatureRegistry:
    def __init__(self) -> None:
        self._features: dict[str, FeatureSpec] = {}

    def register(self, spec: FeatureSpec) -> None:
        key = f"{spec.feature_id}:{spec.version}"
        if key in self._features:
            raise ValueError(f"Feature already registered: {key}")
        self._features[key] = spec

    def get(self, feature_id: str, version: str = "1.0") -> FeatureSpec:
        key = f"{feature_id}:{version}"
        try:
            return self._features[key]
        except KeyError as exc:
            raise KeyError(f"Feature is not registered: {key}") from exc

    def list_definitions(self) -> list[FeatureSpec]:
        return list(self._features.values())

    def list_by_category(self, category: FeatureCategory) -> list[FeatureSpec]:
        return [
            definition
            for definition in self._features.values()
            if definition.category == category
        ]

    def validate_dependencies(self, feature_id: str, available_inputs: set[str]) -> None:
        spec = self.get(feature_id)
        missing = set(spec.dependencies).difference(available_inputs)
        if missing:
            raise ValueError(
                f"Feature {feature_id} is missing dependencies: {sorted(missing)}"
            )


def default_feature_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    defaults = [
        FeatureSpec(
            "trend_direction",
            "Trend Direction",
            FeatureCategory.TREND,
            "1.0",
            ("ema_fast", "ema_slow"),
            "string",
            "Bullish, bearish, flat, or unknown trend state from fast/slow EMA.",
        ),
        FeatureSpec(
            "trend_strength",
            "Trend Strength",
            FeatureCategory.TREND,
            "1.0",
            ("ema_fast", "ema_slow", "close"),
            "float",
            "Normalized trend strength from fast/slow EMA distance.",
        ),
        FeatureSpec(
            "momentum_state",
            "Momentum State",
            FeatureCategory.MOMENTUM,
            "1.0",
            ("rsi",),
            "string",
            "Increasing, decreasing, flat, or unknown RSI momentum state.",
        ),
        FeatureSpec(
            "volatility_regime",
            "Volatility Regime",
            FeatureCategory.VOLATILITY,
            "1.0",
            ("atr", "close"),
            "string",
            "Low, medium, high, or unknown ATR percentage volatility regime.",
        ),
        FeatureSpec(
            "candle_body_ratio",
            "Candle Body Ratio",
            FeatureCategory.PRICE_ACTION,
            "1.0",
            ("body_percent",),
            "float",
            "Candle body as a percentage of total candle range.",
        ),
        FeatureSpec(
            "wick_ratio",
            "Wick Ratio",
            FeatureCategory.PRICE_ACTION,
            "1.0",
            ("upper_wick", "lower_wick", "range"),
            "float",
            "Combined wick length as a percentage of total candle range.",
        ),
        FeatureSpec(
            "range_expansion",
            "Range Expansion",
            FeatureCategory.VOLATILITY,
            "1.0",
            ("range", "range_mean_20"),
            "boolean",
            "True when current range expands materially beyond recent average range.",
        ),
        FeatureSpec(
            "ema_distance",
            "EMA Distance",
            FeatureCategory.TREND,
            "1.0",
            ("ema_fast", "ema_slow", "close"),
            "float",
            "Normalized distance between fast and slow EMA.",
        ),
        FeatureSpec(
            "pullback_state",
            "Pullback State",
            FeatureCategory.PRICE_ACTION,
            "1.0",
            ("trend_direction", "close", "ema_fast"),
            "boolean",
            "True when price pulls back against the current trend toward the fast EMA.",
        ),
        FeatureSpec(
            "breakout_state",
            "Breakout State",
            FeatureCategory.MARKET_STRUCTURE,
            "1.0",
            ("bos",),
            "boolean",
            "True when the latest candle breaks known market structure.",
        ),
        FeatureSpec(
            "session",
            "Session",
            FeatureCategory.SESSION,
            "1.0",
            ("time",),
            "string",
            "Current trading session label.",
        ),
    ]
    for definition in defaults:
        registry.register(definition)
    return registry
