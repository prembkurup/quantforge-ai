from quantforge.live import ShadowTradingPlatform


def main() -> None:
    result = ShadowTradingPlatform().run()

    print("System")
    print()
    print("Receive Live Market")
    print("YES" if result.live_market_received else "NO")
    print()
    print("Generate Signals")
    print(result.signals_generated)
    print()
    print("Trade Paper Portfolio")
    print(f"{len(result.paper_orders)} orders")
    print()
    print("Monitor Drift")
    print(f"{len(result.drift_metrics)} dimensions")
    print()
    print("Audit Decisions")
    print("100%" if result.monthly_review.decision_trace_coverage == 1.0 else "INCOMPLETE")
    print()
    print("Generate Reports")
    print("Daily + Monthly")
    print()
    print("Update Knowledge")
    print(f"{result.knowledge_updates} records")
    print()
    print("Recommend Promotion")
    print(result.monthly_review.decision.value)
    print()
    print("Digital Twin")
    print("MATCH" if result.digital_twin.decisions_match else "DIVERGED")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
