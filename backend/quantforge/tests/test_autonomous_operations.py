import pytest

from quantforge.infrastructure import (
    AutonomousOperationsManager,
    AutonomousOperationsResult,
    DriftDimension,
)


@pytest.fixture(scope="module")
def operations_result() -> AutonomousOperationsResult:
    return AutonomousOperationsManager().run_validation()


def test_validation_runs_90_day_autonomous_production_simulation(
    operations_result: AutonomousOperationsResult,
) -> None:
    assert operations_result.config.consecutive_days == 90
    assert operations_result.config.hours_per_day == 24
    assert operations_result.config.trading_days_per_week == 5
    assert operations_result.config.sampling_interval_seconds == 60
    assert operations_result.total_monitoring_samples >= 90_000
    assert operations_result.operationally_mature is True


def test_incidents_are_detected_and_self_healed_without_duplicate_orders(
    operations_result: AutonomousOperationsResult,
) -> None:
    assert operations_result.incidents
    assert all(incident.resolved for incident in operations_result.incidents)
    assert all(incident.resolution_time_seconds < 30 for incident in operations_result.incidents)
    assert operations_result.reliability_kpis.duplicate_orders == 0
    assert operations_result.reliability_kpis.failed_recovery_attempts == 0


def test_broker_synchronization_runs_every_60_seconds_and_reconciles_state(
    operations_result: AutonomousOperationsResult,
) -> None:
    broker_sync = operations_result.broker_synchronization

    assert broker_sync.interval_seconds == 60
    assert broker_sync.accuracy == 1.0
    assert broker_sync.unreconciled_mismatches == 0
    assert set(broker_sync.checks) == {
        "missing_orders",
        "missing_positions",
        "stop_loss_mismatch",
        "take_profit_mismatch",
        "position_size_mismatch",
    }


def test_all_drift_dimensions_remain_within_configured_tolerance(
    operations_result: AutonomousOperationsResult,
) -> None:
    drift_map = {observation.dimension for observation in operations_result.drift_observations}

    assert drift_map == set(DriftDimension)
    assert all(observation.within_tolerance for observation in operations_result.drift_observations)
    assert not any(observation.alert_created for observation in operations_result.drift_observations)


def test_maintenance_and_capacity_planning_are_non_interrupting(
    operations_result: AutonomousOperationsResult,
) -> None:
    assert len(operations_result.maintenance_tasks) == 9
    assert all(task.completed for task in operations_result.maintenance_tasks)
    assert not any(task.interrupts_trading for task in operations_result.maintenance_tasks)
    assert {forecast.resource for forecast in operations_result.capacity_forecasts} >= {
        "candle_count_millions",
        "database_size_gb",
        "strategy_assets",
        "knowledge_records",
        "log_growth_gb",
    }
    assert all(forecast.horizon_365d < forecast.limit for forecast in operations_result.capacity_forecasts)


def test_reliability_trading_and_research_kpis_meet_targets(
    operations_result: AutonomousOperationsResult,
) -> None:
    assert operations_result.reliability_kpis.passed is True
    assert operations_result.trading_kpis.passed is True
    assert operations_result.trading_kpis.execution_success_rate >= 0.99
    assert operations_result.trading_kpis.risk_violations == 0
    assert operations_result.research_kpis.approved_strategy_assets_monthly > 0
    assert operations_result.research_kpis.knowledge_base_growth_monthly > 0


def test_reports_compliance_and_audit_trail_are_complete(
    operations_result: AutonomousOperationsResult,
) -> None:
    reports = (
        operations_result.daily_report,
        operations_result.weekly_report,
        operations_result.monthly_report,
        operations_result.capacity_report,
    )

    assert all(report.archived for report in reports)
    assert operations_result.compliance.passed is True
    assert len(operations_result.audit_trail) >= 9
    assert "daily_weekly_monthly_reports_archived" in operations_result.audit_trail
    assert "compliance_checks_passed" in operations_result.audit_trail
