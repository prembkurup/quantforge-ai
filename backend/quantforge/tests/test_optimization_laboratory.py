from quantforge.research import (
    KnowledgeObjectType,
    OptimizationLaboratory,
    OptimizationPlanner,
    ResearchReviewBoard,
    ReviewDecision,
    RobustnessLevel,
    SearchAlgorithm,
    SearchEngine,
    StabilityAnalyzer,
)


def test_optimization_planner_targets_stability_not_max_profit() -> None:
    plan = OptimizationPlanner().plan("Trend Pullback")

    assert plan.algorithm == SearchAlgorithm.GRID
    assert plan.objective == "find_stable_parameter_regions"
    assert plan.estimated_tests == 124_000
    assert plan.parameter_ranges[0].name == "ema_fast"


def test_stability_analyzer_finds_regions_not_single_best_value() -> None:
    plan = OptimizationPlanner().plan("Trend Pullback")
    trials = SearchEngine().search(plan)

    regions = StabilityAnalyzer().find_regions(trials)

    assert len(regions) == 7
    assert regions[0].parameter_bounds["ema_fast"] == (18, 26)
    assert regions[0].parameter_bounds["ema_slow"] == (60, 90)
    assert regions[0].parameter_bounds["atr_multiplier"] == (1.8, 2.3)
    assert regions[0].robustness == RobustnessLevel.STRONG


def test_optimization_laboratory_reports_recommended_regions_and_writes_knowledge() -> None:
    lab = OptimizationLaboratory()

    report = lab.run("Trend Pullback")

    assert report.parameters_tested == 124_000
    assert len(report.stable_regions) == 7
    assert len(report.recommended_regions) == 2
    assert report.best_region.parameter_bounds["ema_fast"] == (18, 26)
    assert report.knowledge_records_written == 6
    assert report.review.decision == ReviewDecision.APPROVED
    assert lab.knowledge_engine.repository.records(KnowledgeObjectType.PARAMETER)


def test_research_review_board_rejects_unstable_or_overcomplex_outputs() -> None:
    review = ResearchReviewBoard().review(
        regions=(),
        complexity_score=95,
        diversity_score=0.2,
        knowledge_alignment=0.4,
    )

    assert review.decision == ReviewDecision.REJECTED
    assert "Strategy complexity is too high." in review.reasons
