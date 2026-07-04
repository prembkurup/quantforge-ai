# Production Certification Platform

Milestone 17 adds the final quality gate before controlled live trading. QuantForge AI is not allowed to trade live because it is feature-complete; it must first prove that it is technically reliable, operationally resilient, statistically sound, financially bounded, and fully auditable.

## Certification Pipeline

```text
Research Platform
  -> Production Validation
  -> Operational Validation
  -> Risk Certification
  -> Infrastructure Certification
  -> Performance Certification
  -> Security Certification
  -> Governance Certification
  -> Final Certification
  -> Live Trading Approval
```

## Certification Domains

The certification engine evaluates mandatory domains:

- Research Certification: reproducibility, hypothesis traceability, feature consistency, plugin versioning, decision trace, and Knowledge Base updates.
- Strategy Certification: grade A validation, confidence threshold, stable parameter regions, low complexity, high diversity, robustness, complete Strategy Passport, and approved deployment decision.
- Infrastructure Certification: database, Redis, broker, live trading services, logging, metrics, tracing, recovery, synchronization, and duplicate-order controls.
- Operations Certification: 60-day shadow evidence, automatic recovery, state persistence, backup restoration, and pre-market checkpoints.
- Security Certification: credential rotation, encrypted secrets, database permissions, internal TLS, audit logging, and no hard-coded credentials.
- Risk Certification: daily loss guard, drawdown, exposure, kill switch, portfolio allocation, and capital limits.
- Performance Certification: feature generation, strategy selection, trade decision, execution submission, recovery, and database target checks.
- Governance Certification: approval policy, traceability, strategy versioning, audit trail, and live-gate enforcement.

Supporting certifications also run for disaster recovery, data integrity, audit, and knowledge consistency.

## Production Readiness Score

The weighted production readiness score follows the Milestone 17 policy:

| Domain | Weight |
| --- | ---: |
| Research | 20% |
| Infrastructure | 20% |
| Security | 15% |
| Operations | 15% |
| Risk | 15% |
| Performance | 10% |
| Governance | 5% |

The default certification threshold is 95%. Strategy, disaster recovery, data integrity, audit, and knowledge checks are mandatory gate evidence even when they are not part of the weighted score.

## Approval Decisions

Possible outcomes:

- `CERTIFIED`: all mandatory domains pass, no critical findings remain, score meets threshold, and controlled live trading is authorized.
- `PROVISIONALLY_CERTIFIED`: score is near threshold but live trading remains blocked.
- `REQUIRES_REMEDIATION`: failed evidence must be remediated before certification can proceed.
- `REJECTED`: critical findings block live trading.

Only `CERTIFIED` authorizes controlled live trading.

## Certification Report

The report includes:

- executive summary
- certification results
- failed items
- recommendations
- performance benchmarks
- risk summary
- infrastructure summary
- approval decision

The dashboard exposes research, strategies, infrastructure, operations, risk, security, performance, knowledge, certification score, and production readiness status.

## Demo

Run:

```powershell
.\.venv\Scripts\python .\scripts\certify_production.py
```

Expected output:

```text
Production Certification

Research
PASS

Strategy
PASS

Infrastructure
PASS

Operations
PASS

Risk
PASS

Security
PASS

Performance
PASS

Governance
PASS

Score
100%

Decision
CERTIFIED

Live Trading Approval
AUTHORIZED
```

## Exit Criteria

Milestone 17 is complete when all certification domains pass, the readiness score meets threshold, critical findings are zero, the report is approved, and QuantForge AI is authorized only for controlled live trading.
