# Production Engineering and SRE

Milestone 15 hardens QuantForge AI for production operation.

This milestone adds operational excellence rather than new trading functionality. The goal is to keep the platform available, detect failures automatically, recover whenever possible, preserve trading state, prevent duplicate orders, and protect capital.

## Reliability Principles

- Every component can fail.
- Failure must be detected automatically.
- Recovery must be automatic whenever possible.
- No single failure should lose trading state.
- No single failure should cause duplicate orders.
- Every critical event must be logged.
- Every production action must be traceable.

## Health Architecture

Every service exposes:

- heartbeat
- readiness
- liveness
- version
- build
- uptime
- dependency health

Example health response:

```json
{
  "service": "ExecutionManager",
  "status": "Healthy",
  "uptime": "5d 12h",
  "version": "1.0.0",
  "build": "production-readiness-15",
  "database": "Healthy",
  "oanda": "Healthy",
  "redis": "Healthy"
}
```

## Monitored Components

- Market Data
- Calculation Engine
- Feature Engine
- Research Orchestrator
- Strategy Catalog
- Live Trading Engine
- Risk Engine
- Execution Manager
- Database
- Redis
- OANDA Connection

Health states are `Healthy`, `Warning`, `Critical`, and `Offline`.

## Heartbeats

`HeartbeatService` records timestamp, service name, CPU, memory, queue size, and current activity. Missing heartbeats are detectable by comparing received heartbeat service names with expected services.

## Metrics

`MetricsCollector` exports Prometheus-style samples, including:

- signals generated
- orders sent
- orders rejected
- positions open
- signal latency
- execution latency
- feature calculation time
- backtest duration
- CPU
- memory
- PostgreSQL connections
- Redis memory
- experiments running
- optimization jobs
- validation queue
- knowledge updates

## Structured Logging

`StructuredLogger` emits JSON records with:

- timestamp
- service
- level
- trace ID
- user
- strategy
- experiment
- event
- message

Production logs should be JSON, not plain text.

## Distributed Tracing

`DistributedTracer` keeps a single trace ID across the live trading path:

```text
Market Event
  -> Feature Engine
  -> Market Regime
  -> Strategy Selector
  -> Trade Decision Engine
  -> Risk Engine
  -> Execution Manager
  -> Broker
```

## Alerting

Alerts are classified as:

- `Information`
- `Warning`
- `Critical`
- `Emergency`

Examples:

- Information: new strategy deployed.
- Warning: latency or queue size increased.
- Critical: database unavailable.
- Emergency: daily loss exceeded and kill switch activated.

## Recovery

`RecoveryCoordinator` creates automatic recovery actions for critical or offline services. When no failure is active, it still verifies that the live trading state snapshot is current.

Automatic recovery covers database restart, Redis restart, OANDA disconnect, network failure, and service crash. Recovery actions reconnect services, rebuild cache, reconcile broker state, pause execution when needed, restore state, and resume processing.

## State Recovery

`StateRecoveryManager` snapshots durable trading state:

- portfolio
- positions
- orders
- strategy allocation
- risk exposure
- active signals

The state snapshot is designed to survive server reboot, service restart, and power failure.

## Synchronization

`StateSynchronizer` runs on a 60-second interval. It compares internal state with broker state and repairs missing positions, missing orders, unexpected fills, and modified stop-loss records. Duplicate order prevention is part of the synchronization report.

## Disaster Recovery

`DisasterRecoveryManager` defines recovery objectives for database corruption, server loss, power outage, network outage, and disk failure.

- RPO: 5 minutes
- RTO: 15 minutes

## Backups

`BackupManager` verifies the backup policy:

- database full backup: daily
- WAL archive: hourly
- configuration: every change
- Knowledge Base: daily
- research results: daily
- Strategy Assets: immediately after publication

## Production Checkpoints

`ProductionCheckpointService` runs before market open. No trading should begin unless all checks pass:

- database
- broker
- internet
- clock synchronization
- active strategies
- risk limits
- portfolio state

## Dashboard

`OperationalDashboard` displays system health, trading status, research status, portfolio, risk, latency, alerts, recovery events, and broker status.

## Failure Injection

`FailureInjectionFramework` simulates database offline, Redis offline, broker disconnect, internet failure, clock drift, memory exhaustion, and CPU overload. Each scenario must recover automatically unless a runbook explicitly requires operator action.

## Performance Targets

The benchmark suite enforces:

- market event processing below 100 ms
- feature generation below 50 ms
- strategy selection below 20 ms
- trade decision below 20 ms
- execution submission below 250 ms
- recovery below 30 seconds

## Security Operations

`SecurityOperations` verifies controls for API credential rotation, encrypted secrets, privileged action audit, restricted database permissions, and TLS for internal communication where appropriate.

## Runbooks

`RunbookLibrary` includes runbooks for database recovery, broker recovery, server recovery, kill switch activation, manual trading suspension, emergency shutdown, and disaster recovery.

Each runbook contains symptoms, diagnosis, recovery steps, verification, and escalation.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\production_readiness.py
```

Expected shape:

```text
Production Readiness

Health
11/11 services healthy

Heartbeats
11 received

Metrics
16 Prometheus samples

Structured Logs
8 JSON records

Tracing
8 spans

Alerts
0 critical

Recovery
READY

State Sync
REPAIRED

Disaster Recovery
RPO 5m / RTO 15m

Backups
RESTORED

Pre-Market
7/7 checks pass

Failure Injection
7/7 recovered

Latency
PASS

Runbooks
7 ready

Capital Protection
YES
```
