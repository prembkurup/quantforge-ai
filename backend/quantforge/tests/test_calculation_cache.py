from quantforge.calculations import CalculationCache, CalculationCacheKey


def test_calculation_cache_stores_expensive_results_by_key() -> None:
    cache = CalculationCache()
    key = CalculationCacheKey(
        calculation_key="indicator.ema",
        instrument="EUR_USD",
        timeframe="H1",
        parameters_hash="period=200",
        data_fingerprint="latest:2026-07-04T01:00:00Z",
    )

    cache.set(key, [1, 2, 3])

    assert cache.get(key) == [1, 2, 3]
