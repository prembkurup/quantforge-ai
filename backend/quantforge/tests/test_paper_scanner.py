from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from quantforge.live.paper_scanner import (
    DecisionTraceStore,
    MultiPairPaperScanner,
    PaperSignalRecord,
    PaperPositionStore,
    PaperScannerConfig,
    ProcessedCandleStore,
    ProcessedSignalStore,
    _coerce_datetime,
)
from quantforge.live.engine import PositionSnapshot
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
                "time": datetime(2026, 7, 7, 2, 30, tzinfo=UTC),
                "pair_name": pair_name,
                "granularity": granularity,
                "volume": 100,
                "open_price": 1.09,
                "high_price": 1.10,
                "low_price": 1.08,
                "close_price": 1.1,
                "is_complete": True,
                "source": "test",
            },
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
        signal_store=ProcessedSignalStore(tmp_path / "signals.json"),
        position_store=PaperPositionStore(tmp_path / "positions.json"),
        decision_store=DecisionTraceStore(tmp_path / "decisions.jsonl"),
    )

    result = scanner.run()

    assert candles.calls == [("EUR_USD", "H1"), ("GBP_USD", "H1"), ("EUR_USD", "M1")]
    assert result.mode == "paper-scanner"
    assert result.pairs_loaded == 2
    assert result.pair_timeframes_scanned == 2
    assert result.events_processed == 1
    assert result.signals_generated == 1
    assert result.orders_executed == 1
    assert result.orders_blocked == 1
    assert result.open_positions == 1
    assert result.skip_reasons["filled"] == 1
    assert result.skip_reasons["no_compatible_approved_strategy"] == 1
    assert result.pair_results[0].strategy_asset_id == "QF-2026-00431"
    assert result.pair_results[0].feature_vector is not None
    assert result.pair_results[0].feature_vector.candle_time == "2026-07-07T03:30:00+00:00"
    assert result.pair_results[0].regime_result is not None
    assert result.pair_results[0].strategy_selection is not None
    assert result.paper_signals[0].feature_vector_id == result.pair_results[0].feature_vector.feature_vector_id
    assert result.paper_orders[0].execution_path == "OANDA_PAPER"
    assert result.paper_positions[0]["source_candle_time"] == "2026-07-07T03:30:00+00:00"
    assert result.paper_positions[0]["entry_time"] == "2026-07-07T03:30:00+00:00"
    assert result.paper_positions[0]["opened_at"] == "2026-07-07T03:30:00+00:00"
    assert result.pair_results[1].reason == "no_compatible_approved_strategy"

    second = scanner.run()

    assert second.events_processed == 0
    assert second.signals_generated == 0
    assert second.orders_executed == 0
    assert second.open_positions == 1
    assert {item.reason for item in second.pair_results} == {"CANDLE_ALREADY_PROCESSED"}


def test_existing_paper_position_blocks_duplicate_order(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "existing",
                    "instrument": "EUR_USD",
                    "pair": "EUR_USD",
                    "timeframe": "H1",
                    "status": "OPEN",
                }
            ]
        }
    )
    scanner = MultiPairPaperScanner(
        FakeLatestCandleRepository(),
        config=PaperScannerConfig(
            enabled=True,
            pairs=("EUR_USD",),
            timeframes=("H1",),
            max_pairs_per_scan=30,
        ),
        strategy_repository=_strategy_repository(tmp_path),
        processed_store=ProcessedCandleStore(tmp_path / "processed.json"),
        signal_store=ProcessedSignalStore(tmp_path / "signals.json"),
        position_store=position_store,
        decision_store=DecisionTraceStore(tmp_path / "decisions.jsonl"),
    )

    result = scanner.run()

    assert result.orders_executed == 0
    assert result.pair_results[0].reason == "CONFLICTING_PAPER_POSITION"
    assert result.open_positions == 1


def test_position_store_matches_new_positions_to_exact_signal_timeframe(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    h1_signal = PaperSignalRecord(
        signal_id="SIG-REPLAY-EUR_USD-H1-000001",
        strategy_asset_id="QF-H1",
        pair="EUR_USD",
        timeframe="H1",
        candle_time="2026-07-07T04:00:00+00:00",
        signal_type="BUY",
        confidence=0.93,
        reason_codes=(),
        feature_vector_id="fv-h1",
        signal_key="key-h1",
    )
    m15_signal = PaperSignalRecord(
        signal_id="SIG-REPLAY-EUR_USD-M15-000001",
        strategy_asset_id="QF-M15",
        pair="EUR_USD",
        timeframe="M15",
        candle_time="2026-07-07T03:45:00+00:00",
        signal_type="SELL",
        confidence=0.91,
        reason_codes=(),
        feature_vector_id="fv-m15",
        signal_key="key-m15",
    )

    position_store.add_many(
        (
            PositionSnapshot(
                strategy_id="QF-LIVE-0001",
                instrument="EUR_USD",
                units=10000,
                floating_pl=0.0,
                margin_used=363.0,
                exposure=0.1,
                position_id="pos_paper_sig-replay-eur_usd-m15-000001",
            ),
            PositionSnapshot(
                strategy_id="QF-LIVE-0001",
                instrument="EUR_USD",
                units=10000,
                floating_pl=0.0,
                margin_used=363.0,
                exposure=0.1,
                position_id="pos_paper_sig-replay-eur_usd-h1-000001",
            ),
        ),
        (h1_signal, m15_signal),
        {"EUR_USD:H1": 1.2, "EUR_USD:M15": 1.1},
    )

    by_id = {position["position_id"]: position for position in position_store._load()["positions"]}

    assert by_id["pos_paper_sig-replay-eur_usd-m15-000001"]["timeframe"] == "M15"
    assert by_id["pos_paper_sig-replay-eur_usd-m15-000001"]["source_signal_id"] == m15_signal.signal_id
    assert by_id["pos_paper_sig-replay-eur_usd-m15-000001"]["entry_price"] == 1.1
    assert by_id["pos_paper_sig-replay-eur_usd-h1-000001"]["timeframe"] == "H1"
    assert by_id["pos_paper_sig-replay-eur_usd-h1-000001"]["source_signal_id"] == h1_signal.signal_id
    assert by_id["pos_paper_sig-replay-eur_usd-h1-000001"]["entry_price"] == 1.2


def test_paper_position_store_enriches_legacy_open_positions(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "legacy",
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "status": "OPEN",
                    "units": 10000,
                    "close_price": 1.105,
                    "floating_pl": 50.0,
                    "strategy_id": "QF-LIVE-0001",
                    "signal_id": "SIG-REPLAY-EUR_USD-H1-000001",
                    "opened_at": "2026-07-07T03:46:55+00:00",
                }
            ]
        }
    )

    positions = position_store.list_open()

    assert positions[0]["pair"] == "EUR_USD"
    assert positions[0]["direction"] == "BUY"
    assert positions[0]["entry_price"] == 1.1
    assert positions[0]["open_price"] == 1.1
    assert positions[0]["stop_loss"] == 1.0989
    assert positions[0]["take_profit"] == 1.1022
    assert positions[0]["strategy_asset_id"] == "QF-LIVE-0001"
    assert positions[0]["source_signal_id"] == "SIG-REPLAY-EUR_USD-H1-000001"
    assert positions[0]["entry_time"] == "2026-07-07T03:46:55+00:00"


def test_paper_position_store_prefers_source_candle_time_for_open_time(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "open",
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 1.1,
                    "opened_at": "2026-07-07T03:46:55+00:00",
                    "source_candle_time": "2026-07-07 03:30:00",
                }
            ]
        }
    )

    positions = position_store.list_open()

    assert positions[0]["entry_time"] == "2026-07-07T03:30:00+00:00"
    assert positions[0]["opened_at"] == "2026-07-07T03:30:00+00:00"


def test_paper_scanner_treats_naive_candle_times_as_utc() -> None:
    assert _coerce_datetime("2026-07-07 03:30:00").isoformat() == "2026-07-07T03:30:00+00:00"


def test_mark_to_market_closes_open_position_when_take_profit_touched(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "tp-hit",
                    "pair": "EUR_USD",
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 1.1,
                    "open_price": 1.1,
                    "stop_loss": 1.099,
                    "take_profit": 1.102,
                    "opened_at": "2026-07-07T03:00:00+00:00",
                }
            ]
        }
    )

    position_store.mark_to_market(
        {"EUR_USD:H1": 1.101},
        {
            "EUR_USD:H1": {
                "time": datetime(2026, 7, 7, 4, 0, tzinfo=UTC),
                "high_price": 1.1021,
                "low_price": 1.1005,
            }
        },
    )

    positions = position_store._load()["positions"]
    assert positions[0]["status"] == "CLOSED"
    assert positions[0]["close_reason"] == "TAKE_PROFIT"
    assert positions[0]["close_price"] == 1.102
    assert positions[0]["p_l"] == 20.0
    assert position_store.list_open() == ()


def test_mark_to_market_closes_open_position_when_stop_loss_touched(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "sl-hit",
                    "pair": "EUR_USD",
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 1.1,
                    "open_price": 1.1,
                    "stop_loss": 1.099,
                    "take_profit": 1.102,
                    "opened_at": "2026-07-07T03:00:00+00:00",
                }
            ]
        }
    )

    position_store.mark_to_market(
        {"EUR_USD:H1": 1.101},
        {
            "EUR_USD:H1": {
                "time": datetime(2026, 7, 7, 4, 0, tzinfo=UTC),
                "high_price": 1.1021,
                "low_price": 1.0989,
            }
        },
    )

    positions = position_store._load()["positions"]
    assert positions[0]["status"] == "CLOSED"
    assert positions[0]["close_reason"] == "STOP_LOSS"
    assert positions[0]["close_price"] == 1.099
    assert positions[0]["p_l"] == -10.0


def test_mark_to_market_uses_m1_monitor_candle_for_h1_position_exit(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "h1-tracked-by-m1",
                    "pair": "EUR_USD",
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 1.1,
                    "open_price": 1.1,
                    "stop_loss": 1.099,
                    "take_profit": 1.102,
                    "source_candle_time": "2026-07-07T03:00:00+00:00",
                    "opened_at": "2026-07-07T03:00:00+00:00",
                }
            ]
        }
    )

    position_store.mark_to_market(
        {"EUR_USD:H1": 1.1005, "EUR_USD:M1": 1.1018},
        {
            "EUR_USD:H1": {
                "time": datetime(2026, 7, 7, 4, 0, tzinfo=UTC),
                "high_price": 1.1008,
                "low_price": 1.1002,
            },
            "EUR_USD:M1": {
                "time": datetime(2026, 7, 7, 3, 41, tzinfo=UTC),
                "high_price": 1.1021,
                "low_price": 1.101,
            },
        },
    )

    positions = position_store._load()["positions"]
    assert positions[0]["status"] == "CLOSED"
    assert positions[0]["close_reason"] == "TAKE_PROFIT"
    assert positions[0]["close_price"] == 1.102
    assert positions[0]["close_timeframe"] == "M1"
    assert positions[0]["closed_at"] == "2026-07-07T03:41:00+00:00"


def test_mark_to_market_uses_first_m1_hit_instead_of_next_h1_close_time(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "first-m1-hit",
                    "pair": "EUR_USD",
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 1.1,
                    "open_price": 1.1,
                    "stop_loss": 1.099,
                    "take_profit": 1.102,
                    "source_candle_time": "2026-07-07T03:00:00+00:00",
                    "opened_at": "2026-07-07T03:00:00+00:00",
                }
            ]
        }
    )

    position_store.mark_to_market(
        {"EUR_USD:H1": 1.103, "EUR_USD:M1": 1.1025},
        {
            "EUR_USD:H1": {
                "time": datetime(2026, 7, 7, 4, 0, tzinfo=UTC),
                "high_price": 1.103,
                "low_price": 1.1002,
            },
            "EUR_USD:M1": {
                "time": datetime(2026, 7, 7, 3, 59, tzinfo=UTC),
                "high_price": 1.1025,
                "low_price": 1.1018,
            },
        },
        {
            "EUR_USD:M1": [
                {
                    "time": datetime(2026, 7, 7, 3, 1, tzinfo=UTC),
                    "high_price": 1.1004,
                    "low_price": 1.0998,
                },
                {
                    "time": datetime(2026, 7, 7, 3, 12, tzinfo=UTC),
                    "high_price": 1.1022,
                    "low_price": 1.1011,
                },
                {
                    "time": datetime(2026, 7, 7, 3, 59, tzinfo=UTC),
                    "high_price": 1.1025,
                    "low_price": 1.1018,
                },
            ],
        },
    )

    positions = position_store._load()["positions"]
    assert positions[0]["status"] == "CLOSED"
    assert positions[0]["close_reason"] == "TAKE_PROFIT"
    assert positions[0]["close_timeframe"] == "M1"
    assert positions[0]["closed_at"] == "2026-07-07T03:12:00+00:00"


def test_mark_to_market_converts_jpy_quote_pl_to_usd_account_currency(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "jpy-cross",
                    "pair": "AUD_JPY",
                    "instrument": "AUD_JPY",
                    "timeframe": "M15",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 100.0,
                    "open_price": 100.0,
                    "close_price": 99.9,
                    "opened_at": "2026-07-07T03:00:00+00:00",
                }
            ]
        }
    )

    position_store.mark_to_market(
        {"AUD_JPY:M15": 99.9},
        conversion_prices={"AUD_JPY": 99.9, "USD_JPY": 100.0},
    )

    positions = position_store._load()["positions"]
    assert positions[0]["p_l_quote_currency"] == -1000.0
    assert positions[0]["p_l_account_currency"] == -10.0
    assert positions[0]["p_l_currency"] == "USD"
    assert positions[0]["p_l"] == -10.0


def test_mark_to_market_normalizes_usd_index_pl_units(tmp_path: Path) -> None:
    position_store = PaperPositionStore(tmp_path / "positions.json")
    position_store._save(
        {
            "positions": [
                {
                    "position_id": "nas-open",
                    "pair": "NAS100_USD",
                    "instrument": "NAS100_USD",
                    "timeframe": "H1",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 28831.0,
                    "open_price": 28831.0,
                    "close_price": 28831.0,
                    "opened_at": "2026-07-08T10:00:00+00:00",
                },
                {
                    "position_id": "spx-open",
                    "pair": "SPX500_USD",
                    "instrument": "SPX500_USD",
                    "timeframe": "H1",
                    "direction": "BUY",
                    "status": "OPEN",
                    "units": 10000,
                    "entry_price": 7447.4,
                    "open_price": 7447.4,
                    "close_price": 7447.4,
                    "opened_at": "2026-07-08T10:00:00+00:00",
                },
            ]
        }
    )

    position_store.mark_to_market({"NAS100_USD:H1": 28841.0, "SPX500_USD:H1": 7442.4})

    positions = position_store._load()["positions"]
    assert positions[0]["p_l"] == 10.0
    assert positions[0]["p_l_account_currency"] == 10.0
    assert positions[0]["p_l_currency"] == "USD"
    assert positions[1]["p_l"] == -5.0
    assert positions[1]["p_l_account_currency"] == -5.0
    assert positions[1]["p_l_currency"] == "USD"


def test_risk_rejection_prevents_order(tmp_path: Path) -> None:
    scanner = MultiPairPaperScanner(
        FakeLatestCandleRepository(),
        config=PaperScannerConfig(
            enabled=True,
            pairs=("EUR_USD",),
            timeframes=("H1",),
            max_pairs_per_scan=30,
            max_open_positions=0,
        ),
        strategy_repository=_strategy_repository(tmp_path),
        processed_store=ProcessedCandleStore(tmp_path / "processed.json"),
        signal_store=ProcessedSignalStore(tmp_path / "signals.json"),
        position_store=PaperPositionStore(tmp_path / "positions.json"),
        decision_store=DecisionTraceStore(tmp_path / "decisions.jsonl"),
    )

    result = scanner.run()

    assert result.orders_executed == 0
    assert result.pair_results[0].risk_result is not None
    assert result.pair_results[0].risk_result.status == "REJECTED"
    assert "MAX_OPEN_POSITIONS_EXCEEDED" in result.pair_results[0].reason


def test_scanner_rejects_major_recent_candle_gap(tmp_path: Path) -> None:
    class GapRepository(FakeLatestCandleRepository):
        def load_latest(self, *args, **kwargs) -> list[dict]:
            rows = super().load_latest(*args, **kwargs)
            rows[0]["time"] = datetime(2026, 7, 7, 0, 0, tzinfo=UTC)
            return rows

    scanner = MultiPairPaperScanner(
        GapRepository(),
        config=PaperScannerConfig(
            enabled=True,
            pairs=("EUR_USD",),
            timeframes=("H1",),
            max_pairs_per_scan=30,
        ),
        strategy_repository=_strategy_repository(tmp_path),
        processed_store=ProcessedCandleStore(tmp_path / "processed.json"),
        signal_store=ProcessedSignalStore(tmp_path / "signals.json"),
        position_store=PaperPositionStore(tmp_path / "positions.json"),
        decision_store=DecisionTraceStore(tmp_path / "decisions.jsonl"),
    )

    result = scanner.run()

    assert result.signals_generated == 0
    assert result.pair_results[0].reason == "RECENT_LOOKBACK_GAP"


def _strategy_repository(tmp_path: Path) -> StrategyAssetRepository:
    repository = StrategyAssetRepository(tmp_path / "assets.json")
    asset = ProductionStrategyManagementPlatform()._demo_asset()
    record = ApprovedStrategyAssetStore(repository).publish(
        asset,
        status=ApprovedStrategyAssetStatus.APPROVED,
    )
    repository.upsert(replace(record, pair="EUR_USD", timeframe="H1", market_regime="TRENDING"))
    return repository
