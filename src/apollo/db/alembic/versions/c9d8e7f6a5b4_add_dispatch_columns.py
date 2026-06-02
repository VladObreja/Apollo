"""add_dispatch_columns

Adds dispatch provenance columns to corpus_record:
  - dispatched_at: timestamp when tasking email was sent (UTC)
  - dispatch_agent_version: Apollo package version at dispatch time

These are mutable lifecycle columns — the column-selective immutability
trigger (a1b2c3d4e5f6) only guards the 8 core identity columns; new
columns are mutable by design without any trigger update.

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dispatch provenance columns and index."""
    op.add_column(
        "corpus_record",
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column("dispatch_agent_version", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_corpus_record_dispatched_at",
        "corpus_record",
        ["dispatched_at"],
    )


def downgrade() -> None:
    """Remove dispatch provenance columns and index."""
    op.drop_index("ix_corpus_record_dispatched_at", table_name="corpus_record")
    op.drop_column("corpus_record", "dispatch_agent_version")
    op.drop_column("corpus_record", "dispatched_at")
