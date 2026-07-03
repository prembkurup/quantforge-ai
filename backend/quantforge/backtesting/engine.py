from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    """Historical simulation boundary."""

    def run(self, strategy_version: dict[str, Any], candles: Any) -> BacktestResult:
        raise NotImplementedError("Backtest simulation rules will be implemented with strategy templates.")

