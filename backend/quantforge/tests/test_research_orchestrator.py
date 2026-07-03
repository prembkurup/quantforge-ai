from quantforge.research import (
    ExperimentResultKnowledge,
    KnowledgeEngine,
    KnowledgeOutcome,
    build_demo_knowledge_engine,
)
from quantforge.research.orchestrator import (
    OrchestrationDecision,
    ResearchContext,
    ResearchOrchestrationRequest,
    ResearchOrchestrator,
)


def test_orchestrator_builds_knowledge_guided_research_plan() -> None:
    orchestrator = ResearchOrchestrator(build_demo_knowledge_engine())

    plan = orchestrator.plan(
        ResearchOrchestrationRequest(
            hypothesis_id="hyp_trend_pullback_london",
            hypothesis_statement="Trend pullbacks outperform breakouts during London sessions on major pairs.",
            context=ResearchContext(
                instrument="EUR_USD",
                timeframe="H1",
                market_regime="TRENDING",
                session="London",
            ),
            required_features=("trend_strength", "pullback_state"),
        )
    )

    assert plan.decision == OrchestrationDecision.RUN_EXPERIMENT
    assert "trend_strength" in plan.recommended_features
    assert "ema_pullback" in plan.recommended_plugins
    assert "TRENDING" in plan.recommended_regimes
    assert plan.constraints["avoid_plugins"] == ()
    assert plan.next_experiments


def test_orchestrator_registers_new_hypothesis_and_requests_refinement() -> None:
    orchestrator = ResearchOrchestrator(KnowledgeEngine())

    plan = orchestrator.plan(
        ResearchOrchestrationRequest(
            hypothesis_id="hyp_new",
            hypothesis_statement="A new idea needs evidence.",
            context=ResearchContext(instrument="EUR_USD", timeframe="H1", market_regime="TRENDING"),
        )
    )

    assert plan.decision == OrchestrationDecision.COLLECT_MORE_EVIDENCE
    assert plan.hypothesis_status == "proposed"
    assert orchestrator.knowledge_engine.repository.hypothesis("hyp_new") is not None


def test_orchestrator_skips_strongly_rejected_hypothesis() -> None:
    engine = KnowledgeEngine()
    engine.collect_results(
        ExperimentResultKnowledge(
            experiment_id="exp_fail",
            outcome=KnowledgeOutcome.FAILURE,
            hypothesis_id="hyp_rejected",
            hypothesis_statement="Breakouts work during Asian session.",
            plugin_success={"asian_breakout": 0.12},
        )
    )
    orchestrator = ResearchOrchestrator(engine)

    plan = orchestrator.plan(
        ResearchOrchestrationRequest(
            hypothesis_id="hyp_rejected",
            hypothesis_statement="Breakouts work during Asian session.",
            context=ResearchContext(instrument="EUR_USD", timeframe="H1", market_regime="RANGING", session="Asian"),
        )
    )

    assert plan.decision == OrchestrationDecision.SKIP_KNOWN_FAILURE
    assert plan.hypothesis_status == "rejected"


def test_orchestrator_dashboard_payload_is_json_ready() -> None:
    orchestrator = ResearchOrchestrator(build_demo_knowledge_engine())

    payload = orchestrator.dashboard_payload(
        ResearchOrchestrationRequest(
            hypothesis_id="hyp_trend_pullback_london",
            hypothesis_statement="Trend pullbacks outperform breakouts during London sessions on major pairs.",
            context=ResearchContext(instrument="EUR_USD", timeframe="H1", market_regime="TRENDING"),
        )
    )

    assert payload["decision"] == "run_experiment"
    assert payload["recommended_features"]
    assert payload["recommended_plugins"]
    assert payload["next_experiments"]
