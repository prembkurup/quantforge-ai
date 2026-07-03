from typing import Any

from quantforge.calculations.indicators import (
    atr,
    bollinger_bands,
    cci,
    donchian,
    ema,
    hma,
    ichimoku,
    keltner_channels,
    macd,
    mfi,
    momentum,
    obv,
    roc,
    rsi,
    sma,
    stochastic,
    supertrend,
    vwap,
    wma,
)
from quantforge.calculations.market_structure import structure_points
from quantforge.calculations.price_action import candle_parts, candle_patterns
from quantforge.calculations.registry import CalculationCategory, CalculationSpec
from quantforge.calculations.sessions import session_flags
from quantforge.calculations.statistics import (
    kurtosis,
    log_returns,
    percentile,
    rolling_mean,
    rolling_median,
    rolling_std,
    simple_returns,
    skewness,
    variance,
    zscore,
)
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
            CalculationSpec("indicator.sma", CalculationCategory.INDICATOR, sma),
            CalculationSpec("indicator.wma", CalculationCategory.INDICATOR, wma),
            CalculationSpec("indicator.hma", CalculationCategory.INDICATOR, hma),
            CalculationSpec("indicator.supertrend", CalculationCategory.INDICATOR, supertrend),
            CalculationSpec("indicator.ichimoku", CalculationCategory.INDICATOR, ichimoku),
            CalculationSpec("indicator.donchian", CalculationCategory.INDICATOR, donchian),
            CalculationSpec("indicator.rsi", CalculationCategory.INDICATOR, rsi),
            CalculationSpec("indicator.macd", CalculationCategory.INDICATOR, macd),
            CalculationSpec("indicator.stochastic", CalculationCategory.INDICATOR, stochastic),
            CalculationSpec("indicator.cci", CalculationCategory.INDICATOR, cci),
            CalculationSpec("indicator.roc", CalculationCategory.INDICATOR, roc),
            CalculationSpec("indicator.momentum", CalculationCategory.INDICATOR, momentum),
            CalculationSpec("indicator.atr", CalculationCategory.INDICATOR, atr),
            CalculationSpec("indicator.bollinger_bands", CalculationCategory.INDICATOR, bollinger_bands),
            CalculationSpec("indicator.keltner_channels", CalculationCategory.INDICATOR, keltner_channels),
            CalculationSpec("indicator.obv", CalculationCategory.INDICATOR, obv),
            CalculationSpec("indicator.vwap", CalculationCategory.INDICATOR, vwap),
            CalculationSpec("indicator.mfi", CalculationCategory.INDICATOR, mfi),
            CalculationSpec("statistical.rolling_mean", CalculationCategory.STATISTICAL, rolling_mean),
            CalculationSpec("statistical.rolling_median", CalculationCategory.STATISTICAL, rolling_median),
            CalculationSpec("statistical.rolling_std", CalculationCategory.STATISTICAL, rolling_std),
            CalculationSpec("statistical.zscore", CalculationCategory.STATISTICAL, zscore),
            CalculationSpec("statistical.variance", CalculationCategory.STATISTICAL, variance),
            CalculationSpec("statistical.percentile", CalculationCategory.STATISTICAL, percentile),
            CalculationSpec("statistical.skewness", CalculationCategory.STATISTICAL, skewness),
            CalculationSpec("statistical.kurtosis", CalculationCategory.STATISTICAL, kurtosis),
            CalculationSpec("statistical.log_returns", CalculationCategory.STATISTICAL, log_returns),
            CalculationSpec("statistical.simple_returns", CalculationCategory.STATISTICAL, simple_returns),
            CalculationSpec("price_action.candle_parts", CalculationCategory.PRICE_ACTION, candle_parts),
            CalculationSpec("price_action.candle_patterns", CalculationCategory.PRICE_ACTION, candle_patterns),
            CalculationSpec(
                "market_structure.structure_points",
                CalculationCategory.MARKET_STRUCTURE,
                structure_points,
            ),
            CalculationSpec("session.flags", CalculationCategory.SESSION, session_flags),
            CalculationSpec("volatility.true_range", CalculationCategory.VOLATILITY, true_range),
            CalculationSpec(
                "volatility.close_to_close",
                CalculationCategory.VOLATILITY,
                close_to_close_volatility,
            ),
        ]
        for spec in defaults:
            self.register(spec)
