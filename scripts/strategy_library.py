from __future__ import annotations

from quantforge.research import InstitutionalStrategyLibraryBuilder


def main() -> None:
    result = InstitutionalStrategyLibraryBuilder().build()

    print("Workstream 1 Strategy Library")
    print()
    print(f"Status: {result.dashboard.status.value}")
    print(f"Experiments: {result.kpis.experiments_executed:,}")
    print(f"Candidate Strategies: {result.kpis.candidate_strategies:,}")
    print(f"Optimized Strategies: {result.kpis.optimized_strategies:,}")
    print(f"Validated Strategy Assets: {result.kpis.validated_strategy_assets:,}")
    print(f"Production-Grade Strategies: {result.kpis.production_grade_strategies}")
    print(f"Knowledge Records: {result.kpis.knowledge_records_written:,}")
    print(f"Average Confidence: {result.kpis.average_confidence:.1%}")
    print(f"Average Profit Factor: {result.kpis.average_profit_factor:.2f}")
    print(f"Max Drawdown: {result.kpis.max_observed_drawdown:.1%}")
    print(f"Portfolio Readiness: {result.dashboard.portfolio_readiness}")
    print(f"Reproducibility Key: {result.reproducibility_key}")
    print(f"Successful: {'YES' if result.successful else 'NO'}")


if __name__ == "__main__":
    main()
