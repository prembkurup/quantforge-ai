from datetime import date

from quantforge.live import (
    EvolutionAction,
    PerformanceLearningEngine,
    demo_portfolio_decision_inputs,
    demo_trade_performance_inputs,
)


def test_performance_learning_explains_strategy_regime_session_and_feature_contribution() -> None:
    snapshot = PerformanceLearningEngine().analyze(
        demo_trade_performance_inputs(),
        demo_portfolio_decision_inputs(),
        trading_day=date(2026, 7, 7),
    )

    assert snapshot.attribution.total_profit_loss == 1900.0
    assert snapshot.attribution.strategy[0].item == "QF-PI-001"
    assert snapshot.attribution.market_regime[0].item == "Trending"
    assert snapshot.attribution.session[0].item == "London"
    assert snapshot.learning.feature_rankings[0].contribution > 0
    assert snapshot.learning.knowledge_records_written >= 20
    assert snapshot.daily_report.report_id == "LEARNING-DAILY-20260707"


def test_performance_learning_generates_research_and_evolution_recommendations() -> None:
    snapshot = PerformanceLearningEngine().analyze(
        demo_trade_performance_inputs(),
        demo_portfolio_decision_inputs(),
        trading_day=date(2026, 7, 7),
    )

    assert any(priority.theme == "mean_reversion" for priority in snapshot.research_priorities)
    assert any(priority.theme == "volatility" for priority in snapshot.research_priorities)
    assert any(item.action == EvolutionAction.INCREASE_ALLOCATION for item in snapshot.strategy_evolution)
    assert all(item.action == EvolutionAction.INCREASE_ALLOCATION for item in snapshot.portfolio_evolution)
    assert snapshot.decision_quality.trade_rejection_quality == 1.0
    assert snapshot.weekly_review.knowledge_growth == snapshot.learning.knowledge_records_written
    assert snapshot.monthly_review.knowledge_base_maturity > 0


def test_performance_learning_payload_is_serializable() -> None:
    payload = PerformanceLearningEngine().analyze(
        demo_trade_performance_inputs(),
        demo_portfolio_decision_inputs(),
    ).to_payload()

    assert payload["strategy_evolution"][0]["action"] in {
        "INCREASE_ALLOCATION",
        "MAINTAIN",
        "REOPTIMIZE",
    }
    assert payload["daily_report"]["knowledge_updates"]
    assert payload["timestamp"].endswith("+00:00")
