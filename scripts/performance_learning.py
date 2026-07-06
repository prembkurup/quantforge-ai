from __future__ import annotations

from quantforge.dashboard.service import DashboardService


def main() -> None:
    payload = DashboardService().performance_learning()
    attribution = payload["attribution"]
    learning = payload["learning"]
    quality = payload["decision_quality"]
    daily = payload["daily_report"]

    print("QuantForge AI Version 2.0")
    print("Milestone 26 - Performance Attribution & Continuous Learning")
    print()
    print("Performance Attribution")
    print(f"Total P/L: {attribution['total_profit_loss']}")
    print(f"Top Strategy: {attribution['strategy'][0]['item']} ({attribution['strategy'][0]['contribution_percent']}%)")
    print(f"Top Regime: {attribution['market_regime'][0]['item']} ({attribution['market_regime'][0]['contribution_percent']}%)")
    print(f"Top Session: {attribution['session'][0]['item']} ({attribution['session'][0]['contribution_percent']}%)")
    print()
    print("Continuous Learning")
    print(f"Knowledge Records Written: {learning['knowledge_records_written']}")
    print(f"Top Feature: {learning['feature_rankings'][0]['item']}")
    print(f"Top Plugin: {learning['plugin_rankings'][0]['item']}")
    print()
    print("Decision Quality")
    print(f"Decision Accuracy: {quality['decision_accuracy']}")
    print(f"Opportunity Accuracy: {quality['opportunity_accuracy']}")
    print(f"Portfolio Decision Quality: {quality['portfolio_decision_quality']}")
    print()
    print("Research Priorities")
    for priority in payload["research_priorities"]:
        print(f"- {priority['theme']}: {priority['action']}")
    print()
    print("Daily Learning Report")
    print(daily["report_id"])
    for recommendation in daily["research_recommendations"]:
        print(f"- {recommendation}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
