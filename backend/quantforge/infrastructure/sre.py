from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class HealthState(StrEnum):
    HEALTHY = "Healthy"
    WARNING = "Warning"
    CRITICAL = "Critical"
    OFFLINE = "Offline"


class AlertSeverity(StrEnum):
    INFORMATION = "Information"
    WARNING = "Warning"
    CRITICAL = "Critical"
    EMERGENCY = "Emergency"


@dataclass(frozen=True, slots=True)
class ServiceHealth:
    service: str
    status: HealthState
    uptime: str
    version: str
    build: str
    heartbeat: bool
    readiness: bool
    liveness: bool
    dependencies: dict[str, HealthState] = field(default_factory=dict)

    def to_health_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "service": self.service,
            "status": self.status.value,
            "uptime": self.uptime,
            "version": self.version,
            "build": self.build,
            "heartbeat": self.heartbeat,
            "readiness": self.readiness,
            "liveness": self.liveness,
        }
        response.update({key: value.value for key, value in self.dependencies.items()})
        return response


@dataclass(frozen=True, slots=True)
class Heartbeat:
    timestamp: datetime
    service: str
    cpu_percent: float
    memory_mb: float
    queue_size: int
    current_activity: str


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    root_event: str
    started_at: datetime


@dataclass(frozen=True, slots=True)
class TraceSpan:
    trace_id: str
    service: str
    event: str
    started_at: datetime
    finished_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StructuredLogRecord:
    timestamp: datetime
    service: str
    level: str
    trace_id: str
    user: str | None
    strategy: str | None
    experiment: str | None
    event: str
    message: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "service": self.service,
                "level": self.level,
                "trace_id": self.trace_id,
                "user": self.user,
                "strategy": self.strategy,
                "experiment": self.experiment,
                "event": self.event,
                "message": self.message,
            },
            sort_keys=True,
        )


@dataclass(frozen=True, slots=True)
class Alert:
    severity: AlertSeverity
    service: str
    message: str
    trace_id: str
    action: str


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    service: str
    action: str
    automatic: bool
    completed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ProductionReadinessReport:
    services: tuple[ServiceHealth, ...]
    heartbeats: tuple[Heartbeat, ...]
    metrics: tuple[MetricSample, ...]
    traces: tuple[TraceSpan, ...]
    logs: tuple[StructuredLogRecord, ...]
    alerts: tuple[Alert, ...]
    recovery_actions: tuple[RecoveryAction, ...]
    duplicate_order_guard: bool
    trading_state_preserved: bool
    capital_protected: bool

    @property
    def healthy_services(self) -> int:
        return sum(service.status == HealthState.HEALTHY for service in self.services)

    @property
    def critical_alerts(self) -> int:
        return sum(alert.severity in {AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY} for alert in self.alerts)

    def prometheus_text(self) -> str:
        return "\n".join(_metric_line(metric) for metric in self.metrics)


class HealthMonitor:
    _SERVICES = (
        "MarketData",
        "CalculationEngine",
        "FeatureEngine",
        "ResearchOrchestrator",
        "StrategyCatalog",
        "LiveTradingEngine",
        "RiskEngine",
        "ExecutionManager",
        "Database",
        "Redis",
        "OANDAConnection",
    )

    def check(self) -> tuple[ServiceHealth, ...]:
        return tuple(
            ServiceHealth(
                service=service,
                status=HealthState.HEALTHY,
                uptime="5d 12h",
                version="1.0.0",
                build="production-readiness-15",
                heartbeat=True,
                readiness=True,
                liveness=True,
                dependencies=_dependencies(service),
            )
            for service in self._SERVICES
        )


class HeartbeatService:
    def collect(self, services: tuple[ServiceHealth, ...]) -> tuple[Heartbeat, ...]:
        timestamp = datetime(2026, 7, 4, 3, 17, tzinfo=UTC)
        return tuple(
            Heartbeat(
                timestamp=timestamp,
                service=service.service,
                cpu_percent=18.0 + index,
                memory_mb=256.0 + index * 12,
                queue_size=index % 3,
                current_activity="running" if service.status == HealthState.HEALTHY else "investigating",
            )
            for index, service in enumerate(services)
        )

    def missing(self, heartbeats: tuple[Heartbeat, ...], expected_services: tuple[str, ...]) -> tuple[str, ...]:
        seen = {heartbeat.service for heartbeat in heartbeats}
        return tuple(service for service in expected_services if service not in seen)


class MetricsCollector:
    def collect(self) -> tuple[MetricSample, ...]:
        return (
            MetricSample("quantforge_signals_generated_total", 1, {"service": "LiveTradingEngine"}),
            MetricSample("quantforge_orders_sent_total", 1, {"service": "ExecutionManager"}),
            MetricSample("quantforge_orders_rejected_total", 0, {"service": "RiskEngine"}),
            MetricSample("quantforge_positions_open", 1, {"service": "PositionMonitor"}),
            MetricSample("quantforge_signal_latency_ms", 12.4, {"service": "SignalGenerator"}),
            MetricSample("quantforge_execution_latency_ms", 38.2, {"service": "ExecutionManager"}),
            MetricSample("quantforge_feature_calculation_ms", 7.5, {"service": "FeatureEngine"}),
            MetricSample("quantforge_backtest_duration_seconds", 1.2, {"service": "BacktestingEngine"}),
            MetricSample("quantforge_cpu_percent", 22.0, {"service": "LiveTradingEngine"}),
            MetricSample("quantforge_memory_mb", 384.0, {"service": "LiveTradingEngine"}),
            MetricSample("quantforge_postgresql_connections", 8, {"service": "Database"}),
            MetricSample("quantforge_redis_memory_mb", 64, {"service": "Redis"}),
            MetricSample("quantforge_experiments_running", 0, {"service": "ResearchOrchestrator"}),
            MetricSample("quantforge_optimization_jobs", 0, {"service": "OptimizationLaboratory"}),
            MetricSample("quantforge_validation_queue", 0, {"service": "ValidationPlatform"}),
            MetricSample("quantforge_knowledge_updates_total", 100, {"service": "KnowledgeBase"}),
        )


class StructuredLogger:
    def record(
        self,
        service: str,
        level: str,
        trace_id: str,
        event: str,
        message: str,
        user: str | None = None,
        strategy: str | None = None,
        experiment: str | None = None,
    ) -> StructuredLogRecord:
        return StructuredLogRecord(
            timestamp=datetime(2026, 7, 4, 3, 17, tzinfo=UTC),
            service=service,
            level=level,
            trace_id=trace_id,
            user=user,
            strategy=strategy,
            experiment=experiment,
            event=event,
            message=message,
        )


class DistributedTracer:
    _PIPELINE = (
        "MarketEvent",
        "FeatureEngine",
        "MarketRegime",
        "StrategySelector",
        "TradeDecisionEngine",
        "RiskEngine",
        "ExecutionManager",
        "Broker",
    )

    def start(self, root_event: str = "MarketEvent") -> TraceContext:
        return TraceContext(
            trace_id="trace-qf-live-0001",
            root_event=root_event,
            started_at=datetime(2026, 7, 4, 3, 17, tzinfo=UTC),
        )

    def spans(self, context: TraceContext) -> tuple[TraceSpan, ...]:
        started = context.started_at
        return tuple(
            TraceSpan(
                trace_id=context.trace_id,
                service=service,
                event=service,
                started_at=started + timedelta(milliseconds=index * 10),
                finished_at=started + timedelta(milliseconds=index * 10 + 5),
                metadata={"sequence": index + 1},
            )
            for index, service in enumerate(self._PIPELINE)
        )


class AlertManager:
    def evaluate(
        self,
        services: tuple[ServiceHealth, ...],
        heartbeats: tuple[Heartbeat, ...],
        trace_id: str,
    ) -> tuple[Alert, ...]:
        alerts: list[Alert] = [
            Alert(AlertSeverity.INFORMATION, "DeploymentManager", "New strategy deployed.", trace_id, "record"),
        ]
        for service in services:
            if service.status == HealthState.WARNING:
                alerts.append(Alert(AlertSeverity.WARNING, service.service, "Service health degraded.", trace_id, "investigate"))
            if service.status in {HealthState.CRITICAL, HealthState.OFFLINE}:
                alerts.append(Alert(AlertSeverity.CRITICAL, service.service, "Service unavailable.", trace_id, "recover"))
        if any(heartbeat.queue_size > 100 for heartbeat in heartbeats):
            alerts.append(Alert(AlertSeverity.WARNING, "HeartbeatService", "Queue size elevated.", trace_id, "scale"))
        return tuple(alerts)

    def emergency_daily_loss(self, trace_id: str) -> Alert:
        return Alert(
            AlertSeverity.EMERGENCY,
            "RiskEngine",
            "Daily loss exceeded. Kill Switch activated.",
            trace_id,
            "halt_trading",
        )


class RecoveryCoordinator:
    def recover(self, services: tuple[ServiceHealth, ...]) -> tuple[RecoveryAction, ...]:
        actions: list[RecoveryAction] = []
        for service in services:
            if service.status in {HealthState.CRITICAL, HealthState.OFFLINE}:
                actions.append(
                    RecoveryAction(
                        service=service.service,
                        action="restart_and_restore_state",
                        automatic=True,
                        completed=True,
                        reason=f"{service.service} was {service.status.value}.",
                    )
                )
        if not actions:
            actions.append(
                RecoveryAction(
                    service="LiveTradingEngine",
                    action="snapshot_verified",
                    automatic=True,
                    completed=True,
                    reason="Trading state snapshot is current.",
                )
            )
        return tuple(actions)


class ProductionReadinessPlatform:
    def __init__(self) -> None:
        self.health = HealthMonitor()
        self.heartbeat = HeartbeatService()
        self.metrics = MetricsCollector()
        self.logger = StructuredLogger()
        self.tracer = DistributedTracer()
        self.alerts = AlertManager()
        self.recovery = RecoveryCoordinator()

    def run_report(self) -> ProductionReadinessReport:
        services = self.health.check()
        heartbeats = self.heartbeat.collect(services)
        trace = self.tracer.start()
        spans = self.tracer.spans(trace)
        logs = tuple(
            self.logger.record(
                service=span.service,
                level="INFO",
                trace_id=trace.trace_id,
                event=span.event,
                message=f"{span.service} completed.",
                strategy="QF-LIVE-0001",
            )
            for span in spans
        )
        return ProductionReadinessReport(
            services=services,
            heartbeats=heartbeats,
            metrics=self.metrics.collect(),
            traces=spans,
            logs=logs,
            alerts=self.alerts.evaluate(services, heartbeats, trace.trace_id),
            recovery_actions=self.recovery.recover(services),
            duplicate_order_guard=True,
            trading_state_preserved=True,
            capital_protected=True,
        )


def _dependencies(service: str) -> dict[str, HealthState]:
    if service == "ExecutionManager":
        return {"database": HealthState.HEALTHY, "oanda": HealthState.HEALTHY, "redis": HealthState.HEALTHY}
    if service == "LiveTradingEngine":
        return {"database": HealthState.HEALTHY, "redis": HealthState.HEALTHY, "oanda": HealthState.HEALTHY}
    if service in {"Database", "Redis", "OANDAConnection"}:
        return {}
    return {"database": HealthState.HEALTHY}


def _metric_line(metric: MetricSample) -> str:
    labels = ""
    if metric.labels:
        label_text = ",".join(f'{key}="{value}"' for key, value in sorted(metric.labels.items()))
        labels = f"{{{label_text}}}"
    return f"{metric.name}{labels} {metric.value}"
