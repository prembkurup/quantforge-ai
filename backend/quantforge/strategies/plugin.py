from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True, slots=True)
class StrategySignal:
    side: str | None
    confidence: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyPlugin(Protocol):
    plugin_key: str
    name: str
    version: str

    def parameter_space(self) -> list[dict[str, Any]]:
        """Return parameter templates to test in the research engine."""

    def required_indicators(self, parameters: dict[str, Any]) -> list[str]:
        """Declare derived indicators needed for this strategy run."""

    def generate_signal(self, candles: pd.DataFrame, parameters: dict[str, Any]) -> StrategySignal:
        """Generate a signal from candles and dynamically calculated features."""

