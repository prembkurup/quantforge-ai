"""create research knowledge base tables

Revision ID: 0002_research_knowledge
Revises: 0001_create_market_candles
Create Date: 2026-07-04 03:45:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_research_knowledge"
down_revision: str | None = "0001_create_market_candles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute("CREATE SCHEMA IF NOT EXISTS research")

    op.create_table(
        "hypothesis",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hypothesis_key", sa.String(length=160), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("supported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("hypothesis_key", "version", name="uq_hypothesis_key_version"),
        schema="research",
    )

    op.create_table(
        "knowledge_record",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("object_type", sa.String(length=40), nullable=False),
        sa.Column("object_key", sa.String(length=180), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("experiment_key", sa.String(length=160), nullable=False),
        sa.Column("hypothesis_key", sa.String(length=160), nullable=True),
        sa.Column("instrument", sa.String(length=32), nullable=True),
        sa.Column("timeframe", sa.String(length=20), nullable=True),
        sa.Column("market_regime", sa.String(length=80), nullable=True),
        sa.Column("session", sa.String(length=80), nullable=True),
        sa.Column("metric_name", sa.String(length=80), nullable=False, server_default="success_rate"),
        sa.Column("metric_value", sa.Numeric(12, 6), nullable=True),
        sa.Column("stability", sa.Numeric(8, 4), nullable=True),
        sa.Column("importance", sa.Numeric(8, 4), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("lessons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="research",
    )
    op.create_index(
        "idx_knowledge_record_object",
        "knowledge_record",
        ["object_type", "object_key"],
        schema="research",
    )
    op.create_index(
        "idx_knowledge_record_context",
        "knowledge_record",
        ["instrument", "timeframe", "market_regime", "session"],
        schema="research",
    )

    op.create_table(
        "knowledge_score",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("object_type", sa.String(length=40), nullable=False),
        sa.Column("object_key", sa.String(length=180), nullable=False),
        sa.Column("success_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("stability", sa.Numeric(8, 4), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(8, 4), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("object_type", "object_key", "version", name="uq_knowledge_score_object_version"),
        schema="research",
    )

    op.create_table(
        "knowledge_recommendation",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recommendation_key", sa.String(length=180), nullable=False),
        sa.Column("recommendation_type", sa.String(length=60), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("source_object_type", sa.String(length=40), nullable=True),
        sa.Column("source_object_key", sa.String(length=180), nullable=True),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("recommendation_key", name="uq_knowledge_recommendation_key"),
        schema="research",
    )


def downgrade() -> None:
    op.drop_table("knowledge_recommendation", schema="research")
    op.drop_table("knowledge_score", schema="research")
    op.drop_index("idx_knowledge_record_context", table_name="knowledge_record", schema="research")
    op.drop_index("idx_knowledge_record_object", table_name="knowledge_record", schema="research")
    op.drop_table("knowledge_record", schema="research")
    op.drop_table("hypothesis", schema="research")
