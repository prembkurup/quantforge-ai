from quantforge.live import (
    DigitalTwin,
    DriftType,
    LiveFeatureVector,
    MarketRegimeSnapshot,
    PredictionAnalyzer,
    PromotionDecision,
    SignalAction,
    ShadowTradingPlatform,
    TradingSignal,
)


def test_shadow_trading_runs_paper_portfolio_and_generates_reports() -> None:
    result = ShadowTradingPlatform().run()

    assert result.live_market_received is True
    assert result.signals_generated == 1
    assert len(result.paper_orders) == 1
    assert result.paper_portfolio.account_id == "PAPER-USD-0001"
    assert result.paper_portfolio.balance == 100_000.0
    assert result.daily_report.trades == 1
    assert result.monthly_review.decision == PromotionDecision.PROMOTE


def test_decision_trace_exists_for_all_shadow_trades() -> None:
    result = ShadowTradingPlatform().run()

    assert result.monthly_review.decision_trace_coverage == 1.0
    assert len(result.decision_audits) == result.signals_generated
    assert all(audit.trace for audit in result.decision_audits)
    assert any("Risk OK" in reason for audit in result.decision_audits for reason in audit.reasons)


def test_expected_vs_actual_and_execution_quality_are_within_thresholds() -> None:
    result = ShadowTradingPlatform().run()

    assert result.prediction_analysis.research_profit_factor == 2.1
    assert result.prediction_analysis.paper_profit_factor == 1.9
    assert result.prediction_analysis.within_tolerance is True
    assert result.prediction_analysis.investigation_required is False
    assert result.execution_analysis.within_tolerance is True
    assert result.execution_analysis.latency_ms < 250


def test_drift_analytics_and_digital_twin_guard_promotion() -> None:
    result = ShadowTradingPlatform().run()

    assert {metric.drift_type for metric in result.drift_metrics} == {
        DriftType.PREDICTION,
        DriftType.EXECUTION,
        DriftType.MARKET,
        DriftType.FEATURE,
        DriftType.DECISION,
    }
    assert result.digital_twin.decisions_match is True
    assert result.digital_twin.promotion_frozen is False
    assert result.monthly_review.zero_unrecovered_failures is True
    assert result.monthly_review.duplicate_orders == 0
    assert result.monthly_review.portfolio_consistent is True


def test_digital_twin_freezes_promotion_on_divergence() -> None:
    feature = LiveFeatureVector("EUR_USD", "H1", 0.84, True, 0.00012, "London")
    regime = MarketRegimeSnapshot("TRENDING", 0.91)
    buy = TradingSignal("a", "strategy", SignalAction.BUY, "EUR_USD", 10_000, "buy", feature, regime)
    hold = TradingSignal("b", "strategy", SignalAction.HOLD, "EUR_USD", 0, "hold", feature, regime)

    comparison = DigitalTwin().compare((buy,), (hold,))
    assert comparison.decisions_match is False
    assert comparison.promotion_frozen is True
    assert comparison.alert == "Digital twin divergence detected."


def test_prediction_analyzer_flags_large_deviation() -> None:
    analysis = PredictionAnalyzer().compare(research_profit_factor=2.3, paper_profit_factor=0.9)

    assert analysis.within_tolerance is False
    assert analysis.investigation_required is True
