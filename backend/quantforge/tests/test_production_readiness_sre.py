import json

from quantforge.infrastructure import (
    AlertManager,
    AlertSeverity,
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


def test_alert_manager_classifies_emergency_kill_switch() -> None:
    alert = AlertManager().emergency_daily_loss("trace-123")

    assert alert.severity == AlertSeverity.EMERGENCY
    assert alert.action == "halt_trading"
    assert "Kill Switch" in alert.message
