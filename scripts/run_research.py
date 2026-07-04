import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.research.knowledge_base import build_demo_knowledge_engine  # noqa: E402
from quantforge.research.orchestrator import (  # noqa: E402
    ResearchContext,
    ResearchOrchestrationRequest,
    ResearchOrchestrator,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a knowledge-driven QuantForge research loop demo.")
    parser.add_argument("--goal", default="Improve Trend Pullback")
    parser.add_argument("--pair", default="EUR_USD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--regime", default="TRENDING")
    parser.add_argument("--session", default="London")
    parser.add_argument("--hypothesis-id", default="hyp_trend_pullback_london")
    parser.add_argument(
        "--hypothesis",
        default="Trend pullbacks outperform breakouts during London sessions on major pairs.",
    )
    parser.add_argument("--max-experiments", type=int, default=14)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    orchestrator = ResearchOrchestrator(build_demo_knowledge_engine())
    request = ResearchOrchestrationRequest(
        hypothesis_id=args.hypothesis_id,
        hypothesis_statement=args.hypothesis,
        research_goal=args.goal,
        context=ResearchContext(
            instrument=args.pair,
            timeframe=args.timeframe,
            market_regime=args.regime,
            session=args.session,
        ),
        required_features=("trend_strength", "pullback_state"),
        max_experiments=args.max_experiments,
    )
    plan = orchestrator.plan(request)
    run = plan.research_run
    if run is None:
        raise RuntimeError("Research Orchestrator did not create a research run.")

    print(f"Research Goal: {run.research_goal}")
    print(f"Knowledge Base: consulted ({len(plan.reasons)} reasons)")
    print(f"Generated: {run.experiment_count} Experiments")
    print(f"Running: {run.progress.running}")
    print(f"Queued: {run.progress.queued} Jobs")
    print(f"Completed: {run.progress.completed}")
    print("Knowledge Updated: pending result collection")
    print("Approved Strategies: pending validation")
    print()
    print(f"Decision: {plan.decision.value}")
    print(f"Dataset: {', '.join(run.dataset.instruments)} / {', '.join(run.dataset.timeframes)}")
    print(f"Features: {', '.join(run.features.selected_features)}")
    print(f"Templates: {', '.join(run.templates.selected_templates)}")
    print(f"Plugins: {', '.join(run.templates.selected_plugins)}")
    print(f"Parameter Search: {run.parameters.search_space}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
