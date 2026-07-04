# Institutional Research Campaign

Milestone 18 turns QuantForge AI from a component-complete research system into an autonomous quantitative research organization. The purpose is to demonstrate research outcomes: validated Strategy Assets, portfolio candidates, Knowledge Base growth, and archived campaign reports.

## Research Question

Can QuantForge AI consistently discover statistically robust trading strategies using a scientific research process?

The campaign only accepts strategies that are hypothesis-led, reproducible, explainable, validated, ranked, and auditable. Random strategy generation is not permitted.

## Scope

- Asset class: Forex
- Instrument universe: supported OANDA Forex pairs
- Timeframes: M15, H1, H4
- Historical dataset: full 10-year validated history
- Research period: entire historical database
- Validation: walk-forward, out-of-sample, Monte Carlo, cross-pair, cross-timeframe, stress testing

## Independent Programs

The campaign runs five independently managed programs:

- Trend Following: EMA Pullback, Trend Continuation, Moving Average Breakout
- Mean Reversion: Bollinger Reversal, RSI Reversal, Support/Resistance Bounce
- Breakout: Donchian Breakout, Opening Range Breakout, Volatility Expansion
- Momentum: Momentum Continuation, MACD Momentum, ADX Momentum
- Volatility: ATR Expansion, Compression Breakout, Volatility Reversal

Each program follows the same workflow:

```text
Research Goal
  -> Hypothesis Selection
  -> Experiment Planning
  -> Strategy Composition
  -> Optimization
  -> Backtesting
  -> Validation
  -> Ranking
  -> Knowledge Update
  -> Strategy Asset Publication
```

## Configurable Targets

Default institutional targets:

- 100,000+ experiments
- 1,000,000+ candidate strategies
- 100,000+ optimized strategies
- 5,000+ validated strategies
- 200-500 approved Strategy Assets
- 20-50 production candidates

These are represented by `CampaignTargets`, so the campaign can be scaled based on available compute.

## Quality Requirements

Default Strategy Asset requirements:

- Profit Factor >= 2.0
- Maximum Drawdown <= 10%
- Walk-Forward PASS
- Monte Carlo PASS
- Cross Pair PASS
- Cross Timeframe PASS
- Complexity below threshold
- Robustness high

Rejected strategies still update the Knowledge Base with failure reasons and research lessons.

## Portfolio Construction

After Strategy Asset publication, the portfolio engine selects production candidates for diversification rather than raw profit ranking alone. It reduces correlation and diversifies:

- strategy families
- market regimes
- currency exposure
- timeframes
- instruments

The demo portfolio is `QF-INST-PORT-001`.

## Reports

The campaign generates archived daily, weekly, and monthly research reports. Reports include experiments completed, new Strategy Assets, validation summaries, Knowledge Base changes, feature ranking changes, plugin performance, and recommendations.

## Demo

Run:

```powershell
.\.venv\Scripts\python .\scripts\institutional_campaign.py
```

Expected output:

```text
Institutional Research Campaign

Programs
5

Experiments
100,000

Candidate Strategies
1,000,000

Validated Strategies
5,000

Approved Strategy Assets
300

Production Candidates
29

Portfolio
QF-INST-PORT-001

Knowledge Base Growth
104,000 records

Reports
DAILY, WEEKLY, MONTHLY

Autonomous
YES
```

## Exit Criteria

Milestone 18 is complete when QuantForge AI demonstrates it can autonomously run an institutional-scale research campaign, publish validated Strategy Assets, construct a diversified portfolio candidate set, grow the Knowledge Base, preserve full traceability, and generate campaign reports without normal manual intervention.
