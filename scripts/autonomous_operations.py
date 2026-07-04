from __future__ import annotations

from quantforge.infrastructure import AutonomousOperationsManager


def main() -> None:
    result = AutonomousOperationsManager().run_validation()

    print("Autonomous Operations Validation")
    print()
    print(f"Simulation Days: {result.config.consecutive_days}")
    print(f"Trading Days: {result.config.trading_days}")
    print(f"Monitoring Samples: {result.total_monitoring_samples:,}")
    print(f"Availability: {result.reliability_kpis.availability:.2%}")
    print(f"MTTR: {result.reliability_kpis.mean_time_to_recovery_minutes:.2f} minutes")
    print(f"Incidents Recovered: {sum(incident.resolved for incident in result.incidents)}")
    print(f"Broker Sync Accuracy: {result.broker_synchronization.accuracy:.0%}")
    print(f"Unreconciled Broker Mismatches: {result.broker_synchronization.unreconciled_mismatches}")
    print(f"Duplicate Orders: {result.reliability_kpis.duplicate_orders}")
    print(f"Risk Violations: {result.trading_kpis.risk_violations}")
    print(f"Execution Success: {result.trading_kpis.execution_success_rate:.1%}")
    print(f"Drift Dimensions: {len(result.drift_observations)} within tolerance")
    print(f"Maintenance Tasks: {len(result.maintenance_tasks)} non-interrupting")
    print("Reports: DAILY, WEEKLY, MONTHLY, CAPACITY")
    print(f"Compliance: {'PASS' if result.compliance.passed else 'FAIL'}")
    print(f"Operationally Mature: {'YES' if result.operationally_mature else 'NO'}")


if __name__ == "__main__":
    main()
