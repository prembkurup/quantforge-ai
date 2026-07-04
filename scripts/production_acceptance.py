from __future__ import annotations

from quantforge.infrastructure import ProductionAcceptanceManager


def main() -> None:
    result = ProductionAcceptanceManager().accept()

    print("Production Acceptance and Live Capital Qualification")
    print()
    print(f"Version: {result.report.version}")
    print(f"Decision: {result.report.decision.value}")
    print(f"Approved: {'YES' if result.approved else 'NO'}")
    print(f"Production Score: {result.score.overall:.1f}%")
    print(f"Threshold: {result.score.threshold:.1f}%")
    print(f"Current Capital Stage: {result.capital_policy.current_stage.value}")
    print(f"Initial Capital: ${result.capital_policy.stages[0].capital_usd}")
    print(f"Active Strategy Assets: {result.dashboard.active_strategy_assets}")
    print(f"Portfolio: {result.dashboard.portfolio_summary}")
    print(f"Recent Incidents: {result.dashboard.recent_incidents}")
    print(f"Checklist: {'PASS' if result.checklist.passed else 'FAIL'}")
    print(f"Signoffs: {sum(signoff.recorded for signoff in result.signoffs)} recorded")
    print(f"Version 1.0 Feature Complete: {'YES' if result.version_declared_feature_complete else 'NO'}")
    print()
    print("Domains")
    for domain in result.domains:
        print(f"- {domain.domain.value}: {domain.status.value}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
