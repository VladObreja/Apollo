"""add_env_fingerprint_table

Creates the env_fingerprint table (Story 2.4):
  - Stores environmental context snapshot for each sealed session
  - UNIQUE FK → corpus_record with ON DELETE CASCADE (one fingerprint per record)
  - retrieval_status tracks completeness of external NOAA API fetches

Revision ID: b5c6d7e8f9a0
Revises: a2b3c4d5e6f7
Create Date: 2026-06-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "env_fingerprint",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "corpus_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("corpus_record.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("fingerprinted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measurement_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local_sidereal_time", sa.Float(), nullable=True),
        sa.Column("kp_index", sa.Float(), nullable=True),
        sa.Column("solar_wind_speed", sa.Float(), nullable=True),
        sa.Column(
            "retrieval_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retrieval_notes", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_env_fingerprint_corpus_record_id",
        "env_fingerprint",
        ["corpus_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_env_fingerprint_corpus_record_id", table_name="env_fingerprint")
    op.drop_table("env_fingerprint")
