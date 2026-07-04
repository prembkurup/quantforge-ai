from datetime import UTC, datetime, timedelta

from quantforge.backtesting import (
    BacktestEngine,
    BacktestEventType,
    BacktestOrder,
    Candle,
    ExecutionSimulator,
    MarketSimulator,
    OrderSide,
    OrderType,
    PositionManager,
    ReplayEngine,
    TimeMachine,
)


def test_market_simulator_emits_event_stream_not_just_candles() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    candles = (
        Candle(start, 1.1, 1.2, 1.0, 1.15, session="London"),
        Candle(start + timedelta(hours=1), 1.15, 1.2, 1.1, 1.18, session="NewYork"),
    )

    events = MarketSimulator().events(candles)

    assert events[0].event_type == BacktestEventType.SESSION_OPEN
    assert BacktestEventType.NEW_CANDLE in {event.event_type for event in events}
    assert BacktestEventType.SESSION_CLOSE in {event.event_type for event in events}


def test_execution_simulator_applies_spread_slippage_and_latency() -> None:
    order = BacktestOrder(
        order_id="order_1",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        units=10_000,
        requested_price=1.1000,
        timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        reason="test",
    )

    execution = ExecutionSimulator(spread=0.0002, slippage=0.0001, latency_ms=50).fill(order)

    assert execution.fill_price == 1.1002
    assert execution.timestamp == order.timestamp + timedelta(milliseconds=50)


def test_position_manager_records_auditable_trade_object() -> None:
    order = BacktestOrder(
        order_id="order_1",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        units=10_000,
        requested_price=1.1000,
        timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        reason="trend pullback",
    )
    execution = ExecutionSimulator(spread=0.0, slippage=0.0).fill(order)
    manager = PositionManager()
    position = manager.open_position(
        execution,
        strategy_id="trend_pullback",
        instrument="EUR_USD",
        metadata={
            "entry_reason": "Trend pullback confirmed.",
            "decision_trace": ("constraint_satisfied", "order_filled"),
            "feature_vector": {"trend_strength": 0.8},
            "parameters": {"ema_fast": "18-26"},
        },
    )

    trade = manager.close_position(position.position_id, 1.1100, execution.timestamp + timedelta(hours=1), "target")

    assert trade.pnl == 100.0
    assert trade.decision_trace == ("constraint_satisfied", "order_filled")
    assert trade.feature_vector["trend_strength"] == 0.8


def test_backtest_engine_reports_validation_ready_professional_metrics() -> None:
    report = BacktestEngine().run().report

    assert report is not None
    assert report.metrics.trades == 843
    assert report.metrics.profit_factor == 2.21
    assert report.metrics.max_drawdown == 0.082
    assert report.metrics.sharpe == 1.78
    assert report.validation_ready is True
    assert report.equity_curve
    assert report.monthly_returns
    assert report.decision_trace_summary["entry_signal"] == 843


def test_replay_engine_and_time_machine_support_debugging_without_future_knowledge() -> None:
    engine = BacktestEngine()
    report = engine.run().report
    assert report is not None

    frames = ReplayEngine().build(engine.market.events(()), report.trades)
    start = datetime(2017, 5, 1, tzinfo=UTC)
    candles = tuple(
        Candle(start + timedelta(days=index), 1.1, 1.2, 1.0, 1.15)
        for index in range(5)
    )
    frozen = TimeMachine().freeze(candles, datetime(2017, 5, 3, tzinfo=UTC))

    assert frames[0].event_type == BacktestEventType.ORDER_FILLED
    assert len(frozen) == 3
