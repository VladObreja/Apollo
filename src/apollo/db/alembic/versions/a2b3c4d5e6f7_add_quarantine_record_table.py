"""add_quarantine_record_table

Creates the quarantine_record table (Story 2.3):
  - Holds raw email bytes from failed extractions (bypasses main ledger)
  - FK → corpus_record with ON DELETE CASCADE
  - Tracks clarification dispatch: clarification_sent_at, clarification_agent_version
  - ON DELETE CASCADE means DELETE FROM corpus_record cascades automatically

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quarantine_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "corpus_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("corpus_record.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_email_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("quarantine_reason", sa.String(), nullable=False),
        sa.Column("error_detail", sa.String(), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clarification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clarification_agent_version", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_quarantine_record_corpus_record_id",
        "quarantine_record",
        ["corpus_record_id"],
    )
    op.create_index(
        "ix_quarantine_record_quarantined_at",
        "quarantine_record",
        ["quarantined_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_quarantine_record_quarantined_at", table_name="quarantine_record")
    op.drop_index(
        "ix_quarantine_record_corpus_record_id", table_name="quarantine_record"
    )
    op.drop_table("quarantine_record")
