import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.research.knowledge_base import (  # noqa: E402
    KnowledgeEngine,
    KnowledgeRepository,
    build_demo_knowledge_engine,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show QuantForge research knowledge reports.")
    parser.add_argument(
        "--knowledge-file",
        type=Path,
        help="Optional JSON knowledge store. If omitted with --demo, a seeded demo store is used.",
    )
    parser.add_argument("--demo", action="store_true", help="Use seeded demo knowledge records.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.demo:
        engine = build_demo_knowledge_engine()
    elif args.knowledge_file:
        engine = KnowledgeEngine(KnowledgeRepository.load_json(args.knowledge_file))
    else:
        engine = KnowledgeEngine()

    print(json.dumps(engine.dashboard_payload(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
