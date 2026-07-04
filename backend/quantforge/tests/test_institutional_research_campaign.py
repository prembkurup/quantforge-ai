import pytest

from quantforge.research import InstitutionalResearchCampaign, InstitutionalResearchCampaignResult


@pytest.fixture(scope="module")
def campaign_result() -> InstitutionalResearchCampaignResult:
    return InstitutionalResearchCampaign().execute()


def test_campaign_executes_institutional_research_targets(campaign_result: InstitutionalResearchCampaignResult) -> None:
    assert campaign_result.kpis.experiments_completed >= 100_000
    assert campaign_result.kpis.candidate_strategies >= 1_000_000
    assert campaign_result.kpis.optimized_strategies >= 100_000
    assert campaign_result.kpis.validated_strategies >= 5_000
    assert 200 <= campaign_result.kpis.approved_strategy_assets <= 500
    assert 20 <= campaign_result.kpis.production_candidates <= 50


def test_campaign_runs_five_independent_research_programs(campaign_result: InstitutionalResearchCampaignResult) -> None:
    programs = campaign_result.programs

    assert len(programs) == 5
    assert {program.program.family.value for program in programs} == {
        "Trend Following",
        "Mean Reversion",
        "Breakout",
        "Momentum",
        "Volatility",
    }
    assert all(len(program.program.templates) == 3 for program in programs)
    assert all(program.reproducibility_key for program in programs)


def test_strategy_assets_are_ranked_traceable_and_validated(campaign_result: InstitutionalResearchCampaignResult) -> None:
    ranked = campaign_result.ranking.ranked_strategy_assets

    assert len(ranked) == campaign_result.kpis.approved_strategy_assets
    assert all(asset["validation"] == "PASS" for asset in ranked)
    assert all(asset["traceable"] and asset["reproducible"] for asset in ranked)
    assert all(asset["profit_factor"] >= campaign_result.quality_requirements.profit_factor_min for asset in ranked)
    assert all(asset["max_drawdown"] <= campaign_result.quality_requirements.max_drawdown_max for asset in ranked)


def test_portfolio_construction_diversifies_families_timeframes_and_instruments(
    campaign_result: InstitutionalResearchCampaignResult,
) -> None:
    portfolio = campaign_result.portfolio

    assert portfolio.robust is True
    assert len(portfolio.strategy_assets) == 24
    assert len(portfolio.families) >= 5
    assert portfolio.timeframes == ("M15", "H1", "H4")
    assert len(portfolio.instruments) >= 8
    assert portfolio.average_correlation < 0.40


def test_campaign_reports_dashboard_and_knowledge_growth_are_generated(
    campaign_result: InstitutionalResearchCampaignResult,
) -> None:
    assert campaign_result.dashboard.campaign_progress == "COMPLETE"
    assert campaign_result.dashboard.knowledge_base_growth == campaign_result.kpis.knowledge_records_written
    assert campaign_result.daily_report.archived is True
    assert campaign_result.weekly_review.archived is True
    assert campaign_result.monthly_review.archived is True
    assert campaign_result.kpis.knowledge_records_written > campaign_result.kpis.experiments_completed


def test_campaign_is_autonomous_auditable_and_reproducible(campaign_result: InstitutionalResearchCampaignResult) -> None:
    assert campaign_result.autonomous is True
    assert campaign_result.reproducibility_key
    assert len(campaign_result.audit_trail) >= 40
    assert "campaign_ranking_completed" in campaign_result.audit_trail
    assert "portfolio_construction_completed" in campaign_result.audit_trail
