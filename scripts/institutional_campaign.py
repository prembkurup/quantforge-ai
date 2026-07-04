from quantforge.research import InstitutionalResearchCampaign


def main() -> None:
    result = InstitutionalResearchCampaign().execute()

    print("Institutional Research Campaign")
    print()
    print("Programs")
    print(len(result.programs))
    print()
    print("Experiments")
    print(f"{result.kpis.experiments_completed:,}")
    print()
    print("Candidate Strategies")
    print(f"{result.kpis.candidate_strategies:,}")
    print()
    print("Validated Strategies")
    print(f"{result.kpis.validated_strategies:,}")
    print()
    print("Approved Strategy Assets")
    print(result.kpis.approved_strategy_assets)
    print()
    print("Production Candidates")
    print(result.kpis.production_candidates)
    print()
    print("Portfolio")
    print(result.portfolio.portfolio_id)
    print()
    print("Knowledge Base Growth")
    print(f"{result.kpis.knowledge_records_written:,} records")
    print()
    print("Reports")
    print("DAILY, WEEKLY, MONTHLY")
    print()
    print("Autonomous")
    print("YES" if result.autonomous else "NO")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
