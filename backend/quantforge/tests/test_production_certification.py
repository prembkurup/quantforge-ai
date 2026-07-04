from quantforge.infrastructure import (
    CertificationCheck,
    CertificationDecision,
    CertificationDomain,
    CertificationScoreCalculator,
    CertificationStatus,
    DomainCertificationResult,
    ProductionApprovalManager,
    ProductionCertificationEngine,
)


def test_production_certification_authorizes_controlled_live_trading() -> None:
    result = ProductionCertificationEngine().certify()

    assert result.certified is True
    assert result.approval.authorized is True
    assert result.approval.decision == CertificationDecision.CERTIFIED
    assert result.score.overall >= result.score.threshold
    assert result.critical_findings == ()


def test_all_required_certification_domains_pass() -> None:
    result = ProductionCertificationEngine().certify()
    domain_map = {domain.domain: domain for domain in result.domains}

    assert set(domain_map) == {
        CertificationDomain.RESEARCH,
        CertificationDomain.STRATEGY,
        CertificationDomain.INFRASTRUCTURE,
        CertificationDomain.SECURITY,
        CertificationDomain.OPERATIONS,
        CertificationDomain.RISK,
        CertificationDomain.PERFORMANCE,
        CertificationDomain.GOVERNANCE,
    }
    assert all(domain.status == CertificationStatus.PASS for domain in result.domains)
    assert all(domain.passed for domain in result.domains)


def test_supporting_disaster_data_audit_and_knowledge_certifications_pass() -> None:
    result = ProductionCertificationEngine().certify()
    supporting = {domain.domain: domain for domain in result.supporting_domains}

    assert set(supporting) == {
        CertificationDomain.DISASTER_RECOVERY,
        CertificationDomain.DATA_INTEGRITY,
        CertificationDomain.AUDIT,
        CertificationDomain.KNOWLEDGE,
    }
    assert all(domain.passed for domain in result.supporting_domains)


def test_certification_dashboard_and_report_include_approval_evidence() -> None:
    result = ProductionCertificationEngine().certify()

    assert result.dashboard.production_readiness == "AUTHORIZED"
    assert result.dashboard.certification_score == result.score.overall
    assert result.dashboard.knowledge == CertificationStatus.PASS
    assert result.report.approved is True
    assert result.report.approval_decision == CertificationDecision.CERTIFIED
    assert result.report.failed_items == ()
    assert "execution_submission" in result.report.performance_benchmarks


def test_score_calculator_uses_configured_production_readiness_weights() -> None:
    result = ProductionCertificationEngine().certify()

    assert result.score.weights[CertificationDomain.RESEARCH] == 0.20
    assert result.score.weights[CertificationDomain.INFRASTRUCTURE] == 0.20
    assert result.score.weights[CertificationDomain.GOVERNANCE] == 0.05
    assert result.score.overall == 100.0


def test_approval_manager_blocks_failed_critical_domain() -> None:
    failing = DomainCertificationResult(
        domain=CertificationDomain.RISK,
        status=CertificationStatus.FAIL,
        score=0.0,
        weight=0.15,
        checks=(
            CertificationCheck(
                name="kill_switch",
                status=CertificationStatus.FAIL,
                score=0.0,
                evidence="kill switch disabled",
                critical=True,
            ),
        ),
        findings=("kill switch disabled",),
    )
    passing = tuple(
        DomainCertificationResult(
            domain=domain,
            status=CertificationStatus.PASS,
            score=1.0,
            weight=CertificationScoreCalculator.WEIGHTS[domain],
            checks=(CertificationCheck("ok", CertificationStatus.PASS, 1.0, "ok"),),
        )
        for domain in CertificationScoreCalculator.WEIGHTS
        if domain != CertificationDomain.RISK
    )
    domains = passing + (failing,)
    score = CertificationScoreCalculator().calculate(domains)
    approval = ProductionApprovalManager().decide(domains, (), score, failing.findings)

    assert score.passed is False
    assert approval.authorized is False
    assert approval.decision == CertificationDecision.REJECTED
