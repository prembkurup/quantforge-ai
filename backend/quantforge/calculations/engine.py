from typing import Any

from quantforge.calculations.indicators import atr, ema, rsi
from quantforge.calculations.registry import CalculationCategory, CalculationSpec
from quantforge.calculations.statistical import rolling_mean, rolling_std, zscore
from quantforge.calculations.volatility import close_to_close_volatility, true_range


class CalculationEngine:
    """Registry-backed engine for all derived market calculations."""

    def __init__(self) -> None:
        self._calculations: dict[str, CalculationSpec] = {}
        self._register_defaults()

    def register(self, spec: CalculationSpec) -> None:
        if spec.key in self._calculations:
            raise ValueError(f"Calculation already registered: {spec.key}")
        self._calculations[spec.key] = spec

    def calculate(self, key: str, *args: Any, **parameters: Any) -> Any:
        spec = self.get(key)
        merged_parameters = {**spec.default_parameters, **parameters}
        return spec.function(*args, **merged_parameters)

    def get(self, key: str) -> CalculationSpec:
        try:
            return self._calculations[key]
        except KeyError as exc:
            raise KeyError(f"Calculation is not registered: {key}") from exc

    def list_specs(self, category: CalculationCategory | None = None) -> list[CalculationSpec]:
        specs = list(self._calculations.values())
        if category is None:
            return specs
        return [spec for spec in specs if spec.category == category]

    def _register_defaults(self) -> None:
        defaults = [
            CalculationSpec("indicator.ema", CalculationCategory.INDICATOR, ema),
            CalculationSpec("indicator.rsi", CalculationCategory.INDICATOR, rsi),
            CalculationSpec("indicator.atr", CalculationCategory.INDICATOR, atr),
            CalculationSpec("statistical.rolling_mean", CalculationCategory.STATISTICAL, rolling_mean),
            CalculationSpec("statistical.rolling_std", CalculationCategory.STATISTICAL, rolling_std),
            CalculationSpec("statistical.zscore", CalculationCategory.STATISTICAL, zscore),
            CalculationSpec("volatility.true_range", CalculationCategory.VOLATILITY, true_range),
            CalculationSpec(
                "volatility.close_to_close",
                CalculationCategory.VOLATILITY,
                close_to_close_volatility,
            ),
        ]
        for spec in defaults:
            self.register(spec)
