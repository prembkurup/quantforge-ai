# Production Acceptance and Live Capital Qualification

Milestone 20 is the formal QuantForge AI Version 1.0 acceptance process.

This milestone does not introduce trading functionality. It validates that the full platform is ready to operate with real capital under controlled governance.

## Acceptance Decision

Possible outcomes:

- `APPROVED_FOR_PRODUCTION`
- `APPROVED_WITH_RESTRICTIONS`
- `RETURNED_FOR_REMEDIATION`
- `REJECTED`

Only `APPROVED_FOR_PRODUCTION` allows controlled live capital at the first capital stage.

## Acceptance Domains

The acceptance manager evaluates eight weighted domains:

| Domain | Weight |
| --- | ---: |
| Engineering | 15% |
| Research | 20% |
| Strategy | 20% |
| Risk | 15% |
| Operations | 10% |
| Infrastructure | 10% |
| Security | 5% |
| Business | 5% |

The default production threshold is 95%.

## Evidence Sources

`ProductionAcceptanceManager` consumes evidence from:

- Production Certification Platform
- Institutional Research Campaign
- Autonomous Operations Validation
- SRE and recovery controls
- Shadow and paper trading evidence
- Strategy validation and Strategy Passport evidence

## Engineering Acceptance

Engineering acceptance verifies:

- no unresolved critical defects
- automated tests passing
- integration tests passing
- performance tests passing
- documentation complete
- database migrations verified
- Docker deployment verified
- rollback tested
- backup restoration tested

Failure in this domain blocks production.

## Research and Strategy Acceptance

Research acceptance measures scientific process quality rather than profitability.

The Version 1.0 evidence includes:

- 100,000 experiments
- 300 approved Strategy Assets
- 104,000 Knowledge Base records
- 100% reproducible campaign lineage
- hypothesis-led research with no random strategy generation

Strategy acceptance requires Grade A Strategy Assets, confidence >= 90%, complete Strategy Passports, complete decision traces, and mandatory validation passes for walk-forward, Monte Carlo, cross-pair, cross-timeframe, and stress testing.

## Paper Trading and Operations Qualification

Operations qualification uses the Milestone 19 90-day production simulation:

- 90 simulation days
- 65 trading days
- 93,600 monitoring samples
- 99.97% availability
- 0 duplicate orders
- 0 unreconciled broker mismatches
- 0 risk violations
- recovered incidents under recovery objectives
- daily, weekly, monthly, and capacity reports archived

## Capital Scaling Policy

Capital progression is gradual and evidence-based:

| Stage | Capital | Requirement |
| --- | ---: | --- |
| Stage A | $100 | production approval recorded |
| Stage B | $250 | 30 successful trading days |
| Stage C | $500 | 60 successful trading days |
| Stage D | $1,000 | 90 successful trading days |

Capital increases require stable strategy performance, operational reliability, no critical incidents, and risk compliance. Scaling is never based solely on profitability.

## Release Approval

Release approval records signoff from:

- Engineering
- Research
- Risk
- Operations
- Final Production Approval Manager

Every signoff is stored as acceptance evidence.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\production_acceptance.py
```

Expected output includes `APPROVED_FOR_PRODUCTION`, a 100% score, Stage A capital, all domains passing, a passing checklist, recorded signoffs, and Version 1.0 feature-complete declaration.

## Version 1.0 Declaration

After acceptance, QuantForge AI Version 1.0 is feature complete. Future improvements must follow controlled release management, and new functionality should be introduced only when operational evidence demonstrates a need for change.

Success is measured by scientific research quality, strategy robustness, capital protection, operational reliability, auditability, continuous learning, and long-term sustainability.
