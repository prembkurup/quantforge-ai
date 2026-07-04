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

Capital Protection
YES
```
