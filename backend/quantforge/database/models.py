from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

instrument = Table(
    "instrument",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("symbol", String(32), nullable=False),
    Column("display_name", String(120)),
    Column("asset_class", String(40), nullable=False, server_default="forex"),
    Column("pip_location", Integer),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("symbol", name="uq_instrument_symbol"),
    schema="instrument",
)

timeframe = Table(
    "timeframe",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("code", String(10), nullable=False),
    Column("seconds", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("code", name="uq_timeframe_code"),
    schema="instrument",
)

candle = Table(
    "candle",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("instrument_id", UUID(as_uuid=True), ForeignKey("instrument.instrument.id"), nullable=False),
    Column("timeframe_id", UUID(as_uuid=True), ForeignKey("instrument.timeframe.id"), nullable=False),
    Column("candle_time", DateTime(timezone=True), nullable=False),
    Column("open_price", Numeric(18, 8), nullable=False),
    Column("high_price", Numeric(18, 8), nullable=False),
    Column("low_price", Numeric(18, 8), nullable=False),
    Column("close_price", Numeric(18, 8), nullable=False),
    Column("volume", Numeric(20, 8), nullable=False, server_default="0"),
    Column("is_complete", Boolean, nullable=False, server_default=text("true")),
    Column("source", String(40), nullable=False, server_default="oanda"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "instrument_id",
        "timeframe_id",
        "candle_time",
        name="uq_candle_instrument_timeframe_time",
    ),
    Index(
        "idx_candle_instrument_timeframe_time",
        "instrument_id",
        "timeframe_id",
        text("candle_time DESC"),
    ),
    schema="market",
)
