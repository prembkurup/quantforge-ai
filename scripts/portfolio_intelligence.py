from __future__ import annotations

from quantforge.dashboard.service import DashboardService


def main() -> None:
    payload = DashboardService().portfolio_intelligence()
    health = payload["health"]
    kpis = payload["kpis"]
    allocation = payload["allocation"]
    drift = payload["drift"]
    stress = payload["stress"]
    review = payload["daily_review"]
    lifecycle = payload["lifecycle"]

    print("QuantForge AI Version 2.0")
    print("Milestone 25 - Portfolio Intelligence")
    print()
    print("Portfolio Health")
    print(f"{health['status']} ({health['score']}/100)")
    print("; ".join(health["reasons"]) or "All portfolio intelligence checks passed.")
    print()
    print("Portfolio KPIs")
    print(f"Strategies: {kpis['strategy_count']}")
    print(f"Families: {kpis['family_count']}")
    print(f"Instruments: {kpis['instrument_count']}")
    print(f"Expected PF: {kpis['expected_profit_factor']}")
    print(f"Expected Drawdown: {kpis['expected_drawdown']}")
    print()
    print("Allocation")
    print("APPROVED" if allocation["approved"] else "REBALANCE REQUIRED")
    for action in allocation["rebalance_actions"]:
        print(f"- {action}")
    print()
    print("Drift")
    print(drift["status"])
    print(", ".join(drift["degraded_strategies"]) or "No degraded strategies.")
    print()
    print("Stress")
    print(f"Worst drawdown: {stress['worst_expected_drawdown']}")
    print(f"Capital at risk: {stress['capital_at_risk']}")
    print()
    print("Daily Review")
    print(review["review_id"])
    for action in review["next_actions"]:
        print(f"- {action}")
    print()
    print("Lifecycle")
    print(f"{lifecycle['stage']} / {lifecycle['status']}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
