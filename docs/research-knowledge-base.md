# Research Knowledge Base

The Research Knowledge Base is the platform memory layer for QuantForge AI. It records what research has learned so the system does not repeatedly rediscover the same winners, failures, market constraints, or risk warnings.

It sits after the Market Regime Engine and before plugin or strategy template selection:

```text
OHLCV
  -> Calculation Engine
  -> Feature Engine
  -> Market Regime Engine
  -> Research Knowledge Base
  -> Plugin Framework
  -> Strategy Templates
```

## Purpose

The Knowledge Base stores research conclusions and supporting evidence, not raw market data and not routine calculation outputs.

It should answer questions such as:

- Has this idea already been tested on this instrument and timeframe?
- Did this setup work in this market regime and session?
- Which features, regimes, templates, or plugins repeatedly fail together?
- Which market contexts deserve more experiments?
- Which discovered edges are mature enough to influence strategy generation?

## Knowledge Records

A knowledge record captures one durable research finding:

- finding id
- finding type: positive edge, negative edge, neutral, risk warning, data quality note
- hypothesis or setup name
- instrument
- timeframe
- market regime
- session context
- feature conditions
- strategy template or plugin family, when applicable
- experiment ids and run ids that support the finding
- outcome summary
- key metrics
- confidence score
- evidence count
- validity window
- tags
- version

Example:

```json
{
  "finding_type": "positive_edge",
  "setup": "trend_pullback",
  "instrument": "EUR_USD",
  "timeframe": "H1",
  "market_regime": "TRENDING",
  "session": "London",
  "feature_conditions": {
    "trend_direction": "bullish",
    "pullback_state": true,
    "volatility_regime": "medium"
  },
  "outcome": "works_well",
  "confidence": 0.81,
  "evidence_count": 37
}
```

Counterexample:

```json
{
  "finding_type": "negative_edge",
  "setup": "rsi_oversold_reversal",
  "instrument": "USD_JPY",
  "timeframe": "M1",
  "feature_conditions": {
    "rsi": "<30"
  },
  "outcome": "fails",
  "confidence": 0.76,
  "evidence_count": 22
}
```

## Consumers

The Knowledge Base is read before expensive research begins:

- Experiment Runner checks whether a similar experiment already exists.
- Plugin Framework uses findings to prioritize compatible plugins.
- Strategy Template Engine avoids templates with strong negative evidence in the current context.
- Research Analytics updates or retires findings as new evidence arrives.

The Knowledge Base is written after experiments and validation:

- backtest and validation results become evidence
- repeated results increase or decrease confidence
- contradictory evidence lowers confidence instead of deleting history

## Design Rules

- Never treat one backtest as knowledge by itself.
- Store both successful and failed ideas.
- Link findings back to experiment lineage.
- Version feature, regime, plugin, and template dependencies.
- Separate research conclusions from raw OHLCV and derived calculation caches.
- Prefer explainable records before ML-driven recommendations.
