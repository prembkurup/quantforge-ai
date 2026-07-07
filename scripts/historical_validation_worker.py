from __future__ import annotations

import argparse
import time
from pathlib import Path

from quantforge.research.history_validation import (
    HistoricalValidationEngine,
    default_historical_validation_paths,
    historical_validation_config_from_env,
)
from quantforge.research.strategy_assets import StrategyAssetRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run historical validation in controlled batches.")
    parser.add_argument("--once", action="store_true", help="Run one validation batch and exit.")
    parser.add_argument("--sleep-seconds", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    engine = HistoricalValidationEngine(
        asset_repository=StrategyAssetRepository(repo_root / "var" / "approved_strategy_assets.json"),
        paths=default_historical_validation_paths(repo_root),
        config=historical_validation_config_from_env(),
    )
    if args.once:
        status = engine.run_next_batch()
        progress = status["progress"]
        print(f"{status['state']} {progress['completed']}/{progress['total']} queue={status['queue_length']}", flush=True)
        return
    while True:
        status = engine.run_next_batch()
        progress = status["progress"]
        print(f"{status['state']} {progress['completed']}/{progress['total']} queue={status['queue_length']}", flush=True)
        sleep_seconds = 30 if status["queue_length"] else max(args.sleep_seconds, 300)
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
