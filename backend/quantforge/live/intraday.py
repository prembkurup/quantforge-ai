from __future__ import annotations

import json
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
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
