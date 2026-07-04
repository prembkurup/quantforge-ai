# Production Strategy Management Platform

The Production Strategy Management Platform is the bridge between research and live trading.

Research publishes approved Strategy Assets. Production decides whether to install, paper trade, promote, monitor, roll back, disable, archive, or retire them.

Think of it like an internal app store for strategies.

## Pipeline

```text
Research
  -> Approved Strategy Asset
  -> Strategy Catalog
  -> Portfolio Manager
  -> Deployment Manager
  -> Paper Trading
  -> Production
  -> Performance Monitor
  -> Retirement
```

## Components

- `StrategyCatalog` stores every Strategy Asset, version, validation, deployment, and retirement record.
- `StrategyRegistry` tracks active, inactive, paper, production, deprecated, and retired states.
- `DeploymentManager` installs, upgrades, rolls back, disables, promotes, and archives Strategy Assets.
- `PortfolioManager` activates portfolios of strategies instead of one strategy at a time.
- `CapitalAllocator` assigns capital across strategy themes, such as trend, mean reversion, breakout, and scalping.
- `StrategyScheduler` controls sessions and timeframes, such as London-only or H1/H4-only execution.
- `LivePerformanceMonitor` compares research performance with live performance.
- `DriftDetector` flags live underperformance versus research expectations.
- `RetirementManager` retires strategies when performance falls below thresholds.
- `LiveLearningLoop` updates the Knowledge Base, Research Analytics, and Strategy Passport from live trades.
- `ProductionDashboard` summarizes approved, installed, paper, production, retired, and drift states.

## Strategy Marketplace

The platform should not think in terms of one active strategy.

```text
250 Approved Strategies
  -> Portfolio Manager
  -> 12 Active Strategies
  -> Capital Allocator
  -> Live Trading
```

Research becomes portfolio optimization.

## Production Loop

```text
Research
  -> Strategy Asset
  -> Deployment
  -> Live Trading
  -> Performance
  -> Knowledge Base
  -> Research
```

Every live trade updates research memory and long-term strategy identity.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\deploy_strategy.py
```

Expected shape:

```text
Approved
YES

Installed
YES

Portfolio
QF-PORT-0001

Capital Allocated
YES

Paper Trading
YES

Production
YES
```

## Next Phase

After this milestone, stop adding major platform components. The next work should harden the system:

- comprehensive integration tests
- performance and load testing
- memory profiling
- long-running stability tests
- failure injection
- recovery testing
- documentation review
- observability and operational excellence
