# Workstream 1 - Institutional Strategy Library

Workstream 1 scales the research system beyond Version 1.0 acceptance and focuses on the platform's core value: building an institutional-quality strategy library.

## Objective

Build a large, validated, auditable Strategy Asset library that can feed portfolio construction, paper trading, and controlled live capital scaling.

## Targets

| Target | Range |
| --- | ---: |
| Experiments | 500,000-1,000,000 |
| Validated Strategy Assets | 500-2,000 |
| Production-grade strategies | 50-100 |

The default workstream plan executes 750,000 experiments, validates 1,000 Strategy Assets, and publishes 75 production-grade strategies.

## Research Programs

The library is built across five independent research programs:

- Trend Following
- Mean Reversion
- Breakout
- Momentum
- Volatility

Each program has its own templates, experiment allocation, validated asset target, production-grade target, audit events, and Knowledge Base updates.

## Strategy Asset Requirements

Every validated Strategy Asset must include:

- Validation Grade A
- confidence >= 90%
- profit factor >= configured minimum
- maximum drawdown <= configured maximum
- walk-forward PASS
- Monte Carlo PASS
- cross-pair PASS
- cross-timeframe PASS
- stress test PASS
- complete decision trace
- Strategy Passport
- reproducibility key

Production-grade status is intentionally scarce. A strategy can be validated and still not enter the production-grade set.

## Outputs

The workstream produces:

- validated Strategy Asset library
- production-grade strategy set
- Strategy Library KPI report
- Strategy Library dashboard
- archived Strategy Library report
- audit trail
- reproducibility key

## Demo

```powershell
.\.venv\Scripts\python .\scripts\strategy_library.py
```

Expected output includes 750,000 experiments, 1,000 validated Strategy Assets, 75 production-grade strategies, Knowledge Base growth, average confidence, average profit factor, max drawdown, portfolio readiness, and a reproducibility key.
