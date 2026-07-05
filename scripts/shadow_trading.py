from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone

from quantforge.config.settings import get_settings
from quantforge.live import (
    HistoricalCandleReplayStream,
    PaperTradingReplayRunner,
    ReplaySession,
    ShadowTradingPlatform,
    default_replay_progress_store,
    infer_replay_mode,
)
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.research.strategy_assets import default_strategy_asset_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run paper/shadow trading.")
    parser.add_argument("--source", choices=("candles",), default="candles")
    parser.add_argument("--pair", default="EUR_USD", help="Single pair or comma-separated pairs.")
    parser.add_argument("--timeframe", default="H1", help="Single timeframe or comma-separated timeframes.")
    parser.add_argument("--from", dest="start", default="2024-01-01", help="Replay start date/time.")
    parser.add_argument("--to", dest="end", default="2024-12-31", help="Replay end date/time; date-only is inclusive.")
    parser.add_argument("--strategy-asset-id", help="Persisted approved Strategy Asset ID. Defaults to latest.")
    parser.add_argument("--demo", action="store_true", help="Explicitly use seeded synthetic demo events.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.demo:
        result = ShadowTradingPlatform().run()
    else:
        pairs = tuple(item.strip().upper() for item in args.pair.split(",") if item.strip())
        timeframes = tuple(item.strip().upper() for item in args.timeframe.split(",") if item.strip())
        session = ReplaySession(
            replay_id=f"REPLAY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            pairs=pairs,
            timeframes=timeframes,
            start_time=parse_datetime(args.start, end_of_date=False),
            end_time=parse_datetime(args.end, end_of_date=True),
            mode=infer_replay_mode(pairs, timeframes),
        )
        repository = default_strategy_asset_repository()
        assets = repository.list()
        strategy_asset_id = args.strategy_asset_id or (assets[0].strategy_asset_id if assets else "")
        if not strategy_asset_id:
            raise SystemExit("No persisted approved Strategy Asset is available. Run autonomous research first.")
        settings = get_settings()
        engine = get_coreui_history_engine()
        with engine.connect() as connection:
            candle_repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
            runner = PaperTradingReplayRunner(
                HistoricalCandleReplayStream(candle_repository),
                default_replay_progress_store(),
            )
            result = runner.run(session, strategy_asset_id=strategy_asset_id)

    print("System")
    print()
    print("Receive Live Market")
    print("YES" if result.live_market_received else "NO")
    print()
    print("Generate Signals")
    print(result.signals_generated)
    if result.replay_cursor is not None:
        print()
        print("Replay Events")
        print(result.replay_cursor.processed_events)
    print()
    print("Trade Paper Portfolio")
    print(f"{len(result.paper_orders)} orders")
    print()
    print("Monitor Drift")
    print(f"{len(result.drift_metrics)} dimensions")
    print()
    print("Audit Decisions")
    print("100%" if result.monthly_review.decision_trace_coverage == 1.0 else "INCOMPLETE")
    print()
    print("Generate Reports")
    print("Daily + Monthly")
    print()
    print("Update Knowledge")
    print(f"{result.knowledge_updates} records")
    print()
    print("Recommend Promotion")
    print(result.monthly_review.decision.value)
    print()
    print("Digital Twin")
    print("MATCH" if result.digital_twin.decisions_match else "DIVERGED")


def parse_datetime(value: str, *, end_of_date: bool) -> datetime:
    if "T" not in value and len(value) == 10:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
        if end_of_date:
            parsed += timedelta(days=1)
        return parsed

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
