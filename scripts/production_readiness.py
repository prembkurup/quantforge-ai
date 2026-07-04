from quantforge.infrastructure import ProductionReadinessPlatform


def main() -> None:
    report = ProductionReadinessPlatform().run_report()

    print("Production Readiness")
    print()
    print("Health")
    print(f"{report.healthy_services}/{len(report.services)} services healthy")
    print()
    print("Heartbeats")
    print(f"{len(report.heartbeats)} received")
    print()
    print("Metrics")
    print(f"{len(report.metrics)} Prometheus samples")
    print()
    print("Structured Logs")
    print(f"{len(report.logs)} JSON records")
    print()
    print("Tracing")
    print(f"{len(report.traces)} spans")
    print()
    print("Alerts")
    print(f"{report.critical_alerts} critical")
    print()
    print("Recovery")
    print("READY" if all(action.completed for action in report.recovery_actions) else "BLOCKED")
    print()
    print("Capital Protection")
    print("YES" if report.capital_protected and report.duplicate_order_guard else "NO")


if __name__ == "__main__":
    main()
