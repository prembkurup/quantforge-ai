import json

from quantforge.infrastructure import (
    AlertManager,
    AlertSeverity,
    CheckpointStatus,
    HealthMonitor,
    HealthState,
    HeartbeatService,
    ProductionReadinessPlatform,
    StructuredLogger,
)


def test_health_monitor_reports_required_service_health_fields() -> None:
    health = HealthMonitor().check()
    execution = next(service for service in health if service.service == "ExecutionManager")

    assert len(health) == 11
    assert execution.status == HealthState.HEALTHY
    assert execution.readiness is True
    assert execution.liveness is True
    assert execution.heartbeat is True
    assert execution.to_health_response()["oanda"] == "Healthy"


def test_heartbeat_service_detects_missing_heartbeats() -> None:
    services = HealthMonitor().check()
    heartbeats = HeartbeatService().collect(services[:-1])

    assert HeartbeatService().missing(heartbeats, tuple(service.service for service in services)) == ("OANDAConnection",)


def test_structured_logger_outputs_json_with_trace_id() -> None:
    record = StructuredLogger().record(
        service="ExecutionManager",
        level="INFO",
        trace_id="trace-123",
        event="OrderSubmitted",
        message="Order submitted.",
        strategy="QF-LIVE-0001",
    )

    payload = json.loads(record.to_json())
    assert payload["trace_id"] == "trace-123"
    assert payload["service"] == "ExecutionManager"
    assert payload["strategy"] == "QF-LIVE-0001"


def test_production_readiness_report_exports_metrics_traces_and_recovery() -> None:
    report = ProductionReadinessPlatform().run_report()

    assert report.healthy_services == len(report.services)
    assert len(report.metrics) >= 10
    assert "quantforge_orders_sent_total" in report.prometheus_text()
    assert {span.trace_id for span in report.traces} == {"trace-qf-live-0001"}
    assert all(action.completed for action in report.recovery_actions)
    assert report.trading_state_preserved is True
    assert report.duplicate_order_guard is True
    assert report.capital_protected is True


def test_automatic_recovery_state_sync_and_disaster_objectives_pass() -> None:
    report = ProductionReadinessPlatform().run_report()

    assert len(report.recovery_actions) >= 6
    assert report.persistent_state.durable is True
    assert report.trading_state_preserved is True
    assert report.synchronization.interval_seconds == 60
    assert all(repair.repaired for repair in report.synchronization.repairs)
    assert report.synchronization.duplicate_order_prevention is True
    assert report.disaster_recovery.rpo_minutes <= 5
    assert report.disaster_recovery.rto_minutes <= 15
    assert report.disaster_recovery.objectives_met is True


def test_backups_checkpoints_failure_injection_and_latency_targets_pass() -> None:
    report = ProductionReadinessPlatform().run_report()

    assert report.backup_report.restoration_verified is True
    assert report.backup_report.rpo_met is True
    assert report.backup_report.policy.strategy_assets == "immediate_after_publication"
    assert all(checkpoint.status == CheckpointStatus.PASS for checkpoint in report.pre_market_checkpoints)
    assert all(result.recovered and not result.manual_intervention_required for result in report.failure_injection_results)
    assert all(result.recovery_time_seconds < 30 for result in report.failure_injection_results)
    assert all(benchmark.passed for benchmark in report.performance_benchmarks)


def test_security_controls_dashboard_and_runbooks_are_present() -> None:
    report = ProductionReadinessPlatform().run_report()

    assert report.operational_dashboard.system_health == HealthState.HEALTHY
    assert report.operational_dashboard.broker_status == "connected"
    assert all(control.enabled for control in report.security_controls)
    assert {runbook.name for runbook in report.runbooks} == {
        "Database Recovery",
        "Broker Recovery",
        "Server Recovery",
        "Kill Switch Activation",
        "Manual Trading Suspension",
        "Emergency Shutdown",
        "Disaster Recovery",
    }


def test_alert_manager_classifies_emergency_kill_switch() -> None:
    alert = AlertManager().emergency_daily_loss("trace-123")

    assert alert.severity == AlertSeverity.EMERGENCY
    assert alert.action == "halt_trading"
    assert "Kill Switch" in alert.message
