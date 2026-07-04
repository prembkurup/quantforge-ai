from quantforge.live import LiveTradingEngine


def main() -> None:
    result = LiveTradingEngine().run()

    print("System")
    print()
    print("Connect")
    print("YES" if result.connected else "NO")
    print()
    print("Receive Market")
    print(f"{result.events_processed} events")
    print()
    print("Generate Signals")
    print(len(result.signals))
    print()
    print("Execute")
    print(f"{len(result.executions)} orders")
    print()
    print("Monitor")
    print(f"{len(result.positions)} open positions")
    print()
    print("Recover")
    print("YES" if result.recovery_completed else "NO")
    print()
    print("Synchronize")
    print("YES" if not result.synchronization.repaired else "REPAIRED")
    print()
    print("Run")
    print("24/7 READY" if result.dashboard.run_24_7_ready else "NOT READY")


if __name__ == "__main__":
    main()
