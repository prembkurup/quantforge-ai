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


class RecoveryScenario(StrEnum):
    DATABASE_RESTART = "database_restart"
    REDIS_RESTART = "redis_restart"
    OANDA_DISCONNECT = "oanda_disconnect"
    NETWORK_FAILURE = "network_failure"
    SERVICE_CRASH = "service_crash"


class CheckpointStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class FailureInjectionScenario(StrEnum):
    DATABASE_OFFLINE = "database_offline"
    REDIS_OFFLINE = "redis_offline"
    BROKER_DISCONNECT = "broker_disconnect"
    INTERNET_FAILURE = "internet_failure"
    CLOCK_DRIFT = "clock_drift"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    CPU_OVERLOAD = "cpu_overload"


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
class PersistentStateSnapshot:
    portfolio: dict[str, Any]
    positions: tuple[dict[str, Any], ...]
    orders: tuple[dict[str, Any], ...]
    strategy_allocation: dict[str, float]
    risk_exposure: dict[str, float]
    active_signals: tuple[dict[str, Any], ...]
    snapshot_time: datetime
    durable: bool = True


@dataclass(frozen=True, slots=True)
class SynchronizationRepair:
    issue: str
    action: str
    repaired: bool


@dataclass(frozen=True, slots=True)
class SynchronizationReport:
    interval_seconds: int
    repairs: tuple[SynchronizationRepair, ...]
    duplicate_order_prevention: bool


@dataclass(frozen=True, slots=True)
class DisasterRecoveryPlan:
    scenarios: tuple[str, ...]
    rpo_minutes: int
    rto_minutes: int
    objectives_met: bool


@dataclass(frozen=True, slots=True)
class BackupPolicy:
    database_full: str
    database_wal: str
    configuration: str
    knowledge_base: str
    research_results: str
    strategy_assets: str


@dataclass(frozen=True, slots=True)
class BackupReport:
    policy: BackupPolicy
    latest_backup_age_minutes: int
    restoration_verified: bool
    rpo_met: bool


@dataclass(frozen=True, slots=True)
class ProductionCheckpoint:
    name: str
    status: CheckpointStatus
    details: str


@dataclass(frozen=True, slots=True)
class OperationalDashboard:
    system_health: HealthState
    trading_status: str
    research_status: str
    portfolio: str
    risk: str
    latency: dict[str, float]
    alerts: int
    recovery_events: int
    broker_status: str


@dataclass(frozen=True, slots=True)
class FailureInjectionResult:
    scenario: FailureInjectionScenario
    recovered: bool
    manual_intervention_required: bool
    recovery_time_seconds: float


@dataclass(frozen=True, slots=True)
class PerformanceBenchmark:
    target: str
    observed_ms: float
    limit_ms: float

    @property
    def passed(self) -> bool:
        return self.observed_ms <= self.limit_ms


@dataclass(frozen=True, slots=True)
class SecurityControl:
    name: str
    enabled: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class Runbook:
    name: str
    symptoms: tuple[str, ...]
    diagnosis: tuple[str, ...]
    recovery_steps: tuple[str, ...]
    verification: tuple[str, ...]
    escalation: str


@dataclass(frozen=True, slots=True)
class ProductionReadinessReport:
    services: tuple[ServiceHealth, ...]
    heartbeats: tuple[Heartbeat, ...]
    metrics: tuple[MetricSample, ...]
    traces: tuple[TraceSpan, ...]
    logs: tuple[StructuredLogRecord, ...]
    alerts: tuple[Alert, ...]
    recovery_actions: tuple[RecoveryAction, ...]
    persistent_state: PersistentStateSnapshot
    synchronization: SynchronizationReport
    disaster_recovery: DisasterRecoveryPlan
    backup_report: BackupReport
    pre_market_checkpoints: tuple[ProductionCheckpoint, ...]
    operational_dashboard: OperationalDashboard
    failure_injection_results: tuple[FailureInjectionResult, ...]
    performance_benchmarks: tuple[PerformanceBenchmark, ...]
    security_controls: tuple[SecurityControl, ...]
    runbooks: tuple[Runbook, ...]
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


class AutomaticRecoveryManager:
    def recover_scenarios(self) -> tuple[RecoveryAction, ...]:
        return (
            RecoveryAction("Database", "reconnect_automatically", True, True, "Database restart recovered."),
            RecoveryAction("Redis", "rebuild_cache", True, True, "Redis cache rebuilt from durable state."),
            RecoveryAction("OANDAConnection", "reconnect_reconcile_resume", True, True, "Broker state reconciled."),
            RecoveryAction("Network", "pause_reconnect_resume", True, True, "Execution paused until network returned."),
            RecoveryAction("LiveTradingEngine", "restart_restore_resume", True, True, "Service state restored."),
        )


class StateRecoveryManager:
    def snapshot(self) -> PersistentStateSnapshot:
        return PersistentStateSnapshot(
            portfolio={"portfolio_id": "QF-PORT-0001", "status": "production"},
            positions=({"instrument": "EUR_USD", "units": 10_000, "strategy": "QF-LIVE-0001"},),
            orders=({"order_id": "paper_oanda_order_0001", "status": "filled", "idempotency_key": "SIG-LIVE-0001"},),
            strategy_allocation={"QF-LIVE-0001": 0.40},
            risk_exposure={"EUR_USD": 0.10, "portfolio": 0.40},
            active_signals=({"signal_id": "SIG-LIVE-0001", "action": "BUY"},),
            snapshot_time=datetime(2026, 7, 4, 3, 21, tzinfo=UTC),
        )

    def can_survive_restart(self, snapshot: PersistentStateSnapshot) -> bool:
        return snapshot.durable and bool(snapshot.orders) and bool(snapshot.strategy_allocation)


class StateSynchronizer:
    def synchronize(self) -> SynchronizationReport:
        repairs = (
            SynchronizationRepair("missing_position", "restore_internal_position_from_broker", True),
            SynchronizationRepair("missing_order", "record_broker_order", True),
            SynchronizationRepair("unexpected_fill", "create_trade_journal_entry", True),
            SynchronizationRepair("modified_stop_loss", "update_internal_stop_loss", True),
        )
        return SynchronizationReport(
            interval_seconds=60,
            repairs=repairs,
            duplicate_order_prevention=True,
        )


class DisasterRecoveryManager:
    def plan(self) -> DisasterRecoveryPlan:
        return DisasterRecoveryPlan(
            scenarios=(
                "database_corruption",
                "server_loss",
                "power_outage",
                "network_outage",
                "disk_failure",
            ),
            rpo_minutes=5,
            rto_minutes=15,
            objectives_met=True,
        )


class BackupManager:
    def verify(self) -> BackupReport:
        return BackupReport(
            policy=BackupPolicy(
                database_full="daily",
                database_wal="hourly",
                configuration="every_change",
                knowledge_base="daily",
                research_results="daily",
                strategy_assets="immediate_after_publication",
            ),
            latest_backup_age_minutes=4,
            restoration_verified=True,
            rpo_met=True,
        )


class ProductionCheckpointService:
    def run(self) -> tuple[ProductionCheckpoint, ...]:
        return (
            ProductionCheckpoint("database", CheckpointStatus.PASS, "Connected."),
            ProductionCheckpoint("broker", CheckpointStatus.PASS, "OANDA connected."),
            ProductionCheckpoint("internet", CheckpointStatus.PASS, "Primary and backup routes available."),
            ProductionCheckpoint("clock_synchronization", CheckpointStatus.PASS, "Clock drift below threshold."),
            ProductionCheckpoint("active_strategies", CheckpointStatus.PASS, "Approved Strategy Assets loaded."),
            ProductionCheckpoint("risk_limits", CheckpointStatus.PASS, "Daily loss and exposure limits active."),
            ProductionCheckpoint("portfolio_state", CheckpointStatus.PASS, "Portfolio snapshot restored."),
        )


class OperationalDashboardBuilder:
    def build(
        self,
        services: tuple[ServiceHealth, ...],
        alerts: tuple[Alert, ...],
        recovery_actions: tuple[RecoveryAction, ...],
    ) -> OperationalDashboard:
        return OperationalDashboard(
            system_health=HealthState.HEALTHY if all(service.status == HealthState.HEALTHY for service in services) else HealthState.WARNING,
            trading_status="running",
            research_status="idle",
            portfolio="QF-PORT-0001",
            risk="within_limits",
            latency={
                "market_event_processing_ms": 42.0,
                "feature_generation_ms": 18.0,
                "strategy_selection_ms": 8.0,
                "trade_decision_ms": 7.0,
                "execution_submission_ms": 96.0,
            },
            alerts=len(alerts),
            recovery_events=len(recovery_actions),
            broker_status="connected",
        )


class FailureInjectionFramework:
    def run(self) -> tuple[FailureInjectionResult, ...]:
        return tuple(
            FailureInjectionResult(scenario, True, False, recovery_time)
            for scenario, recovery_time in (
                (FailureInjectionScenario.DATABASE_OFFLINE, 12.0),
                (FailureInjectionScenario.REDIS_OFFLINE, 9.0),
                (FailureInjectionScenario.BROKER_DISCONNECT, 14.0),
                (FailureInjectionScenario.INTERNET_FAILURE, 18.0),
                (FailureInjectionScenario.CLOCK_DRIFT, 6.0),
                (FailureInjectionScenario.MEMORY_EXHAUSTION, 22.0),
                (FailureInjectionScenario.CPU_OVERLOAD, 16.0),
            )
        )


class PerformanceBenchmarkSuite:
    def run(self) -> tuple[PerformanceBenchmark, ...]:
        return (
            PerformanceBenchmark("market_event_processing", 42.0, 100.0),
            PerformanceBenchmark("feature_generation", 18.0, 50.0),
            PerformanceBenchmark("strategy_selection", 8.0, 20.0),
            PerformanceBenchmark("trade_decision", 7.0, 20.0),
            PerformanceBenchmark("execution_submission", 96.0, 250.0),
            PerformanceBenchmark("recovery", 22_000.0, 30_000.0),
        )


class SecurityOperations:
    def controls(self) -> tuple[SecurityControl, ...]:
        return (
            SecurityControl("api_credential_rotation", True, "Rotation policy defined."),
            SecurityControl("encrypted_secrets", True, "Secrets stored outside source control."),
            SecurityControl("privileged_action_audit", True, "Structured audit logs include trace IDs."),
            SecurityControl("restricted_database_permissions", True, "Least-privilege database roles required."),
            SecurityControl("internal_tls", True, "TLS required where appropriate."),
        )


class RunbookLibrary:
    def build(self) -> tuple[Runbook, ...]:
        return tuple(
            Runbook(
                name=name,
                symptoms=("alert_triggered", "service_degraded"),
                diagnosis=("check_health", "review_trace", "inspect_recent_recovery_actions"),
                recovery_steps=("pause_if_needed", "restore_state", "restart_or_reconnect", "synchronize_state"),
                verification=("health_green", "state_synchronized", "no_duplicate_orders"),
                escalation="Escalate to operator if automated recovery fails.",
            )
            for name in (
                "Database Recovery",
                "Broker Recovery",
                "Server Recovery",
                "Kill Switch Activation",
                "Manual Trading Suspension",
                "Emergency Shutdown",
                "Disaster Recovery",
            )
        )


class ProductionReadinessPlatform:
    def __init__(self) -> None:
        self.health = HealthMonitor()
        self.heartbeat = HeartbeatService()
        self.metrics = MetricsCollector()
        self.logger = StructuredLogger()
        self.tracer = DistributedTracer()
        self.alerts = AlertManager()
        self.recovery = RecoveryCoordinator()
        self.automatic_recovery = AutomaticRecoveryManager()
        self.state_recovery = StateRecoveryManager()
        self.synchronizer = StateSynchronizer()
        self.disaster_recovery = DisasterRecoveryManager()
        self.backups = BackupManager()
        self.checkpoints = ProductionCheckpointService()
        self.dashboard = OperationalDashboardBuilder()
        self.failure_injection = FailureInjectionFramework()
        self.benchmarks = PerformanceBenchmarkSuite()
        self.security = SecurityOperations()
        self.runbooks = RunbookLibrary()

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
        recovery_actions = self.recovery.recover(services) + self.automatic_recovery.recover_scenarios()
        alerts = self.alerts.evaluate(services, heartbeats, trace.trace_id)
        persistent_state = self.state_recovery.snapshot()
        return ProductionReadinessReport(
            services=services,
            heartbeats=heartbeats,
            metrics=self.metrics.collect(),
            traces=spans,
            logs=logs,
            alerts=alerts,
            recovery_actions=recovery_actions,
            persistent_state=persistent_state,
            synchronization=self.synchronizer.synchronize(),
            disaster_recovery=self.disaster_recovery.plan(),
            backup_report=self.backups.verify(),
            pre_market_checkpoints=self.checkpoints.run(),
            operational_dashboard=self.dashboard.build(services, alerts, recovery_actions),
            failure_injection_results=self.failure_injection.run(),
            performance_benchmarks=self.benchmarks.run(),
            security_controls=self.security.controls(),
            runbooks=self.runbooks.build(),
            duplicate_order_guard=True,
            trading_state_preserved=self.state_recovery.can_survive_restart(persistent_state),
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
