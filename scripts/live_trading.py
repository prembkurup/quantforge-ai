from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, is_dataclass, replace
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
    parser.add_argument("--pairs", help="Comma-separated pair override for paper-scanner mode.")
    parser.add_argument("--timeframes", help="Comma-separated timeframe override for paper-scanner mode.")
    parser.add_argument("--max-pairs", type=int, help="Maximum enabled pairs to scan.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and decide without placing paper orders.")
    parser.add_argument("--once", action="store_true", help="Run one scanner cycle and exit.")
    parser.add_argument("--loop", action="store_true", help="Keep scanning until stopped.")
    parser.add_argument("--interval-seconds", type=int, default=60, help="Loop interval for --loop.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.loop and args.mode == "demo":
        raise SystemExit("--loop is only supported for --mode paper-scanner.")
    if args.mode == "demo":
        result = LiveTradingEngine().run(mode="demo")
        _write_result(result)
        _print_result(result)
    elif args.loop:
        while True:
            result = _run_paper_scanner(args)
            _write_result(result)
            _print_result(result)
            time.sleep(max(1, args.interval_seconds))
    else:
        result = _run_paper_scanner(args)
        _write_result(result)
        _print_result(result)


def _run_paper_scanner(args: argparse.Namespace) -> Any:
    settings = get_settings()
    config = _config_from_args(args)
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        scanner = MultiPairPaperScanner(
            CoreUiCandleRepository(connection, settings.coreui_candle_table),
            config=config,
        )
        return scanner.run()


def _config_from_args(args: argparse.Namespace):
    config = load_paper_scanner_config()
    updates: dict[str, Any] = {}
    if args.pairs:
        updates["pairs"] = tuple(item.strip().upper() for item in args.pairs.split(",") if item.strip())
    if args.timeframes:
        updates["timeframes"] = tuple(item.strip().upper() for item in args.timeframes.split(",") if item.strip())
    if args.max_pairs is not None:
        updates["max_pairs_per_scan"] = args.max_pairs
    if args.dry_run:
        updates["dry_run"] = True
    return replace(config, **updates) if updates else config


def _print_result(result: Any) -> None:
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
        "orders_blocked": getattr(result, "orders_blocked", 0),
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
        "pairs_scanned": getattr(result, "pairs_loaded", 0),
        "timeframes_loaded": getattr(result, "timeframes_loaded", 0),
        "timeframes_scanned": getattr(result, "timeframes_loaded", 0),
        "pair_timeframes_scanned": getattr(result, "pair_timeframes_scanned", 0),
        "candles_loaded": getattr(result, "candles_loaded", 0),
        "candles_checked": getattr(result, "candles_loaded", 0),
        "new_candles": getattr(result, "new_candles", 0),
        "skip_reasons": _to_jsonable(getattr(result, "skip_reasons", {})),
        "pair_results": _to_jsonable(getattr(result, "pair_results", ())),
        "paper_scanner_pair_result": _to_jsonable(_pair_table_rows(getattr(result, "pair_results", ()))),
        "paper_scanner_run": _to_jsonable(getattr(result, "paper_scanner_run", {})),
        "paper_signals": _to_jsonable(getattr(result, "paper_signals", ())),
        "paper_orders": _to_jsonable(getattr(result, "paper_orders", ())),
        "paper_positions": _to_jsonable(getattr(result, "paper_positions", ())),
        "open_paper_positions": _open_position_rows(getattr(result, "paper_positions", ())),
        "closed_paper_positions": _closed_position_rows(getattr(result, "closed_paper_positions", ())),
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


def _pair_table_rows(pair_results: Any) -> list[dict[str, Any]]:
    rows = []
    for item in pair_results:
        regime = getattr(item, "regime_result", None)
        risk = getattr(item, "risk_result", None)
        rows.append(
            {
                "pair": getattr(item, "pair", ""),
                "timeframe": getattr(item, "timeframe", ""),
                "candle_time": getattr(item, "candle_time", ""),
                "regime": getattr(regime, "regime", ""),
                "strategy_asset": getattr(item, "strategy_asset_id", ""),
                "signal": getattr(item, "signal_action", ""),
                "decision": getattr(item, "status", ""),
                "order_status": getattr(item, "execution_status", ""),
                "skip_reason": getattr(item, "reason", ""),
                "risk_result": getattr(risk, "status", ""),
                "execution_path": getattr(item, "execution_status", "") and "OANDA_PAPER",
            }
        )
    return rows


def _open_position_rows(positions: Any) -> list[dict[str, Any]]:
    rows = []
    for position in positions:
        entry_price = _field(position, "entry_price", _field(position, "open_price", ""))
        close_price = _field(position, "close_price", _field(position, "current_price", ""))
        rows.append(
            {
                "pair": _field(position, "pair", _field(position, "instrument", "")),
                "timeframe": _field(position, "timeframe", ""),
                "direction": _field(position, "direction", ""),
                "units": _field(position, "units", 0),
                "open_price": _display_price(entry_price),
                "close_price": _display_price(close_price),
                "take_profit": _display_price(_field(position, "take_profit", "")),
                "stop_loss": _display_price(_field(position, "stop_loss", "")),
                "p_l": _display_money(_field(position, "p_l", _field(position, "floating_pl", 0))),
                "status": _field(position, "status", ""),
                "opened_at": _field(position, "entry_time", _field(position, "opened_at", "")),
                "entry_time": _field(position, "entry_time", ""),
                "source_candle_time": _field(position, "source_candle_time", ""),
            }
        )
    return rows


def _closed_position_rows(positions: Any) -> list[dict[str, Any]]:
    rows = []
    for position in positions:
        entry_price = _field(position, "entry_price", _field(position, "open_price", ""))
        close_price = _field(position, "close_price", _field(position, "current_price", ""))
        rows.append(
            {
                "pair": _field(position, "pair", _field(position, "instrument", "")),
                "timeframe": _field(position, "timeframe", ""),
                "direction": _field(position, "direction", ""),
                "units": _field(position, "units", 0),
                "open_price": _display_price(entry_price),
                "close_price": _display_price(close_price),
                "take_profit": _display_price(_field(position, "take_profit", "")),
                "stop_loss": _display_price(_field(position, "stop_loss", "")),
                "p_l": _display_money(_field(position, "p_l", _field(position, "floating_pl", 0))),
                "close_reason": _field(position, "close_reason", ""),
                "opened_at": _field(position, "entry_time", _field(position, "opened_at", "")),
                "closed_at": _field(position, "closed_at", ""),
                "source_candle_time": _field(position, "source_candle_time", ""),
            }
        )
    return rows


def _field(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _display_price(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if number <= 0:
        return "N/A"
    return f"{number:.5f}"


def _display_money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.2f}"


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
