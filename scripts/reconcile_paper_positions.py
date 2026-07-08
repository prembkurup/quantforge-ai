from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quantforge.config.settings import get_settings
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile open paper positions against real UTC candle data.")
    parser.add_argument("--positions-file", default="var/paper_positions.json")
    parser.add_argument("--audit-file", default="var/paper_positions_reconciliation.json")
    parser.add_argument("--write", action="store_true", help="Persist corrected positions.")
    args = parser.parse_args()

    positions_path = Path(args.positions_file)
    payload = json.loads(positions_path.read_text(encoding="utf-8"))
    audit: list[dict[str, Any]] = []
    changed = False

    with get_coreui_history_engine().connect() as connection:
        repository = CoreUiCandleRepository(connection, get_settings().coreui_candle_table)
        for position in payload.get("positions", []):
            if position.get("status") != "OPEN":
                continue
            result = _reconcile_position(repository, position)
            audit.append(result)
            changed = result["changed"] or changed

    summary = {
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "positions_checked": len(audit),
        "positions_changed": sum(1 for item in audit if item["changed"]),
        "positions_unmatched": sum(1 for item in audit if item["status"] != "MATCHED"),
        "items": audit,
    }
    audit_path = Path(args.audit_file)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    if args.write and changed:
        positions_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({k: summary[k] for k in ("positions_checked", "positions_changed", "positions_unmatched")}, indent=2))
    return 1 if summary["positions_unmatched"] else 0


def _reconcile_position(repository: CoreUiCandleRepository, position: dict[str, Any]) -> dict[str, Any]:
    pair = str(position.get("pair") or position.get("instrument") or "")
    timeframe = str(position.get("timeframe") or "")
    original = {
        "entry_time": position.get("entry_time"),
        "opened_at": position.get("opened_at"),
        "source_candle_time": position.get("source_candle_time"),
        "entry_price": position.get("entry_price"),
        "open_price": position.get("open_price"),
        "close_price": position.get("close_price"),
        "take_profit": position.get("take_profit"),
        "stop_loss": position.get("stop_loss"),
        "p_l": position.get("p_l"),
    }
    candle_time = _position_candle_time(position)
    if candle_time is None:
        return _audit(position, original, "NO_POSITION_TIME", False)
    candle_time = _floor_to_timeframe(candle_time, timeframe)
    candle = _load_exact_candle(repository, pair, timeframe, candle_time)
    if candle is None:
        return _audit(position, original, "NO_CANDLE", False, candle_time=candle_time.isoformat())

    latest = repository.load_latest(pair, timeframe, limit=1)
    entry_price = _float(candle["close_price"])
    current_price = _float(latest[-1]["close_price"] if latest else candle["close_price"])
    direction = str(position.get("direction") or "").upper()
    units = _float(position.get("units"))
    take_profit, stop_loss = _default_exit_prices(entry_price, direction)
    floating_pl = _position_pl(pair, entry_price, current_price, units, direction)
    normalized_time = candle["time"].isoformat()
    updates = {
        "entry_time": normalized_time,
        "opened_at": normalized_time,
        "source_candle_time": normalized_time,
        "entry_price": entry_price,
        "open_price": entry_price,
        "close_price": current_price,
        "current_price": current_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "floating_pl": floating_pl,
        "p_l": floating_pl,
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    changed = any(position.get(key) != value for key, value in updates.items())
    position.update(updates)
    return _audit(
        position,
        original,
        "MATCHED",
        changed,
        candle_time=normalized_time,
        candle_open=_float(candle["open_price"]),
        candle_high=_float(candle["high_price"]),
        candle_low=_float(candle["low_price"]),
        candle_close=entry_price,
    )


def _load_exact_candle(
    repository: CoreUiCandleRepository,
    pair: str,
    timeframe: str,
    candle_time: datetime,
) -> dict[str, Any] | None:
    window = repository.load_window(pair, timeframe, candle_time, candle_time.replace(microsecond=0) + _timeframe_delta(timeframe), limit=1)
    for candle in window:
        if candle["time"] == candle_time:
            return candle
    return None


def _position_candle_time(position: dict[str, Any]) -> datetime | None:
    for key in ("source_candle_time", "entry_time", "opened_at"):
        value = position.get(key)
        if value:
            return _parse_utc(value)
    return None


def _parse_utc(value: Any) -> datetime:
    timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _floor_to_timeframe(value: datetime, timeframe: str) -> datetime:
    delta = _timeframe_delta(timeframe)
    seconds = int(delta.total_seconds())
    epoch_seconds = int(value.timestamp())
    floored = epoch_seconds - (epoch_seconds % seconds)
    return datetime.fromtimestamp(floored, UTC)


def _timeframe_delta(timeframe: str):
    from datetime import timedelta

    value = timeframe.upper()
    if value.startswith("M") and value[1:].isdigit():
        return timedelta(minutes=int(value[1:]))
    if value.endswith("M") and value[:-1].isdigit():
        return timedelta(minutes=int(value[:-1]))
    if value.startswith("H") and value[1:].isdigit():
        return timedelta(hours=int(value[1:]))
    if value.endswith("H") and value[:-1].isdigit():
        return timedelta(hours=int(value[:-1]))
    return timedelta(hours=1)


def _default_exit_prices(entry_price: float, direction: str) -> tuple[float | None, float | None]:
    if entry_price <= 0:
        return None, None
    if direction == "SELL":
        return round(entry_price * 0.9980, 8), round(entry_price * 1.0010, 8)
    return round(entry_price * 1.0020, 8), round(entry_price * 0.9990, 8)


def _position_pl(pair: str, entry_price: float, close_price: float, units: float, direction: str) -> float:
    if entry_price <= 0 or close_price <= 0 or units == 0:
        return 0.0
    multiplier = -1.0 if direction == "SELL" else 1.0
    return round((close_price - entry_price) * _effective_pl_units(pair, units) * multiplier, 4)


def _effective_pl_units(pair: str, units: float) -> float:
    if pair.replace("/", "_").upper() in {"NAS100_USD", "SPX500_USD"}:
        return abs(units) / 10_000.0
    return abs(units)


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _audit(
    position: dict[str, Any],
    original: dict[str, Any],
    status: str,
    changed: bool,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "position_id": position.get("position_id"),
        "pair": position.get("pair") or position.get("instrument"),
        "timeframe": position.get("timeframe"),
        "status": status,
        "changed": changed,
        "original": original,
        "corrected": {
            "entry_time": position.get("entry_time"),
            "opened_at": position.get("opened_at"),
            "source_candle_time": position.get("source_candle_time"),
            "entry_price": position.get("entry_price"),
            "open_price": position.get("open_price"),
            "close_price": position.get("close_price"),
            "take_profit": position.get("take_profit"),
            "stop_loss": position.get("stop_loss"),
            "p_l": position.get("p_l"),
        },
        **extra,
    }


if __name__ == "__main__":
    raise SystemExit(main())
