from __future__ import annotations

from quantforge.dashboard.service import DashboardService


def main() -> None:
    payload = DashboardService().intraday_decision_intelligence()
    opportunity = payload["opportunity_score"]
    quality = payload["market_quality"]
    eligibility = payload["eligibility"]
    decision = payload["trade_decision"]
    plan = payload["daily_trading_plan"]
    budget = payload["dynamic_daily_risk_budget"]
    status = payload["intraday_trading_status"]

    print("QuantForge AI Version 2.0")
    print("Milestone 24 - Intraday Decision Intelligence")
    print()
    print("Opportunity Score")
    print(f"{opportunity['score']}/100 - {opportunity['band']}")
    print()
    print("Market Quality")
    print(f"{quality['score']}/100 - {quality['rating']}")
    print()
    print("Trade Eligibility")
    print(eligibility["status"])
    print("; ".join(eligibility["reasons"]) or "Eligible for trade decision.")
    print()
    print("Final Decision")
    print(f"{decision['decision']} ({decision['confidence']})")
    print(decision["reason"])
    print()
    print("Intraday Trading Status")
    print(status["status"])
    print("; ".join(status["reasons"]))
    print()
    print("Daily Trading Plan")
    print(f"Preferred Sessions: {', '.join(plan['preferred_sessions'])}")
    print(f"Daily Risk Budget: {plan['daily_risk_budget']}")
    print(f"Maximum Trades: {plan['maximum_trades']}")
    print(f"Risk Policy: {budget['policy']}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
