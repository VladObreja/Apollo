"""Add closed_at to validation_record for closure ceremony tracking.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-06
"""

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validation_record",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_validation_record_closed_at", "validation_record", ["closed_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_validation_record_closed_at", table_name="validation_record")
    op.drop_column("validation_record", "closed_at")
