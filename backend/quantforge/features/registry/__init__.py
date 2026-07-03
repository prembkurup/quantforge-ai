from dataclasses import dataclass
from enum import StrEnum


class FeatureCategory(StrEnum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    PRICE_ACTION = "price_action"
    MARKET_STRUCTURE = "market_structure"
    SESSION = "session"
    LIQUIDITY = "liquidity"


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    feature_id: str
    name: str
    description: str
    version: str
    calculator: str
    dependencies: tuple[str, ...]
    output_type: str
    category: FeatureCategory


class FeatureRegistry:
    def __init__(self) -> None:
        self._features: dict[str, FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> None:
        key = f"{definition.feature_id}:{definition.version}"
        if key in self._features:
            raise ValueError(f"Feature already registered: {key}")
        self._features[key] = definition

    def get(self, feature_id: str, version: str = "1.0") -> FeatureDefinition:
        return self._features[f"{feature_id}:{version}"]

    def list_definitions(self) -> list[FeatureDefinition]:
        return list(self._features.values())


def default_feature_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    defaults = [
        FeatureDefinition(
            "trend",
            "Trend",
            "Latest directional trend state.",
            "1.0",
            "feature.generator",
            ("ema_fast", "ema_slow"),
            "string",
            FeatureCategory.TREND,
        ),
        FeatureDefinition(
            "trend_strength",
            "Trend Strength",
            "Normalized distance between fast and slow EMA.",
            "1.0",
            "feature.generator",
            ("ema_fast", "ema_slow", "close"),
            "float",
            FeatureCategory.TREND,
        ),
        FeatureDefinition(
            "momentum",
            "Momentum",
            "Latest RSI slope state.",
            "1.0",
            "feature.generator",
            ("rsi",),
            "string",
            FeatureCategory.MOMENTUM,
        ),
        FeatureDefinition(
            "volatility",
            "Volatility",
            "ATR percentage bucket.",
            "1.0",
            "feature.generator",
            ("atr", "close"),
            "string",
            FeatureCategory.VOLATILITY,
        ),
        FeatureDefinition(
            "session",
            "Session",
            "Current trading session.",
            "1.0",
            "feature.generator",
            ("time",),
            "string",
            FeatureCategory.SESSION,
        ),
    ]
    for definition in defaults:
        registry.register(definition)
    return registry
