from quantforge.research import AutonomousResearchPipeline, DatasetSelector, ResearchGoal


def test_autonomous_pipeline_runs_one_hundred_experiments_and_publishes_assets() -> None:
    result = AutonomousResearchPipeline().execute()

    assert result.kpis.experiments_completed == 100
    assert len(result.schedule) == 100
    assert len(result.strategy_assets) == 12
    assert result.strategy_catalog_count == 12
    assert result.dashboard.autonomous is True
    assert result.kpis.candidates_generated == 284_000
    assert result.kpis.candidates_rejected == 212_000


def test_research_plan_keeps_reserved_test_period_out_of_optimization() -> None:
    goal = ResearchGoal(
        goal_id="RG-TEST",
        version="1.0",
        description="Discover robust trend strategies.",
        success_criteria=("Do not leak future data.",),
        created_at=AutonomousResearchPipeline().execute().research_goal.created_at,
    )
    dataset = DatasetSelector().select(goal)

    assert dataset.reserved_test_period == "2023"
    assert dataset.reserved_test_period not in dataset.optimization_periods


def test_autonomous_pipeline_is_reproducible_for_same_inputs() -> None:
    first = AutonomousResearchPipeline().execute()
    second = AutonomousResearchPipeline().execute()

    assert first.plan.plan_hash == second.plan.plan_hash
    assert first.reproducibility_key == second.reproducibility_key
    assert [asset.passport.strategy_id for asset in first.strategy_assets] == [
        asset.passport.strategy_id for asset in second.strategy_assets
    ]


def test_autonomous_pipeline_updates_knowledge_and_preserves_audit_trail() -> None:
    result = AutonomousResearchPipeline().execute()

    assert result.knowledge_report.records_written >= 100
    assert len(result.audit_trail) >= result.kpis.experiments_completed
    assert result.research_report.to_json_payload()["experiment_summary"]["experiments_completed"] == 100
    assert "Autonomous Research Report" in result.research_report.to_pdf_text()


def test_rejected_experiments_are_not_published_as_partial_assets() -> None:
    result = AutonomousResearchPipeline().execute()

    rejected = [item for item in result.experiment_results if item.failure_reason]
    assert rejected
    assert all(item.strategy_asset_id is None for item in rejected)
    assert result.kpis.failure_reasons == {"statistically_weak": 68, "structurally_invalid": 20}
