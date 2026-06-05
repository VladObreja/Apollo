"""add_sealing_columns

Adds epistemological sealing columns to corpus_record (Story 2.2):
  - extraction_payload: JSONB storing validated ExtractionResultSchema
  - raw_hash: SHA-256 hex digest of raw_email_bytes (unique)
  - sealed_at: UTC timestamp of sealing
  - seal_agent_version: Apollo package version at sealing time
  - real_money_at_stake: 2x2 Stakes Matrix — objective capital flag
  - asset_financial_awareness: 2x2 Stakes Matrix — subjective awareness flag

All columns are mutable lifecycle columns exempt from the immutability
trigger (a1b2c3d4e5f6), which only guards the 8 named core identity columns.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "corpus_record",
        sa.Column("extraction_payload", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column("raw_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column("seal_agent_version", sa.String(), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column(
            "real_money_at_stake",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "corpus_record",
        sa.Column("asset_financial_awareness", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_corpus_record_sealed_at", "corpus_record", ["sealed_at"])
    op.create_index(
        "ix_corpus_record_raw_hash", "corpus_record", ["raw_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_corpus_record_raw_hash", table_name="corpus_record")
    op.drop_index("ix_corpus_record_sealed_at", table_name="corpus_record")
    op.drop_column("corpus_record", "asset_financial_awareness")
    op.drop_column("corpus_record", "real_money_at_stake")
    op.drop_column("corpus_record", "seal_agent_version")
    op.drop_column("corpus_record", "sealed_at")
    op.drop_column("corpus_record", "raw_hash")
    op.drop_column("corpus_record", "extraction_payload")
