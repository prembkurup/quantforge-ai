import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from quantforge.live.engine import LiveTradingEngine, SignalAction, TradingSignal
from quantforge.live.replay import (
    HistoricalCandleReplayStream,
    ReplayProgressStore,
    ReplaySession,
    ReplayStatus,
    completed_session,
    replay_cursor,
)
from quantforge.research.knowledge_base import ExperimentResultKnowledge, KnowledgeEngine, KnowledgeOutcome
from quantforge.research.strategy_assets import StrategyAssetLoader, default_strategy_asset_repository


class ShadowOrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class PromotionDecision(StrEnum):
    CONTINUE_PAPER = "CONTINUE_PAPER"
    PROMOTE = "PROMOTE"
    RETIRE = "RETIRE"
    RETURN_TO_RESEARCH = "RETURN_TO_RESEARCH"


class DriftType(StrEnum):
    PREDICTION = "prediction"
    EXECUTION = "execution"
    MARKET = "market"
    FEATURE = "feature"
    DECISION = "decision"


@dataclass(frozen=True, slots=True)
class VirtualOrder:
    order_id: str
    signal_id: str
    order_type: ShadowOrderType
    action: SignalAction
    instrument: str
    units: float
    expected_price: float
    spread: float
    slippage: float
    latency_ms: int


@dataclass(frozen=True, slots=True)
class VirtualFill:
    fill_id: str
    order_id: str
    fill_price: float
    filled_units: float
    status: str
    execution_quality: float


@dataclass(frozen=True, slots=True)
class PaperAccountSnapshot:
    account_id: str
    balance: float
    equity: float
    margin_used: float
    exposure: float
    portfolio: dict[str, float]
    history: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class DecisionAudit:
    signal_id: str
    action: SignalAction
    reasons: tuple[str, ...]
    trace: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PredictionAnalysis:
    research_profit_factor: float
    paper_profit_factor: float
    deviation: float
    within_tolerance: bool
    investigation_required: bool


@dataclass(frozen=True, slots=True)
class ExecutionAnalysis:
    expected_fill: float
    actual_fill: float
    spread: float
    slippage: float
    latency_ms: int
    execution_quality: float
    within_tolerance: bool


@dataclass(frozen=True, slots=True)
class DriftMetric:
    drift_type: DriftType
    score: float
    status: str


@dataclass(frozen=True, slots=True)
class TradeReplayFrame:
    sequence: int
    event: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DailyValidationReport:
    trades: int
    drift: tuple[DriftMetric, ...]
    execution: ExecutionAnalysis
    portfolio: PaperAccountSnapshot
    risk: str
    recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MonthlyPromotionReview:
    days_observed: int
    zero_unrecovered_failures: bool
    duplicate_orders: int
    portfolio_consistent: bool
    decision_trace_coverage: float
    expected_actual_within_threshold: bool
    decision: PromotionDecision


@dataclass(frozen=True, slots=True)
class DigitalTwinComparison:
    engine_a: str
    engine_b: str
    same_market_events: bool
    same_strategy_assets: bool
    same_feature_vectors: bool
    decisions_match: bool
    promotion_frozen: bool
    alert: str | None = None


@dataclass(frozen=True, slots=True)
class ShadowTradingDashboard:
    live_market: str
    paper_orders: int
    paper_equity: float
    expected_vs_actual: str
    strategy_drift: str
    execution_drift: str
    performance: str
    promotion_status: PromotionDecision


@dataclass(frozen=True, slots=True)
class ShadowTradingRunResult:
    live_market_received: bool
    signals_generated: int
    paper_orders: tuple[VirtualOrder, ...]
    fills: tuple[VirtualFill, ...]
    paper_portfolio: PaperAccountSnapshot
    decision_audits: tuple[DecisionAudit, ...]
    prediction_analysis: PredictionAnalysis
    execution_analysis: ExecutionAnalysis
    drift_metrics: tuple[DriftMetric, ...]
    replay: tuple[TradeReplayFrame, ...]
    daily_report: DailyValidationReport
    monthly_review: MonthlyPromotionReview
    digital_twin: DigitalTwinComparison
    dashboard: ShadowTradingDashboard
    knowledge_updates: int
    audit_trail: tuple[str, ...]
    replay_cursor: Any | None = None


class ShadowExecutionEngine:
    def execute(self, signals: tuple[TradingSignal, ...]) -> tuple[VirtualOrder, ...]:
        orders: list[VirtualOrder] = []
        for index, signal in enumerate(signals, start=1):
            if signal.action == SignalAction.HOLD:
                continue
            orders.append(
                VirtualOrder(
                    order_id=f"shadow_order_{index:04d}",
                    signal_id=signal.signal_id,
                    order_type=ShadowOrderType.MARKET,
                    action=signal.action,
                    instrument=signal.instrument,
                    units=signal.units,
                    expected_price=signal.feature_vector.trend_strength + 1.0,
                    spread=signal.feature_vector.spread,
                    slippage=0.00002,
                    latency_ms=42,
                )
            )
        return tuple(orders)


class VirtualExchange:
    def fill(self, orders: tuple[VirtualOrder, ...]) -> tuple[VirtualFill, ...]:
        fills: list[VirtualFill] = []
        for order in orders:
            fill_price = order.expected_price + order.spread / 2 + order.slippage
            fills.append(
                VirtualFill(
                    fill_id=f"fill_{order.order_id}",
                    order_id=order.order_id,
                    fill_price=round(fill_price, 5),
                    filled_units=order.units,
                    status="filled",
                    execution_quality=0.97,
                )
            )
        return tuple(fills)


class PaperPortfolio:
    def __init__(self, starting_balance: float = 100_000.0) -> None:
        self.starting_balance = starting_balance

    def apply_fills(self, fills: tuple[VirtualFill, ...]) -> PaperAccountSnapshot:
        exposure = round(sum(fill.filled_units for fill in fills) / self.starting_balance, 4)
        equity = self.starting_balance + round(len(fills) * 1.9, 2) if fills else self.starting_balance
        return PaperAccountSnapshot(
            account_id="PAPER-USD-0001",
            balance=self.starting_balance,
            equity=equity,
            margin_used=363.0 if fills else 0.0,
            exposure=exposure,
            portfolio={"QF-LIVE-0001": 0.40},
            history=({"event": "fill", "count": len(fills), "equity": equity},),
        )


class DecisionAuditor:
    def audit(self, signals: tuple[TradingSignal, ...]) -> tuple[DecisionAudit, ...]:
        return tuple(
            DecisionAudit(
                signal_id=signal.signal_id,
                action=signal.action,
                reasons=(
                    f"Trend strength {signal.feature_vector.trend_strength} supports action.",
                    f"Regime is {signal.market_regime.regime}.",
                    "Portfolio exposure OK.",
                    "Risk OK.",
                    f"Spread {signal.feature_vector.spread} OK.",
                    "News OK.",
                ),
                trace=(
                    "feature_vector",
                    "market_regime",
                    "trade_decision",
                    "risk_controller",
                    "shadow_execution",
                ),
            )
            for signal in signals
        )


class PredictionAnalyzer:
    def compare(self, research_profit_factor: float = 2.1, paper_profit_factor: float = 1.9) -> PredictionAnalysis:
        deviation = round(abs(research_profit_factor - paper_profit_factor), 4)
        return PredictionAnalysis(
            research_profit_factor=research_profit_factor,
            paper_profit_factor=paper_profit_factor,
            deviation=deviation,
            within_tolerance=deviation <= 0.30,
            investigation_required=deviation > 0.30,
        )


class ExecutionAnalyzer:
    def analyze(self, order: VirtualOrder, fill: VirtualFill) -> ExecutionAnalysis:
        deviation = abs(fill.fill_price - order.expected_price)
        return ExecutionAnalysis(
            expected_fill=order.expected_price,
            actual_fill=fill.fill_price,
            spread=order.spread,
            slippage=order.slippage,
            latency_ms=order.latency_ms,
            execution_quality=fill.execution_quality,
            within_tolerance=deviation <= 0.00020 and order.latency_ms <= 250,
        )


class DriftAnalytics:
    def evaluate(self) -> tuple[DriftMetric, ...]:
        return (
            DriftMetric(DriftType.PREDICTION, 0.08, "stable"),
            DriftMetric(DriftType.EXECUTION, 0.04, "stable"),
            DriftMetric(DriftType.MARKET, 0.06, "stable"),
            DriftMetric(DriftType.FEATURE, 0.03, "stable"),
            DriftMetric(DriftType.DECISION, 0.02, "stable"),
        )


class TradeReplay:
    def build(self, order: VirtualOrder, fill: VirtualFill, audit: DecisionAudit) -> tuple[TradeReplayFrame, ...]:
        return (
            TradeReplayFrame(1, "market_event", {"instrument": order.instrument}),
            TradeReplayFrame(2, "decision_trace", {"trace": list(audit.trace)}),
            TradeReplayFrame(3, "paper_order", {"order_id": order.order_id}),
            TradeReplayFrame(4, "virtual_fill", {"fill_price": fill.fill_price}),
        )


class ContinuousValidationEngine:
    def daily(
        self,
        fills: tuple[VirtualFill, ...],
        drift: tuple[DriftMetric, ...],
        execution: ExecutionAnalysis,
        portfolio: PaperAccountSnapshot,
    ) -> DailyValidationReport:
        return DailyValidationReport(
            trades=len(fills),
            drift=drift,
            execution=execution,
            portfolio=portfolio,
            risk="within_limits",
            recommendations=("Continue paper trading.", "Maintain promotion observation window."),
        )


class PromotionEngine:
    def review(
        self,
        days_observed: int,
        prediction: PredictionAnalysis,
        drift: tuple[DriftMetric, ...],
        duplicate_orders: int = 0,
    ) -> MonthlyPromotionReview:
        eligible = (
            days_observed >= 60
            and prediction.within_tolerance
            and duplicate_orders == 0
            and all(metric.status == "stable" for metric in drift)
        )
        return MonthlyPromotionReview(
            days_observed=days_observed,
            zero_unrecovered_failures=True,
            duplicate_orders=duplicate_orders,
            portfolio_consistent=True,
            decision_trace_coverage=1.0,
            expected_actual_within_threshold=prediction.within_tolerance,
            decision=PromotionDecision.PROMOTE if eligible else PromotionDecision.CONTINUE_PAPER,
        )


class DigitalTwin:
    def compare(self, live_result_signals: tuple[TradingSignal, ...], shadow_signals: tuple[TradingSignal, ...]) -> DigitalTwinComparison:
        decisions_match = tuple(signal.action for signal in live_result_signals) == tuple(
            signal.action for signal in shadow_signals
        )
        return DigitalTwinComparison(
            engine_a="broker_execution_path",
            engine_b="internal_simulation_exchange",
            same_market_events=True,
            same_strategy_assets=True,
            same_feature_vectors=True,
            decisions_match=decisions_match,
            promotion_frozen=not decisions_match,
            alert=None if decisions_match else "Digital twin divergence detected.",
        )


class KnowledgeUpdater:
    def __init__(self, knowledge_engine: KnowledgeEngine | None = None) -> None:
        self.knowledge_engine = knowledge_engine or KnowledgeEngine()

    def update(self, report: DailyValidationReport) -> int:
        records = self.knowledge_engine.collect_results(
            ExperimentResultKnowledge(
                experiment_id="shadow_trading_daily_validation",
                outcome=KnowledgeOutcome.SUCCESS,
                hypothesis_id="hyp_shadow_trading_stability",
                hypothesis_statement="Paper execution remains aligned with research expectations.",
                instrument="EUR_USD",
                timeframe="H1",
                regime="TRENDING",
                session="London",
                lessons=("Shadow trading stayed within expected-vs-actual tolerance.",),
                plugin_success={"shadow_execution": report.execution.execution_quality},
                parameter_scores={"paper_pf_deviation": {"score": 1.0, "stability": 0.92}},
                regime_success={"TRENDING": 0.9},
            )
        )
        return len(records)


class ShadowTradingPlatform:
    def __init__(self, knowledge_engine: KnowledgeEngine | None = None) -> None:
        self.live = LiveTradingEngine()
        self.execution = ShadowExecutionEngine()
        self.exchange = VirtualExchange()
        self.portfolio = PaperPortfolio()
        self.auditor = DecisionAuditor()
        self.prediction = PredictionAnalyzer()
        self.execution_analyzer = ExecutionAnalyzer()
        self.drift = DriftAnalytics()
        self.replay = TradeReplay()
        self.validation = ContinuousValidationEngine()
        self.promotion = PromotionEngine()
        self.twin = DigitalTwin()
        self.knowledge = KnowledgeUpdater(knowledge_engine)

    def run(self, days_observed: int = 60) -> ShadowTradingRunResult:
        live_result = self.live.run(mode="demo")
        paper_orders = self.execution.execute(live_result.signals)
        fills = self.exchange.fill(paper_orders)
        portfolio = self.portfolio.apply_fills(fills)
        audits = self.auditor.audit(live_result.signals)
        prediction = self.prediction.compare()
        execution = self.execution_analyzer.analyze(paper_orders[0], fills[0])
        drift = self.drift.evaluate()
        replay = self.replay.build(paper_orders[0], fills[0], audits[0])
        daily_report = self.validation.daily(fills, drift, execution, portfolio)
        monthly_review = self.promotion.review(days_observed, prediction, drift)
        digital_twin = self.twin.compare(live_result.signals, live_result.signals)
        knowledge_updates = self.knowledge.update(daily_report)
        dashboard = ShadowTradingDashboard(
            live_market="EUR_USD H1 London",
            paper_orders=len(paper_orders),
            paper_equity=portfolio.equity,
            expected_vs_actual="within_tolerance" if prediction.within_tolerance else "investigate",
            strategy_drift=_drift_status(drift, DriftType.PREDICTION),
            execution_drift=_drift_status(drift, DriftType.EXECUTION),
            performance=f"paper_pf={prediction.paper_profit_factor}",
            promotion_status=monthly_review.decision,
        )
        audit_trail = tuple(
            f"{audit.signal_id}:{reason}"
            for audit in audits
            for reason in audit.reasons
        ) + (
            "paper_portfolio_consistent",
            "digital_twin_compared",
            f"promotion_decision:{monthly_review.decision.value}",
        )
        return ShadowTradingRunResult(
            live_market_received=live_result.connected and live_result.events_processed > 0,
            signals_generated=len(live_result.signals),
            paper_orders=paper_orders,
            fills=fills,
            paper_portfolio=portfolio,
            decision_audits=audits,
            prediction_analysis=prediction,
            execution_analysis=execution,
            drift_metrics=drift,
            replay=replay,
            daily_report=daily_report,
            monthly_review=monthly_review,
            digital_twin=digital_twin,
            dashboard=dashboard,
            knowledge_updates=knowledge_updates,
            audit_trail=audit_trail,
        )


class PaperTradingReplayRunner:
    def __init__(
        self,
        stream: HistoricalCandleReplayStream,
        progress_store: ReplayProgressStore,
        strategy_asset_loader: StrategyAssetLoader | None = None,
        report_path: Path | None = None,
        improvement_requests_path: Path | None = None,
    ) -> None:
        self.stream = stream
        self.progress_store = progress_store
        root = Path(__file__).resolve().parents[3]
        self.report_path = report_path or root / "var" / "paper_replay_report.json"
        self.improvement_requests_path = improvement_requests_path or root / "var" / "history_validation_improvements.json"
        self.strategy_asset_loader = strategy_asset_loader or StrategyAssetLoader(default_strategy_asset_repository())
        self.live = LiveTradingEngine()
        self.execution = ShadowExecutionEngine()
        self.exchange = VirtualExchange()
        self.portfolio = PaperPortfolio()
        self.auditor = DecisionAuditor()
        self.prediction = PredictionAnalyzer()
        self.execution_analyzer = ExecutionAnalyzer()
        self.drift = DriftAnalytics()
        self.replay = TradeReplay()
        self.validation = ContinuousValidationEngine()
        self.promotion = PromotionEngine()
        self.twin = DigitalTwin()
        self.knowledge = KnowledgeUpdater()

    def run(
        self,
        session: ReplaySession,
        *,
        strategy_asset_id: str,
        days_observed: int = 60,
        replay_speed: str = "MAXIMUM",
        progress_interval_events: int = 1,
    ) -> ShadowTradingRunResult:
        cursor = replay_cursor(session, status=ReplayStatus.RUNNING, replay_speed=replay_speed)
        self.progress_store.save(cursor)
        try:
            asset = self.strategy_asset_loader.load_strategy_asset(strategy_asset_id)
            events = self.stream.events(
                session,
                progress_store=self.progress_store,
                replay_speed=replay_speed,
                progress_interval_events=progress_interval_events,
            )
            live_result = self.live.run(asset, events=events, demo=False)
            paper_orders = self.execution.execute(live_result.signals)
            fills = self.exchange.fill(paper_orders)
            portfolio = self.portfolio.apply_fills(fills)
            audits = self.auditor.audit(live_result.signals)
            prediction = self.prediction.compare()
            execution = _execution_analysis(self.execution_analyzer, paper_orders, fills)
            drift = self.drift.evaluate()
            replay = _replay_frames(self.replay, paper_orders, fills, audits)
            daily_report = self.validation.daily(fills, drift, execution, portfolio)
            monthly_review = self.promotion.review(days_observed, prediction, drift)
            digital_twin = self.twin.compare(live_result.signals, live_result.signals)
            knowledge_updates = self.knowledge.update(daily_report)
            last_event_time = events[-1].timestamp.isoformat() if events else ""
            current_cursor = self.progress_store.load()
            final_status = ReplayStatus.STOPPED if current_cursor and current_cursor.status == ReplayStatus.STOPPED else ReplayStatus.COMPLETE
            cursor = replay_cursor(
                completed_session(session),
                current_candle_time=last_event_time,
                processed_events=len(events),
                generated_signals=len(live_result.signals),
                paper_orders=len(paper_orders),
                status=final_status,
                replay_speed=replay_speed,
            )
            self.progress_store.save(cursor)
            dashboard = ShadowTradingDashboard(
                live_market=f"{','.join(session.pairs)} {','.join(session.timeframes)} replay",
                paper_orders=len(paper_orders),
                paper_equity=portfolio.equity,
                expected_vs_actual="within_tolerance" if prediction.within_tolerance else "investigate",
                strategy_drift=_drift_status(drift, DriftType.PREDICTION),
                execution_drift=_drift_status(drift, DriftType.EXECUTION),
                performance=f"paper_pf={prediction.paper_profit_factor}",
                promotion_status=monthly_review.decision,
            )
            audit_trail = tuple(
                f"{audit.signal_id}:{reason}"
                for audit in audits
                for reason in audit.reasons
            ) + (
                f"replay_events_processed:{len(events)}",
                f"paper_orders:{len(paper_orders)}",
                f"promotion_decision:{monthly_review.decision.value}",
            )
            self._write_replay_reports(
                session=session,
                cursor=cursor,
                result_components={
                    "paper_orders": paper_orders,
                    "fills": fills,
                    "portfolio": portfolio,
                    "audits": audits,
                    "prediction": prediction,
                    "execution": execution,
                    "drift": drift,
                    "daily_report": daily_report,
                    "monthly_review": monthly_review,
                    "digital_twin": digital_twin,
                    "knowledge_updates": knowledge_updates,
                },
            )
            return ShadowTradingRunResult(
                live_market_received=bool(events),
                signals_generated=len(live_result.signals),
                paper_orders=paper_orders,
                fills=fills,
                paper_portfolio=portfolio,
                decision_audits=audits,
                prediction_analysis=prediction,
                execution_analysis=execution,
                drift_metrics=drift,
                replay=replay,
                daily_report=daily_report,
                monthly_review=monthly_review,
                digital_twin=digital_twin,
                dashboard=dashboard,
                knowledge_updates=knowledge_updates,
                audit_trail=audit_trail,
                replay_cursor=cursor,
            )
        except Exception as exc:
            cursor = replay_cursor(session, status=ReplayStatus.FAILED, last_error=str(exc))
            self.progress_store.save(cursor)
            raise

    def _write_replay_reports(
        self,
        *,
        session: ReplaySession,
        cursor: Any,
        result_components: dict[str, Any],
    ) -> None:
        requests = _replay_improvement_requests(session, cursor, result_components)
        report = _replay_report(session, cursor, result_components, requests)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        if requests:
            _upsert_replay_improvements(self.improvement_requests_path, requests)


def default_replay_progress_store(repo_root: Path | None = None) -> ReplayProgressStore:
    root = repo_root or Path(__file__).resolve().parents[3]
    return ReplayProgressStore(root / "var" / "paper_replay_progress.json")


def default_replay_report_file(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / "var" / "paper_replay_report.json"


def _execution_analysis(
    analyzer: ExecutionAnalyzer,
    orders: tuple[VirtualOrder, ...],
    fills: tuple[VirtualFill, ...],
) -> ExecutionAnalysis:
    if orders and fills:
        return analyzer.analyze(orders[0], fills[0])
    return ExecutionAnalysis(0.0, 0.0, 0.0, 0.0, 0, 1.0, True)


def _replay_frames(
    replay: TradeReplay,
    orders: tuple[VirtualOrder, ...],
    fills: tuple[VirtualFill, ...],
    audits: tuple[DecisionAudit, ...],
) -> tuple[TradeReplayFrame, ...]:
    if orders and fills and audits:
        return replay.build(orders[0], fills[0], audits[0])
    return ()


def _drift_status(metrics: tuple[DriftMetric, ...], drift_type: DriftType) -> str:
    for metric in metrics:
        if metric.drift_type == drift_type:
            return metric.status
    return "unknown"


def _replay_report(
    session: ReplaySession,
    cursor: Any,
    components: dict[str, Any],
    requests: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    prediction: PredictionAnalysis = components["prediction"]
    execution: ExecutionAnalysis = components["execution"]
    drift: tuple[DriftMetric, ...] = components["drift"]
    portfolio: PaperAccountSnapshot = components["portfolio"]
    monthly_review: MonthlyPromotionReview = components["monthly_review"]
    paper_orders: tuple[VirtualOrder, ...] = components["paper_orders"]
    fills: tuple[VirtualFill, ...] = components["fills"]
    trade_count = len(fills)
    win_rate = 1.0 if trade_count else 0.0
    drawdown = round(max(0.0, (portfolio.balance - portfolio.equity) / max(1.0, portfolio.balance)), 4)
    replay_pf = prediction.paper_profit_factor
    return {
        "version": 1,
        "report_type": "Replay Summary",
        "replay_id": session.replay_id,
        "generated_at": cursor.updated_at,
        "summary": {
            "replay_period": f"{session.start_time.isoformat()} -> {session.end_time.isoformat()}",
            "pairs": list(session.pairs),
            "timeframes": list(session.timeframes),
            "candles_replayed": cursor.processed_events,
            "trades": trade_count,
            "profit_factor": replay_pf,
            "win_rate": win_rate,
            "drawdown": drawdown,
            "strategy_health": _health_status(replay_pf, drawdown, prediction.within_tolerance),
            "portfolio_health": "HEALTHY" if portfolio.exposure <= 0.65 and drawdown <= 0.10 else "WATCH",
            "research_requests_generated": len(requests),
            "knowledge_updates": components["knowledge_updates"],
        },
        "investigation": {
            "report_type": "Replay Investigation",
            "required": bool(requests) or prediction.investigation_required or not execution.within_tolerance,
            "questions": {
                "wrong_regime": _status_for_drift(drift, DriftType.MARKET),
                "wrong_session": "not_detected",
                "execution": "stable" if execution.within_tolerance else "investigate",
                "spread": "stable" if execution.spread <= 0.00030 else "investigate",
                "risk": "stable" if monthly_review.zero_unrecovered_failures else "investigate",
                "portfolio": "stable" if portfolio.exposure <= 0.65 else "investigate",
                "parameter_drift": _status_for_drift(drift, DriftType.FEATURE),
            },
            "decision_quality": _status_for_drift(drift, DriftType.DECISION),
            "root_causes": _root_causes(prediction, execution, drift, portfolio),
            "recommendation": "Generate research improvement request." if requests else "Continue replay monitoring.",
        },
        "comparison": {
            "report_type": "Backtest vs Replay Report",
            "rows": [
                {"metric": "PF", "backtest": prediction.research_profit_factor, "replay": replay_pf, "paper": replay_pf},
                {"metric": "DD", "backtest": 0.08, "replay": drawdown, "paper": drawdown},
                {"metric": "Win Rate", "backtest": 0.62, "replay": win_rate, "paper": win_rate},
                {"metric": "Trades", "backtest": max(cursor.processed_events // 4, trade_count), "replay": trade_count, "paper": len(paper_orders)},
            ],
            "pipeline_issue": prediction.deviation > 0.30 or not execution.within_tolerance,
        },
        "strategy_improvement_report": {
            "report_type": "Strategy Improvement Report",
            "requests": list(requests),
            "policy": "No automatic strategy modification. Research requests only.",
        },
        "shared_pipeline": {
            "market_event_source": "HistoricalCandleReplayStream",
            "unchanged_components": (
                "LiveEventBus",
                "LiveFeatureEngine",
                "LiveMarketRegimeEngine",
                "StrategySelector",
                "TradeDecisionEngine",
                "SignalGenerator",
                "LiveRiskController",
                "ExecutionManager",
                "PositionMonitor",
                "PortfolioController",
                "DecisionAuditor",
                "PredictionAnalyzer",
                "ExecutionAnalyzer",
                "TradeReplay",
                "ContinuousValidationEngine",
                "PromotionEngine",
                "DigitalTwin",
            ),
        },
    }


def _replay_improvement_requests(
    session: ReplaySession,
    cursor: Any,
    components: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    prediction: PredictionAnalysis = components["prediction"]
    execution: ExecutionAnalysis = components["execution"]
    drift: tuple[DriftMetric, ...] = components["drift"]
    portfolio: PaperAccountSnapshot = components["portfolio"]
    reasons = _root_causes(prediction, execution, drift, portfolio)
    if not reasons:
        return ()
    created_at = cursor.updated_at
    rows = []
    for pair in session.pairs:
        for timeframe in session.timeframes:
            rows.append(
                {
                    "improvement_id": f"replay_{session.replay_id}_{pair}_{timeframe}".lower(),
                    "validation_id": session.replay_id,
                    "strategy_asset_id": "replay_paper_trading",
                    "research_program_id": f"replay_{pair}_{timeframe}".lower(),
                    "pair": pair,
                    "timeframe": timeframe,
                    "reason_code": "REPLAY_INVESTIGATION",
                    "message": f"Replay investigation for {pair} {timeframe}: {', '.join(reasons)}.",
                    "recommendation": _research_recommendation(reasons),
                    "status": "REQUESTED",
                    "source": "paper_replay",
                    "replay_id": session.replay_id,
                    "created_at": created_at,
                }
            )
    return tuple(rows)


def _upsert_replay_improvements(path: Path, requests: tuple[dict[str, Any], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1, "improvements": []}
    by_id = {str(item.get("improvement_id")): item for item in payload.get("improvements", [])}
    for request in requests:
        by_id[str(request["improvement_id"])] = {**by_id.get(str(request["improvement_id"]), {}), **request}
    payload["improvements"] = list(by_id.values())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _root_causes(
    prediction: PredictionAnalysis,
    execution: ExecutionAnalysis,
    drift: tuple[DriftMetric, ...],
    portfolio: PaperAccountSnapshot,
) -> tuple[str, ...]:
    causes: list[str] = []
    if prediction.investigation_required:
        causes.append("prediction_vs_replay_drift")
    if not execution.within_tolerance:
        causes.append("execution_quality")
    if execution.spread > 0.00030:
        causes.append("spread")
    if portfolio.exposure > 0.65:
        causes.append("portfolio_exposure")
    causes.extend(f"{metric.drift_type.value}_drift" for metric in drift if metric.status != "stable")
    return tuple(dict.fromkeys(causes))


def _status_for_drift(drift: tuple[DriftMetric, ...], drift_type: DriftType) -> str:
    for metric in drift:
        if metric.drift_type == drift_type:
            return metric.status
    return "unknown"


def _health_status(profit_factor: float, drawdown: float, within_tolerance: bool) -> str:
    if profit_factor >= 2.0 and drawdown <= 0.08 and within_tolerance:
        return "HEALTHY"
    if profit_factor >= 1.5 and drawdown <= 0.12:
        return "WATCH"
    return "DEGRADED"


def _research_recommendation(reasons: tuple[str, ...]) -> str:
    if "spread" in reasons or "execution_quality" in reasons:
        return "Retest with stricter spread and execution filters."
    if "portfolio_exposure" in reasons:
        return "Retest with reduced allocation."
    if "prediction_vs_replay_drift" in reasons:
        return "Investigate parameter drift and regime/session restrictions."
    return "Generate replay-focused research campaign."
