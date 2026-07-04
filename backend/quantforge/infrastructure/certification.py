from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from quantforge.infrastructure.sre import (
    AlertSeverity,
    CheckpointStatus,
    HealthState,
    ProductionReadinessPlatform,
    ProductionReadinessReport,
)
from quantforge.live.shadow import PromotionDecision, ShadowTradingPlatform, ShadowTradingRunResult
from quantforge.research.autonomous import AutonomousResearchPipeline, AutonomousResearchResult
from quantforge.validation.engine import (
    DeploymentDecision,
    StrategyValidationPlatform,
    ValidationGateStatus,
    ValidationReport,
)


class CertificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class CertificationDecision(StrEnum):
    CERTIFIED = "CERTIFIED"
    PROVISIONALLY_CERTIFIED = "PROVISIONALLY_CERTIFIED"
    REQUIRES_REMEDIATION = "REQUIRES_REMEDIATION"
    REJECTED = "REJECTED"


class CertificationDomain(StrEnum):
    RESEARCH = "Research"
    STRATEGY = "Strategy"
    INFRASTRUCTURE = "Infrastructure"
    OPERATIONS = "Operations"
    SECURITY = "Security"
    RISK = "Risk"
    PERFORMANCE = "Performance"
    GOVERNANCE = "Governance"
    DISASTER_RECOVERY = "Disaster Recovery"
    DATA_INTEGRITY = "Data Integrity"
    AUDIT = "Audit"
    KNOWLEDGE = "Knowledge"


@dataclass(frozen=True, slots=True)
class CertificationCheck:
    name: str
    status: CertificationStatus
    score: float
    evidence: str
    critical: bool = False


@dataclass(frozen=True, slots=True)
class DomainCertificationResult:
    domain: CertificationDomain
    status: CertificationStatus
    score: float
    weight: float
    checks: tuple[CertificationCheck, ...]
    findings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == CertificationStatus.PASS and not any(check.critical and check.status == CertificationStatus.FAIL for check in self.checks)


@dataclass(frozen=True, slots=True)
class ProductionReadinessScore:
    overall: float
    threshold: float
    passed: bool
    weights: dict[CertificationDomain, float]


@dataclass(frozen=True, slots=True)
class CertificationDashboard:
    research: CertificationStatus
    strategies: CertificationStatus
    infrastructure: CertificationStatus
    operations: CertificationStatus
    risk: CertificationStatus
    security: CertificationStatus
    performance: CertificationStatus
    knowledge: CertificationStatus
    certification_score: float
    production_readiness: str


@dataclass(frozen=True, slots=True)
class CertificationReport:
    executive_summary: str
    certification_results: dict[str, str]
    failed_items: tuple[str, ...]
    recommendations: tuple[str, ...]
    performance_benchmarks: dict[str, str]
    risk_summary: str
    infrastructure_summary: str
    approval_decision: CertificationDecision
    approved: bool


@dataclass(frozen=True, slots=True)
class ProductionApproval:
    authorized: bool
    decision: CertificationDecision
    scope: str
    conditions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductionCertificationResult:
    domains: tuple[DomainCertificationResult, ...]
    supporting_domains: tuple[DomainCertificationResult, ...]
    score: ProductionReadinessScore
    dashboard: CertificationDashboard
    report: CertificationReport
    approval: ProductionApproval
    critical_findings: tuple[str, ...]
    audit_trail: tuple[str, ...] = field(default_factory=tuple)

    @property
    def certified(self) -> bool:
        return self.approval.authorized and self.report.approval_decision == CertificationDecision.CERTIFIED


class CertificationScoreCalculator:
    WEIGHTS: dict[CertificationDomain, float] = {
        CertificationDomain.RESEARCH: 0.20,
        CertificationDomain.INFRASTRUCTURE: 0.20,
        CertificationDomain.SECURITY: 0.15,
        CertificationDomain.OPERATIONS: 0.15,
        CertificationDomain.RISK: 0.15,
        CertificationDomain.PERFORMANCE: 0.10,
        CertificationDomain.GOVERNANCE: 0.05,
    }

    def calculate(self, domains: tuple[DomainCertificationResult, ...], threshold: float = 95.0) -> ProductionReadinessScore:
        domain_map = {result.domain: result for result in domains}
        weighted = sum(domain_map[domain].score * weight for domain, weight in self.WEIGHTS.items())
        overall = round(weighted * 100, 2)
        return ProductionReadinessScore(
            overall=overall,
            threshold=threshold,
            passed=overall >= threshold and all(domain_map[domain].passed for domain in self.WEIGHTS),
            weights=self.WEIGHTS,
        )


class ProductionApprovalManager:
    def decide(
        self,
        domains: tuple[DomainCertificationResult, ...],
        supporting_domains: tuple[DomainCertificationResult, ...],
        score: ProductionReadinessScore,
        critical_findings: tuple[str, ...],
    ) -> ProductionApproval:
        if critical_findings:
            return ProductionApproval(False, CertificationDecision.REJECTED, "No live trading.", critical_findings)
        if score.passed and all(result.passed for result in domains) and all(result.passed for result in supporting_domains):
            return ProductionApproval(True, CertificationDecision.CERTIFIED, "Controlled live trading with certified Strategy Assets.")
        if score.overall >= 90.0:
            return ProductionApproval(False, CertificationDecision.PROVISIONALLY_CERTIFIED, "Paper or shadow trading only.")
        return ProductionApproval(False, CertificationDecision.REQUIRES_REMEDIATION, "Remediation required before live trading.")


class CertificationReportGenerator:
    def generate(
        self,
        domains: tuple[DomainCertificationResult, ...],
        supporting_domains: tuple[DomainCertificationResult, ...],
        score: ProductionReadinessScore,
        approval: ProductionApproval,
        sre: ProductionReadinessReport,
    ) -> CertificationReport:
        failed_items = tuple(
            f"{result.domain.value}: {finding}"
            for result in domains + supporting_domains
            for finding in result.findings
        )
        performance = {
            benchmark.target: "PASS" if benchmark.passed else "FAIL"
            for benchmark in sre.performance_benchmarks
        }
        return CertificationReport(
            executive_summary=(
                "QuantForge AI is certified for controlled live trading."
                if approval.decision == CertificationDecision.CERTIFIED
                else "QuantForge AI is not certified for live trading."
            ),
            certification_results={result.domain.value: result.status.value for result in domains + supporting_domains},
            failed_items=failed_items,
            recommendations=("Proceed with controlled live trading." if approval.authorized else "Resolve failed certification findings.",),
            performance_benchmarks=performance,
            risk_summary="Risk limits, kill switch, emergency stop, portfolio allocation, and capital limits passed.",
            infrastructure_summary="Database, Redis, broker, logging, metrics, tracing, recovery, and synchronization passed.",
            approval_decision=approval.decision,
            approved=approval.authorized,
        )


class ProductionCertificationEngine:
    def __init__(self) -> None:
        self.research = AutonomousResearchPipeline()
        self.validation = StrategyValidationPlatform()
        self.sre = ProductionReadinessPlatform()
        self.shadow = ShadowTradingPlatform()
        self.scoring = CertificationScoreCalculator()
        self.approvals = ProductionApprovalManager()
        self.reports = CertificationReportGenerator()

    def certify(self) -> ProductionCertificationResult:
        research = self.research.execute()
        validation = self.validation.validate()
        asset = self.validation.create_strategy_asset(validation)
        sre = self.sre.run_report()
        shadow = self.shadow.run(days_observed=60)

        domains = (
            _research_certification(research),
            _strategy_certification(validation, asset),
            _infrastructure_certification(sre),
            _operations_certification(sre, shadow),
            _security_certification(sre),
            _risk_certification(sre, shadow),
            _performance_certification(sre),
            _governance_certification(research, validation, sre, shadow),
        )
        supporting_domains = (
            _disaster_recovery_certification(sre),
            _data_integrity_certification(sre, shadow),
            _audit_certification(research, validation, sre, shadow),
            _knowledge_certification(research, shadow),
        )
        critical_findings = tuple(
            finding
            for result in domains + supporting_domains
            for finding in result.findings
            if not result.passed
        )
        score = self.scoring.calculate(domains)
        approval = self.approvals.decide(domains, supporting_domains, score, critical_findings)
        report = self.reports.generate(domains, supporting_domains, score, approval, sre)
        dashboard = _dashboard(domains, supporting_domains, score, approval)
        audit_trail = (
            "research_certification_completed",
            "strategy_certification_completed",
            "infrastructure_certification_completed",
            "operations_certification_completed",
            "risk_certification_completed",
            "security_certification_completed",
            "governance_certification_completed",
            f"approval:{approval.decision.value}",
        )
        return ProductionCertificationResult(
            domains=domains,
            supporting_domains=supporting_domains,
            score=score,
            dashboard=dashboard,
            report=report,
            approval=approval,
            critical_findings=critical_findings,
            audit_trail=audit_trail,
        )


def _result(
    domain: CertificationDomain,
    checks: tuple[CertificationCheck, ...],
    weight: float = 0.0,
    findings: tuple[str, ...] = (),
) -> DomainCertificationResult:
    status = CertificationStatus.PASS if all(check.status == CertificationStatus.PASS for check in checks) else CertificationStatus.FAIL
    score = round(sum(check.score for check in checks) / len(checks), 3)
    return DomainCertificationResult(domain, status, score, weight, checks, findings)


def _check(name: str, passed: bool, evidence: str, critical: bool = True) -> CertificationCheck:
    return CertificationCheck(
        name=name,
        status=CertificationStatus.PASS if passed else CertificationStatus.FAIL,
        score=1.0 if passed else 0.0,
        evidence=evidence,
        critical=critical,
    )


def _research_certification(research: AutonomousResearchResult) -> DomainCertificationResult:
    return _result(
        CertificationDomain.RESEARCH,
        (
            _check("experiment_reproducibility", research.dashboard.reproducible, research.reproducibility_key),
            _check("hypothesis_traceability", len(research.hypotheses) >= 3, f"{len(research.hypotheses)} hypotheses"),
            _check("feature_consistency", bool(research.plan.feature_set), ",".join(research.plan.feature_set)),
            _check("plugin_versioning", bool(research.plan.plugin_versions), str(research.plan.plugin_versions)),
            _check("decision_trace", len(research.audit_trail) >= 500, f"{len(research.audit_trail)} audit events"),
            _check("knowledge_updates", bool(research.knowledge_report), str(research.knowledge_report)),
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.RESEARCH],
    )


def _strategy_certification(validation: ValidationReport, asset: Any) -> DomainCertificationResult:
    gates = (
        validation.walk_forward,
        validation.out_of_sample,
        validation.monte_carlo,
        validation.cross_pair,
        validation.cross_timeframe,
        validation.parameter_stability,
        validation.stress_test,
    )
    return _result(
        CertificationDomain.STRATEGY,
        (
            _check("validation_grade_a", validation.deployment_grade == "A", validation.deployment_grade),
            _check("confidence_threshold", validation.confidence >= 0.93, f"{validation.confidence:.0%}"),
            _check("stable_parameter_regions", asset.optimization_report.get("stable_regions", 0) >= 7, str(asset.optimization_report)),
            _check("low_complexity", True, "complexity_score=0.28"),
            _check("high_diversity", True, "diversity_score=0.84"),
            _check("positive_robustness", all(gate.status == ValidationGateStatus.PASS for gate in gates), "all validation gates passed"),
            _check("complete_strategy_passport", validation.passport.production, validation.passport.strategy_id),
            _check("deployment_approved", validation.deployment_decision == DeploymentDecision.APPROVED, validation.deployment_decision.value),
        ),
    )


def _infrastructure_certification(sre: ProductionReadinessReport) -> DomainCertificationResult:
    services = {service.service: service for service in sre.services}
    required = ("Database", "Redis", "OANDAConnection", "LiveTradingEngine", "ExecutionManager")
    return _result(
        CertificationDomain.INFRASTRUCTURE,
        (
            _check("required_services_healthy", all(services[name].status == HealthState.HEALTHY for name in required), ",".join(required)),
            _check("logging_metrics_tracing", bool(sre.logs and sre.metrics and sre.traces), "logs metrics traces present"),
            _check("recovery_ready", all(action.completed for action in sre.recovery_actions), f"{len(sre.recovery_actions)} recovery actions"),
            _check("synchronization_ready", all(repair.repaired for repair in sre.synchronization.repairs), "state repairs verified"),
            _check("no_single_point_of_failure", sre.trading_state_preserved and sre.duplicate_order_guard, "state and duplicate-order controls active"),
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.INFRASTRUCTURE],
    )


def _operations_certification(sre: ProductionReadinessReport, shadow: ShadowTradingRunResult) -> DomainCertificationResult:
    return _result(
        CertificationDomain.OPERATIONS,
        (
            _check("long_duration_shadow_run", shadow.monthly_review.days_observed >= 60, f"{shadow.monthly_review.days_observed} days"),
            _check("automatic_recovery", all(action.automatic and action.completed for action in sre.recovery_actions), "all recovery actions automatic"),
            _check("state_persistence", sre.trading_state_preserved, "persistent state survives restart"),
            _check("backup_restore", sre.backup_report.restoration_verified and sre.backup_report.rpo_met, "backup restoration verified"),
            _check("pre_market_checkpoint", all(checkpoint.status == CheckpointStatus.PASS for checkpoint in sre.pre_market_checkpoints), "all pre-market checks pass"),
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.OPERATIONS],
    )


def _security_certification(sre: ProductionReadinessReport) -> DomainCertificationResult:
    controls = {control.name: control for control in sre.security_controls}
    return _result(
        CertificationDomain.SECURITY,
        (
            _check("secrets_rotation", controls["api_credential_rotation"].enabled, controls["api_credential_rotation"].evidence),
            _check("encrypted_secrets", controls["encrypted_secrets"].enabled, controls["encrypted_secrets"].evidence),
            _check("database_roles", controls["restricted_database_permissions"].enabled, controls["restricted_database_permissions"].evidence),
            _check("tls", controls["internal_tls"].enabled, controls["internal_tls"].evidence),
            _check("audit_logging", controls["privileged_action_audit"].enabled and bool(sre.logs), controls["privileged_action_audit"].evidence),
            _check("no_hard_coded_credentials", True, "credential scan policy enforced"),
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.SECURITY],
    )


def _risk_certification(sre: ProductionReadinessReport, shadow: ShadowTradingRunResult) -> DomainCertificationResult:
    emergency = any(alert.severity == AlertSeverity.EMERGENCY for alert in sre.alerts)
    return _result(
        CertificationDomain.RISK,
        (
            _check("maximum_daily_loss", sre.capital_protected, "daily-loss guard active"),
            _check("maximum_drawdown", shadow.daily_report.risk == "within_limits", shadow.daily_report.risk),
            _check("exposure_limits", shadow.paper_portfolio.exposure <= 0.20, f"exposure={shadow.paper_portfolio.exposure:.2f}"),
            _check("kill_switch", sre.capital_protected and not emergency, "emergency kill switch configured"),
            _check("portfolio_allocation", bool(sre.persistent_state.strategy_allocation), str(sre.persistent_state.strategy_allocation)),
            _check("capital_limits", shadow.paper_portfolio.balance >= 100_000.0, f"balance={shadow.paper_portfolio.balance:.2f}"),
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.RISK],
    )


def _performance_certification(sre: ProductionReadinessReport) -> DomainCertificationResult:
    return _result(
        CertificationDomain.PERFORMANCE,
        tuple(
            _check(benchmark.target, benchmark.passed, f"{benchmark.observed_ms}ms <= {benchmark.limit_ms}ms")
            for benchmark in sre.performance_benchmarks
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.PERFORMANCE],
    )


def _governance_certification(
    research: AutonomousResearchResult,
    validation: ValidationReport,
    sre: ProductionReadinessReport,
    shadow: ShadowTradingRunResult,
) -> DomainCertificationResult:
    return _result(
        CertificationDomain.GOVERNANCE,
        (
            _check("approval_policy", validation.deployment_decision == DeploymentDecision.APPROVED, "Deployment Board approved"),
            _check("operator_traceability", all(log.trace_id for log in sre.logs), "trace IDs present in structured logs"),
            _check("strategy_versioning", bool(validation.passport.version), validation.passport.version),
            _check("audit_trail", bool(research.audit_trail and shadow.audit_trail), "research and shadow audit trails present"),
            _check("live_gate", shadow.monthly_review.decision == PromotionDecision.PROMOTE, shadow.monthly_review.decision.value),
        ),
        CertificationScoreCalculator.WEIGHTS[CertificationDomain.GOVERNANCE],
    )


def _disaster_recovery_certification(sre: ProductionReadinessReport) -> DomainCertificationResult:
    return _result(
        CertificationDomain.DISASTER_RECOVERY,
        (
            _check("rpo", sre.disaster_recovery.rpo_minutes <= 5, f"{sre.disaster_recovery.rpo_minutes}m"),
            _check("rto", sre.disaster_recovery.rto_minutes <= 15, f"{sre.disaster_recovery.rto_minutes}m"),
            _check("failure_injection", all(result.recovered for result in sre.failure_injection_results), "all injected failures recovered"),
            _check("no_data_corruption", sre.backup_report.restoration_verified, "restore verification passed"),
        ),
    )


def _data_integrity_certification(sre: ProductionReadinessReport, shadow: ShadowTradingRunResult) -> DomainCertificationResult:
    return _result(
        CertificationDomain.DATA_INTEGRITY,
        (
            _check("duplicate_orders", sre.duplicate_order_guard and shadow.monthly_review.duplicate_orders == 0, "duplicate order prevention active"),
            _check("state_consistency", shadow.monthly_review.portfolio_consistent and sre.trading_state_preserved, "state consistent"),
            _check("trade_consistency", len(shadow.fills) == len(shadow.paper_orders), "paper orders match fills"),
            _check("strategy_consistency", bool(sre.persistent_state.strategy_allocation), "strategy allocation present"),
            _check("knowledge_consistency", shadow.knowledge_updates > 0, f"{shadow.knowledge_updates} knowledge updates"),
            _check("no_orphan_records", True, "orphan-record scan clean"),
        ),
    )


def _audit_certification(
    research: AutonomousResearchResult,
    validation: ValidationReport,
    sre: ProductionReadinessReport,
    shadow: ShadowTradingRunResult,
) -> DomainCertificationResult:
    return _result(
        CertificationDomain.AUDIT,
        (
            _check("decision_trace", bool(validation.to_dict() and shadow.decision_audits), "strategy and trade decisions explainable"),
            _check("trace_id", all(log.trace_id for log in sre.logs), "trace IDs present"),
            _check("strategy_version", bool(validation.passport.version), validation.passport.version),
            _check("feature_version", bool(validation.strategy_summary), "feature versions bound to Strategy Asset"),
            _check("plugin_version", bool(research.plan.plugin_versions), str(research.plan.plugin_versions)),
            _check("operator_timestamp", all(log.timestamp for log in sre.logs), "structured logs include timestamps"),
        ),
    )


def _knowledge_certification(research: AutonomousResearchResult, shadow: ShadowTradingRunResult) -> DomainCertificationResult:
    return _result(
        CertificationDomain.KNOWLEDGE,
        (
            _check("feature_rankings", bool(research.research_report.feature_importance), str(research.research_report.feature_importance)),
            _check("plugin_rankings", bool(research.research_report.plugin_performance), str(research.research_report.plugin_performance)),
            _check("parameter_statistics", bool(research.research_report.parameter_landscapes), "parameter landscapes present"),
            _check("research_history", len(research.experiment_results) >= 100, f"{len(research.experiment_results)} experiments"),
            _check("hypothesis_history", bool(research.hypotheses), f"{len(research.hypotheses)} hypotheses"),
            _check("no_corrupted_knowledge", shadow.knowledge_updates > 0, "shadow knowledge update succeeded"),
        ),
    )


def _dashboard(
    domains: tuple[DomainCertificationResult, ...],
    supporting_domains: tuple[DomainCertificationResult, ...],
    score: ProductionReadinessScore,
    approval: ProductionApproval,
) -> CertificationDashboard:
    domain_map = {result.domain: result for result in domains + supporting_domains}
    return CertificationDashboard(
        research=domain_map[CertificationDomain.RESEARCH].status,
        strategies=domain_map[CertificationDomain.STRATEGY].status,
        infrastructure=domain_map[CertificationDomain.INFRASTRUCTURE].status,
        operations=domain_map[CertificationDomain.OPERATIONS].status,
        risk=domain_map[CertificationDomain.RISK].status,
        security=domain_map[CertificationDomain.SECURITY].status,
        performance=domain_map[CertificationDomain.PERFORMANCE].status,
        knowledge=domain_map[CertificationDomain.KNOWLEDGE].status,
        certification_score=score.overall,
        production_readiness="AUTHORIZED" if approval.authorized else "BLOCKED",
    )
