from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Connection, MetaData, Table, and_, create_engine, func, select

from quantforge.config.settings import get_settings


class CoreUiCandleRepository:
    """Read-only access to CoreUI's continuously updated OANDA candle history table."""

    def __init__(self, connection: Connection, table_name: str = "oanda_candles") -> None:
        self._connection = connection
        self._table = Table(table_name, MetaData(), autoload_with=connection)

    def load_window(
        self,
        pair_name: str,
        granularity: str,
        start: datetime,
        end: datetime,
        *,
        complete_only: bool = True,
        limit: int = 50_000,
    ) -> list[dict[str, Any]]:
        start = _normalize_datetime_for_coreui(start)
        end = _normalize_datetime_for_coreui(end)

        statement = (
            select(
                self._table.c.time,
                self._table.c.pair_name,
                self._table.c.granularity,
                self._table.c.volume,
                self._table.c.mid_o,
                self._table.c.mid_h,
                self._table.c.mid_l,
                self._table.c.mid_c,
                self._table.c.complete,
            )
            .where(
                and_(
                    self._table.c.pair_name == pair_name,
                    self._table.c.granularity == granularity,
                    self._table.c.time >= start,
                    self._table.c.time < end,
                )
            )
            .order_by(self._table.c.time.asc())
            .limit(limit)
        )
        if complete_only:
            statement = statement.where(self._table.c.complete.is_(True))

        return [_normalize_row(row._mapping) for row in self._connection.execute(statement)]

    def latest_candle_time(
        self,
        pair_name: str,
        granularity: str,
        *,
        complete_only: bool = True,
    ) -> datetime | None:
        statement = select(func.max(self._table.c.time)).where(
            and_(
                self._table.c.pair_name == pair_name,
                self._table.c.granularity == granularity,
            )
        )
        if complete_only:
            statement = statement.where(self._table.c.complete.is_(True))
        return self._connection.execute(statement).scalar_one_or_none()

    def load_latest(
        self,
        pair_name: str,
        granularity: str,
        *,
        complete_only: bool = True,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                self._table.c.time,
                self._table.c.pair_name,
                self._table.c.granularity,
                self._table.c.volume,
                self._table.c.mid_o,
                self._table.c.mid_h,
                self._table.c.mid_l,
                self._table.c.mid_c,
                self._table.c.complete,
            )
            .where(
                and_(
                    self._table.c.pair_name == pair_name,
                    self._table.c.granularity == granularity,
                )
            )
            .order_by(self._table.c.time.desc())
            .limit(limit)
        )
        if complete_only:
            statement = statement.where(self._table.c.complete.is_(True))

        rows = [_normalize_row(row._mapping) for row in self._connection.execute(statement)]
        return sorted(rows, key=lambda row: row["time"])

    def count_window(
        self,
        pair_name: str,
        granularity: str,
        start: datetime,
        end: datetime,
        *,
        complete_only: bool = True,
    ) -> int:
        start = _normalize_datetime_for_coreui(start)
        end = _normalize_datetime_for_coreui(end)
        statement = (
            select(func.count())
            .select_from(self._table)
            .where(
                and_(
                    self._table.c.pair_name == pair_name,
                    self._table.c.granularity == granularity,
                    self._table.c.time >= start,
                    self._table.c.time < end,
                )
            )
        )
        if complete_only:
            statement = statement.where(self._table.c.complete.is_(True))
        return int(self._connection.execute(statement).scalar_one())

    def duplicate_count(
        self,
        pair_name: str,
        granularity: str,
        start: datetime,
        end: datetime,
        *,
        complete_only: bool = True,
    ) -> int:
        start = _normalize_datetime_for_coreui(start)
        end = _normalize_datetime_for_coreui(end)
        grouped = (
            select(self._table.c.time, func.count().label("row_count"))
            .where(
                and_(
                    self._table.c.pair_name == pair_name,
                    self._table.c.granularity == granularity,
                    self._table.c.time >= start,
                    self._table.c.time < end,
                )
            )
            .group_by(self._table.c.time)
            .having(func.count() > 1)
        )
        if complete_only:
            grouped = grouped.where(self._table.c.complete.is_(True))
        grouped_subquery = grouped.subquery()
        statement = select(func.coalesce(func.sum(grouped_subquery.c.row_count - 1), 0))
        return int(self._connection.execute(statement).scalar_one())


def get_coreui_history_engine():
    settings = get_settings()
    if not settings.coreui_history_database_url:
        raise RuntimeError("QUANTFORGE_COREUI_HISTORY_DATABASE_URL is not configured.")
    return create_engine(
        _sqlalchemy_psycopg_url(settings.coreui_history_database_url),
        connect_args={"connect_timeout": 5},
        pool_pre_ping=True,
    )


def _normalize_datetime_for_coreui(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _sqlalchemy_psycopg_url(value: str) -> str:
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


def _normalize_row(row: Any) -> dict[str, Any]:
    return {
        "time": row["time"],
        "pair_name": row["pair_name"],
        "granularity": row["granularity"],
        "volume": row["volume"],
        "open_price": _decimal_or_none(row["mid_o"]),
        "high_price": _decimal_or_none(row["mid_h"]),
        "low_price": _decimal_or_none(row["mid_l"]),
        "close_price": _decimal_or_none(row["mid_c"]),
        "is_complete": row["complete"],
        "source": "coreui.oanda_candles",
    }


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
