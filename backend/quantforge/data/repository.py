from datetime import datetime
from typing import Protocol

import pandas as pd

from quantforge.core.types import Candle, Granularity


class CandleRepository(Protocol):
    """Durable candle storage boundary.

    Implementations must treat raw OHLCV candles as permanent source-of-truth
    records and use idempotent upsert semantics.
    """

    def upsert_many(self, candles: list[Candle]) -> int:
        """Persist candles and return the number of inserted or updated rows."""

    def load_window(
        self,
        instrument: str,
        granularity: Granularity,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Load OHLCV candles as a DataFrame indexed or sorted by time."""

