from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from quantforge.dashboard.service import DashboardService  # noqa: E402


def main() -> int:
    summary = DashboardService().refresh_full_history_research_summary()
    cache = summary.get("cache", {})
    print("Full-history research summary refreshed")
    print(f"Cache: {cache.get('status', 'UNKNOWN')}")
    print(f"Generated At: {cache.get('generated_at', '')}")
    print(f"Pairs: {summary['pair_count']}")
    print(f"Timeframes: {summary['timeframe_count']}")
    print(f"Coverage Rows: {len(summary['coverage'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
