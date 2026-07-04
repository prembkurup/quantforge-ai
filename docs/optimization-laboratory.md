# Optimization Laboratory

The Optimization Laboratory answers a different question from a normal optimizer:

```text
What is the best stable parameter space for this strategy?
```

It does not try to find the highest historical profit. Single-point winners are treated as overfitting risk unless the surrounding parameter region is also strong.

## Pipeline

```text
Composer
  -> Optimization Laboratory
  -> Stable Parameters
  -> Research Review Board
  -> Backtesting
  -> Validation
```

Optimization produces parameter candidates and stable regions. Backtesting and validation come later.

## Components

- `OptimizationPlanner` chooses the search algorithm, parameter ranges, objective, and stability objective.
- `SearchEngine` runs grid, random, Bayesian, Optuna, genetic, particle swarm, and future ML search surfaces. The first implementation demonstrates grid search.
- `StabilityAnalyzer` finds broad regions where nearby parameter values perform well.
- `SensitivityAnalyzer` rejects sharp peaks where small parameter changes cause large performance drops.
- `ParameterLandscapeGenerator` produces parameter surfaces such as EMA fast, EMA slow, and profit factor.
- `RobustnessEstimator` labels regions as weak, medium, or strong.
- `OptimizationKnowledgeWriter` writes stable parameter regions back into the Research Knowledge Base.
- `OptimizationReport` summarizes tested parameters, stable regions, recommended regions, best region, landscapes, knowledge writes, and review status.
- `ResearchReviewBoard` is an automated gate that checks parameter stability, complexity score, diversity score, decision trace, and Knowledge Base alignment before validation.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\optimize_strategy.py
```

Expected shape:

```text
Strategy
Trend Pullback

Parameters Tested
124,000

Stable Regions
7

Recommended Regions
2

Best Region
EMA Fast
18-26

EMA Slow
60-90

ATR
1.8-2.3
```

The result is a region, not a single value like `EMA = 21`.

## Rule

Never promote a strategy to expensive validation just because one parameter point wins.

The automated Research Review Board must approve the research output first:

```text
Parameter Stability
  + Complexity Score
  + Diversity Score
  + Decision Trace
  + Knowledge Base Alignment
  -> Approved for Backtesting and Validation
```
