"""Add market validation columns to corpus_record and validation_record table.

Revision ID: c1d2e3f4a5b6
Revises: b5c6d7e8f9a0
Create Date: 2026-06-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c1d2e3f4a5b6"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("corpus_record", sa.Column("ticker", sa.String(), nullable=True))
    op.add_column(
        "corpus_record",
        sa.Column("expiry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "corpus_record", sa.Column("threshold_pct", sa.Float(), nullable=True)
    )
    op.add_column(
        "corpus_record", sa.Column("threshold_direction", sa.String(), nullable=True)
    )
    op.create_index("ix_corpus_record_expiry_at", "corpus_record", ["expiry_at"])

    op.create_table(
        "validation_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "corpus_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("corpus_record.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("param_value", sa.Float(), nullable=False),
        sa.Column("actual_open", sa.Float(), nullable=True),
        sa.Column("actual_close", sa.Float(), nullable=True),
        sa.Column("actual_change_pct", sa.Float(), nullable=True),
        sa.Column("threshold_pct_snapshot", sa.Float(), nullable=True),
        sa.Column("threshold_direction_snapshot", sa.String(), nullable=True),
        sa.Column("predicted_positive", sa.Boolean(), nullable=True),
        sa.Column("actual_positive", sa.Boolean(), nullable=True),
        sa.Column("fetch_delay_seconds", sa.Float(), nullable=True),
        sa.Column("validation_agent_version", sa.String(), nullable=True),
        sa.Column("fetch_error", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_validation_record_corpus_record_id",
        "validation_record",
        ["corpus_record_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validation_record_corpus_record_id", table_name="validation_record"
    )
    op.drop_table("validation_record")
    op.drop_index("ix_corpus_record_expiry_at", table_name="corpus_record")
    op.drop_column("corpus_record", "threshold_direction")
    op.drop_column("corpus_record", "threshold_pct")
    op.drop_column("corpus_record", "expiry_at")
    op.drop_column("corpus_record", "ticker")
