from typing import Any


def require_feature_keys(feature_vector: dict[str, Any], required_keys: set[str]) -> None:
    missing = required_keys.difference(feature_vector)
    if missing:
        raise ValueError(f"Feature vector is missing required keys: {sorted(missing)}")
