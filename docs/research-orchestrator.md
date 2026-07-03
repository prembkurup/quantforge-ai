# Research Orchestrator

The Research Orchestrator is the coordinator that sits between institutional knowledge and strategy generation.

It exists because QuantForge AI now has strong components:

- market data
- Calculation Engine
- Feature Engine
- Market Regime Engine
- Research Knowledge Base
- Hypothesis Management

The orchestrator decides how those pieces should be used before Strategy Factory generates anything.

```text
Hypothesis
  -> Feature Context
  -> Market Regime
  -> Knowledge Base Lookup
  -> Research Orchestrator
  -> Plugin Framework
  -> Strategy Templates
```

## Responsibilities

- Ensure every experiment has a hypothesis.
- Read current market context and required features.
- Query Knowledge Base scores and recommendations.
- Block known weak combinations.
- Convert evidence into experiment constraints.
- Recommend the next experiments.
- Decide whether to run, refine, skip, or collect more evidence.

## Decisions

The V1 orchestrator returns one of:

- `run_experiment`
- `refine_hypothesis`
- `skip_known_failure`
- `collect_more_evidence`

This means Strategy Factory should not receive raw random requests. It should receive a constrained research plan.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\orchestrate_research.py --pair EUR_USD --timeframe H1 --regime TRENDING --session London
```

Example output includes:

- decision
- hypothesis status
- confidence
- recommended features
- recommended plugins
- recommended regimes
- blocked plugins
- constraints for Strategy Factory
- next experiment recommendations
- reasons
