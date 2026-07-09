from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, time
from enum import StrEnum
from pathlib import Path
from typing import Any

from quantforge.validation import StrategyAsset


class TradingStyle(StrEnum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITION = "POSITION"


class IntradaySession(StrEnum):
    ASIAN = "Asian"
    LONDON_OPEN = "London Open"
    LONDON = "London"
    LONDON_NEW_YORK_OVERLAP = "London-New York Overlap"
    NEW_YORK = "New York"
    LATE_NEW_YORK = "Late New York"
    NO_TRADING = "No Trading"


class IntradayTradingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED_RISK_LIMIT = "PAUSED (Risk Limit)"
    FINISHED_END_OF_DAY = "FINISHED (End Of Day)"
    NO_TRADING = "NO TRADING"


class MarketReadinessBand(StrEnum):
    EXCELLENT = "Excellent trading conditions"
    NORMAL = "Normal trading"
    SELECTIVE = "Trade selectively"
    NO_TRADE = "No new trades unless exceptional conditions arise"


class MarketReadinessDecision(StrEnum):
    EXCELLENT = "EXCELLENT"
    NORMAL = "NORMAL"
    SELECTIVE = "SELECTIVE"
    NO_NEW_TRADES = "NO_NEW_TRADES"


class MarketQualityRating(StrEnum):
    POOR = "Poor"
    FAIR = "Fair"
    GOOD = "Good"
    EXCELLENT = "Excellent"


class NewsEventType(StrEnum):
    INTEREST_RATE_DECISION = "Interest Rate Decision"
    CPI = "CPI"
    PPI = "PPI"
    GDP = "GDP"
    EMPLOYMENT_REPORT = "Employment Report"
    CENTRAL_BANK_SPEECH = "Central Bank Speech"
    NFP = "NFP"
    PMI = "PMI"


class TradeEligibilityStatus(StrEnum):
    ELIGIBLE = "Eligible"
    NOT_ELIGIBLE = "Not Eligible"


class IntradayTradeDecision(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"
    HOLD = "HOLD"
    NO_TRADE = "NO TRADE"


class DecisionIntelligenceTradingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    PAUSED = "PAUSED"
    NO_TRADING = "NO TRADING"
    FINISHED = "FINISHED"


@dataclass(frozen=True, slots=True)
class IntradayPolicy:
    trading_style: TradingStyle = TradingStyle.INTRADAY
    overnight_positions_allowed: bool = False
    weekend_positions_allowed: bool = False
    force_close_required: bool = True
    daily_risk_limits_required: bool = True
    session_awareness_required: bool = True


@dataclass(frozen=True, slots=True)
class DailyRiskProfile:
    max_daily_loss: float
    max_daily_drawdown: float
    max_trades_per_day: int
    max_consecutive_losses: int
    max_daily_exposure: float
    max_strategy_allocation: float
    max_currency_exposure: float


@dataclass(frozen=True, slots=True)
class IntradayStrategyProfile:
    trading_style: TradingStyle
    preferred_session: IntradaySession
    allowed_sessions: tuple[IntradaySession, ...]
    blocked_sessions: tuple[IntradaySession, ...]
    maximum_trade_duration_minutes: int
    force_close_time_utc: time
    earliest_entry_time_utc: time
    latest_entry_time_utc: time
    daily_risk_profile: DailyRiskProfile
    intraday_score: float
    session_compatibility: str


@dataclass(frozen=True, slots=True)
class IntradayPolicyDecision:
    approved: bool
    reasons: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DailyRiskState:
    realized_daily_loss: float = 0.0
    current_daily_drawdown: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    daily_exposure: float = 0.0
    strategy_allocation: float = 0.0
    currency_exposure: float = 0.0


@dataclass(frozen=True, slots=True)
class SessionPortfolio:
    session: IntradaySession
    strategy_asset_ids: tuple[str, ...]
    status: IntradayTradingStatus


@dataclass(frozen=True, slots=True)
class ForcedCloseInstruction:
    position_id: str
    strategy_id: str
    instrument: str
    reason: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class IntradayCertificationResult:
    certified: bool
    status: str
    checks: dict[str, str]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IntradayPerformanceMetrics:
    average_daily_profit: float
    winning_days: int
    losing_days: int
    average_trades_per_day: float
    average_trade_duration_minutes: float
    profit_per_trading_hour: float
    daily_expectancy: float


@dataclass(frozen=True, slots=True)
class IntradayRiskMetrics:
    maximum_daily_drawdown: float
    average_daily_drawdown: float
    daily_risk_utilization: float


@dataclass(frozen=True, slots=True)
class IntradayOperationalMetrics:
    average_daily_signals: float
    average_daily_executions: float
    average_daily_exposure: float
    average_daily_slippage: float


@dataclass(frozen=True, slots=True)
class IntradayMetrics:
    performance: IntradayPerformanceMetrics
    risk: IntradayRiskMetrics
    operational: IntradayOperationalMetrics


@dataclass(frozen=True, slots=True)
class DailyOperationsSnapshot:
    current_session: IntradaySession
    todays_pl: float
    todays_trades: int
    open_positions: int
    remaining_daily_risk: float
    daily_drawdown: float
    session_portfolio: str
    active_strategies: tuple[str, ...]
    trading_status: IntradayTradingStatus
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class DailyTradingReport:
    report_id: str
    trading_day: str
    daily_performance: dict[str, Any]
    strategy_performance: dict[str, Any]
    session_performance: dict[str, Any]
    risk_utilization: dict[str, Any]
    trade_summary: dict[str, Any]
    execution_summary: dict[str, Any]
    drift_summary: dict[str, Any]
    knowledge_updates: tuple[str, ...]
    improvement_recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TradeJournalEntry:
    event_id: str
    timestamp: datetime
    event_type: str
    strategy_id: str
    instrument: str
    position_id: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarketReadinessInputs:
    market_regime: str
    volatility: float
    spread: float
    session: IntradaySession
    available_strategies: int
    portfolio_exposure: float


@dataclass(frozen=True, slots=True)
class MarketReadinessScore:
    score: int
    band: MarketReadinessBand
    decision: MarketReadinessDecision
    factors: dict[str, int]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MarketQualityInputs:
    spread: float
    liquidity: float
    volatility: float
    price_stability: float
    session: IntradaySession
    market_structure: str


@dataclass(frozen=True, slots=True)
class MarketQualityScore:
    score: int
    rating: MarketQualityRating
    factors: dict[str, int]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScheduledNewsEvent:
    event_type: NewsEventType
    event_time: datetime
    impact: str
    instrument: str


@dataclass(frozen=True, slots=True)
class NewsFilterState:
    paused: bool
    reason: str
    next_event: ScheduledNewsEvent | None = None
    minutes_to_event: int | None = None


@dataclass(frozen=True, slots=True)
class TradeEligibilityRequest:
    strategy_active: bool
    session_allowed: bool
    opportunity_score: MarketReadinessScore
    market_quality: MarketQualityScore
    portfolio_exposure: float
    daily_risk_remaining: float
    news_state: NewsFilterState
    manual_trading_suspension: bool
    broker_healthy: bool


@dataclass(frozen=True, slots=True)
class TradeEligibilityResult:
    status: TradeEligibilityStatus
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionTraceRecord:
    timestamp: datetime
    instrument: str
    strategy_asset_id: str
    feature_vector_id: str
    market_regime: str
    opportunity_score: int
    market_quality: str
    risk_state: dict[str, Any]
    portfolio_state: dict[str, Any]
    news_state: dict[str, Any]
    final_decision: IntradayTradeDecision
    decision_confidence: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IntradayTradeDecisionResult:
    decision: IntradayTradeDecision
    confidence: float
    reason: str
    supporting_evidence: dict[str, Any]
    decision_trace: DecisionTraceRecord


@dataclass(frozen=True, slots=True)
class DailyTradingPlan:
    trading_day: str
    preferred_sessions: tuple[IntradaySession, ...]
    preferred_strategy_families: tuple[str, ...]
    daily_risk_budget: float
    capital_allocation: dict[str, float]
    expected_regimes: tuple[str, ...]
    maximum_trades: int
    trading_objectives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionTimelineEvent:
    timestamp: datetime
    stage: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class DailyDecisionJournal:
    journal_id: str
    trading_day: str
    market_summary: dict[str, Any]
    trading_opportunities: tuple[dict[str, Any], ...]
    trades_executed: tuple[dict[str, Any], ...]
    trades_skipped: tuple[dict[str, Any], ...]
    risk_summary: dict[str, Any]
    strategy_performance: dict[str, Any]
    knowledge_updates: tuple[str, ...]
    recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionQualityMetrics:
    trading_days: int
    opportunity_days: int
    no_trade_days: int
    trades_avoided: int
    average_opportunity_score: float
    average_market_quality: float
    average_decision_confidence: float
    trade_acceptance_rate: float
    trade_rejection_reasons: dict[str, int]


@dataclass(frozen=True, slots=True)
class DynamicDailyRiskBudget:
    opportunity_decision: MarketReadinessDecision
    budget: float
    policy: str


@dataclass(frozen=True, slots=True)
class DecisionIntelligenceStatus:
    status: DecisionIntelligenceTradingStatus
    reasons: tuple[str, ...]


class SessionEngine:
    def current_session(self, timestamp: datetime) -> IntradaySession:
        hour = timestamp.astimezone(UTC).hour
        if 0 <= hour < 7:
            return IntradaySession.ASIAN
        if hour == 7:
            return IntradaySession.LONDON_OPEN
        if 8 <= hour < 12:
            return IntradaySession.LONDON
        if 12 <= hour < 16:
            return IntradaySession.LONDON_NEW_YORK_OVERLAP
        if 16 <= hour < 21:
            return IntradaySession.NEW_YORK
        if 21 <= hour < 22:
            return IntradaySession.LATE_NEW_YORK
        return IntradaySession.NO_TRADING

    def trading_status(self, timestamp: datetime, force_close_time_utc: time, risk_paused: bool = False) -> IntradayTradingStatus:
        if risk_paused:
            return IntradayTradingStatus.PAUSED_RISK_LIMIT
        if _utc_time(timestamp) >= _naive_time(force_close_time_utc):
            return IntradayTradingStatus.FINISHED_END_OF_DAY
        if self.current_session(timestamp) == IntradaySession.NO_TRADING:
            return IntradayTradingStatus.NO_TRADING
        return IntradayTradingStatus.ACTIVE

    def allows_entry(self, profile: IntradayStrategyProfile, timestamp: datetime) -> bool:
        current_session = self.current_session(timestamp)
        current_time = _utc_time(timestamp)
        earliest = _naive_time(profile.earliest_entry_time_utc)
        latest = _naive_time(profile.latest_entry_time_utc)
        force_close = _naive_time(profile.force_close_time_utc)
        return (
            current_session in profile.allowed_sessions
            and current_session not in profile.blocked_sessions
            and earliest <= current_time <= latest
            and current_time < force_close
        )


class IntradayPolicyEngine:
    def evaluate(self, profile: IntradayStrategyProfile, policy: IntradayPolicy | None = None) -> IntradayPolicyDecision:
        active_policy = policy or IntradayPolicy()
        reasons: list[str] = []
        if profile.trading_style != active_policy.trading_style:
            reasons.append("Trading style must be INTRADAY.")
        if active_policy.force_close_required and profile.force_close_time_utc <= profile.latest_entry_time_utc:
            reasons.append("Force close time must be after latest entry time.")
        if active_policy.daily_risk_limits_required and not profile.daily_risk_profile:
            reasons.append("Daily risk profile is required.")
        if active_policy.session_awareness_required and not profile.allowed_sessions:
            reasons.append("Allowed sessions are required.")
        if profile.maximum_trade_duration_minutes <= 0:
            reasons.append("Maximum trade duration must be positive.")
        if profile.session_compatibility.upper() != "PASS":
            reasons.append("Session compatibility must pass.")
        return IntradayPolicyDecision(not reasons, tuple(reasons), {"trading_style": profile.trading_style.value})


class DailyRiskController:
    def evaluate_new_trade(self, profile: DailyRiskProfile, state: DailyRiskState) -> IntradayPolicyDecision:
        checks = {
            "realized_daily_loss": state.realized_daily_loss <= profile.max_daily_loss,
            "current_daily_drawdown": state.current_daily_drawdown <= profile.max_daily_drawdown,
            "trades_today": state.trades_today < profile.max_trades_per_day,
            "consecutive_losses": state.consecutive_losses < profile.max_consecutive_losses,
            "daily_exposure": state.daily_exposure <= profile.max_daily_exposure,
            "strategy_allocation": state.strategy_allocation <= profile.max_strategy_allocation,
            "currency_exposure": state.currency_exposure <= profile.max_currency_exposure,
        }
        reasons = tuple(f"{name} limit violated." for name, passed in checks.items() if not passed)
        return IntradayPolicyDecision(not reasons, reasons, {"checks": checks})


class ForcedCloseManager:
    def instructions(
        self,
        positions: tuple[dict[str, Any], ...],
        timestamp: datetime,
        force_close_time_utc: time,
    ) -> tuple[ForcedCloseInstruction, ...]:
        if _utc_time(timestamp) < _naive_time(force_close_time_utc):
            return ()
        return tuple(
            ForcedCloseInstruction(
                position_id=str(position.get("position_id", f"position-{index}")),
                strategy_id=str(position.get("strategy_id", "")),
                instrument=str(position.get("instrument", "")),
                reason="Forced end-of-day intraday close.",
                timestamp=timestamp.astimezone(UTC),
            )
            for index, position in enumerate(positions, start=1)
        )


class SessionPortfolioManager:
    def build(self, profiles: dict[str, IntradayStrategyProfile]) -> tuple[SessionPortfolio, ...]:
        portfolios: list[SessionPortfolio] = []
        sessions = [session for session in IntradaySession if session != IntradaySession.NO_TRADING]
        for session in sessions:
            strategy_ids = tuple(
                strategy_id
                for strategy_id, profile in profiles.items()
                if session in profile.allowed_sessions and session not in profile.blocked_sessions
            )
            portfolios.append(
                SessionPortfolio(
                    session=session,
                    strategy_asset_ids=strategy_ids,
                    status=IntradayTradingStatus.ACTIVE if strategy_ids else IntradayTradingStatus.NO_TRADING,
                )
            )
        return tuple(portfolios)

    def active_portfolio(
        self,
        portfolios: tuple[SessionPortfolio, ...],
        timestamp: datetime,
        session_engine: SessionEngine | None = None,
    ) -> SessionPortfolio:
        current_session = (session_engine or SessionEngine()).current_session(timestamp)
        for portfolio in portfolios:
            if portfolio.session == current_session:
                return portfolio
        return SessionPortfolio(IntradaySession.NO_TRADING, (), IntradayTradingStatus.NO_TRADING)


class IntradayCertificationEngine:
    def certify(
        self,
        asset: StrategyAsset,
        profile: IntradayStrategyProfile | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> IntradayCertificationResult:
        active_profile = profile or intraday_profile_from_strategy_definition(asset.strategy_definition)
        if active_profile is None:
            return IntradayCertificationResult(
                False,
                "FAIL",
                {"intraday_profile": "Missing"},
                ("Strategy Asset does not define an intraday profile.",),
            )
        policy_decision = IntradayPolicyEngine().evaluate(active_profile)
        metric_payload = metrics or {}
        checks = {
            "no_overnight_positions": "PASS" if metric_payload.get("overnight_positions", 0) == 0 else "FAIL",
            "trades_closed_before_cutoff": "PASS"
            if metric_payload.get("late_closes", 0) == 0
            else "FAIL",
            "session_compatibility": "PASS" if active_profile.session_compatibility.upper() == "PASS" else "FAIL",
            "daily_drawdown": "PASS"
            if float(metric_payload.get("maximum_daily_drawdown", 0.0)) <= active_profile.daily_risk_profile.max_daily_drawdown
            else "FAIL",
            "average_trade_duration": "PASS"
            if int(metric_payload.get("average_trade_duration_minutes", 0)) <= active_profile.maximum_trade_duration_minutes
            else "FAIL",
        }
        reasons = list(policy_decision.reasons)
        reasons.extend(f"{name} check failed." for name, status in checks.items() if status != "PASS")
        certified = not reasons
        return IntradayCertificationResult(certified, "PASS" if certified else "FAIL", checks, tuple(reasons))


class IntradayMetricsCalculator:
    def calculate(
        self,
        daily_results: tuple[dict[str, Any], ...],
        *,
        daily_signals: tuple[int, ...] = (),
        daily_executions: tuple[int, ...] = (),
        daily_exposure: tuple[float, ...] = (),
        daily_slippage: tuple[float, ...] = (),
    ) -> IntradayMetrics:
        profits = [float(item.get("profit", 0.0)) for item in daily_results]
        trades = [int(item.get("trades", 0)) for item in daily_results]
        durations = [float(item.get("average_trade_duration_minutes", 0.0)) for item in daily_results]
        drawdowns = [float(item.get("drawdown", 0.0)) for item in daily_results]
        trading_hours = [float(item.get("trading_hours", 0.0)) for item in daily_results]
        return IntradayMetrics(
            performance=IntradayPerformanceMetrics(
                average_daily_profit=round(_avg(profits), 2),
                winning_days=sum(1 for profit in profits if profit > 0),
                losing_days=sum(1 for profit in profits if profit < 0),
                average_trades_per_day=round(_avg(trades), 2),
                average_trade_duration_minutes=round(_avg(durations), 2),
                profit_per_trading_hour=round(sum(profits) / max(sum(trading_hours), 1.0), 2),
                daily_expectancy=round(sum(profits) / max(sum(trades), 1), 2),
            ),
            risk=IntradayRiskMetrics(
                maximum_daily_drawdown=round(max(drawdowns, default=0.0), 4),
                average_daily_drawdown=round(_avg(drawdowns), 4),
                daily_risk_utilization=round(max(drawdowns, default=0.0), 4),
            ),
            operational=IntradayOperationalMetrics(
                average_daily_signals=round(_avg(daily_signals), 2),
                average_daily_executions=round(_avg(daily_executions), 2),
                average_daily_exposure=round(_avg(daily_exposure), 4),
                average_daily_slippage=round(_avg(daily_slippage), 4),
            ),
        )


class DailyOperationsDashboardBuilder:
    def snapshot(
        self,
        profile: IntradayStrategyProfile,
        risk_state: DailyRiskState,
        portfolios: tuple[SessionPortfolio, ...],
        timestamp: datetime,
        *,
        todays_pl: float = 0.0,
        open_positions: int = 0,
        risk_paused: bool = False,
    ) -> DailyOperationsSnapshot:
        session_engine = SessionEngine()
        active_portfolio = SessionPortfolioManager().active_portfolio(portfolios, timestamp, session_engine)
        status = session_engine.trading_status(timestamp, profile.force_close_time_utc, risk_paused=risk_paused)
        remaining_daily_risk = max(profile.daily_risk_profile.max_daily_loss - risk_state.realized_daily_loss, 0.0)
        return DailyOperationsSnapshot(
            current_session=session_engine.current_session(timestamp),
            todays_pl=round(todays_pl, 2),
            todays_trades=risk_state.trades_today,
            open_positions=open_positions,
            remaining_daily_risk=round(remaining_daily_risk, 4),
            daily_drawdown=risk_state.current_daily_drawdown,
            session_portfolio=active_portfolio.session.value,
            active_strategies=active_portfolio.strategy_asset_ids,
            trading_status=status,
            timestamp=timestamp.astimezone(UTC),
        )


class DailyReportGenerator:
    def generate(
        self,
        snapshot: DailyOperationsSnapshot,
        metrics: IntradayMetrics,
        *,
        strategy_performance: dict[str, Any] | None = None,
        drift_summary: dict[str, Any] | None = None,
    ) -> DailyTradingReport:
        trading_day = snapshot.timestamp.date().isoformat()
        return DailyTradingReport(
            report_id=f"INTRADAY-DAILY-{trading_day}",
            trading_day=trading_day,
            daily_performance={
                "todays_pl": snapshot.todays_pl,
                "average_daily_profit": metrics.performance.average_daily_profit,
                "daily_expectancy": metrics.performance.daily_expectancy,
            },
            strategy_performance=strategy_performance or {},
            session_performance={
                "current_session": snapshot.current_session.value,
                "session_portfolio": snapshot.session_portfolio,
                "active_strategies": list(snapshot.active_strategies),
            },
            risk_utilization={
                "remaining_daily_risk": snapshot.remaining_daily_risk,
                "daily_drawdown": snapshot.daily_drawdown,
                "daily_risk_utilization": metrics.risk.daily_risk_utilization,
            },
            trade_summary={
                "todays_trades": snapshot.todays_trades,
                "open_positions": snapshot.open_positions,
                "average_trade_duration_minutes": metrics.performance.average_trade_duration_minutes,
            },
            execution_summary={
                "average_daily_executions": metrics.operational.average_daily_executions,
                "average_daily_slippage": metrics.operational.average_daily_slippage,
            },
            drift_summary=drift_summary or {},
            knowledge_updates=("daily_report_recorded", "intraday_metrics_available"),
            improvement_recommendations=("Prioritize sessions with positive daily expectancy.",),
        )


class DailyLearningLoop:
    def update_priorities(self, report: DailyTradingReport) -> dict[str, Any]:
        expectancy = float(report.daily_performance.get("daily_expectancy", 0.0))
        if expectancy <= 0:
            priority = "Review intraday filters and reduce low-quality entries."
        else:
            priority = "Expand research around profitable session-compatible intraday setups."
        return {
            "knowledge_updates": report.knowledge_updates,
            "research_priorities": (priority,),
            "future_campaigns": ("intraday_session_portfolio_refinement",),
        }


class TradeJournalStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: TradeJournalEntry) -> None:
        payload = self._load()
        entries = list(payload.get("entries", []))
        entries.append(
            {
                **asdict(entry),
                "timestamp": entry.timestamp.astimezone(UTC).isoformat(),
            }
        )
        payload["entries"] = entries
        self._save(payload)

    def append_many(self, entries: tuple[TradeJournalEntry, ...]) -> None:
        for entry in entries:
            self.append(entry)

    def list(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._load().get("entries", []))

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "entries": []}
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
        except OSError:
            return {"version": 1, "entries": []}
        if not raw:
            return {"version": 1, "entries": []}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            payload, _ = json.JSONDecoder().raw_decode(raw)
            return payload if isinstance(payload, dict) else {"version": 1, "entries": []}

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        try:
            tmp_path.replace(self.path)
        except OSError:
            fallback_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.fallback")
            tmp_path.replace(fallback_path)


class DailyMarketReadinessEvaluator:
    def evaluate(self, inputs: MarketReadinessInputs) -> MarketReadinessScore:
        factors = {
            "market_regime": self._regime_score(inputs.market_regime),
            "volatility": self._volatility_score(inputs.volatility),
            "spread": self._spread_score(inputs.spread),
            "session_quality": self._session_score(inputs.session),
            "strategy_availability": self._strategy_score(inputs.available_strategies),
            "portfolio_exposure": self._exposure_score(inputs.portfolio_exposure),
        }
        score = max(0, min(100, sum(factors.values())))
        band, decision = self._classify(score)
        return MarketReadinessScore(score, band, decision, factors, self._reasons(inputs, factors, decision))

    def _regime_score(self, market_regime: str) -> int:
        regime = market_regime.strip().upper().replace(" ", "_")
        if regime in {"TRENDING", "BREAKOUT", "TREND_FOLLOWING"}:
            return 20
        if regime in {"RANGING", "MEAN_REVERSION", "BALANCED"}:
            return 14
        if regime in {"VOLATILE", "CHOPPY", "NEWS_RISK"}:
            return 8
        return 10

    def _volatility_score(self, volatility: float) -> int:
        if 0.002 <= volatility <= 0.012:
            return 20
        if 0.001 <= volatility < 0.002 or 0.012 < volatility <= 0.02:
            return 12
        return 4

    def _spread_score(self, spread: float) -> int:
        if spread <= 0.00015:
            return 15
        if spread <= 0.00030:
            return 10
        if spread <= 0.00050:
            return 5
        return 0

    def _session_score(self, session: IntradaySession) -> int:
        scores = {
            IntradaySession.LONDON_OPEN: 18,
            IntradaySession.LONDON: 20,
            IntradaySession.LONDON_NEW_YORK_OVERLAP: 20,
            IntradaySession.NEW_YORK: 16,
            IntradaySession.ASIAN: 12,
            IntradaySession.LATE_NEW_YORK: 8,
            IntradaySession.NO_TRADING: 0,
        }
        return scores[session]

    def _strategy_score(self, available_strategies: int) -> int:
        if available_strategies >= 3:
            return 15
        if available_strategies >= 1:
            return 10
        return 0

    def _exposure_score(self, portfolio_exposure: float) -> int:
        if portfolio_exposure <= 0.25:
            return 10
        if portfolio_exposure <= 0.50:
            return 6
        return 2

    def _classify(self, score: int) -> tuple[MarketReadinessBand, MarketReadinessDecision]:
        if score >= 90:
            return MarketReadinessBand.EXCELLENT, MarketReadinessDecision.EXCELLENT
        if score >= 70:
            return MarketReadinessBand.NORMAL, MarketReadinessDecision.NORMAL
        if score >= 40:
            return MarketReadinessBand.SELECTIVE, MarketReadinessDecision.SELECTIVE
        return MarketReadinessBand.NO_TRADE, MarketReadinessDecision.NO_NEW_TRADES

    def _reasons(
        self,
        inputs: MarketReadinessInputs,
        factors: dict[str, int],
        decision: MarketReadinessDecision,
    ) -> tuple[str, ...]:
        reasons: list[str] = [f"Daily market readiness decision: {decision.value}."]
        if factors["market_regime"] < 14:
            reasons.append(f"Market regime is {inputs.market_regime}, reducing readiness.")
        if factors["volatility"] < 20:
            reasons.append("Volatility is outside the preferred intraday range.")
        if factors["spread"] < 10:
            reasons.append("Spread is too wide for normal intraday execution.")
        if factors["session_quality"] < 12:
            reasons.append(f"Session quality is low for {inputs.session.value}.")
        if factors["strategy_availability"] == 0:
            reasons.append("No certified intraday strategies are available.")
        if factors["portfolio_exposure"] < 10:
            reasons.append("Existing portfolio exposure is consuming daily capacity.")
        return tuple(reasons)


class MarketQualityEngine:
    def evaluate(self, inputs: MarketQualityInputs) -> MarketQualityScore:
        factors = {
            "spread": DailyMarketReadinessEvaluator()._spread_score(inputs.spread),
            "liquidity": self._liquidity_score(inputs.liquidity),
            "volatility": DailyMarketReadinessEvaluator()._volatility_score(inputs.volatility),
            "price_stability": self._price_stability_score(inputs.price_stability),
            "session": DailyMarketReadinessEvaluator()._session_score(inputs.session),
            "market_structure": self._structure_score(inputs.market_structure),
        }
        score = max(0, min(100, sum(factors.values())))
        rating = self._rating(score)
        reasons = [f"Market quality is {rating.value}."]
        if rating in {MarketQualityRating.POOR, MarketQualityRating.FAIR}:
            reasons.append("Current trading environment requires additional selectivity.")
        return MarketQualityScore(score, rating, factors, tuple(reasons))

    def _liquidity_score(self, liquidity: float) -> int:
        if liquidity >= 0.80:
            return 15
        if liquidity >= 0.60:
            return 10
        if liquidity >= 0.40:
            return 5
        return 0

    def _price_stability_score(self, price_stability: float) -> int:
        if price_stability >= 0.80:
            return 15
        if price_stability >= 0.60:
            return 10
        if price_stability >= 0.40:
            return 5
        return 0

    def _structure_score(self, market_structure: str) -> int:
        structure = market_structure.strip().upper().replace(" ", "_")
        if structure in {"CLEAN_TREND", "ORDERLY_RANGE", "BREAKOUT_STRUCTURE"}:
            return 15
        if structure in {"MIXED", "TRANSITION"}:
            return 8
        return 3

    def _rating(self, score: int) -> MarketQualityRating:
        if score >= 85:
            return MarketQualityRating.EXCELLENT
        if score >= 70:
            return MarketQualityRating.GOOD
        if score >= 45:
            return MarketQualityRating.FAIR
        return MarketQualityRating.POOR


class NewsEventFilter:
    def evaluate(
        self,
        events: tuple[ScheduledNewsEvent, ...],
        timestamp: datetime,
        *,
        pause_before_minutes: int = 30,
        cooldown_after_minutes: int = 15,
    ) -> NewsFilterState:
        current = timestamp.astimezone(UTC)
        for event in sorted(events, key=lambda item: item.event_time):
            event_time = event.event_time.astimezone(UTC)
            minutes_to_event = int((event_time - current).total_seconds() // 60)
            minutes_after_event = int((current - event_time).total_seconds() // 60)
            if 0 <= minutes_to_event <= pause_before_minutes:
                return NewsFilterState(True, f"High-impact news in {minutes_to_event} minutes.", event, minutes_to_event)
            if 0 <= minutes_after_event <= cooldown_after_minutes:
                return NewsFilterState(True, f"Cooling down after {event.event_type.value}.", event, -minutes_after_event)
        return NewsFilterState(False, "No blocking scheduled news events.")


class TradeEligibilityEngine:
    def evaluate(self, request: TradeEligibilityRequest) -> TradeEligibilityResult:
        reasons: list[str] = []
        if not request.strategy_active:
            reasons.append("Strategy is not active.")
        if not request.session_allowed:
            reasons.append("Session is not allowed.")
        if request.opportunity_score.score < 40:
            reasons.append("Opportunity score is below trading threshold.")
        if request.market_quality.rating == MarketQualityRating.POOR:
            reasons.append("Market quality is poor.")
        if request.portfolio_exposure > 0.60:
            reasons.append("Portfolio exposure is above allowed intraday capacity.")
        if request.daily_risk_remaining <= 0:
            reasons.append("No daily risk budget remains.")
        if request.news_state.paused:
            reasons.append(request.news_state.reason)
        if request.manual_trading_suspension:
            reasons.append("Manual trading suspension is active.")
        if not request.broker_healthy:
            reasons.append("Broker health check failed.")
        eligible = not reasons
        return TradeEligibilityResult(TradeEligibilityStatus.ELIGIBLE if eligible else TradeEligibilityStatus.NOT_ELIGIBLE, eligible, tuple(reasons))


class IntradayTradeDecisionEngine:
    def decide(
        self,
        *,
        instrument: str,
        strategy_asset_id: str,
        feature_vector_id: str,
        market_regime: str,
        signal: IntradayTradeDecision,
        eligibility: TradeEligibilityResult,
        opportunity_score: MarketReadinessScore,
        market_quality: MarketQualityScore,
        risk_state: DailyRiskState,
        portfolio_state: dict[str, Any],
        news_state: NewsFilterState,
        timestamp: datetime,
    ) -> IntradayTradeDecisionResult:
        if not eligibility.eligible:
            final_decision = IntradayTradeDecision.NO_TRADE
            confidence = 0.0
            reason = "; ".join(eligibility.reasons)
            reason_codes = tuple(reason.upper().replace(" ", "_").replace(".", "") for reason in eligibility.reasons)
        else:
            final_decision = signal if signal in {IntradayTradeDecision.BUY, IntradayTradeDecision.SELL, IntradayTradeDecision.EXIT} else IntradayTradeDecision.HOLD
            confidence = round(min((opportunity_score.score / 100) * (market_quality.score / 100), 0.99), 2)
            reason = "Trade decision passed decision intelligence checks."
            reason_codes = ("DECISION_INTELLIGENCE_APPROVED",)
        trace = DecisionTraceRecord(
            timestamp=timestamp.astimezone(UTC),
            instrument=instrument,
            strategy_asset_id=strategy_asset_id,
            feature_vector_id=feature_vector_id,
            market_regime=market_regime,
            opportunity_score=opportunity_score.score,
            market_quality=market_quality.rating.value,
            risk_state=asdict(risk_state),
            portfolio_state=portfolio_state,
            news_state={
                "paused": news_state.paused,
                "reason": news_state.reason,
                "minutes_to_event": news_state.minutes_to_event,
            },
            final_decision=final_decision,
            decision_confidence=confidence,
            reason_codes=reason_codes,
        )
        return IntradayTradeDecisionResult(
            decision=final_decision,
            confidence=confidence,
            reason=reason,
            supporting_evidence={
                "eligibility": eligibility.status.value,
                "opportunity_band": opportunity_score.band.value,
                "market_quality": market_quality.rating.value,
            },
            decision_trace=trace,
        )


class DynamicDailyRiskBudgetEngine:
    def allocate(self, base_daily_risk: float, opportunity_score: MarketReadinessScore) -> DynamicDailyRiskBudget:
        if opportunity_score.decision == MarketReadinessDecision.EXCELLENT:
            return DynamicDailyRiskBudget(opportunity_score.decision, base_daily_risk, "Normal Risk")
        if opportunity_score.decision == MarketReadinessDecision.NORMAL:
            return DynamicDailyRiskBudget(opportunity_score.decision, round(base_daily_risk * 0.75, 4), "Reduced Risk")
        if opportunity_score.decision == MarketReadinessDecision.SELECTIVE:
            return DynamicDailyRiskBudget(opportunity_score.decision, round(base_daily_risk * 0.35, 4), "Minimal Risk")
        return DynamicDailyRiskBudget(opportunity_score.decision, 0.0, "No New Trades")


class DailyTradingPlanGenerator:
    def generate(
        self,
        *,
        trading_day: str,
        profile: IntradayStrategyProfile,
        opportunity_score: MarketReadinessScore,
        risk_budget: DynamicDailyRiskBudget,
    ) -> DailyTradingPlan:
        return DailyTradingPlan(
            trading_day=trading_day,
            preferred_sessions=profile.allowed_sessions,
            preferred_strategy_families=("intraday_momentum", "session_breakout", "mean_reversion"),
            daily_risk_budget=risk_budget.budget,
            capital_allocation={
                session.value: round(1 / max(len(profile.allowed_sessions), 1), 4)
                for session in profile.allowed_sessions
            },
            expected_regimes=("TRENDING", "RANGING") if opportunity_score.score >= 40 else ("NO_TRADE",),
            maximum_trades=profile.daily_risk_profile.max_trades_per_day if risk_budget.budget > 0 else 0,
            trading_objectives=(
                "Trade only high-quality intraday opportunities.",
                "End the trading day with zero open positions.",
                "Preserve daily risk budget when market quality is weak.",
            ),
        )


class DecisionIntelligenceStatusEngine:
    def status(
        self,
        *,
        snapshot: DailyOperationsSnapshot,
        eligibility: TradeEligibilityResult,
        news_state: NewsFilterState,
    ) -> DecisionIntelligenceStatus:
        if snapshot.trading_status == IntradayTradingStatus.FINISHED_END_OF_DAY:
            return DecisionIntelligenceStatus(DecisionIntelligenceTradingStatus.FINISHED, ("End-of-day cutoff reached.",))
        if news_state.paused:
            return DecisionIntelligenceStatus(DecisionIntelligenceTradingStatus.NO_TRADING, (news_state.reason,))
        if not eligibility.eligible:
            return DecisionIntelligenceStatus(DecisionIntelligenceTradingStatus.PAUSED, eligibility.reasons)
        if snapshot.trading_status == IntradayTradingStatus.NO_TRADING:
            return DecisionIntelligenceStatus(DecisionIntelligenceTradingStatus.WAITING, ("Waiting for an approved trading session.",))
        return DecisionIntelligenceStatus(DecisionIntelligenceTradingStatus.ACTIVE, ("Decision intelligence allows new trade evaluation.",))


class DecisionTimelineBuilder:
    def build(
        self,
        *,
        timestamp: datetime,
        opportunity_score: MarketReadinessScore,
        market_quality: MarketQualityScore,
        eligibility: TradeEligibilityResult,
        decision: IntradayTradeDecisionResult,
        status: DecisionIntelligenceStatus,
    ) -> tuple[DecisionTimelineEvent, ...]:
        return (
            DecisionTimelineEvent(timestamp, "Daily Opportunity Engine", opportunity_score.decision.value, opportunity_score.band.value),
            DecisionTimelineEvent(timestamp, "Market Quality Engine", market_quality.rating.value, f"Score {market_quality.score}/100"),
            DecisionTimelineEvent(timestamp, "Trade Eligibility Engine", eligibility.status.value, "; ".join(eligibility.reasons) or "Eligible."),
            DecisionTimelineEvent(timestamp, "Trade Decision Engine", decision.decision.value, decision.reason),
            DecisionTimelineEvent(timestamp, "Intraday Trading Status", status.status.value, "; ".join(status.reasons)),
        )


class DailyDecisionJournalGenerator:
    def generate(
        self,
        *,
        trading_day: str,
        opportunity_score: MarketReadinessScore,
        market_quality: MarketQualityScore,
        decision: IntradayTradeDecisionResult,
        eligibility: TradeEligibilityResult,
        risk_budget: DynamicDailyRiskBudget,
    ) -> DailyDecisionJournal:
        skipped = () if eligibility.eligible else ({"decision": decision.decision.value, "reasons": list(eligibility.reasons)},)
        executed = ({"decision": decision.decision.value, "confidence": decision.confidence},) if decision.decision in {IntradayTradeDecision.BUY, IntradayTradeDecision.SELL, IntradayTradeDecision.EXIT} else ()
        return DailyDecisionJournal(
            journal_id=f"DECISION-JOURNAL-{trading_day}",
            trading_day=trading_day,
            market_summary={
                "opportunity_score": opportunity_score.score,
                "opportunity_band": opportunity_score.band.value,
                "market_quality": market_quality.rating.value,
            },
            trading_opportunities=({"score": opportunity_score.score, "decision": opportunity_score.decision.value},),
            trades_executed=executed,
            trades_skipped=skipped,
            risk_summary={"daily_risk_budget": risk_budget.budget, "risk_policy": risk_budget.policy},
            strategy_performance={"decision_confidence": decision.confidence},
            knowledge_updates=("decision_trace_recorded", "decision_quality_inputs_available"),
            recommendations=("Keep avoiding trades when decision intelligence rejects participation.",),
        )


class DecisionQualityMetricsCalculator:
    def calculate(self, decisions: tuple[IntradayTradeDecisionResult, ...]) -> DecisionQualityMetrics:
        trading_days = max(len(decisions), 1)
        accepted = [item for item in decisions if item.decision != IntradayTradeDecision.NO_TRADE]
        rejected = [item for item in decisions if item.decision == IntradayTradeDecision.NO_TRADE]
        opportunity_scores = [float(item.decision_trace.opportunity_score) for item in decisions]
        quality_scores = [
            {"Poor": 25.0, "Fair": 50.0, "Good": 75.0, "Excellent": 100.0}.get(item.decision_trace.market_quality, 0.0)
            for item in decisions
        ]
        reasons: dict[str, int] = {}
        for item in rejected:
            for reason in item.decision_trace.reason_codes:
                reasons[reason] = reasons.get(reason, 0) + 1
        return DecisionQualityMetrics(
            trading_days=trading_days,
            opportunity_days=sum(1 for score in opportunity_scores if score >= 40),
            no_trade_days=len(rejected),
            trades_avoided=len(rejected),
            average_opportunity_score=round(_avg(opportunity_scores), 2),
            average_market_quality=round(_avg(quality_scores), 2),
            average_decision_confidence=round(_avg([item.confidence for item in decisions]), 2),
            trade_acceptance_rate=round(len(accepted) / trading_days, 4),
            trade_rejection_reasons=reasons,
        )


def default_trade_journal_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / "var" / "intraday_trade_journal.json"


def journal_entries_from_forced_close(
    instructions: tuple[ForcedCloseInstruction, ...],
    *,
    execution_status: str,
) -> tuple[TradeJournalEntry, ...]:
    return tuple(
        TradeJournalEntry(
            event_id=f"forced-close-{instruction.timestamp.strftime('%Y%m%dT%H%M%S')}-{instruction.position_id}",
            timestamp=instruction.timestamp,
            event_type="FORCED_CLOSE",
            strategy_id=instruction.strategy_id,
            instrument=instruction.instrument,
            position_id=instruction.position_id,
            reason=instruction.reason,
            evidence={
                "execution_status": execution_status,
                "policy": "INTRADAY_FORCE_CLOSE",
                "overnight_positions_allowed": False,
            },
        )
        for instruction in instructions
    )


def default_intraday_profile() -> IntradayStrategyProfile:
    return IntradayStrategyProfile(
        trading_style=TradingStyle.INTRADAY,
        preferred_session=IntradaySession.LONDON,
        allowed_sessions=(
            IntradaySession.LONDON_OPEN,
            IntradaySession.LONDON,
            IntradaySession.LONDON_NEW_YORK_OVERLAP,
            IntradaySession.NEW_YORK,
        ),
        blocked_sessions=(IntradaySession.ASIAN, IntradaySession.LATE_NEW_YORK),
        maximum_trade_duration_minutes=180,
        force_close_time_utc=time(21, 45),
        earliest_entry_time_utc=time(7, 0),
        latest_entry_time_utc=time(19, 30),
        daily_risk_profile=DailyRiskProfile(
            max_daily_loss=0.02,
            max_daily_drawdown=0.03,
            max_trades_per_day=12,
            max_consecutive_losses=3,
            max_daily_exposure=0.60,
            max_strategy_allocation=0.20,
            max_currency_exposure=0.35,
        ),
        intraday_score=0.94,
        session_compatibility="PASS",
    )


def intraday_profile_from_strategy_definition(definition: dict[str, Any]) -> IntradayStrategyProfile | None:
    payload = definition.get("intraday_profile")
    if not isinstance(payload, dict):
        return None
    risk = payload.get("daily_risk_profile", {})
    if not isinstance(risk, dict):
        return None
    return IntradayStrategyProfile(
        trading_style=TradingStyle(str(payload.get("trading_style", TradingStyle.INTRADAY.value))),
        preferred_session=IntradaySession(str(payload.get("preferred_session", IntradaySession.LONDON.value))),
        allowed_sessions=tuple(IntradaySession(str(item)) for item in payload.get("allowed_sessions", ())),
        blocked_sessions=tuple(IntradaySession(str(item)) for item in payload.get("blocked_sessions", ())),
        maximum_trade_duration_minutes=int(payload.get("maximum_trade_duration_minutes", 0)),
        force_close_time_utc=_parse_time(str(payload.get("force_close_time_utc", "21:45"))),
        earliest_entry_time_utc=_parse_time(str(payload.get("earliest_entry_time_utc", "07:00"))),
        latest_entry_time_utc=_parse_time(str(payload.get("latest_entry_time_utc", "19:30"))),
        daily_risk_profile=DailyRiskProfile(
            max_daily_loss=float(risk.get("max_daily_loss", 0.0)),
            max_daily_drawdown=float(risk.get("max_daily_drawdown", 0.0)),
            max_trades_per_day=int(risk.get("max_trades_per_day", 0)),
            max_consecutive_losses=int(risk.get("max_consecutive_losses", 0)),
            max_daily_exposure=float(risk.get("max_daily_exposure", 0.0)),
            max_strategy_allocation=float(risk.get("max_strategy_allocation", 0.0)),
            max_currency_exposure=float(risk.get("max_currency_exposure", 0.0)),
        ),
        intraday_score=float(payload.get("intraday_score", 0.0)),
        session_compatibility=str(payload.get("session_compatibility", "")),
    )


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", maxsplit=1)
    return time(int(hour), int(minute))


def _utc_time(value: datetime) -> time:
    return value.astimezone(UTC).time().replace(tzinfo=None)


def _naive_time(value: time) -> time:
    return value.replace(tzinfo=None)


def _avg(values: list[float] | tuple[float, ...] | tuple[int, ...]) -> float:
    return sum(values) / len(values) if values else 0.0
