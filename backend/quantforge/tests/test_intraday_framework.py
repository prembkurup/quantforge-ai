from dataclasses import replace
from datetime import UTC, datetime, time

from quantforge.live import (
    DailyRiskController,
    DailyRiskProfile,
    DailyRiskState,
    DailyLearningLoop,
    DailyOperationsDashboardBuilder,
    DailyReportGenerator,
    ForcedCloseManager,
    IntradayCertificationEngine,
    IntradayMetricsCalculator,
    IntradayPolicyEngine,
    IntradaySession,
    IntradayStrategyProfile,
    IntradayTradingStatus,
    SessionEngine,
    SessionPortfolioManager,
    TradingStyle,
    intraday_profile_from_strategy_definition,
)
from quantforge.validation import StrategyValidationPlatform


def intraday_profile() -> IntradayStrategyProfile:
    return IntradayStrategyProfile(
        trading_style=TradingStyle.INTRADAY,
        preferred_session=IntradaySession.LONDON,
        allowed_sessions=(IntradaySession.LONDON_OPEN, IntradaySession.LONDON, IntradaySession.LONDON_NEW_YORK_OVERLAP),
        blocked_sessions=(IntradaySession.ASIAN, IntradaySession.LATE_NEW_YORK),
        maximum_trade_duration_minutes=180,
        force_close_time_utc=time(21, 45, tzinfo=UTC),
        earliest_entry_time_utc=time(7, 0, tzinfo=UTC),
        latest_entry_time_utc=time(19, 30, tzinfo=UTC),
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


def test_intraday_policy_requires_intraday_assets_and_force_close_after_latest_entry() -> None:
    decision = IntradayPolicyEngine().evaluate(intraday_profile())

    assert decision.approved is True

    invalid = replace(
        intraday_profile(),
        trading_style=TradingStyle.SWING,
        force_close_time_utc=time(18, 0, tzinfo=UTC),
    )

    blocked = IntradayPolicyEngine().evaluate(invalid)
    assert blocked.approved is False
    assert "Trading style must be INTRADAY." in blocked.reasons
    assert "Force close time must be after latest entry time." in blocked.reasons


def test_session_engine_activates_only_allowed_entry_windows() -> None:
    engine = SessionEngine()
    profile = intraday_profile()

    assert engine.current_session(datetime(2026, 7, 6, 9, 0, tzinfo=UTC)) == IntradaySession.LONDON
    assert engine.allows_entry(profile, datetime(2026, 7, 6, 9, 0, tzinfo=UTC)) is True
    assert engine.allows_entry(profile, datetime(2026, 7, 6, 2, 0, tzinfo=UTC)) is False
    assert engine.trading_status(datetime(2026, 7, 6, 21, 50, tzinfo=UTC), profile.force_close_time_utc) == IntradayTradingStatus.FINISHED_END_OF_DAY


def test_daily_risk_controller_stops_new_trades_after_limit_breach() -> None:
    profile = intraday_profile().daily_risk_profile
    state = DailyRiskState(realized_daily_loss=0.021, trades_today=12)

    decision = DailyRiskController().evaluate_new_trade(profile, state)

    assert decision.approved is False
    assert "realized_daily_loss limit violated." in decision.reasons
    assert "trades_today limit violated." in decision.reasons


def test_forced_close_manager_generates_trade_journal_reasons_at_cutoff() -> None:
    instructions = ForcedCloseManager().instructions(
        (
            {
                "position_id": "POS-1",
                "strategy_id": "QF-INTRADAY-1",
                "instrument": "EUR_USD",
            },
        ),
        datetime(2026, 7, 6, 21, 45, tzinfo=UTC),
        time(21, 45, tzinfo=UTC),
    )

    assert len(instructions) == 1
    assert instructions[0].reason == "Forced end-of-day intraday close."


def test_session_portfolio_manager_selects_current_session_portfolio() -> None:
    manager = SessionPortfolioManager()
    portfolios = manager.build({"QF-INTRADAY-1": intraday_profile()})

    active = manager.active_portfolio(portfolios, datetime(2026, 7, 6, 12, 30, tzinfo=UTC))

    assert active.session == IntradaySession.LONDON_NEW_YORK_OVERLAP
    assert active.strategy_asset_ids == ("QF-INTRADAY-1",)


def test_intraday_certification_requires_profile_and_metrics() -> None:
    report = StrategyValidationPlatform().validate("QF-INTRADAY-1")
    asset = StrategyValidationPlatform().create_strategy_asset(report)
    profile = intraday_profile()

    result = IntradayCertificationEngine().certify(
        asset,
        profile,
        {
            "overnight_positions": 0,
            "late_closes": 0,
            "maximum_daily_drawdown": 0.02,
            "average_trade_duration_minutes": 90,
        },
    )

    assert result.certified is True
    assert result.checks["no_overnight_positions"] == "PASS"

    missing_profile = IntradayCertificationEngine().certify(asset)
    assert missing_profile.certified is False
    assert "does not define an intraday profile" in missing_profile.reasons[0]


def test_intraday_profile_can_be_loaded_from_strategy_definition() -> None:
    payload = {
        "intraday_profile": {
            "trading_style": "INTRADAY",
            "preferred_session": "London",
            "allowed_sessions": ["London", "London-New York Overlap"],
            "blocked_sessions": ["Asian"],
            "maximum_trade_duration_minutes": 120,
            "force_close_time_utc": "21:45",
            "earliest_entry_time_utc": "07:00",
            "latest_entry_time_utc": "19:30",
            "daily_risk_profile": {
                "max_daily_loss": 0.02,
                "max_daily_drawdown": 0.03,
                "max_trades_per_day": 10,
                "max_consecutive_losses": 3,
                "max_daily_exposure": 0.5,
                "max_strategy_allocation": 0.2,
                "max_currency_exposure": 0.35,
            },
            "intraday_score": 0.91,
            "session_compatibility": "PASS",
        }
    }

    profile = intraday_profile_from_strategy_definition(payload)

    assert profile is not None
    assert profile.trading_style == TradingStyle.INTRADAY
    assert IntradaySession.LONDON_NEW_YORK_OVERLAP in profile.allowed_sessions


def test_intraday_metrics_report_and_learning_loop_support_daily_operations() -> None:
    profile = intraday_profile()
    portfolios = SessionPortfolioManager().build({"QF-INTRADAY-1": profile})
    snapshot = DailyOperationsDashboardBuilder().snapshot(
        profile,
        DailyRiskState(realized_daily_loss=0.004, current_daily_drawdown=0.006, trades_today=4),
        portfolios,
        datetime(2026, 7, 6, 12, 30, tzinfo=UTC),
        todays_pl=420.50,
        open_positions=1,
    )
    metrics = IntradayMetricsCalculator().calculate(
        (
            {"profit": 420.50, "trades": 4, "average_trade_duration_minutes": 64, "drawdown": 0.006, "trading_hours": 5.5},
            {"profit": -95.10, "trades": 2, "average_trade_duration_minutes": 72, "drawdown": 0.012, "trading_hours": 3.5},
        ),
        daily_signals=(9, 5),
        daily_executions=(4, 2),
        daily_exposure=(0.18, 0.11),
        daily_slippage=(0.2, 0.3),
    )
    report = DailyReportGenerator().generate(snapshot, metrics)
    learning = DailyLearningLoop().update_priorities(report)

    assert snapshot.trading_status == IntradayTradingStatus.ACTIVE
    assert metrics.performance.winning_days == 1
    assert metrics.risk.maximum_daily_drawdown == 0.012
    assert report.report_id == "INTRADAY-DAILY-2026-07-06"
    assert "intraday_session_portfolio_refinement" in learning["future_campaigns"]
