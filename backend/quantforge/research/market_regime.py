from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from quantforge.features import FeatureVector


class MarketRegime(StrEnum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    BREAKOUT = "BREAKOUT"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True, slots=True)
class RegimeConfidenceScore:
    value: float
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 1:
            raise ValueError("Regime confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class RegimeResult:
    instrument: str
    timeframe: str
    timestamp: str
    regime: MarketRegime
    confidence: float
    features_used: tuple[str, ...]
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "regime": self.regime.value,
            "confidence": self.confidence,
            "features_used": list(self.features_used),
            "reasons": list(self.reasons),
        }


RuleEvaluator = Callable[[dict[str, Any]], RegimeConfidenceScore | None]


@dataclass(frozen=True, slots=True)
class RegimeSpec:
    regime: MarketRegime
    name: str
    version: str
    required_features: tuple[str, ...]
    description: str
    evaluator: RuleEvaluator


class RegimeRegistry:
    def __init__(self) -> None:
        self._specs: dict[MarketRegime, RegimeSpec] = {}

    def register(self, spec: RegimeSpec) -> None:
        if spec.regime in self._specs:
            raise ValueError(f"Regime already registered: {spec.regime}")
        self._specs[spec.regime] = spec

    def get(self, regime: MarketRegime) -> RegimeSpec:
        try:
            return self._specs[regime]
        except KeyError as exc:
            raise KeyError(f"Regime is not registered: {regime}") from exc

    def list_specs(self) -> list[RegimeSpec]:
        return list(self._specs.values())


class RegimeDetector:
    def __init__(self, registry: RegimeRegistry | None = None) -> None:
        self._registry = registry or default_regime_registry()

    def detect(self, feature_vector: FeatureVector) -> RegimeResult:
        features = feature_vector.features
        self._validate_required_features(features)

        best_spec = self._registry.get(MarketRegime.NO_TRADE)
        best_score = RegimeConfidenceScore(0.35, ("No higher-confidence regime matched.",))
        for spec in self._registry.list_specs():
            score = spec.evaluator(features)
            if score is not None and score.value > best_score.value:
                best_spec = spec
                best_score = score

        return RegimeResult(
            instrument=feature_vector.instrument,
            timeframe=feature_vector.timeframe,
            timestamp=feature_vector.timestamp,
            regime=best_spec.regime,
            confidence=round(best_score.value, 4),
            features_used=best_spec.required_features,
            reasons=best_score.reasons,
        )

    def _validate_required_features(self, features: dict[str, Any]) -> None:
        required = {
            "trend_strength",
            "volatility_regime",
            "breakout_state",
        }
        missing = required.difference(features)
        if missing:
            raise ValueError(f"FeatureVector is missing regime features: {sorted(missing)}")


class MarketRegimeEngine(RegimeDetector):
    """Compatibility alias for older research pipeline imports."""


def default_regime_registry() -> RegimeRegistry:
    registry = RegimeRegistry()
    for spec in [
        RegimeSpec(
            MarketRegime.BREAKOUT,
            "Breakout",
            "1.0",
            ("volatility_regime", "breakout_state", "trend_strength"),
            "High volatility plus structure break.",
            _breakout_rule,
        ),
        RegimeSpec(
            MarketRegime.TRENDING,
            "Trending",
            "1.0",
            ("trend_strength", "volatility_regime"),
            "Strong directional structure with enough volatility.",
            _trending_rule,
        ),
        RegimeSpec(
            MarketRegime.RANGING,
            "Ranging",
            "1.0",
            ("trend_strength", "volatility_regime"),
            "Weak trend strength in low volatility.",
            _ranging_rule,
        ),
        RegimeSpec(
            MarketRegime.HIGH_VOLATILITY,
            "High Volatility",
            "1.0",
            ("volatility_regime",),
            "High volatility without a confirmed breakout.",
            _high_volatility_rule,
        ),
        RegimeSpec(
            MarketRegime.LOW_VOLATILITY,
            "Low Volatility",
            "1.0",
            ("volatility_regime", "trend_strength"),
            "Low volatility without a strong ranging score.",
            _low_volatility_rule,
        ),
        RegimeSpec(
            MarketRegime.NO_TRADE,
            "No Trade",
            "1.0",
            ("trend_strength", "volatility_regime", "breakout_state"),
            "Default state when no actionable regime is clear.",
            _no_trade_rule,
        ),
    ]:
        registry.register(spec)
    return registry


def _breakout_rule(features: dict[str, Any]) -> RegimeConfidenceScore | None:
    if features["volatility_regime"] == "high" and features["breakout_state"]:
        trend_strength = float(features.get("trend_strength") or 0)
        return RegimeConfidenceScore(
            min(0.85 + (trend_strength * 0.1), 0.98),
            ("High volatility and breakout_state is true.",),
        )
    return None


def _trending_rule(features: dict[str, Any]) -> RegimeConfidenceScore | None:
    trend_strength = float(features["trend_strength"])
    if trend_strength > 0.7 and features["volatility_regime"] in {"medium", "high"}:
        return RegimeConfidenceScore(
            min(0.6 + (trend_strength * 0.35), 0.95),
            ("Trend strength is high with sufficient volatility.",),
        )
    return None


def _ranging_rule(features: dict[str, Any]) -> RegimeConfidenceScore | None:
    trend_strength = float(features["trend_strength"])
    if trend_strength < 0.3 and features["volatility_regime"] == "low":
        return RegimeConfidenceScore(
            min(0.55 + ((0.3 - trend_strength) * 0.8), 0.8),
            ("Trend strength is weak and volatility is low.",),
        )
    return None


def _high_volatility_rule(features: dict[str, Any]) -> RegimeConfidenceScore | None:
    if features["volatility_regime"] == "high":
        return RegimeConfidenceScore(0.72, ("Volatility regime is high.",))
    return None


def _low_volatility_rule(features: dict[str, Any]) -> RegimeConfidenceScore | None:
    trend_strength = float(features["trend_strength"])
    if features["volatility_regime"] == "low" and trend_strength >= 0.3:
        return RegimeConfidenceScore(0.58, ("Volatility regime is low.",))
    return None


def _no_trade_rule(features: dict[str, Any]) -> RegimeConfidenceScore:
    if features.get("volatility_regime") == "unknown":
        return RegimeConfidenceScore(0.5, ("Volatility is unknown.",))
    return RegimeConfidenceScore(0.35, ("No actionable rule matched.",))
