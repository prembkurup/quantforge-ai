from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quantforge.research import DatabaseBackedStrategyLibraryRunner, DatabaseResearchScope


class FakeCandleRepository:
    def __init__(self) -> None:
        self.rows = [
            {
                "time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=index),
                "pair_name": "EUR_USD",
                "granularity": "H1",
                "open_price": Decimal("1.1000") + Decimal(index) * Decimal("0.0001"),
                "high_price": Decimal("1.1010") + Decimal(index) * Decimal("0.0001"),
                "low_price": Decimal("1.0990") + Decimal(index) * Decimal("0.0001"),
                "close_price": Decimal("1.1005") + Decimal(index) * Decimal("0.0001"),
                "volume": 100 + index,
                "is_complete": True,
            }
            for index in range(1_000)
        ]

    def count_window(self, pair_name: str, granularity: str, start: datetime, end: datetime, **_: object) -> int:
        return len(self._window(pair_name, granularity, start, end))

    def duplicate_count(self, pair_name: str, granularity: str, start: datetime, end: datetime, **_: object) -> int:
        return 0

    def load_window(
        self,
        pair_name: str,
        granularity: str,
        start: datetime,
        end: datetime,
        **kwargs: object,
    ) -> list[dict]:
        limit = int(kwargs.get("limit", 50_000))
        return self._window(pair_name, granularity, start, end)[:limit]

    def _window(self, pair_name: str, granularity: str, start: datetime, end: datetime) -> list[dict]:
        return [
            row
            for row in self.rows
            if row["pair_name"] == pair_name
            and row["granularity"] == granularity
            and start <= row["time"] < end
        ]


def test_database_runner_executes_real_candle_batches() -> None:
    scope = DatabaseResearchScope(
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        window_candles=100,
        stride_candles=50,
        max_batches=12,
    )

    result = DatabaseBackedStrategyLibraryRunner(FakeCandleRepository()).run(scope)

    assert result.successful is True
    assert result.coverage[0].database_ready is True
    assert result.coverage[0].stored_candles >= 700
    assert result.coverage[0].duplicate_candles == 0
    assert result.coverage[0].missing_candle_count == 0
    assert len(result.experiment_batches) == 12
    assert len(result.candidate_assets) == 12
    assert all(batch.candles_loaded == 100 for batch in result.experiment_batches)
    assert all(asset.database_backed for asset in result.candidate_assets)
    assert result.reproducibility_key


def test_database_runner_blocks_gappy_or_underfilled_coverage() -> None:
    scope = DatabaseResearchScope(
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 2, tzinfo=timezone.utc),
        window_candles=100,
        max_batches=12,
    )

    result = DatabaseBackedStrategyLibraryRunner(FakeCandleRepository()).run(scope)

    assert result.successful is False
    assert result.coverage[0].database_ready is False
    assert result.experiment_batches == ()
    assert result.candidate_assets == ()
