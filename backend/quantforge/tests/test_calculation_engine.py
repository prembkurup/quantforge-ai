import pandas as pd

from quantforge.calculations import CalculationCategory, CalculationEngine


def test_calculation_engine_registers_indicator_calculator() -> None:
    engine = CalculationEngine()
    candles = pd.DataFrame(
        {
            "high": [2.0, 3.0, 4.0, 5.0, 6.0],
            "low": [1.0, 1.5, 2.0, 3.0, 4.0],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5],
        }
    )

    result = engine.calculate("indicator.ema", candles["close"], period=3)

    assert len(result) == len(candles)
    assert "indicator.ema" in {
        spec.key for spec in engine.list_specs(CalculationCategory.INDICATOR)
    }


def test_calculation_engine_registers_non_indicator_calculators() -> None:
    engine = CalculationEngine()
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    result = engine.calculate("statistical.rolling_mean", close, window=3)

    assert result.iloc[-1] == 4.0
    assert engine.list_specs(CalculationCategory.VOLATILITY)
