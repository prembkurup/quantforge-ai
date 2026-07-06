from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quantforge.dashboard.service import DashboardService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run QuantForge AI intraday start/end-of-day automation.")
    parser.add_argument("--mode", choices=("start", "end"), default="end")
    parser.add_argument("--output-dir", default="var", help="Directory for daily report and knowledge outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = DashboardService().intraday_daily()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trading_day = str(payload.get("daily_report", {}).get("trading_day") or datetime.now(UTC).date().isoformat())
    record = {
        "mode": args.mode,
        "generated_at": datetime.now(UTC).isoformat(),
        "trading_day": trading_day,
        "intraday_daily": payload,
    }
    if args.mode == "start":
        _append_json_record(output_dir / "intraday_start_of_day.json", record)
        print("Start-of-day intraday activation recorded.")
        print(_market_readiness_line(payload))
        print(f"Trading Status: {payload.get('trading_status')}")
        print(f"Current Session: {payload.get('current_session')}")
        print(f"Active Strategies: {', '.join(payload.get('active_strategies', [])) or 'NONE'}")
        return

    _append_json_record(output_dir / "intraday_daily_reports.json", record)
    _append_json_record(
        output_dir / "intraday_knowledge_updates.json",
        {
            "generated_at": record["generated_at"],
            "trading_day": trading_day,
            "knowledge_updates": payload.get("learning_loop", {}).get("knowledge_updates", []),
            "research_priorities": payload.get("learning_loop", {}).get("research_priorities", []),
            "future_campaigns": payload.get("learning_loop", {}).get("future_campaigns", []),
            "report_id": payload.get("daily_report", {}).get("report_id", ""),
        },
    )
    print("End-of-day intraday report and knowledge update recorded.")
    print(f"Report: {payload.get('daily_report', {}).get('report_id')}")
    print(_market_readiness_line(payload))
    print(f"Trading Status: {payload.get('trading_status')}")
    print(f"Open Positions: {payload.get('open_positions')}")


def _market_readiness_line(payload: dict[str, Any]) -> str:
    readiness = payload.get("market_readiness", {})
    return f"Market Readiness: {readiness.get('score', 0)}/100 - {readiness.get('band', 'UNKNOWN')}"


def _append_json_record(path: Path, record: dict[str, Any]) -> None:
    payload = _load_json(path)
    records = list(payload.get("records", []))
    records.append(record)
    payload["records"] = records
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "records": []}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
