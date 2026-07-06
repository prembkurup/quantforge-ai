from dataclasses import replace
from datetime import date

from quantforge.live import (
    PortfolioIntelligenceEngine,
    PortfolioIntelligenceStatus,
    PortfolioPolicy,
    demo_portfolio_strategy_inputs,
)


def test_portfolio_intelligence_accepts_diversified_portfolio() -> None:
    snapshot = PortfolioIntelligenceEngine().analyze(
        demo_portfolio_strategy_inputs(),
        trading_day=date(2026, 7, 7),
    )

    assert snapshot.health.status == PortfolioIntelligenceStatus.READY
    assert snapshot.allocation.approved is True
    assert snapshot.acceptance.accepted is True
    assert snapshot.lifecycle.promotion_ready is True
    assert snapshot.kpis.strategy_count == 8
    assert snapshot.kpis.family_count >= 5
    assert snapshot.correlation.average_correlation <= snapshot.policy.max_average_correlation
    assert snapshot.daily_review.review_id == "PORT-REVIEW-20260707"
    assert snapshot.decision_trace.decision == "READY"


def test_portfolio_intelligence_flags_allocation_and_drift() -> None:
    strategies = demo_portfolio_strategy_inputs()
    overloaded = replace(
        strategies[0],
        target_weight=0.62,
        live_profit_factor=1.20,
        live_drawdown=0.11,
    )
    snapshot = PortfolioIntelligenceEngine().analyze(
        (overloaded, *strategies[1:]),
        policy=PortfolioPolicy(max_strategy_weight=0.20),
        trading_day=date(2026, 7, 7),
    )

    assert snapshot.health.status == PortfolioIntelligenceStatus.REBALANCE_REQUIRED
    assert snapshot.allocation.approved is False
    assert "QF-PI-001" in snapshot.drift.degraded_strategies
    assert snapshot.lifecycle.retirement_candidates == ("QF-PI-001",)
    assert snapshot.acceptance.accepted is False
    assert any("QF-PI-001" in action for action in snapshot.allocation.rebalance_actions)


def test_portfolio_intelligence_payload_serializes_status_values() -> None:
    payload = PortfolioIntelligenceEngine().analyze(demo_portfolio_strategy_inputs()).to_payload()

    assert payload["health"]["status"] == "READY"
    assert payload["lifecycle"]["stage"] == "PRODUCTION_READY"
    assert payload["decision_trace"]["timestamp"].endswith("+00:00")
