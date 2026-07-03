import pytest

from quantforge.features import FeatureVector
from quantforge.research.market_regime import (
    MarketRegime,
    RegimeConfidenceScore,
    RegimeDetector,
    default_regime_registry,
)


def _feature_vector(**features: object) -> FeatureVector:
    defaults = {
        "trend_strength": 0.5,
        "volatility_regime": "medium",
        "breakout_state": False,
    }
    defaults.update(features)
    return FeatureVector(
        instrument="EUR_USD",
        timeframe="H1",
        timestamp="2026-07-04T10:00:00Z",
        features=defaults,
    )


def test_trending_detection() -> None:
    result = RegimeDetector().detect(
        _feature_vector(trend_strength=0.82, volatility_regime="medium")
    )

    assert result.regime == MarketRegime.TRENDING
    assert result.confidence > 0.8
    assert result.features_used == ("trend_strength", "volatility_regime")


def test_ranging_detection() -> None:
    result = RegimeDetector().detect(
        _feature_vector(trend_strength=0.12, volatility_regime="low")
    )

    assert result.regime == MarketRegime.RANGING
    assert result.confidence > 0.6


def test_breakout_detection_wins_over_high_volatility() -> None:
    result = RegimeDetector().detect(
        _feature_vector(
            trend_strength=0.55,
            volatility_regime="high",
            breakout_state=True,
        )
    )

    assert result.regime == MarketRegime.BREAKOUT
    assert result.confidence >= 0.85
    assert "breakout_state" in result.features_used


def test_high_volatility_detection() -> None:
    result = RegimeDetector().detect(
        _feature_vector(trend_strength=0.4, volatility_regime="high")
    )

    assert result.regime == MarketRegime.HIGH_VOLATILITY
    assert result.confidence == 0.72


def test_low_volatility_detection() -> None:
    result = RegimeDetector().detect(
        _feature_vector(trend_strength=0.4, volatility_regime="low")
    )

    assert result.regime == MarketRegime.LOW_VOLATILITY


def test_no_trade_detection() -> None:
    result = RegimeDetector().detect(
        _feature_vector(trend_strength=0.45, volatility_regime="medium")
    )

    assert result.regime == MarketRegime.NO_TRADE
    assert result.confidence == 0.35


def test_confidence_score_bounds() -> None:
    assert RegimeConfidenceScore(1.0).value == 1.0
    with pytest.raises(ValueError, match="between 0 and 1"):
        RegimeConfidenceScore(1.1)


def test_missing_feature_handling() -> None:
    vector = FeatureVector(
        instrument="EUR_USD",
        timeframe="H1",
        timestamp="2026-07-04T10:00:00Z",
        features={"trend_strength": 0.5},
    )

    with pytest.raises(ValueError, match="missing regime features"):
        RegimeDetector().detect(vector)


def test_regime_registry_guards_duplicates_and_missing_specs() -> None:
    registry = default_regime_registry()
    spec = registry.get(MarketRegime.TRENDING)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec)

    registry = default_regime_registry()
    registry._specs.pop(MarketRegime.TRENDING)
    with pytest.raises(KeyError, match="not registered"):
        registry.get(MarketRegime.TRENDING)


def test_regime_result_serializes_for_json_output() -> None:
    payload = RegimeDetector().detect(
        _feature_vector(trend_strength=0.82, volatility_regime="medium")
    ).to_dict()

    assert payload["instrument"] == "EUR_USD"
    assert payload["timeframe"] == "H1"
    assert payload["regime"] == "TRENDING"
    assert isinstance(payload["features_used"], list)
