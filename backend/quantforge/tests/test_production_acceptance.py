import pytest

from quantforge.infrastructure import (
    AcceptanceDomain,
    AcceptanceStatus,
    CapitalStage,
    ProductionAcceptanceDecision,
    ProductionAcceptanceManager,
    ProductionAcceptanceResult,
    ProductionQualificationScoreCalculator,
)


@pytest.fixture(scope="module")
def acceptance_result() -> ProductionAcceptanceResult:
    return ProductionAcceptanceManager().accept()


def test_acceptance_approves_version_1_for_controlled_production(
    acceptance_result: ProductionAcceptanceResult,
) -> None:
    assert acceptance_result.approved is True
    assert acceptance_result.report.approved is True
    assert acceptance_result.report.decision == ProductionAcceptanceDecision.APPROVED_FOR_PRODUCTION
    assert acceptance_result.version_declared_feature_complete is True
    assert acceptance_result.score.overall >= acceptance_result.score.threshold


def test_all_acceptance_domains_pass(acceptance_result: ProductionAcceptanceResult) -> None:
    domain_map = {domain.domain: domain for domain in acceptance_result.domains}

    assert set(domain_map) == {
        AcceptanceDomain.ENGINEERING,
        AcceptanceDomain.RESEARCH,
        AcceptanceDomain.STRATEGY,
        AcceptanceDomain.RISK,
        AcceptanceDomain.OPERATIONS,
        AcceptanceDomain.INFRASTRUCTURE,
        AcceptanceDomain.SECURITY,
        AcceptanceDomain.BUSINESS,
    }
    assert all(domain.status == AcceptanceStatus.PASS for domain in domain_map.values())
    assert all(domain.passed for domain in domain_map.values())


def test_scorecard_uses_configured_acceptance_weights(
    acceptance_result: ProductionAcceptanceResult,
) -> None:
    weights = acceptance_result.score.weights

    assert weights[AcceptanceDomain.ENGINEERING] == 0.15
    assert weights[AcceptanceDomain.RESEARCH] == 0.20
    assert weights[AcceptanceDomain.STRATEGY] == 0.20
    assert weights[AcceptanceDomain.RISK] == 0.15
    assert weights[AcceptanceDomain.OPERATIONS] == 0.10
    assert weights[AcceptanceDomain.INFRASTRUCTURE] == 0.10
    assert weights[AcceptanceDomain.SECURITY] == 0.05
    assert weights[AcceptanceDomain.BUSINESS] == 0.05
    assert acceptance_result.score.overall == 100.0


def test_research_strategy_paper_trading_and_operations_evidence_is_present(
    acceptance_result: ProductionAcceptanceResult,
) -> None:
    assert acceptance_result.campaign.kpis.experiments_completed >= 100_000
    assert acceptance_result.campaign.kpis.approved_strategy_assets >= 300
    assert acceptance_result.operations.config.consecutive_days == 90
    assert acceptance_result.operations.operationally_mature is True
    assert acceptance_result.operations.reliability_kpis.duplicate_orders == 0
    assert acceptance_result.operations.broker_synchronization.unreconciled_mismatches == 0
    assert acceptance_result.certification.certified is True


def test_capital_scaling_policy_is_gradual_and_evidence_based(
    acceptance_result: ProductionAcceptanceResult,
) -> None:
    policy = acceptance_result.capital_policy

    assert policy.current_stage == CapitalStage.STAGE_A
    assert policy.gradual is True
    assert policy.evidence_based is True
    assert [stage.capital_usd for stage in policy.stages] == [100, 250, 500, 1_000]
    assert [stage.required_successful_days for stage in policy.stages] == [0, 30, 60, 90]


def test_dashboard_checklist_signoffs_and_report_are_complete(
    acceptance_result: ProductionAcceptanceResult,
) -> None:
    assert acceptance_result.dashboard.overall_production_score == acceptance_result.score.overall
    assert acceptance_result.dashboard.current_capital_stage == CapitalStage.STAGE_A
    assert acceptance_result.checklist.passed is True
    assert all(signoff.recorded for signoff in acceptance_result.signoffs)
    assert all(signoff.status == AcceptanceStatus.PASS for signoff in acceptance_result.signoffs)
    assert acceptance_result.report.archived is True
    assert len(acceptance_result.audit_trail) >= 10


def test_score_calculator_blocks_failed_domain(acceptance_result: ProductionAcceptanceResult) -> None:
    failed = tuple(
        domain
        if domain.domain != AcceptanceDomain.RISK
        else type(domain)(
            domain=domain.domain,
            status=AcceptanceStatus.FAIL,
            score=0.0,
            weight=domain.weight,
            checks=domain.checks,
            findings=("risk control failed",),
        )
        for domain in acceptance_result.domains
    )
    score = ProductionQualificationScoreCalculator().calculate(failed)

    assert score.passed is False
    assert score.overall < acceptance_result.score.overall
