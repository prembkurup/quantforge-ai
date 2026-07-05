import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.strategies import ProductionStrategyManagementPlatform  # noqa: E402
from quantforge.research.strategy_assets import StrategyAssetLoader, default_strategy_asset_repository  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy an approved persisted Strategy Asset.")
    parser.add_argument("--strategy-asset-id", help="Persisted approved Strategy Asset ID to deploy.")
    parser.add_argument("--demo", action="store_true", help="Explicitly deploy the seeded demo Strategy Asset.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    platform = ProductionStrategyManagementPlatform()
    if args.demo:
        result = platform.deploy_demo()
    else:
        if not args.strategy_asset_id:
            raise SystemExit("Deployment requires --strategy-asset-id. Use --demo only for explicit demo mode.")
        asset = StrategyAssetLoader(default_strategy_asset_repository(PROJECT_ROOT)).load_strategy_asset(args.strategy_asset_id)
        result = platform.deploy(asset)

    print("Approved")
    print("YES" if result.approved else "NO")
    print()
    print("Installed")
    print("YES" if result.installed else "NO")
    print()
    print("Portfolio")
    print(result.portfolio.portfolio_id)
    print()
    print("Capital Allocated")
    print("YES" if result.capital_allocated else "NO")
    print()
    print("Paper Trading")
    print("YES" if result.paper_trading else "NO")
    print()
    print("Production")
    print("YES" if result.production else "NO")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
