from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Connection, Select, and_, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from quantforge.database.models import candle, instrument, timeframe
from quantforge.market_data.oanda import OandaCandle


class PostgresCandleRepository:
    """PostgreSQL implementation for permanent raw OHLCV candles."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert_candles(self, candles: Iterable[OandaCandle]) -> int:
        rows = []
        for item in candles:
            instrument_id = self._get_or_create_instrument(item.instrument)
            timeframe_id = self._get_or_create_timeframe(item.granularity)
            rows.append(
                {
                    "instrument_id": instrument_id,
                    "timeframe_id": timeframe_id,
                    "candle_time": item.time,
                    "open_price": item.open,
                    "high_price": item.high,
                    "low_price": item.low,
                    "close_price": item.close,
                    "volume": item.volume,
                    "is_complete": item.complete,
                    "source": "oanda",
                }
            )

        if not rows:
            return 0

        statement = pg_insert(candle).values(rows)
        upsert = statement.on_conflict_do_update(
            constraint="uq_candle_instrument_timeframe_time",
            set_={
                "open_price": statement.excluded.open_price,
                "high_price": statement.excluded.high_price,
                "low_price": statement.excluded.low_price,
                "close_price": statement.excluded.close_price,
                "volume": statement.excluded.volume,
                "is_complete": statement.excluded.is_complete,
                "updated_at": func.now(),
            },
        )
        result = self._connection.execute(upsert)
        return result.rowcount or 0

    def load_window(
        self,
        symbol: str,
        granularity: str,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        statement: Select = (
            select(
                candle.c.candle_time,
                candle.c.open_price,
                candle.c.high_price,
                candle.c.low_price,
                candle.c.close_price,
                candle.c.volume,
                candle.c.is_complete,
            )
            .join(instrument, candle.c.instrument_id == instrument.c.id)
            .join(timeframe, candle.c.timeframe_id == timeframe.c.id)
            .where(
                and_(
                    instrument.c.symbol == symbol,
                    timeframe.c.code == granularity,
                    candle.c.candle_time >= start,
                    candle.c.candle_time <= end,
                )
            )
            .order_by(candle.c.candle_time)
        )
        return [dict(row._mapping) for row in self._connection.execute(statement)]

    def count_window(
        self,
        symbol: str,
        granularity: str,
        start: datetime,
        end: datetime,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(candle)
            .join(instrument, candle.c.instrument_id == instrument.c.id)
            .join(timeframe, candle.c.timeframe_id == timeframe.c.id)
            .where(
                and_(
                    instrument.c.symbol == symbol,
                    timeframe.c.code == granularity,
                    candle.c.candle_time >= start,
                    candle.c.candle_time < end,
                )
            )
        )
        return int(self._connection.execute(statement).scalar_one())

    def duplicate_count(
        self,
        symbol: str,
        granularity: str,
        start: datetime,
        end: datetime,
    ) -> int:
        grouped = (
            select(candle.c.candle_time, func.count().label("row_count"))
            .join(instrument, candle.c.instrument_id == instrument.c.id)
            .join(timeframe, candle.c.timeframe_id == timeframe.c.id)
            .where(
                and_(
                    instrument.c.symbol == symbol,
                    timeframe.c.code == granularity,
                    candle.c.candle_time >= start,
                    candle.c.candle_time < end,
                )
            )
            .group_by(candle.c.candle_time)
            .having(func.count() > 1)
            .subquery()
        )
        statement = select(func.coalesce(func.sum(grouped.c.row_count - 1), 0))
        return int(self._connection.execute(statement).scalar_one())

    def _get_or_create_instrument(self, symbol: str):
        existing = self._connection.execute(
            select(instrument.c.id).where(instrument.c.symbol == symbol)
        ).scalar_one_or_none()
        if existing:
            return existing
        return self._connection.execute(
            insert(instrument)
            .values(symbol=symbol, display_name=symbol.replace("_", "/"), asset_class="forex")
            .returning(instrument.c.id)
        ).scalar_one()

    def _get_or_create_timeframe(self, code: str):
        existing = self._connection.execute(
            select(timeframe.c.id).where(timeframe.c.code == code)
        ).scalar_one_or_none()
        if existing:
            return existing
        return self._connection.execute(
            insert(timeframe).values(code=code, seconds=_timeframe_seconds(code)).returning(timeframe.c.id)
        ).scalar_one()


def _timeframe_seconds(code: str) -> int:
    known = {
        "S5": 5,
        "S10": 10,
        "S15": 15,
        "S30": 30,
        "M1": 60,
        "M5": 300,
        "M15": 900,
        "M30": 1800,
        "H1": 3600,
        "H4": 14400,
        "D": 86400,
    }
    return known.get(code, 0)
