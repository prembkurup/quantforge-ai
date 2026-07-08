from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quantforge.dashboard.service import DashboardService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    payload = DashboardService().strategy_lifecycle()
    snapshot_file = PROJECT_ROOT / "var" / "strategy_lifecycle_snapshot.json"
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    queued = _upsert_research_requests(payload, PROJECT_ROOT / "var" / "history_validation_improvements.json")

    print("QuantForge AI Version 2.0")
    print("Milestone 28 - Strategy Lifecycle Intelligence")
    print()
    print("Strategy Lifecycle Health")
    print(f"Strategies: {payload['strategy_count']}")
    print(f"Average Health: {payload['average_health_score']}")
    print(f"Acceptance Gaps: {_acceptance_gaps(payload)}")
    print()
    print("Status Counts")
    for status, count in payload["status_counts"].items():
        print(f"- {status}: {count}")
    print()
    print("Policy Actions")
    for action, count in payload["action_counts"].items():
        print(f"- {action}: {count}")
    print()
    print("Autonomous Research Feedback")
    print(f"Lifecycle research requests queued: {queued}")
    print(f"Snapshot: {snapshot_file.relative_to(PROJECT_ROOT)}")


def _upsert_research_requests(payload: dict[str, Any], path: Path) -> int:
    now = datetime.now(UTC).isoformat()
    existing = _load_json(path)
    rows = list(existing.get("improvements", []))
    by_id = {str(item.get("improvement_id")): index for index, item in enumerate(rows)}
    queued = 0
    for strategy in payload.get("strategies", []):
        goal = strategy.get("research_goal")
        if not goal:
            continue
        improvement_id = f"imp_lifecycle_{strategy['strategy_asset_id']}"
        row = {
            "improvement_id": improvement_id,
            "source": "strategy_lifecycle",
            "strategy_asset_id": strategy["strategy_asset_id"],
            "strategy_name": strategy["strategy_name"],
            "pair": strategy["pair"],
            "timeframe": strategy["timeframe"],
            "reason_code": str(strategy.get("root_cause") or "STRATEGY_LIFECYCLE_HEALTH"),
            "research_program_id": f"RP-{strategy['pair']}-{strategy['timeframe']}",
            "research_goal_id": goal["research_goal_id"],
            "hypothesis": goal["hypothesis"],
            "campaign": goal["campaign"],
            "priority": goal["priority"],
            "status": "REQUESTED",
            "created_at": now,
            "updated_at": now,
        }
        current_index = by_id.get(improvement_id)
        if current_index is None:
            rows.append(row)
            queued += 1
            continue
        current = rows[current_index]
        current_status = str(current.get("status", "")).upper()
        if current_status in {"RESEARCH_RUNNING", "RESEARCHED"}:
            continue
        rows[current_index] = {**current, **row, "created_at": current.get("created_at", now)}
        queued += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "improvements": rows}, indent=2, sort_keys=True), encoding="utf-8")
    return queued


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _acceptance_gaps(payload: dict[str, Any]) -> int:
    return sum(1 for value in payload.get("acceptance_criteria", {}).values() if not value)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
