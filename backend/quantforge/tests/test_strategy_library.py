import pytest

from quantforge.research import (
    InstitutionalStrategyLibraryBuilder,
    InstitutionalStrategyLibraryResult,
    StrategyLibraryStatus,
)


@pytest.fixture(scope="module")
def library_result() -> InstitutionalStrategyLibraryResult:
    return InstitutionalStrategyLibraryBuilder().build()


def test_strategy_library_hits_workstream_targets(
    library_result: InstitutionalStrategyLibraryResult,
) -> None:
    assert 500_000 <= library_result.kpis.experiments_executed <= 1_000_000
    assert 500 <= library_result.kpis.validated_strategy_assets <= 2_000
    assert 50 <= library_result.kpis.production_grade_strategies <= 100
    assert library_result.successful is True


def test_strategy_library_runs_independent_research_programs(
    library_result: InstitutionalStrategyLibraryResult,
) -> None:
    assert len(library_result.programs) == 5
    assert sum(program.experiment_allocation for program in library_result.programs) == 750_000
    assert sum(program.validated_asset_target for program in library_result.programs) == 1_000
    assert sum(program.production_grade_target for program in library_result.programs) == 75
    assert all(len(program.templates) == 3 for program in library_result.programs)


def test_validated_assets_are_qualified_traceable_and_reproducible(
    library_result: InstitutionalStrategyLibraryResult,
) -> None:
    assets = library_result.validated_assets

    assert len(assets) == 1_000
    assert all(asset.validation_grade == "A" for asset in assets)
    assert all(asset.confidence >= 0.90 for asset in assets)
    assert all(asset.profit_factor >= 2.0 for asset in assets)
    assert all(asset.max_drawdown <= 0.10 for asset in assets)
    assert all(asset.decision_trace_complete for asset in assets)
    assert all(asset.strategy_passport_present for asset in assets)
    assert all(asset.reproducibility_key for asset in assets)


def test_production_grade_strategies_are_scarce_and_diversified(
    library_result: InstitutionalStrategyLibraryResult,
) -> None:
    production = library_result.production_grade_strategies

    assert len(production) == 75
    assert all(asset.production_grade for asset in production)
    assert len({asset.family for asset in production}) == 5
    assert len({asset.timeframe for asset in production}) == 3


def test_dashboard_report_and_audit_trail_are_complete(
    library_result: InstitutionalStrategyLibraryResult,
) -> None:
    assert library_result.dashboard.status == StrategyLibraryStatus.COMPLETE
    assert library_result.dashboard.validated_assets == 1_000
    assert library_result.dashboard.production_grade_strategies == 75
    assert library_result.dashboard.portfolio_readiness == "READY_FOR_PORTFOLIO_CONSTRUCTION"
    assert library_result.report.archived is True
    assert "production_grade_strategy_set_published" in library_result.audit_trail
    assert library_result.reproducibility_key
