from datetime import UTC, datetime

from quantforge.live import (
    RootCauseCategory,
    StrategyHealthInput,
    StrategyLifecycleAction,
    StrategyLifecycleEngine,
    StrategyLifecycleStatus,
    demo_strategy_lifecycle_inputs,
)


def test_strategy_lifecycle_scores_every_strategy_and_serializes_reports() -> None:
    payload = StrategyLifecycleEngine().analyze(
        demo_strategy_lifecycle_inputs(),
        generated_at=datetime(2026, 7, 8, tzinfo=UTC),
    ).to_payload()

    assert payload["strategy_count"] == len(demo_strategy_lifecycle_inputs())
    assert all("health_score" in strategy for strategy in payload["strategies"])
    assert payload["reports"]["daily_strategy_health"]["report_id"] == "DAILY-STRATEGY-HEALTH-20260708"
    assert payload["reports"]["weekly_lifecycle"]["need_replacement"]
    assert payload["reports"]["monthly_strategy_evolution"]["version_replacements"]
    assert payload["acceptance_criteria"]["dashboard_lifecycle_history_available"] is True
    assert payload["acceptance_criteria"]["portfolio_impact_evaluated"] is True


def test_excellent_strategy_can_receive_more_allocation() -> None:
    strategy = StrategyHealthInput(
        strategy_asset_id="QF-EXCELLENT",
        strategy_name="Excellent Trend",
        version="v1.0",
        pair="EUR_USD",
        timeframe="H1",
        family="TREND",
        allocation=0.10,
        validation_profit_factor=1.8,
        rolling_profit_factor=2.4,
        rolling_sharpe=2.2,
        rolling_expectancy=0.04,
        win_rate=0.66,
        rolling_drawdown=0.03,
        regime_match=0.97,
        opportunity_score=0.96,
        market_quality=0.96,
        execution_quality=0.98,
        slippage_pips=0.2,
        latency_ms=70,
        correlation=0.12,
        allocation_pressure=0.2,
        knowledge_confidence=0.97,
        validation_confidence=0.98,
        data_quality=1.0,
    )

    decision = StrategyLifecycleEngine().analyze((strategy,)).strategies[0]

    assert decision.status == StrategyLifecycleStatus.EXCELLENT
    assert decision.action == StrategyLifecycleAction.INCREASE_ALLOCATION
    assert decision.target_allocation > decision.current_allocation


def test_degraded_strategy_generates_root_cause_and_research_goal() -> None:
    strategy = StrategyHealthInput(
        strategy_asset_id="QF-DEGRADED",
        strategy_name="Drifted Breakout",
        version="v2.1",
        pair="GBP_USD",
        timeframe="M15",
        family="BREAKOUT",
        validation_profit_factor=1.7,
        rolling_profit_factor=0.9,
        rolling_sharpe=0.25,
        rolling_expectancy=-0.004,
        rolling_drawdown=0.19,
        regime_match=0.42,
        market_quality=0.45,
    )

    decision = StrategyLifecycleEngine().analyze((strategy,)).strategies[0]

    assert decision.status in {StrategyLifecycleStatus.DEGRADED, StrategyLifecycleStatus.CRITICAL}
    assert decision.action in {StrategyLifecycleAction.SEND_BACK_TO_RESEARCH, StrategyLifecycleAction.PAUSE}
    assert decision.research_goal is not None
    assert {cause.category for cause in decision.root_causes} >= {
        RootCauseCategory.MARKET,
        RootCauseCategory.STRATEGY,
        RootCauseCategory.RISK,
    }


def test_retirement_requires_evidence_and_replacement_support() -> None:
    strategy = StrategyHealthInput(
        strategy_asset_id="QF-RETIRE",
        strategy_name="Old Range Fade",
        version="v1.4",
        pair="USD_CHF",
        timeframe="H1",
        family="RANGE",
        validation_profit_factor=1.4,
        rolling_profit_factor=0.55,
        rolling_sharpe=-0.1,
        rolling_expectancy=-0.01,
        rolling_drawdown=0.29,
        daily_loss=0.05,
        regime_match=0.31,
        market_quality=0.32,
        execution_quality=0.62,
        data_quality=0.8,
        days_below_threshold=35,
        replacement_available=True,
    )

    decision = StrategyLifecycleEngine().analyze((strategy,)).strategies[0]

    assert decision.action == StrategyLifecycleAction.RETIRE
    assert "Health below threshold for 35 days" in decision.retirement_evidence
    assert decision.replacement_candidate is not None
    assert decision.portfolio_impact["decision"] == "RETIRE"
