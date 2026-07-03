"""create market candle tables

Revision ID: 0001_create_market_candles
Revises:
Create Date: 2026-07-04 00:55:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_market_candles"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute("CREATE SCHEMA IF NOT EXISTS instrument")
    op.execute("CREATE SCHEMA IF NOT EXISTS market")

    op.create_table(
        "instrument",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("asset_class", sa.String(length=40), nullable=False, server_default="forex"),
        sa.Column("pip_location", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("symbol", name="uq_instrument_symbol"),
        schema="instrument",
    )

    op.create_table(
        "timeframe",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_timeframe_code"),
        schema="instrument",
    )

    op.create_table(
        "candle",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("timeframe_id", sa.Uuid(), nullable=False),
        sa.Column("candle_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("high_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("low_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("volume", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="oanda"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["instrument_id"], ["instrument.instrument.id"]),
        sa.ForeignKeyConstraint(["timeframe_id"], ["instrument.timeframe.id"]),
        sa.UniqueConstraint(
            "instrument_id",
            "timeframe_id",
            "candle_time",
            name="uq_candle_instrument_timeframe_time",
        ),
        schema="market",
    )
    op.create_index(
        "idx_candle_instrument_timeframe_time",
        "candle",
        ["instrument_id", "timeframe_id", sa.text("candle_time DESC")],
        schema="market",
    )


def downgrade() -> None:
    op.drop_index("idx_candle_instrument_timeframe_time", table_name="candle", schema="market")
    op.drop_table("candle", schema="market")
    op.drop_table("timeframe", schema="instrument")
    op.drop_table("instrument", schema="instrument")
