import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.strategies import ProductionStrategyManagementPlatform  # noqa: E402


def main() -> None:
    result = ProductionStrategyManagementPlatform().deploy()

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
    main()
