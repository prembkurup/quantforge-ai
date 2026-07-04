import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.strategies import ConstraintBasedStrategyComposer, StrategyCompositionRequest  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the constraint-based Strategy Composer demo.")
    parser.add_argument("--goal", default="Trend Pullback")
    parser.add_argument("--hypothesis-id", default="hyp_trend_pullback_london")
    parser.add_argument("--pair", default="EUR_USD")
    parser.add_argument("--regime", default="TRENDING")
    parser.add_argument("--session", default="London")
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    parser.add_argument("--minimum-pf", type=float, default=2.0)
    parser.add_argument("--minimum-trades", type=int, default=500)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    request = StrategyCompositionRequest(
        research_goal=args.goal,
        hypothesis_id=args.hypothesis_id,
        instrument=args.pair,
        market_regime=args.regime,
        session=args.session,
        max_drawdown=args.max_drawdown,
        minimum_profit_factor=args.minimum_pf,
        minimum_trades=args.minimum_trades,
    )
    result = ConstraintBasedStrategyComposer().compose(request)

    print("Research Goal")
    print(result.research_goal)
    print()
    print("Constraints Applied")
    print(len(result.constraints))
    print()
    print("Generated")
    print(f"{result.generated_count:,} candidates")
    print()
    print("Rejected")
    print(f"{result.rejected_count:,}")
    print()
    print("Valid")
    print(f"{result.valid_count:,}")
    print()
    print("Unique")
    print(f"{result.unique_count:,}")
    print()
    print("Ready for Optimization")
    print(len(result.ready_for_optimization))
    print()
    print("Decision Trace")
    for event in result.decision_trace.events:
        print(f"- {event.stage}: {event.reason}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
