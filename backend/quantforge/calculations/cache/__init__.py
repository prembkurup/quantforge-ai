from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CalculationCacheKey:
    calculation_key: str
    instrument: str
    timeframe: str
    parameters_hash: str
    data_fingerprint: str


class CalculationCache:
    """Small in-memory cache for expensive derived calculations."""

    def __init__(self) -> None:
        self._values: dict[CalculationCacheKey, Any] = {}

    def get(self, key: CalculationCacheKey) -> Any | None:
        return self._values.get(key)

    def set(self, key: CalculationCacheKey, value: Any) -> None:
        self._values[key] = value

    def clear(self) -> None:
        self._values.clear()
