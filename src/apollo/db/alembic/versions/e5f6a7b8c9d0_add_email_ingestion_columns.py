"""add_email_ingestion_columns

Adds inbound email ingestion columns to corpus_record (Story 2.1):
  - raw_email_bytes: raw MIME bytes of the Asset's reply email (immutable once written)
  - received_at: UTC timestamp when the email was received from IMAP

These are mutable lifecycle columns exempt from the immutability trigger
(a1b2c3d4e5f6), which only guards the 8 named core identity columns.

Revision ID: e5f6a7b8c9d0
Revises: c9d8e7f6a5b4
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email ingestion columns and index."""
    op.add_column(
        "corpus_record",
        sa.Column("raw_email_bytes", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_corpus_record_received_at",
        "corpus_record",
        ["received_at"],
    )


def downgrade() -> None:
    """Remove email ingestion columns and index."""
    op.drop_index(
        "ix_corpus_record_received_at", table_name="corpus_record", if_exists=True
    )
    op.drop_column("corpus_record", "received_at")
    op.drop_column("corpus_record", "raw_email_bytes")
