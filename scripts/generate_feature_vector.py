import argparse
import json
from decimal import Decimal
from typing import Any

import pandas as pd

from quantforge.config.settings import get_settings
from quantforge.features import StandardFeatureVectorGenerator
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a standardized QuantForge feature vector.")
    parser.add_argument("--pair", default="EUR_USD", help="Instrument, for example EUR_USD.")
    parser.add_argument("--timeframe", default="H1", help="Granularity, for example H1.")
    parser.add_argument("--candles", type=int, default=300, help="Number of latest complete candles to use.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        rows = repository.load_latest(args.pair.upper(), args.timeframe.upper(), limit=args.candles)

    frame = _to_candle_frame(rows)
    feature_vector = StandardFeatureVectorGenerator().generate(
        frame,
        instrument=args.pair.upper(),
        timeframe=args.timeframe.upper(),
    )
    print(json.dumps(feature_vector.to_dict(), indent=2, default=_json_default))


def _to_candle_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame = frame.rename(
        columns={
            "open_price": "open",
            "high_price": "high",
            "low_price": "low",
            "close_price": "close",
        }
    )
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column])
    return frame[["time", "open", "high", "low", "close", "volume"]]


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if pd.isna(value):
        return None
    return str(value)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
