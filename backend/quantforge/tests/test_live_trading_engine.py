from datetime import UTC, datetime, time

from quantforge.live import TradeJournalStore
from quantforge.live import (
    LiveFeatureVector,
    LiveTradingEngine,
    SignalAction,
    StrategySelection,
    TradeDecision,
    TradeDecisionEngine,
)


def test_live_trading_engine_runs_event_driven_pipeline() -> None:
    result = LiveTradingEngine().run()

    assert result.connected is True
    assert result.events_processed == 6
    assert result.signals[0].action == SignalAction.BUY
    assert result.executions[0].status == "filled"
    assert result.dashboard.run_24_7_ready is True


def test_trade_decision_engine_blocks_bad_market_quality_before_signal() -> None:
    decision = TradeDecisionEngine().evaluate(
        LiveFeatureVector(
            instrument="EUR_USD",
            timeframe="H1",
            trend_strength=0.84,
            pullback_state=True,
            spread=0.0005,
            session="London",
        ),
        StrategySelection("QF-TEST", "1.0", 0.40, "test"),
        portfolio_exposure=0.40,
    )

    assert decision.decision == TradeDecision.BLOCK
    assert "Spread" in decision.reason


def test_state_store_recovery_and_synchronization_are_available() -> None:
    engine = LiveTradingEngine()
    result = engine.run()

    assert engine.state.latest() == result.state_snapshot
    assert result.recovery_completed is True
    assert result.synchronization.internal_orders == result.synchronization.broker_orders
    assert result.synchronization.repaired is False


def test_live_risk_blocks_oversized_orders() -> None:
    result = LiveTradingEngine().run()
    signal = result.signals[0]
    oversized_signal = type(signal)(
        signal_id="SIG-LIVE-OVERSIZE",
        strategy_id=signal.strategy_id,
        action=signal.action,
        instrument=signal.instrument,
        units=50_000,
        reason=signal.reason,
        feature_vector=signal.feature_vector,
        market_regime=signal.market_regime,
    )

    decision = LiveTradingEngine().risk.approve(oversized_signal)
    assert decision.approved is False
    assert "max_units" in decision.reason


def test_live_engine_uses_paper_oanda_path_without_real_credentials() -> None:
    result = LiveTradingEngine().run()

    assert result.executions[0].broker == "OANDA_PAPER"
    assert result.executions[0].order_id == "paper_oanda_order_0001"


def test_live_engine_forces_intraday_close_and_records_trade_journal(tmp_path) -> None:
    journal = tmp_path / "intraday_trade_journal.json"

    result = LiveTradingEngine().run(
        intraday_timestamp=datetime(2026, 7, 6, 21, 50, tzinfo=UTC),
        force_close_time_utc=time(21, 45),
        trade_journal_path=journal,
    )

    assert result.positions == ()
    assert result.forced_close_receipts
    assert result.forced_close_receipts[0].status == "filled"
    assert result.dashboard.open_positions == 0

    entries = TradeJournalStore(journal).list()
    assert entries[0]["event_type"] == "FORCED_CLOSE"
    assert entries[0]["reason"] == "Forced end-of-day intraday close."
    assert entries[0]["evidence"]["policy"] == "INTRADAY_FORCE_CLOSE"
