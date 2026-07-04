from quantforge.domain import ValidationStatus
from quantforge.validation import (
    DeploymentDecision,
    StrategyValidationPlatform,
    ValidationEngine,
    ValidationGateStatus,
)


def test_legacy_validation_engine_threshold_api_still_works() -> None:
    result = ValidationEngine().evaluate({"profit_factor": 2.1}, {"profit_factor": 2.0})

    assert result.status == ValidationStatus.PASSED


def test_strategy_validation_platform_runs_all_qa_gates() -> None:
    report = StrategyValidationPlatform().validate("QF-2026-00431")

    assert report.strategy_id == "QF-2026-00431"
    assert report.walk_forward.status == ValidationGateStatus.PASS
    assert report.out_of_sample.status == ValidationGateStatus.PASS
    assert report.monte_carlo.status == ValidationGateStatus.PASS
    assert report.cross_pair.status == ValidationGateStatus.PASS
    assert report.cross_timeframe.status == ValidationGateStatus.PASS
    assert report.parameter_stability.status == ValidationGateStatus.PASS
    assert report.stress_test.status == ValidationGateStatus.PASS
    assert report.confidence == 0.93
    assert report.deployment_grade == "A"
    assert report.deployment_decision == DeploymentDecision.APPROVED


def test_strategy_passport_becomes_permanent_identity() -> None:
    report = StrategyValidationPlatform().validate("QF-2026-00431")

    assert report.passport.strategy_id == "QF-2026-00431"
    assert report.passport.template == "Trend Pullback"
    assert report.passport.validation_grade == "A"
    assert report.passport.production is True
    assert report.passport.version == "3.2"


def test_strategy_asset_wraps_full_auditable_lifecycle() -> None:
    platform = StrategyValidationPlatform()
    report = platform.validate("QF-2026-00431")

    asset = platform.create_strategy_asset(report)

    assert asset.passport.strategy_id == "QF-2026-00431"
    assert asset.strategy_definition["template"] == "Trend Pullback"
    assert asset.plugin_versions["entry"] == "ema_pullback_entry_01@1.0.0"
    assert asset.optimization_report["stable_regions"] == 7
    assert asset.validation_report.deployment_decision == DeploymentDecision.APPROVED
    assert asset.deployment_history[0]["environment"] == "production"
