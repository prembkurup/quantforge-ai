import pandas as pd
import pytest
from pathlib import Path

from quantforge.calculations import CalculationCategory, CalculationEngine, CalculationSpec
from quantforge.calculations.cache import CalculationCache, CalculationCacheKey
from quantforge.calculations.volatility import close_to_close_volatility, true_range
from quantforge.features import (
    FeatureCategory,
    FeatureDefinition,
    FeatureRegistry,
    FeatureStore,
    StandardFeatureVectorGenerator,
    default_feature_registry,
    require_feature_keys,
)
from quantforge.features.engine import FeatureEngine
from quantforge.features.generators import (
    _is_pullback,
    _momentum,
    _safe_float,
    _trend,
    _volatility_bucket,
)


def _candles(rows: int = 80, freq: str = "h") -> pd.DataFrame:
    close = [1.1000 + (index * 0.0005) + ((index % 7) * 0.0001) for index in range(rows)]
    return pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=rows, freq=freq, tz="UTC"),
            "open": [value - 0.0002 for value in close],
            "high": [value + 0.0008 for value in close],
            "low": [value - 0.0007 for value in close],
            "close": close,
            "volume": [100 + index for index in range(rows)],
        }
    )


def test_calculation_engine_supports_custom_plugin_registration() -> None:
    engine = CalculationEngine()
    spec = CalculationSpec(
        key="custom_plugin.close_plus",
        category=CalculationCategory.CUSTOM_PLUGIN,
        function=lambda values, amount=1: values + amount,
        default_parameters={"amount": 2},
    )

    engine.register(spec)

    assert engine.calculate("custom_plugin.close_plus", pd.Series([1, 2])).tolist() == [3, 4]
    assert engine.list_specs()
    with pytest.raises(ValueError, match="already registered"):
        engine.register(spec)
    with pytest.raises(KeyError, match="not registered"):
        engine.get("custom_plugin.missing")


def test_feature_registry_enforces_versioned_unique_definitions() -> None:
    registry = FeatureRegistry()
    definition = FeatureDefinition(
        feature_id="trend",
        name="Trend",
        description="Directional trend.",
        version="1.0",
        calculator="feature.generator",
        dependencies=("ema_fast", "ema_slow"),
        output_type="string",
        category=FeatureCategory.TREND,
    )

    registry.register(definition)

    assert registry.get("trend") == definition
    assert registry.list_by_category(FeatureCategory.TREND) == [definition]
    with pytest.raises(ValueError, match="already registered"):
        registry.register(definition)
    with pytest.raises(KeyError, match="not registered"):
        registry.get("missing")


def test_default_feature_registry_documents_dependencies() -> None:
    registry = default_feature_registry()

    for definition in registry.list_definitions():
        assert definition.feature_id
        assert definition.version == "1.0"
        assert definition.calculator
        assert definition.dependencies
        assert definition.output_type


def test_feature_vector_schema_is_consistent_across_timeframes() -> None:
    generator = StandardFeatureVectorGenerator()

    h1_payload = generator.generate(_candles(freq="h"), "EUR_USD", "H1").to_dict()
    h4_payload = generator.generate(_candles(freq="4h"), "EUR_USD", "H4").to_dict()

    assert h1_payload["features"].keys() == h4_payload["features"].keys()
    assert h4_payload["timeframe"] == "H4"
    require_feature_keys(
        h1_payload["features"],
        {"trend", "momentum", "volatility", "session", "bos", "choch"},
    )


def test_feature_vector_generator_rejects_empty_candles() -> None:
    with pytest.raises(ValueError, match="empty candle frame"):
        StandardFeatureVectorGenerator().generate(pd.DataFrame(), "EUR_USD", "H1")


def test_feature_vector_helper_states_cover_unknown_flat_and_buckets() -> None:
    assert _trend(pd.NA, 1.0) == "unknown"
    assert _trend(1.0, 2.0) == "bearish"
    assert _trend(1.0, 1.0) == "flat"
    assert _momentum(pd.Series([50.0])) == "unknown"
    assert _momentum(pd.Series([50.0, 49.0])) == "decreasing"
    assert _momentum(pd.Series([50.0, 50.0])) == "flat"
    assert _volatility_bucket(None) == "unknown"
    assert _volatility_bucket(0.002) == "medium"
    assert _volatility_bucket(0.01) == "high"
    assert not _is_pullback("bullish", pd.NA, 1.0)
    assert _is_pullback("bearish", 1.2, 1.1)
    assert _safe_float(pd.NA) is None


def test_feature_engine_adds_compatibility_features_when_inputs_exist() -> None:
    engine = FeatureEngine()
    frame = pd.DataFrame(
        {
            "close": [1.0, 1.0, 1.0],
            "ema_fast": [1.1, 0.9, 1.0],
            "ema_slow": [1.0, 1.0, 1.0],
            "atr": [0.01, 0.02, 0.03],
        }
    )

    trend_frame = engine.add_trend_features(frame)
    volatility_frame = engine.add_volatility_features(frame)
    unchanged_trend = engine.add_trend_features(pd.DataFrame({"close": [1.0]}))
    unchanged_volatility = engine.add_volatility_features(pd.DataFrame({"close": [1.0]}))

    assert trend_frame["trend_direction"].tolist() == ["bullish", "bearish", "flat"]
    assert volatility_frame["atr_percent"].tolist() == [0.01, 0.02, 0.03]
    assert "trend_direction" not in unchanged_trend
    assert "atr_percent" not in unchanged_volatility


def test_volatility_calculators_match_reference_values() -> None:
    candles = _candles(5)
    close = candles["close"]

    result = true_range(candles)

    assert result.iloc[0] == pytest.approx(candles["high"].iloc[0] - candles["low"].iloc[0])
    assert close_to_close_volatility(close, 3).iloc[-1] == pytest.approx(
        close.pct_change().rolling(window=3, min_periods=3).std().iloc[-1]
    )


def test_feature_store_and_cache_round_trip_feature_payloads(tmp_path: Path) -> None:
    feature_store = FeatureStore(tmp_path)
    cache = CalculationCache()
    payload = StandardFeatureVectorGenerator().generate(_candles(), "EUR_USD", "H1").to_dict()
    cache_key = CalculationCacheKey(
        calculation_key="indicator.ema",
        instrument="EUR_USD",
        timeframe="H1",
        parameters_hash="period=200",
        data_fingerprint="latest:2025-01-04T07:00:00Z",
    )

    feature_store.write_json_ready_vector("latest", payload)
    cache.set(cache_key, payload)

    stored = feature_store.read_frame("latest")
    assert stored.loc[0, "instrument"] == "EUR_USD"
    assert stored.loc[0, "timeframe"] == "H1"
    assert cache.get(cache_key) == payload
    assert cache.get(
        CalculationCacheKey("indicator.ema", "EUR_USD", "M5", "period=200", "missing")
    ) is None
    cache.clear()
    assert cache.get(cache_key) is None
