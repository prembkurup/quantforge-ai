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
    journal = payload["daily_trading_journal"]
    quality_metrics = payload["decision_quality_metrics"]

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
    print()
    print("Decision Timeline")
    for item in payload["decision_timeline"]:
        print(f"{item['stage']}: {item['status']} - {item['reason']}")
    print()
    print("Daily Trading Journal")
    print(journal["journal_id"])
    print(f"Trades Executed: {len(journal['trades_executed'])}")
    print(f"Trades Skipped: {len(journal['trades_skipped'])}")
    print()
    print("Decision Quality Metrics")
    print(f"Trades Avoided: {quality_metrics['trades_avoided']}")
    print(f"Acceptance Rate: {quality_metrics['trade_acceptance_rate']}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
