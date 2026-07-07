from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quantforge.live import LiveTradingEngine
from quantforge.live.paper_scanner import MultiPairPaperScanner, load_paper_scanner_config
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.config.settings import get_settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEST_RESULT_FILE = PROJECT_ROOT / "var" / "paper_practice_trading_result.json"
HISTORY_FILE = PROJECT_ROOT / "var" / "paper_practice_trading_history.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run QuantForge paper/practice trading.")
    parser.add_argument("--mode", choices=("paper-scanner", "demo"), default="paper-scanner")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "demo":
        result = LiveTradingEngine().run(mode="demo")
    else:
        settings = get_settings()
        engine = get_coreui_history_engine()
        with engine.connect() as connection:
            scanner = MultiPairPaperScanner(
                CoreUiCandleRepository(connection, settings.coreui_candle_table),
                config=load_paper_scanner_config(),
            )
            result = scanner.run()
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
    print(getattr(result, "signals_generated", len(getattr(result, "signals", ()))))
    print()
    print("Execute")
    print(f"{getattr(result, 'orders_executed', len(getattr(result, 'executions', ())))} orders")
    print()
    print("Monitor")
    print(f"{getattr(result, 'open_positions', len(getattr(result, 'positions', ())))} open positions")
    print()
    print("Recover")
    print("YES" if getattr(result, "recovery_completed", True) else "NO")
    print()
    print("Synchronize")
    print("YES" if not getattr(getattr(result, "synchronization", None), "repaired", False) else "REPAIRED")
    print()
    print("Run")
    dashboard = getattr(result, "dashboard", None)
    print("24/7 READY" if getattr(dashboard, "run_24_7_ready", True) else "NOT READY")


def _write_result(result: Any) -> None:
    executions = tuple(getattr(result, "executions", ()))
    positions = tuple(getattr(result, "positions", ()))
    signals = tuple(getattr(result, "signals", ()))
    payload = {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "connected": result.connected,
        "events_processed": result.events_processed,
        "signals_generated": getattr(result, "signals_generated", len(signals)),
        "orders_executed": getattr(result, "orders_executed", len(executions)),
        "open_positions": getattr(result, "open_positions", len(positions)),
        "recovery_completed": getattr(result, "recovery_completed", True),
        "synchronized": not result.synchronization.repaired if hasattr(result, "synchronization") else True,
        "run_24_7_ready": result.dashboard.run_24_7_ready if hasattr(result, "dashboard") else True,
        "execution_path": getattr(result, "execution_path", executions[0].broker if executions else "NO_EXECUTION"),
        "latest_signal": _to_jsonable(signals[-1]) if signals else {},
        "latest_execution": _to_jsonable(executions[-1]) if executions else {},
        "open_position_details": [_to_jsonable(position) for position in positions],
        "mode": getattr(result, "mode", "demo"),
        "pairs_loaded": getattr(result, "pairs_loaded", 0),
        "timeframes_loaded": getattr(result, "timeframes_loaded", 0),
        "pair_timeframes_scanned": getattr(result, "pair_timeframes_scanned", 0),
        "candles_loaded": getattr(result, "candles_loaded", 0),
        "new_candles": getattr(result, "new_candles", 0),
        "pair_results": _to_jsonable(getattr(result, "pair_results", ())),
        "paper_scanner_run": _to_jsonable(getattr(result, "paper_scanner_run", {})),
        "paper_signals": _to_jsonable(getattr(result, "paper_signals", ())),
        "paper_orders": _to_jsonable(getattr(result, "paper_orders", ())),
        "paper_positions": _to_jsonable(getattr(result, "paper_positions", ())),
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
