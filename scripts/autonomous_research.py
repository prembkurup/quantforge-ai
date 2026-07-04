from quantforge.research import AutonomousResearchPipeline


def main() -> None:
    result = AutonomousResearchPipeline().execute()

    print("Research Goal")
    print(result.research_goal.description)
    print()
    print("Hypotheses")
    print(len(result.hypotheses))
    print()
    print("Experiments")
    print(result.kpis.experiments_completed)
    print()
    print("Candidates Generated")
    print(f"{result.kpis.candidates_generated:,}")
    print()
    print("Approved Strategy Assets")
    print(result.kpis.approved_strategy_assets)
    print()
    print("Knowledge Base Updated")
    print("YES" if result.knowledge_report.records_written > 0 else "NO")
    print()
    print("Reports")
    print(", ".join(item.upper() for item in result.dashboard.report_exports))
    print()
    print("Audit Trail")
    print(f"{len(result.audit_trail):,} events")
    print()
    print("Autonomous")
    print("YES" if result.dashboard.autonomous else "NO")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
