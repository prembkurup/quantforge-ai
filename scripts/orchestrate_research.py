import argparse
import json
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
    parser = argparse.ArgumentParser(description="Run the research orchestrator demo.")
    parser.add_argument("--pair", default="EUR_USD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--regime", default="TRENDING")
    parser.add_argument("--session", default="London")
    parser.add_argument("--hypothesis-id", default="hyp_trend_pullback_london")
    parser.add_argument(
        "--hypothesis",
        default="Trend pullbacks outperform breakouts during London sessions on major pairs.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    orchestrator = ResearchOrchestrator(build_demo_knowledge_engine())
    request = ResearchOrchestrationRequest(
        hypothesis_id=args.hypothesis_id,
        hypothesis_statement=args.hypothesis,
        context=ResearchContext(
            instrument=args.pair,
            timeframe=args.timeframe,
            market_regime=args.regime,
            session=args.session,
        ),
        required_features=("trend_strength", "pullback_state"),
    )
    print(json.dumps(orchestrator.dashboard_payload(request), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
