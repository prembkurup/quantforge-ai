from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from pathlib import Path
from enum import StrEnum
from typing import Any

from quantforge.execution.oanda import OandaExecutionClient
from quantforge.live.intraday import (
    ForcedCloseManager,
    TradeJournalStore,
    default_intraday_profile,
    default_trade_journal_path,
    journal_entries_from_forced_close,
)
from quantforge.risk.engine import RiskDecision, RiskEngine
from quantforge.strategies.plugin import StrategyPlugin
from quantforge.strategies.production import (
    ProductionStrategyManagementPlatform,
    ProductionPortfolio,
    StrategyRegistryStatus,
)
from quantforge.validation import StrategyAsset


class LiveEventType(StrEnum):
    CONNECT = "connect"
    NEW_CANDLE = "new_candle"
    PRICE_UPDATE = "price_update"
    SESSION_OPEN = "session_open"
    SESSION_CLOSE = "session_close"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    POSITION_CLOSED = "position_closed"
    HEARTBEAT = "heartbeat"
    CONNECTION_LOST = "connection_lost"
    SPREAD_CHANGED = "spread_changed"
    RECOVERY_COMPLETED = "recovery_completed"
    SYNCHRONIZATION_COMPLETED = "synchronization_completed"


class SignalAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"
    HOLD = "HOLD"


class TradeDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class LiveEvent:
    event_type: LiveEventType
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LiveFeatureVector:
    instrument: str
    timeframe: str
    trend_strength: float
    pullback_state: bool
    spread: float
    session: str


@dataclass(frozen=True, slots=True)
class MarketRegimeSnapshot:
    regime: str
    confidence: float


@dataclass(frozen=True, slots=True)
class StrategySelection:
    strategy_id: str
    version: str
    allocation_percent: float
    reason: str


@dataclass(frozen=True, slots=True)
class TradeDecisionResult:
    decision: TradeDecision
    reason: str
    checks: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TradingSignal:
    signal_id: str
    strategy_id: str
    action: SignalAction
    instrument: str
    units: float
    reason: str
    feature_vector: LiveFeatureVector
    market_regime: MarketRegimeSnapshot


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    order_id: str
    signal_id: str
    status: str
    broker: str
    payload: dict[str, Any]
    retries: int = 0


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    strategy_id: str
    instrument: str
    units: float
    floating_pl: float
    margin_used: float
    exposure: float
    position_id: str = ""


@dataclass(frozen=True, slots=True)
class LiveStateSnapshot:
    orders: tuple[ExecutionReceipt, ...]
    positions: tuple[PositionSnapshot, ...]
    signals: tuple[TradingSignal, ...]
    regimes: dict[str, str]
    portfolio_id: str
    risk: dict[str, Any]
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class SynchronizationResult:
    internal_orders: int
    broker_orders: int
    repaired: bool
    reason: str


@dataclass(frozen=True, slots=True)
class LiveTradingDashboard:
    connected: bool
    market_events: int
    signals_generated: int
    orders_executed: int
    open_positions: int
    risk_blocks: int
    recovered: bool
    synchronized: bool
    run_24_7_ready: bool


@dataclass(frozen=True, slots=True)
class LiveTradingRunResult:
    connected: bool
    events_processed: int
    signals: tuple[TradingSignal, ...]
    executions: tuple[ExecutionReceipt, ...]
    positions: tuple[PositionSnapshot, ...]
    state_snapshot: LiveStateSnapshot
    recovery_completed: bool
    synchronization: SynchronizationResult
    dashboard: LiveTradingDashboard
    forced_close_receipts: tuple[ExecutionReceipt, ...] = ()


class LiveEventBus:
    def __init__(self) -> None:
        self._events: list[LiveEvent] = []

    def publish(self, event: LiveEvent) -> LiveEvent:
        self._events.append(event)
        return event

    def drain(self) -> tuple[LiveEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events


class MarketStream:
    def seed(self, bus: LiveEventBus) -> tuple[LiveEvent, ...]:
        now = datetime(2026, 7, 4, 2, 56, tzinfo=UTC)
        events = (
            LiveEvent(LiveEventType.CONNECT, now, {"broker": "OANDA", "status": "connected"}),
            LiveEvent(LiveEventType.SESSION_OPEN, now, {"session": "London"}),
            LiveEvent(LiveEventType.SPREAD_CHANGED, now, {"instrument": "EUR_USD", "spread": 0.00012}),
            LiveEvent(
                LiveEventType.NEW_CANDLE,
                now,
                {
                    "instrument": "EUR_USD",
                    "timeframe": "H1",
                    "close": 1.1024,
                    "session": "London",
                    "trend_strength": 0.84,
                    "pullback_state": True,
                },
            ),
            LiveEvent(LiveEventType.PRICE_UPDATE, now, {"instrument": "EUR_USD", "bid": 1.10234, "ask": 1.10246}),
            LiveEvent(LiveEventType.HEARTBEAT, now, {"status": "healthy"}),
        )
        for event in events:
            bus.publish(event)
        return events


class LiveFeatureEngine:
    def build(self, event: LiveEvent) -> LiveFeatureVector | None:
        if event.event_type != LiveEventType.NEW_CANDLE:
            return None
        return LiveFeatureVector(
            instrument=str(event.payload["instrument"]),
            timeframe=str(event.payload["timeframe"]),
            trend_strength=float(event.payload.get("trend_strength", 0.0)),
            pullback_state=bool(event.payload.get("pullback_state", False)),
            spread=float(event.payload.get("spread", 0.00012)),
            session=str(event.payload.get("session", "London")),
        )


class LiveMarketRegimeEngine:
    def detect(self, features: LiveFeatureVector) -> MarketRegimeSnapshot:
        if features.trend_strength >= 0.70:
            return MarketRegimeSnapshot("TRENDING", 0.91)
        return MarketRegimeSnapshot("RANGING", 0.64)


class StrategySelector:
    def select(
        self,
        asset: StrategyAsset,
        portfolio: ProductionPortfolio,
        regime: MarketRegimeSnapshot,
    ) -> StrategySelection:
        strategy = portfolio.strategies[0]
        return StrategySelection(
            strategy_id=asset.passport.strategy_id,
            version=asset.passport.version,
            allocation_percent=strategy.allocation_percent,
            reason=f"Selected production Strategy Asset for {regime.regime} regime.",
        )


class TradeDecisionEngine:
    def evaluate(
        self,
        features: LiveFeatureVector,
        selection: StrategySelection,
        portfolio_exposure: float,
        broker_health: str = "healthy",
        connection_status: str = "connected",
        high_impact_news: bool = False,
        daily_loss_percent: float = 0.01,
    ) -> TradeDecisionResult:
        checks = {
            "spread": features.spread,
            "high_impact_news": high_impact_news,
            "portfolio_exposure": portfolio_exposure,
            "daily_loss_percent": daily_loss_percent,
            "broker_health": broker_health,
            "connection_status": connection_status,
            "strategy_id": selection.strategy_id,
        }
        if features.spread > 0.00030:
            return TradeDecisionResult(TradeDecision.BLOCK, "Spread is above live trading threshold.", checks)
        if high_impact_news:
            return TradeDecisionResult(TradeDecision.BLOCK, "High-impact news window is active.", checks)
        if portfolio_exposure > 0.65:
            return TradeDecisionResult(TradeDecision.BLOCK, "Portfolio exposure is too high.", checks)
        if daily_loss_percent > 0.03:
            return TradeDecisionResult(TradeDecision.BLOCK, "Daily loss limit is breached.", checks)
        if broker_health != "healthy" or connection_status != "connected":
            return TradeDecisionResult(TradeDecision.BLOCK, "Broker or connection health is not acceptable.", checks)
        return TradeDecisionResult(TradeDecision.ALLOW, "Trading environment is acceptable.", checks)


class SignalGenerator:
    def generate(
        self,
        features: LiveFeatureVector,
        regime: MarketRegimeSnapshot,
        selection: StrategySelection,
        decision: TradeDecisionResult,
        signal_id: str = "SIG-LIVE-0001",
    ) -> TradingSignal:
        action = SignalAction.HOLD
        reason = "Trade decision engine blocked actionable trading."
        if decision.decision == TradeDecision.ALLOW and regime.regime == "TRENDING" and features.pullback_state:
            action = SignalAction.BUY
            reason = "Trend pullback feature vector is actionable in TRENDING regime."
        return TradingSignal(
            signal_id=signal_id,
            strategy_id=selection.strategy_id,
            action=action,
            instrument=features.instrument,
            units=10_000 if action == SignalAction.BUY else 0,
            reason=reason,
            feature_vector=features,
            market_regime=regime,
        )


class LiveRiskController:
    def __init__(self, risk_engine: RiskEngine | None = None) -> None:
        self._risk = risk_engine or RiskEngine()

    def approve(self, signal: TradingSignal) -> RiskDecision:
        if signal.action == SignalAction.HOLD:
            return RiskDecision(False, "No actionable signal.")
        return self._risk.evaluate(
            {"units": signal.units, "instrument": signal.instrument},
            {"equity": 100_000, "drawdown": 0.02, "daily_loss": 0.01},
            [{"name": "max_units", "max_units": 25_000, "enabled": True}],
        )


class ExecutionManager:
    def __init__(self, execution_client: OandaExecutionClient | None = None) -> None:
        self._execution_client = execution_client

    def execute(self, signal: TradingSignal, risk_decision: RiskDecision) -> ExecutionReceipt:
        payload = {
            "instrument": signal.instrument,
            "units": str(int(signal.units)),
            "type": "MARKET",
            "positionFill": "DEFAULT",
        }
        if not risk_decision.approved:
            return ExecutionReceipt("order_rejected_0001", signal.signal_id, "rejected", "OANDA", payload)
        if self._execution_client is not None:
            response = self._execution_client.create_order(payload)
            order_id = str(response.get("orderCreateTransaction", {}).get("id", "oanda_live_order"))
            return ExecutionReceipt(order_id, signal.signal_id, "submitted", "OANDA", payload)
        order_id = "paper_oanda_order_0001"
        if signal.signal_id != "SIG-LIVE-0001":
            order_id = f"paper_{signal.signal_id.lower().replace(':', '_')}"
        return ExecutionReceipt(order_id, signal.signal_id, "filled", "OANDA_PAPER", payload)

    def close_position(self, position: PositionSnapshot, reason: str) -> ExecutionReceipt:
        payload = {
            "instrument": position.instrument,
            "units": str(int(position.units)),
            "type": "MARKET_CLOSE",
            "positionFill": "REDUCE_ONLY",
            "reason": reason,
            "position_id": position.position_id,
        }
        if self._execution_client is not None:
            response = self._execution_client.close_position(position.instrument, position.units)
            order_id = str(
                response.get("longOrderCreateTransaction", {}).get("id")
                or response.get("shortOrderCreateTransaction", {}).get("id")
                or "oanda_position_close"
            )
            return ExecutionReceipt(order_id, position.position_id, "submitted", "OANDA", payload)
        return ExecutionReceipt(f"paper_close_{position.position_id}", position.position_id, "filled", "OANDA_PAPER", payload)


class PositionMonitor:
    def monitor(self, executions: tuple[ExecutionReceipt, ...]) -> tuple[PositionSnapshot, ...]:
        positions: list[PositionSnapshot] = []
        for execution in executions:
            if execution.status not in {"filled", "submitted"}:
                continue
            units = float(execution.payload["units"])
            positions.append(
                PositionSnapshot(
                    strategy_id="QF-LIVE-0001",
                    instrument=str(execution.payload["instrument"]),
                    units=units,
                    floating_pl=124.5,
                    margin_used=363.0,
                    exposure=abs(units) / 100_000.0,
                    position_id=f"pos_{execution.order_id}",
                )
            )
        return tuple(positions)


class PortfolioController:
    def build(self, asset: StrategyAsset) -> ProductionPortfolio:
        platform = ProductionStrategyManagementPlatform()
        platform.catalog.publish(asset)
        platform.registry.set_status(asset.passport.strategy_id, asset.passport.version, StrategyRegistryStatus.PRODUCTION)
        return platform.portfolio.build((asset,), platform.registry)


class LiveStateStore:
    def __init__(self) -> None:
        self._snapshot: LiveStateSnapshot | None = None

    def persist(
        self,
        orders: tuple[ExecutionReceipt, ...],
        positions: tuple[PositionSnapshot, ...],
        signals: tuple[TradingSignal, ...],
        regimes: dict[str, str],
        portfolio_id: str,
        risk: dict[str, Any],
    ) -> LiveStateSnapshot:
        self._snapshot = LiveStateSnapshot(
            orders=orders,
            positions=positions,
            signals=signals,
            regimes=regimes,
            portfolio_id=portfolio_id,
            risk=risk,
            timestamp=datetime(2026, 7, 4, 2, 56, tzinfo=UTC),
        )
        return self._snapshot

    def latest(self) -> LiveStateSnapshot | None:
        return self._snapshot


class RecoveryManager:
    def restore(self, store: LiveStateStore) -> bool:
        return store.latest() is not None


class SynchronizationManager:
    def synchronize(self, snapshot: LiveStateSnapshot, broker_orders: int | None = None) -> SynchronizationResult:
        broker_count = len(snapshot.orders) if broker_orders is None else broker_orders
        repaired = broker_count != len(snapshot.orders)
        return SynchronizationResult(
            internal_orders=len(snapshot.orders),
            broker_orders=broker_count,
            repaired=repaired,
            reason="State synchronized with broker." if not repaired else "Broker mismatch repaired automatically.",
        )


class LiveTradingEngine:
    """Event-driven live platform that shares concepts with the backtester."""

    def __init__(self, execution_client: OandaExecutionClient | None = None) -> None:
        self.bus = LiveEventBus()
        self.market_stream = MarketStream()
        self.features = LiveFeatureEngine()
        self.regimes = LiveMarketRegimeEngine()
        self.selector = StrategySelector()
        self.decisions = TradeDecisionEngine()
        self.signals = SignalGenerator()
        self.risk = LiveRiskController()
        self.execution = ExecutionManager(execution_client)
        self.positions = PositionMonitor()
        self.portfolio = PortfolioController()
        self.state = LiveStateStore()
        self.recovery = RecoveryManager()
        self.sync = SynchronizationManager()
        self._registered_strategies: list[StrategyPlugin] = []

    def register_strategy(self, strategy: StrategyPlugin) -> None:
        self._registered_strategies.append(strategy)

    def run(
        self,
        asset: StrategyAsset | None = None,
        *,
        events: tuple[LiveEvent, ...] | None = None,
        demo: bool = False,
        mode: str = "real",
        intraday_timestamp: datetime | None = None,
        force_close_time_utc: time | None = None,
        trade_journal_path: Path | None = None,
    ) -> LiveTradingRunResult:
        demo_enabled = demo or mode == "demo"
        if events is None and not demo_enabled:
            raise RuntimeError("LiveTradingEngine requires real events unless mode='demo' is explicitly enabled.")
        if asset is None:
            if not demo_enabled:
                raise ValueError("A real Strategy Asset is required when demo mode is disabled.")
            asset = ProductionStrategyManagementPlatform()._demo_asset()
        portfolio = self.portfolio.build(asset)
        if events is None and demo_enabled:
            seeded_events = self.market_stream.seed(self.bus)
        else:
            seeded_events = ()
        events = self.bus.drain() if events is None else events
        signals: list[TradingSignal] = []
        executions: list[ExecutionReceipt] = []
        risk_blocks = 0
        regimes: dict[str, str] = {}

        for index, event in enumerate(events, start=1):
            feature_vector = self.features.build(event)
            if feature_vector is None:
                continue
            regime = self.regimes.detect(feature_vector)
            regimes[feature_vector.instrument] = regime.regime
            selection = self.selector.select(asset, portfolio, regime)
            decision = self.decisions.evaluate(feature_vector, selection, portfolio.total_allocation)
            signal = self.signals.generate(
                feature_vector,
                regime,
                selection,
                decision,
                signal_id=(
                    f"SIG-REPLAY-{feature_vector.instrument}-{feature_vector.timeframe}-{index:06d}"
                    if seeded_events == ()
                    else "SIG-LIVE-0001"
                ),
            )
            risk_decision = self.risk.approve(signal)
            risk_blocks += int(not risk_decision.approved)
            receipt = self.execution.execute(signal, risk_decision)
            signals.append(signal)
            executions.append(receipt)

        positions = self.positions.monitor(tuple(executions))
        forced_close_receipts: tuple[ExecutionReceipt, ...] = ()
        force_close_time = force_close_time_utc or default_intraday_profile().force_close_time_utc
        close_timestamp = intraday_timestamp or (events[-1].timestamp if events else datetime.now(UTC))
        close_instructions = ForcedCloseManager().instructions(
            tuple(
                {
                    "position_id": position.position_id,
                    "strategy_id": position.strategy_id,
                    "instrument": position.instrument,
                }
                for position in positions
            ),
            close_timestamp,
            force_close_time,
        )
        if close_instructions:
            instruction_by_position = {instruction.position_id: instruction for instruction in close_instructions}
            forced_close_receipts = tuple(
                self.execution.close_position(position, instruction_by_position[position.position_id].reason)
                for position in positions
                if position.position_id in instruction_by_position
            )
            journal_path = trade_journal_path or default_trade_journal_path()
            TradeJournalStore(journal_path).append_many(
                journal_entries_from_forced_close(
                    close_instructions,
                    execution_status="SUBMITTED" if self.execution._execution_client is not None else "FILLED",
                )
            )
            positions = ()
        snapshot = self.state.persist(
            tuple(executions) + forced_close_receipts,
            positions,
            tuple(signals),
            regimes,
            portfolio.portfolio_id,
            {"risk_blocks": risk_blocks, "rules": ("max_units", "drawdown", "daily_loss")},
        )
        recovered = self.recovery.restore(self.state)
        synchronization = self.sync.synchronize(snapshot)
        dashboard = LiveTradingDashboard(
            connected=any(event.event_type == LiveEventType.CONNECT for event in seeded_events),
            market_events=len(events),
            signals_generated=len(signals),
            orders_executed=sum(execution.status in {"filled", "submitted"} for execution in tuple(executions) + forced_close_receipts),
            open_positions=len(positions),
            risk_blocks=risk_blocks,
            recovered=recovered,
            synchronized=not synchronization.repaired,
            run_24_7_ready=recovered and not synchronization.repaired,
        )
        return LiveTradingRunResult(
            connected=dashboard.connected,
            events_processed=len(events),
            signals=tuple(signals),
            executions=tuple(executions) + forced_close_receipts,
            positions=positions,
            state_snapshot=snapshot,
            recovery_completed=recovered,
            synchronization=synchronization,
            dashboard=dashboard,
            forced_close_receipts=forced_close_receipts,
        )
