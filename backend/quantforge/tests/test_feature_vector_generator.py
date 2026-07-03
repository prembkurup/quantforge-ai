import pandas as pd

import pytest

from quantforge.features import (
    StandardFeatureVectorGenerator,
    default_feature_registry,
    require_feature_keys,
)


def test_feature_registry_contains_versioned_defaults() -> None:
    registry = default_feature_registry()

    definition = registry.get("trend_direction")

    assert definition.version == "1.0"
    assert definition.output_type == "string"


def test_feature_vector_generator_outputs_standard_payload() -> None:
    candles = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=60, freq="h", tz="UTC"),
            "open": [1.0 + (index * 0.001) for index in range(60)],
            "high": [1.01 + (index * 0.001) for index in range(60)],
            "low": [0.99 + (index * 0.001) for index in range(60)],
            "close": [1.005 + (index * 0.001) for index in range(60)],
            "volume": [100 + index for index in range(60)],
        }
    )

    feature_vector = StandardFeatureVectorGenerator().generate(candles, "EUR_USD", "H1")
    payload = feature_vector.to_dict()

    assert payload["instrument"] == "EUR_USD"
    assert payload["timeframe"] == "H1"
    assert {
        "trend_direction",
        "trend_strength",
        "momentum_state",
        "volatility_regime",
        "session",
        "bos",
        "choch",
    }.issubset(payload["features"])


def test_feature_validator_reports_missing_keys() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        require_feature_keys({"trend_direction": "bullish"}, {"trend_direction", "session"})
