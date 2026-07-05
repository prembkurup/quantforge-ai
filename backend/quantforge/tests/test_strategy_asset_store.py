from quantforge.research.strategy_assets import (
    ApprovedStrategyAssetStore,
    StrategyAssetLoader,
    StrategyAssetRepository,
    StrategyLibraryLoader,
)
from quantforge.validation import StrategyValidationPlatform


def test_approved_strategy_asset_store_persists_and_loads_real_asset(tmp_path) -> None:
    repository = StrategyAssetRepository(tmp_path / "approved_strategy_assets.json")
    validation = StrategyValidationPlatform()
    asset = validation.create_strategy_asset(validation.validate("QF-REAL-0001"))

    stored = ApprovedStrategyAssetStore(repository).publish(
        asset,
        source_workflow_id="workflow-1",
        source_experiment_id="experiment-1",
        source_job_id="job-1",
    )

    assert stored.strategy_asset_id == "QF-REAL-0001"
    assert repository.get("QF-REAL-0001").source_workflow_id == "workflow-1"

    loaded = StrategyAssetLoader(repository).load_strategy_asset("QF-REAL-0001")
    assert loaded.passport.strategy_id == "QF-REAL-0001"
    assert loaded.validation_report.deployment_decision.value == "APPROVED"


def test_strategy_library_loader_uses_persisted_approved_assets(tmp_path) -> None:
    repository = StrategyAssetRepository(tmp_path / "approved_strategy_assets.json")
    validation = StrategyValidationPlatform()
    asset = validation.create_strategy_asset(validation.validate("QF-REAL-0002"))
    ApprovedStrategyAssetStore(repository).publish(
        asset,
        source_workflow_id="workflow-2",
        source_experiment_id="experiment-2",
    )

    library = StrategyLibraryLoader(repository).load()

    assert library.dashboard.status.value == "COMPLETE"
    assert library.kpis.production_grade_strategies == 1
    assert library.production_grade_strategies[0].asset_id == "QF-REAL-0002"
    assert library.production_grade_strategies[0].demo_mode is False
    assert library.production_grade_strategies[0].source_experiment_id == "experiment-2"
