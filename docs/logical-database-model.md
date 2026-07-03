# Logical Database Model

Source: `QuantForge AI - Chapter 5.pdf`.

Chapter 5 defines the logical database model for QuantForge AI. It describes business entities, relationships, ownership, lifecycle, data classification, and access patterns. It is independent of PostgreSQL; physical table details belong in Chapter 6.

## Design Principles

- Raw market data is immutable.
- Indicators are derived data and are calculated by the Research Engine.
- Every business entity has exactly one owning service.
- Every critical change must be auditable.
- Research and production data are isolated.
- Only validated strategies are promoted to production.

## Aggregate Roots

### Instrument Aggregate

Root: `Instrument`

Owned entities:

- Candle
- Tick
- Spread
- Trading Session
- Market Calendar

Instrument owns all market data. Historical candles must not be modified after validation.

### Strategy Aggregate

Root: `Strategy`

Owned entities:

- Version
- Parameters
- Components
- Deployment
- Approval

A strategy cannot skip lifecycle stages. Strategy versions are immutable after approval.

### Research Aggregate

Root: `Experiment`

Owned entities:

- Dataset
- Optimization
- Feature Set
- Backtest
- Validation
- Analytics
- Published Strategy

Everything in research belongs to an experiment. A research run is an execution record inside an experiment, not the top-level business object. Research cannot deploy directly; it can only publish approved strategy versions for the Strategy Service.

### Trading Aggregate

Root: `Signal`

Owned entities:

- Order
- Execution
- Position
- Trade

Signals create orders. Orders create executions. Executions update positions. Positions become completed trades.

## Entity Ownership

- Data Service owns candles, ticks, spreads, and instruments.
- Research Service owns features, research runs, optimization, and backtests.
- Strategy Service owns strategy templates, strategies, and versions.
- Trading Service owns signals, orders, executions, and positions.
- Risk Service owns risk rules, exposure, and limits.
- Reporting Service owns reports and statistics.
- API Service owns users, roles, and configuration.

Only the owning service may modify an entity. Other services have read-only access where appropriate.

## Lifecycles

### Strategy Lifecycle

1. Draft
2. Generated
3. Optimized
4. Backtested
5. Validated
6. Paper Trading
7. Approved
8. Production
9. Retired
10. Archived

### Research Lifecycle

1. Research Project
2. Draft Experiment
3. Configured Experiment
4. Queued Experiment
5. Running Experiment
6. Completed Experiment
7. Validated Experiment
8. Published Experiment
9. Archived Experiment

Execution records inside the experiment include dataset selection, feature set, strategy template, parameter search, research run, optimization, backtesting, validation, analytics, candidate strategies, and published strategies.

## Data Classification

### Permanent Data

Examples:

- Instruments
- Candles
- Strategies
- Strategy versions
- Trades
- Executions
- Reports
- Configurations
- Audit logs

Permanent data is backed up regularly.

### Cached Data

Examples:

- Indicator results
- Feature vectors
- Market regime
- Latest signals

Cached data may be regenerated.

### Temporary Data

Examples:

- Optimization trials
- Research sessions
- Import buffers
- Calculation buffers

Temporary data may be deleted automatically.

### Archive Data

Examples:

- Old backtests
- Old research runs
- Archived reports
- Old logs

Archive data is retained for historical analysis.

## Read / Write Responsibilities

The system follows CQRS principles.

Write side services:

- Market Data Service
- Research Service
- Strategy Service
- Trading Service
- Risk Service

Read side services:

- Dashboard
- Reporting
- Live Trading
- Analytics
- Monitoring

## Strategy Promotion Workflow

Research cannot deploy directly.

1. Research
2. Backtest
3. Validation
4. Approval
5. Strategy Publisher
6. Production Strategy Store
7. Live Trading

## Data Access Rules

- Research cannot modify production trades.
- Trading cannot modify research results.
- Risk Engine can reject any order.
- Execution Engine never bypasses Risk Engine.
- Production Strategy Store contains only approved strategy versions.

## Storage Classes

- Hot: live trading data requiring fast access.
- Warm: frequently accessed research data.
- Cold: historical research and completed backtests.
- Archive: long-term storage.

These classifications guide physical partitioning and indexing in Chapter 6.

## Versioning Rules

Version-controlled entities:

- Plugins
- Strategy templates
- Strategies
- Strategy parameters
- Risk profiles
- Configurations

Historical versions are never overwritten.

## Plugin Registry Rule

Plugin types share a single registry. Entry, exit, risk, confirmation, market regime, position sizing, validation, ranking, indicator, and feature plugins are rows in the same plugin registry. Type-specific metadata belongs in companion configuration tables.

## Experiment-Centric Research Rule

Experiments are the primary research unit. Datasets, feature sets, strategy templates, parameter searches, backtests, validations, analytics, and published strategies must be traceable to an experiment.

Indicators are derived inputs. They should not become the organizing center of the product or database.

## Experiment Management Rule

Every research activity is managed by the Experiment Management System. Experiments must record hypothesis, dataset version, feature set version, plugin versions, parameter space, optimization algorithm, random seed, software version, resource usage, results, and publication approval.

Failed experiments retain metadata and results for future analysis.

## Audit Requirements

Required audit events:

- Strategy approval
- Strategy deployment
- Strategy retirement
- Configuration changes
- User authentication
- Trade execution
- Risk events
- Kill switch activation

Audit records are immutable.
