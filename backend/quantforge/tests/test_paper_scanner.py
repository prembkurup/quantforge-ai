from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from quantforge.live.paper_scanner import (
    DecisionTraceStore,
    MultiPairPaperScanner,
    PaperPositionStore,
    PaperScannerConfig,
    ProcessedCandleStore,
)
from quantforge.research.strategy_assets import (
    ApprovedStrategyAssetStatus,
    ApprovedStrategyAssetStore,
    StrategyAssetRepository,
)
from quantforge.strategies.production import ProductionStrategyManagementPlatform


class FakeLatestCandleRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def load_latest(
        self,
        pair_name: str,
        granularity: str,
        *,
        complete_only: bool = True,
        limit: int = 300,
    ) -> list[dict]:
        self.calls.append((pair_name, granularity))
        return [
            {
                "time": datetime(2026, 7, 7, 3, 30, tzinfo=UTC),
                "pair_name": pair_name,
                "granularity": granularity,
                "volume": 100,
                "open_price": 1.1,
                "high_price": 1.11,
                "low_price": 1.09,
                "close_price": 1.105,
                "is_complete": True,
                "source": "test",
            }
        ]


def test_multi_pair_paper_scanner_reads_latest_candles_and_blocks_duplicate_runs(tmp_path: Path) -> None:
    repository = _strategy_repository(tmp_path)
    candles = FakeLatestCandleRepository()
    scanner = MultiPairPaperScanner(
        candles,
        config=PaperScannerConfig(
            enabled=True,
            pairs=("EUR_USD", "GBP_USD"),
            timeframes=("H1",),
            max_pairs_per_scan=30,
        ),
        strategy_repository=repository,
        processed_store=ProcessedCandleStore(tmp_path / "processed.json"),
        position_store=PaperPositionStore(tmp_path / "positions.json"),
        decision_store=DecisionTraceStore(tmp_path / "decisions.jsonl"),
    )

    result = scanner.run()

    assert candles.calls == [("EUR_USD", "H1"), ("GBP_USD", "H1")]
    assert result.mode == "paper-scanner"
    assert result.pairs_loaded == 2
    assert result.pair_timeframes_scanned == 2
    assert result.events_processed == 1
    assert result.signals_generated == 1
    assert result.orders_executed == 1
    assert result.open_positions == 1
    assert result.pair_results[0].strategy_asset_id == "QF-2026-00431"
    assert result.pair_results[1].reason == "no_compatible_approved_strategy"

    second = scanner.run()

    assert second.events_processed == 0
    assert second.signals_generated == 0
    assert second.orders_executed == 0
    assert second.open_positions == 1
    assert {item.reason for item in second.pair_results} == {"candle_already_processed"}


def _strategy_repository(tmp_path: Path) -> StrategyAssetRepository:
    repository = StrategyAssetRepository(tmp_path / "assets.json")
    asset = ProductionStrategyManagementPlatform()._demo_asset()
    record = ApprovedStrategyAssetStore(repository).publish(
        asset,
        status=ApprovedStrategyAssetStatus.APPROVED,
    )
    repository.upsert(replace(record, pair="EUR_USD", timeframe="H1", market_regime="TRENDING"))
    return repository
