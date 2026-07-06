from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from enum import StrEnum
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
