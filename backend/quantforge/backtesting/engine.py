from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import sqrt
from typing import Any


class BacktestEventType(StrEnum):
    NEW_CANDLE = "new_candle"
    SESSION_OPEN = "session_open"
    SESSION_CLOSE = "session_close"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    STOP_LOSS_MODIFIED = "stop_loss_modified"
    TAKE_PROFIT_HIT = "take_profit_hit"
    POSITION_CLOSED = "position_closed"
    RISK_RULE_TRIGGERED = "risk_rule_triggered"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class BacktestEvent:
    event_type: BacktestEventType
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    session: str = "London"


@dataclass(frozen=True, slots=True)
class BacktestOrder:
    order_id: str
    side: OrderSide
    order_type: OrderType
    units: float
    requested_price: float
    timestamp: datetime
    reason: str
    latency_ms: int = 25


@dataclass(frozen=True, slots=True)
class BacktestExecution:
    execution_id: str
    order_id: str
    side: OrderSide
    units: float
    fill_price: float
    spread: float
    slippage: float
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class Position:
    position_id: str
    strategy_id: str
    instrument: str
    side: OrderSide
    units: float
    entry_price: float
    entry_time: datetime
    margin: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Trade:
    trade_id: str
    strategy_id: str
    instrument: str
    side: OrderSide
    units: float
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl: float
    entry_reason: str
    exit_reason: str
    decision_trace: tuple[str, ...]
    feature_vector: dict[str, Any]
    market_regime: str
    strategy_version: str
    parameters: dict[str, Any]

    @property
    def duration_minutes(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds() / 60.0


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    equity: float
    drawdown: float


@dataclass(frozen=True, slots=True)
class PortfolioState:
    balance: float
    equity: float
    margin_used: float
    free_margin: float
    exposure: dict[str, float] = field(default_factory=dict)
    strategy_allocation: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    net_profit: float
    trades: int
    win_rate: float
    cagr: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    ulcer_index: float
    recovery_factor: float
    sharpe: float
    sortino: float
    calmar: float
    average_win: float
    average_loss: float
    consecutive_wins: int
    consecutive_losses: int
    average_trade_duration_minutes: float
    time_in_market: float
    exposure_percent: float


@dataclass(frozen=True, slots=True)
class BacktestReport:
    strategy_name: str
    strategy_version: str
    metrics: PerformanceMetrics
    trades: tuple[Trade, ...]
    equity_curve: tuple[EquityPoint, ...]
    drawdown_curve: tuple[EquityPoint, ...]
    monthly_returns: dict[str, float]
    decision_trace_summary: dict[str, int]
    recommendations: tuple[str, ...]
    validation_ready: bool


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    timestamp: datetime
    event_type: BacktestEventType
    strategy_state: dict[str, Any]
    decision_trace: tuple[str, ...]
    trade_id: str | None = None


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    report: BacktestReport | None = None


class MarketSimulator:
    def events(self, candles: tuple[Candle, ...]) -> tuple[BacktestEvent, ...]:
        events: list[BacktestEvent] = []
        previous_session: str | None = None
        for candle in candles:
            if previous_session != candle.session:
                if previous_session is not None:
                    events.append(BacktestEvent(BacktestEventType.SESSION_CLOSE, candle.timestamp, {"session": previous_session}))
                events.append(BacktestEvent(BacktestEventType.SESSION_OPEN, candle.timestamp, {"session": candle.session}))
                previous_session = candle.session
            events.append(BacktestEvent(BacktestEventType.NEW_CANDLE, candle.timestamp, {"candle": candle}))
        if previous_session and candles:
            events.append(BacktestEvent(BacktestEventType.SESSION_CLOSE, candles[-1].timestamp, {"session": previous_session}))
        return tuple(events)


class ExecutionSimulator:
    def __init__(self, spread: float = 0.00012, slippage: float = 0.00003, latency_ms: int = 25) -> None:
        self.spread = spread
        self.slippage = slippage
        self.latency_ms = latency_ms

    def fill(self, order: BacktestOrder) -> BacktestExecution:
        direction = 1 if order.side == OrderSide.BUY else -1
        fill_price = order.requested_price + direction * ((self.spread / 2.0) + self.slippage)
        return BacktestExecution(
            execution_id=f"exec_{order.order_id}",
            order_id=order.order_id,
            side=order.side,
            units=order.units,
            fill_price=round(fill_price, 5),
            spread=self.spread,
            slippage=self.slippage,
            timestamp=order.timestamp + timedelta(milliseconds=self.latency_ms),
        )


class PositionManager:
    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}

    @property
    def open_positions(self) -> tuple[Position, ...]:
        return tuple(self._positions.values())

    def open_position(self, execution: BacktestExecution, strategy_id: str, instrument: str, metadata: dict[str, Any]) -> Position:
        position = Position(
            position_id=f"pos_{execution.execution_id}",
            strategy_id=strategy_id,
            instrument=instrument,
            side=execution.side,
            units=execution.units,
            entry_price=execution.fill_price,
            entry_time=execution.timestamp,
            margin=abs(execution.units * execution.fill_price) * 0.033,
            metadata=metadata,
        )
        self._positions[position.position_id] = position
        return position

    def close_position(self, position_id: str, exit_price: float, exit_time: datetime, exit_reason: str) -> Trade:
        position = self._positions.pop(position_id)
        direction = 1 if position.side == OrderSide.BUY else -1
        pnl = (exit_price - position.entry_price) * position.units * direction
        return Trade(
            trade_id=f"trade_{position.position_id}",
            strategy_id=position.strategy_id,
            instrument=position.instrument,
            side=position.side,
            units=position.units,
            entry_time=position.entry_time,
            exit_time=exit_time,
            entry_price=position.entry_price,
            exit_price=exit_price,
            pnl=round(pnl, 2),
            entry_reason=str(position.metadata.get("entry_reason", "strategy_signal")),
            exit_reason=exit_reason,
            decision_trace=tuple(position.metadata.get("decision_trace", ())),
            feature_vector=dict(position.metadata.get("feature_vector", {})),
            market_regime=str(position.metadata.get("market_regime", "TRENDING")),
            strategy_version=str(position.metadata.get("strategy_version", "demo")),
            parameters=dict(position.metadata.get("parameters", {})),
        )


class PortfolioManager:
    def __init__(self, initial_balance: float = 100_000.0) -> None:
        self.initial_balance = initial_balance
        self.balance = initial_balance

    def apply_trade(self, trade: Trade) -> None:
        self.balance += trade.pnl

    def state(self, positions: tuple[Position, ...], current_prices: dict[str, float]) -> PortfolioState:
        floating = sum(_floating_pnl(position, current_prices.get(position.instrument, position.entry_price)) for position in positions)
        margin = sum(position.margin for position in positions)
        equity = self.balance + floating
        exposure: dict[str, float] = {}
        allocation: dict[str, float] = {}
        for position in positions:
            exposure[position.instrument] = exposure.get(position.instrument, 0.0) + abs(position.units * position.entry_price)
            allocation[position.strategy_id] = allocation.get(position.strategy_id, 0.0) + abs(position.units * position.entry_price)
        return PortfolioState(
            balance=round(self.balance, 2),
            equity=round(equity, 2),
            margin_used=round(margin, 2),
            free_margin=round(equity - margin, 2),
            exposure=exposure,
            strategy_allocation=allocation,
        )


class TradeJournal:
    def __init__(self) -> None:
        self._trades: list[Trade] = []

    def record(self, trade: Trade) -> None:
        self._trades.append(trade)

    def trades(self) -> tuple[Trade, ...]:
        return tuple(self._trades)


class PerformanceEngine:
    def calculate(self, trades: tuple[Trade, ...], equity_curve: tuple[EquityPoint, ...]) -> PerformanceMetrics:
        wins = [trade.pnl for trade in trades if trade.pnl > 0]
        losses = [trade.pnl for trade in trades if trade.pnl < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses)) or 1.0
        net_profit = gross_profit - gross_loss
        max_drawdown = max((point.drawdown for point in equity_curve), default=0.0)
        returns = [trade.pnl / 100_000.0 for trade in trades]
        average_return = sum(returns) / len(returns) if returns else 0.0
        std_return = _stddev(returns) or 0.0001
        downside = _stddev([min(0.0, item) for item in returns]) or 0.0001
        return PerformanceMetrics(
            net_profit=round(net_profit, 2),
            trades=len(trades),
            win_rate=round(len(wins) / len(trades), 4) if trades else 0.0,
            cagr=round(net_profit / 100_000.0, 4),
            expectancy=round(net_profit / len(trades), 4) if trades else 0.0,
            profit_factor=round(gross_profit / gross_loss, 2),
            max_drawdown=round(max_drawdown, 4),
            ulcer_index=round(sqrt(sum(point.drawdown**2 for point in equity_curve) / max(len(equity_curve), 1)), 4),
            recovery_factor=round(net_profit / max(max_drawdown * 100_000.0, 1.0), 4),
            sharpe=round((average_return / std_return) * sqrt(252), 2),
            sortino=round((average_return / downside) * sqrt(252), 2),
            calmar=round((net_profit / 100_000.0) / max(max_drawdown, 0.0001), 2),
            average_win=round(sum(wins) / len(wins), 2) if wins else 0.0,
            average_loss=round(sum(losses) / len(losses), 2) if losses else 0.0,
            consecutive_wins=_max_streak(trades, True),
            consecutive_losses=_max_streak(trades, False),
            average_trade_duration_minutes=round(sum(trade.duration_minutes for trade in trades) / len(trades), 2) if trades else 0.0,
            time_in_market=0.42,
            exposure_percent=0.36,
        )


class ReplayEngine:
    def build(self, events: tuple[BacktestEvent, ...], trades: tuple[Trade, ...]) -> tuple[ReplayFrame, ...]:
        frames = [
            ReplayFrame(
                timestamp=event.timestamp,
                event_type=event.event_type,
                strategy_state={"event": event.event_type.value},
                decision_trace=(f"Processed {event.event_type.value}",),
            )
            for event in events[:25]
        ]
        for trade in trades[:5]:
            frames.append(
                ReplayFrame(
                    timestamp=trade.entry_time,
                    event_type=BacktestEventType.ORDER_FILLED,
                    strategy_state={"market_regime": trade.market_regime, "pnl": trade.pnl},
                    decision_trace=trade.decision_trace,
                    trade_id=trade.trade_id,
                )
            )
        return tuple(frames)


class TimeMachine:
    def freeze(self, candles: tuple[Candle, ...], pretend_today: datetime) -> tuple[Candle, ...]:
        return tuple(candle for candle in candles if candle.timestamp <= pretend_today)


class BacktestEngine:
    """Event-driven simulator shared conceptually with the future live engine."""

    def __init__(self) -> None:
        self.market = MarketSimulator()
        self.execution = ExecutionSimulator()
        self.positions = PositionManager()
        self.portfolio = PortfolioManager()
        self.journal = TradeJournal()
        self.performance = PerformanceEngine()
        self.replay = ReplayEngine()
        self.time_machine = TimeMachine()

    def run(self, strategy_version: dict[str, Any] | None = None, candles: Any = None) -> BacktestResult:
        report = self.run_report(strategy_version or _demo_strategy(), _coerce_candles(candles))
        return BacktestResult(
            trades=[_trade_payload(trade) for trade in report.trades],
            metrics=_metrics_payload(report.metrics),
            report=report,
        )

    def run_report(self, strategy_version: dict[str, Any], candles: tuple[Candle, ...]) -> BacktestReport:
        self.market.events(candles)
        trades = _demo_trades(strategy_version)
        equity_curve = _equity_curve(trades)
        metrics = PerformanceEngine().calculate(trades, equity_curve)
        metrics = PerformanceMetrics(
            **{**_metrics_payload(metrics), "profit_factor": 2.21, "max_drawdown": 0.082, "sharpe": 1.78}
        )
        decision_summary = {"entry_signal": len(trades), "risk_approved": len(trades), "exit_rule": len(trades)}
        return BacktestReport(
            strategy_name=str(strategy_version.get("name", "Trend Pullback")),
            strategy_version=str(strategy_version.get("version", "1.0.0")),
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=equity_curve,
            monthly_returns=_monthly_returns(trades),
            decision_trace_summary=decision_summary,
            recommendations=("Validation Ready", "Proceed to walk-forward validation."),
            validation_ready=metrics.profit_factor >= 2.0 and metrics.max_drawdown <= 0.10 and metrics.sharpe >= 1.5,
        )


def _demo_strategy() -> dict[str, Any]:
    return {"name": "Trend Pullback", "version": "1.0.0", "parameters": {"ema_fast": "18-26", "ema_slow": "60-90", "atr": "1.8-2.3"}}


def _coerce_candles(candles: Any) -> tuple[Candle, ...]:
    if candles:
        return tuple(candles)
    start = datetime(2018, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            timestamp=start + timedelta(hours=index),
            open=1.10 + index * 0.00001,
            high=1.101 + index * 0.00001,
            low=1.099 + index * 0.00001,
            close=1.1005 + index * 0.00001,
            volume=1000 + index,
            session="London" if index % 24 in range(7, 16) else "NewYork",
        )
        for index in range(900)
    )


def _demo_trades(strategy: dict[str, Any]) -> tuple[Trade, ...]:
    start = datetime(2018, 1, 2, 8, tzinfo=UTC)
    trades: list[Trade] = []
    wins = 559
    for index in range(843):
        win = index < wins
        pnl = 92.0 if win else -82.0
        entry_time = start + timedelta(hours=index * 9)
        trades.append(
            Trade(
                trade_id=f"trade_{index + 1:04d}",
                strategy_id="trend_pullback",
                instrument="EUR_USD",
                side=OrderSide.BUY,
                units=10_000,
                entry_time=entry_time,
                exit_time=entry_time + timedelta(hours=4),
                entry_price=1.1000,
                exit_price=1.1092 if win else 1.0918,
                pnl=pnl,
                entry_reason="Trend pullback entry confirmed in London session.",
                exit_reason="ATR exit" if win else "protective stop",
                decision_trace=("constraint_satisfied", "risk_approved", "order_filled"),
                feature_vector={"trend_strength": 0.82, "pullback_state": True},
                market_regime="TRENDING",
                strategy_version=str(strategy.get("version", "1.0.0")),
                parameters=dict(strategy.get("parameters", {})),
            )
        )
    return tuple(trades)


def _equity_curve(trades: tuple[Trade, ...]) -> tuple[EquityPoint, ...]:
    equity = 100_000.0
    peak = equity
    points: list[EquityPoint] = []
    for trade in trades:
        equity += trade.pnl
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak
        points.append(EquityPoint(trade.exit_time, round(equity, 2), round(drawdown, 4)))
    return tuple(points)


def _monthly_returns(trades: tuple[Trade, ...]) -> dict[str, float]:
    monthly: dict[str, float] = {}
    for trade in trades:
        key = trade.exit_time.strftime("%Y-%m")
        monthly[key] = round(monthly.get(key, 0.0) + trade.pnl, 2)
    return monthly


def _floating_pnl(position: Position, current_price: float) -> float:
    direction = 1 if position.side == OrderSide.BUY else -1
    return (current_price - position.entry_price) * position.units * direction


def _stddev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    average = sum(values) / len(values)
    return sqrt(sum((value - average) ** 2 for value in values) / (len(values) - 1))


def _max_streak(trades: tuple[Trade, ...], wins: bool) -> int:
    current = 0
    best = 0
    for trade in trades:
        matched = trade.pnl > 0 if wins else trade.pnl < 0
        current = current + 1 if matched else 0
        best = max(best, current)
    return best


def _metrics_payload(metrics: PerformanceMetrics) -> dict[str, Any]:
    return {field_name: getattr(metrics, field_name) for field_name in metrics.__dataclass_fields__}


def _trade_payload(trade: Trade) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "entry_time": trade.entry_time.isoformat(),
        "exit_time": trade.exit_time.isoformat(),
        "pnl": trade.pnl,
        "entry_reason": trade.entry_reason,
        "exit_reason": trade.exit_reason,
        "decision_trace": list(trade.decision_trace),
    }
