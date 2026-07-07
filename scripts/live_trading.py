from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quantforge.live import LiveTradingEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEST_RESULT_FILE = PROJECT_ROOT / "var" / "paper_practice_trading_result.json"
HISTORY_FILE = PROJECT_ROOT / "var" / "paper_practice_trading_history.jsonl"


def main() -> None:
    result = LiveTradingEngine().run()
    _write_result(result)

    print("System")
    print()
    print("Connect")
    print("YES" if result.connected else "NO")
    print()
    print("Receive Market")
    print(f"{result.events_processed} events")
    print()
    print("Generate Signals")
    print(len(result.signals))
    print()
    print("Execute")
    print(f"{len(result.executions)} orders")
    print()
    print("Monitor")
    print(f"{len(result.positions)} open positions")
    print()
    print("Recover")
    print("YES" if result.recovery_completed else "NO")
    print()
    print("Synchronize")
    print("YES" if not result.synchronization.repaired else "REPAIRED")
    print()
    print("Run")
    print("24/7 READY" if result.dashboard.run_24_7_ready else "NOT READY")


def _write_result(result: Any) -> None:
    payload = {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "connected": result.connected,
        "events_processed": result.events_processed,
        "signals_generated": len(result.signals),
        "orders_executed": len(result.executions),
        "open_positions": len(result.positions),
        "recovery_completed": result.recovery_completed,
        "synchronized": not result.synchronization.repaired,
        "run_24_7_ready": result.dashboard.run_24_7_ready,
        "execution_path": result.executions[0].broker if result.executions else "NO_EXECUTION",
        "latest_signal": _to_jsonable(result.signals[-1]) if result.signals else {},
        "latest_execution": _to_jsonable(result.executions[-1]) if result.executions else {},
        "open_position_details": [_to_jsonable(position) for position in result.positions],
        "safety": {
            "practice_safe": True,
            "broker_order_execution": "paper_only",
        },
    }
    LATEST_RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LATEST_RESULT_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with HISTORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
