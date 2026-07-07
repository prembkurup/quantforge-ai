from quantforge.research import (
    ExperimentResultKnowledge,
    KnowledgeEngine,
    KnowledgeOutcome,
    build_demo_knowledge_engine,
)
from quantforge.research.orchestrator import (
    AlwaysOnAutonomousResearchOrchestrator,
    AlwaysOnOrchestratorPaths,
    AlwaysOnResearchState,
    AlwaysOnResearchThresholds,
    IdleReasonCode,
    OrchestrationDecision,
    ResearchContext,
    ResearchJobType,
    ResearchOrchestrationRequest,
    ResearchOrchestrator,
)
from quantforge.research.full_history_scheduler import FullHistoryResearchScheduler, FullHistorySchedulerConfig
from datetime import UTC, datetime
import json


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
    assert plan.constraints["templates"]
    assert plan.constraints["parameter_search"]["ema_fast"] == [20, 30, 40, 50]
    assert plan.next_experiments
    assert plan.research_run is not None
    assert plan.research_run.experiment_count == 14
    assert plan.research_run.dataset.training_period == "first_18_months"
    assert plan.research_run.progress.queued == 57


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
    assert payload["research_run"]["progress"]["total"] == 57


def test_orchestrator_schedules_full_research_loop() -> None:
    orchestrator = ResearchOrchestrator(build_demo_knowledge_engine())

    run = orchestrator.run_research(
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

    assert run.research_goal == "Improve Trend Pullback"
    assert run.dataset.instruments == ("EUR_USD",)
    assert "trend_pullback" in run.templates.selected_templates
    assert "ema_pullback" in run.templates.selected_plugins
    assert run.parameters.narrowed_by_knowledge["ema_fast"].startswith("Knowledge-guided")
    assert run.jobs[-1].job_type == ResearchJobType.KNOWLEDGE_UPDATE


def test_always_on_orchestrator_records_idle_reason_when_coverage_is_healthy(tmp_path) -> None:
    state_file, planned = _completed_full_history_plan(tmp_path)
    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=_always_on_paths(tmp_path),
        thresholds=AlwaysOnResearchThresholds(min_assets_per_program=0, target_families=0, target_regimes=0),
    )

    record = orchestrator.run_once(trigger="test")
    status = orchestrator.current_status()

    assert record.state == AlwaysOnResearchState.IDLE
    assert record.idle_reason_code == IdleReasonCode.NO_WEAK_COVERAGE.value
    assert status["idle_reason"]["message"]
    assert orchestrator.idle_reasons()[0]["reason_code"] == "NO_WEAK_COVERAGE"


def test_always_on_orchestrator_launches_research_for_weak_programs(tmp_path) -> None:
    state_file, planned = _completed_full_history_plan(tmp_path)
    launched: list[str] = []

    def runner(programs) -> None:
        launched.extend(program.program_id for program in programs)

    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=_always_on_paths(tmp_path),
        thresholds=AlwaysOnResearchThresholds(max_jobs_per_pass=1),
        research_runner=runner,
    )

    record = orchestrator.run_once(trigger="test")
    status = orchestrator.current_status()

    assert record.jobs_launched == 1
    assert launched == ["RP-EUR_USD-H1"]
    assert status["state"] == "WAITING_FOR_SCHEDULE"
    assert status["idle_reason"]["reason_code"] == "WAITING_FOR_SCHEDULE"


def test_always_on_orchestrator_launches_research_for_validation_improvements(tmp_path) -> None:
    state_file, planned = _completed_full_history_plan(tmp_path)
    paths = _always_on_paths(tmp_path)
    paths.history_validation_improvements_file.write_text(
        json.dumps(
            {
                "version": 1,
                "improvements": [
                    {
                        "improvement_id": "imp_hv_EUR_USD_H1",
                        "pair": "EUR_USD",
                        "timeframe": "H1",
                        "reason_code": "LOW_WIN_RATE",
                        "research_program_id": "RP-EUR_USD-H1",
                        "status": "REQUESTED",
                    }
                ],
            }
        )
    )
    launched: list[str] = []

    def runner(programs) -> None:
        launched.extend(program.program_id for program in programs)

    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=paths,
        thresholds=AlwaysOnResearchThresholds(min_assets_per_program=0, target_families=0, target_regimes=0),
        research_runner=runner,
    )

    record = orchestrator.run_once(trigger="test")
    payload = json.loads(paths.history_validation_improvements_file.read_text())

    assert record.jobs_launched == 1
    assert launched == ["RP-EUR_USD-H1"]
    assert payload["improvements"][0]["status"] == "RESEARCHED"
    assert payload["improvements"][0]["research_run_id"] == record.run_id


def test_orchestrator_respects_max_jobs_per_cycle(tmp_path) -> None:
    state_file, planned = _completed_full_history_plan(tmp_path, pairs=("EUR_USD", "GBP_USD"), timeframes=("H1", "M15"))
    launched: list[str] = []

    def runner(programs) -> None:
        launched.extend(program.program_id for program in programs)

    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=_always_on_paths(tmp_path),
        thresholds=AlwaysOnResearchThresholds(max_jobs_per_pass=2),
        research_runner=runner,
    )

    record = orchestrator.run_once(trigger="test")

    assert record.jobs_launched == 2
    assert len(launched) == 2


def test_orchestrator_blocks_when_max_in_flight(tmp_path) -> None:
    state_file, planned = _completed_full_history_plan(tmp_path)
    paths = _always_on_paths(tmp_path)
    paths.status_file.write_text(json.dumps({"enabled": True, "jobs_in_flight": 24}))
    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=paths,
        thresholds=AlwaysOnResearchThresholds(max_jobs_in_flight=24),
    )

    record = orchestrator.run_once(trigger="test")

    assert record.state == AlwaysOnResearchState.BLOCKED
    assert record.idle_reason_code == IdleReasonCode.MAX_JOBS_IN_FLIGHT.value
    assert orchestrator.guardrails()[0]["reason_code"] == "MAX_JOBS_IN_FLIGHT"


def test_orchestrator_stop_disables_loop(tmp_path) -> None:
    state_file, planned = _completed_full_history_plan(tmp_path)
    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=_always_on_paths(tmp_path),
    )

    orchestrator.stop()
    record = orchestrator.run_once(trigger="test")

    assert record.state == AlwaysOnResearchState.STOPPED
    assert orchestrator.current_status()["enabled"] is False


def test_always_on_orchestrator_explains_no_usable_datasets(tmp_path) -> None:
    state_file, planned = _pending_full_history_plan(tmp_path)
    orchestrator = AlwaysOnAutonomousResearchOrchestrator(
        planned_jobs=planned,
        full_history_state_file=state_file,
        paths=_always_on_paths(tmp_path),
    )

    record = orchestrator.run_once(trigger="test")

    assert record.jobs_launched == 0
    assert record.idle_reason_code == IdleReasonCode.NO_USABLE_DATASETS.value


def _completed_full_history_plan(tmp_path, pairs=("EUR_USD",), timeframes=("H1",)):
    state_file = tmp_path / "full_history.json"
    scheduler = FullHistoryResearchScheduler(
        FullHistorySchedulerConfig(
            pairs=pairs,
            timeframes=timeframes,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2025, 1, 1, tzinfo=UTC),
            rolling_years=1,
        ),
        state_file,
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    planned = scheduler.plan()
    state_file.write_text(json.dumps({"completed": [job.job_id for job in planned], "failed": []}))
    return state_file, planned


def _pending_full_history_plan(tmp_path):
    state_file = tmp_path / "full_history.json"
    scheduler = FullHistoryResearchScheduler(
        FullHistorySchedulerConfig(
            pairs=("EUR_USD",),
            timeframes=("H1",),
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2025, 1, 1, tzinfo=UTC),
            rolling_years=1,
        ),
        state_file,
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    planned = scheduler.plan()
    state_file.write_text(json.dumps({"completed": [], "failed": []}))
    return state_file, planned


def _always_on_paths(tmp_path) -> AlwaysOnOrchestratorPaths:
    return AlwaysOnOrchestratorPaths(
        status_file=tmp_path / "research_orchestrator_status.json",
        runs_file=tmp_path / "research_orchestrator_runs.json",
        idle_reasons_file=tmp_path / "research_orchestrator_idle_reasons.json",
        guardrails_file=tmp_path / "research_orchestrator_guardrails.json",
        history_validation_improvements_file=tmp_path / "history_validation_improvements.json",
    )
