# Constraint-Based Strategy Composer

The Strategy Composer assembles candidate strategies from reusable plugins. It does not optimize, backtest, or validate performance.

Milestone 8 changes the composer from a random generator into a constraint-based planner:

```text
Research Goal
  -> Constraint Builder
  -> Knowledge Base
  -> Plugin Registry
  -> Strategy Composer
  -> Candidate Strategies
```

## Pipeline

```text
Research Goal
  -> Constraint Builder
  -> Knowledge Base
  -> Compatibility Engine
  -> Dependency Engine
  -> Strategy Graph Builder
  -> Complexity Scoring
  -> Diversity Filter
  -> Candidate Strategies
```

Only structurally valid and sufficiently distinct strategies should reach optimization.

## Components

- `ConstraintBuilder` converts research goals into hard rules, such as maximum drawdown, minimum profit factor, minimum trades, instrument, session, and regime.
- `CompatibilityEngine` rejects incompatible plugin combinations, such as trend entries paired with range-only exits.
- `DependencyEngine` verifies plugin dependencies, required features, and required calculations.
- `StrategyGraphBuilder` represents each candidate as a graph: market regime, entry, confirmation, risk, trade management, and exit.
- `StrategyValidator` rejects missing plugins, invalid combinations, circular dependencies, missing features, missing calculations, and constraint violations before optimization.
- `ComplexityAnalyzer` estimates structural complexity so high-overfit candidates can be avoided.
- `DiversityFilter` removes near-duplicate candidates before optimization.
- `DecisionTrace` records why constraints were applied, which registry choices were made, which filters ran, and why candidates survived or were rejected.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\compose_strategy.py
```

Expected shape:

```text
Research Goal
Trend Pullback

Constraints Applied
7

Generated
2,840 candidates

Rejected
2,120

Valid
720

Unique
168

Ready for Optimization
168
```

## Rule

Never optimize an invalid strategy.

The research pipeline is now:

```text
Compose
  -> Validate Structure
  -> Estimate Complexity
  -> Remove Duplicates
  -> Optimization Laboratory
  -> Backtest
  -> Validate Performance
```
