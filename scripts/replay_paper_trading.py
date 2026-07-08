from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, time, timedelta

from quantforge.config.settings import get_settings
from quantforge.live import (
    HistoricalCandleReplayStream,
    PaperTradingReplayRunner,
    ReplaySession,
    default_replay_progress_store,
    infer_replay_mode,
)
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.research.strategy_assets import default_strategy_asset_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay historical candles through the same Paper Trading pipeline used by live paper trading."
    )
    parser.add_argument("--from", dest="start", required=True, help="Replay start date/time, e.g. 2024-01-01.")
    parser.add_argument("--to", dest="end", required=True, help="Replay end date/time; date-only is inclusive.")
    parser.add_argument("--pairs", default="EUR_USD", help="Comma-separated pair list.")
    parser.add_argument("--timeframes", default="H1", help="Comma-separated timeframe list.")
    parser.add_argument(
        "--speed",
        default="MAXIMUM",
        choices=("REAL_TIME", "2X", "5X", "10X", "100X", "MAXIMUM"),
        help="Replay speed metadata used by dashboard controls. MAXIMUM processes without waiting.",
    )
    parser.add_argument("--strategy-asset-id", help="Approved Strategy Asset ID. Defaults to the latest approved asset.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pairs = tuple(item.strip().upper() for item in args.pairs.split(",") if item.strip())
    timeframes = tuple(item.strip().upper() for item in args.timeframes.split(",") if item.strip())
    session = ReplaySession(
        replay_id=f"REPLAY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
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
        raise SystemExit("No approved Strategy Asset is available. Run autonomous research first.")

    settings = get_settings()
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        candle_repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        runner = PaperTradingReplayRunner(
            HistoricalCandleReplayStream(candle_repository),
            default_replay_progress_store(),
        )
        result = runner.run(session, strategy_asset_id=strategy_asset_id, replay_speed=args.speed)

    print("Historical Replay Paper Trading")
    print()
    print("Pipeline")
    print("HistoricalCandleReplayStream -> LiveEventBus -> LiveFeatureEngine -> LiveMarketRegimeEngine")
    print("StrategySelector -> TradeDecisionEngine -> LiveRiskController -> ExecutionManager -> PaperPortfolio")
    print()
    print("Replay ID")
    print(session.replay_id)
    print()
    print("Mode")
    print(session.mode.value)
    print()
    print("Speed")
    print(args.speed)
    print()
    print("Events")
    print(result.replay_cursor.processed_events if result.replay_cursor else 0)
    print()
    print("Signals")
    print(result.signals_generated)
    print()
    print("Paper Orders")
    print(len(result.paper_orders))
    print()
    print("Progress File")
    print(default_replay_progress_store().path)


def parse_datetime(value: str, *, end_of_date: bool) -> datetime:
    if "T" not in value and len(value) == 10:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, time.min, tzinfo=UTC)
        return parsed + timedelta(days=1) if end_of_date else parsed
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
