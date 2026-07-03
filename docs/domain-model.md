# Enterprise Domain Model

Source: `QuantForge AI - Chapter 4.pdf`.

Chapter 4 defines the conceptual domain model that the PostgreSQL schema, Python services, APIs, and documentation should follow. It is not a physical table design by itself; it defines ownership boundaries and core business concepts.

## Domains

QuantForge AI is divided into these domains:

- Market Data
- Instrument
- Plugin
- Research
- Strategy
- Backtesting
- Validation
- Live Trading
- Risk Management
- Reporting
- Administration
- Infrastructure

## Market Data Domain

Owns historical and live market data.

Core entities:

- Candle
- Tick
- Spread
- Market Session
- Data Source
- Data Import Job
- Data Quality Check
- Missing Data Record

Rules:

- Candles are immutable after validation.
- Duplicate candles are not allowed.
- Only completed candles are used for trading decisions.
- Candle timestamps must be normalized to UTC.

## Instrument Domain

Owns tradable market definitions.

Core entities:

- Asset Class
- Instrument
- Timeframe
- Broker Instrument Mapping

Rules:

- Instrument symbols must be normalized internally.
- Broker symbols are adapter-specific mappings.
- The platform should support additional asset classes without redesign.

## Plugin Domain

Owns discoverable strategy components.

Core entities:

- Plugin
- Plugin Category
- Plugin Version
- Plugin Parameter
- Plugin Dependency

Plugin categories:

- Market regime
- Entry model
- Confirmation
- Exit model
- Risk model
- Position sizing

Rules:

- Plugins must declare metadata, dependencies, parameters, inputs, and outputs.
- Plugin versions must be immutable after release.
- Strategy discovery should assemble structured plugins instead of random indicator combinations.
- Plugin persistence uses one plugin registry with type-specific metadata/configuration tables, not one table per plugin type.

## Research Domain

Owns offline experimentation.

Core entities:

- Experiment
- Dataset
- Feature Set
- Parameter Search
- Research Run
- Optimization Run
- Candidate Result
- Experiment Analytics
- Published Strategy

Rules:

- Experiment is the primary unit of research work.
- Research may use Parquet cache.
- Research must not place live orders.
- Research runs are execution records inside experiments.
- Research outputs must be reproducible from PostgreSQL source data, dataset definitions, feature sets, plugin versions, templates, and recorded parameters.

## Strategy Domain

Owns approved strategy definitions.

Core entities:

- Strategy Template
- Strategy
- Strategy Version
- Strategy Deployment

Rules:

- Strategies are assembled from plugins.
- Strategy versions are immutable after approval.
- Only approved strategy versions can be deployed for live trading.

## Backtesting Domain

Owns historical simulation.

Core entities:

- Backtest Run
- Backtest Trade
- Equity Curve
- Drawdown Record
- Performance Metric

Rules:

- Backtests must model spread, slippage, and trading costs.
- Results must be tied to exact data range, parameters, and strategy version.

## Validation Domain

Owns promotion gates before live trading.

Core entities:

- Validation Run
- Walk-Forward Test
- Out-of-Sample Test
- Robustness Test
- Validation Result

Rules:

- Strategies failing configured thresholds are rejected.
- Only validated strategies can become live candidates.

## Live Trading Domain

Owns live signal and execution flow.

Core entities:

- Live Signal
- Order
- Position
- Execution
- Trade Event

Rules:

- Live trading consumes approved strategy versions only.
- Every order must have a persisted audit trail.
- Live trading uses Redis only for transient state and cache.

## Risk Management Domain

Owns runtime safety constraints.

Core entities:

- Risk Rule
- Position Limit
- Exposure Limit
- Kill Switch
- Risk Event

Rules:

- Risk checks run before order execution.
- Kill switches override strategy signals.
- Risk decisions must be logged.

## Reporting Domain

Owns dashboards, exports, and metrics.

Core entities:

- Report
- Dashboard
- Metric Snapshot
- Export Job

## Administration Domain

Owns users, credentials, and platform configuration.

Core entities:

- User
- Role
- Permission
- API Credential
- Audit Log

Rules:

- Secrets must not be hard-coded.
- Credentials must be encrypted or delegated to the deployment secret manager.

## Infrastructure Domain

Owns deployment and runtime health.

Core entities:

- Server
- Service
- Job
- Health Check
- Alert
- Backup

## Key Relationships

- Instruments have candles, ticks, and spreads.
- Plugins compose strategy templates.
- Strategy templates produce strategy versions.
- Research runs produce candidate results.
- Backtests and validation runs evaluate strategy versions.
- Approved strategy versions can be deployed.
- Deployments can generate live signals.
- Live signals can create orders.
- Orders can create executions and positions.
- Risk rules can block signals and orders.
