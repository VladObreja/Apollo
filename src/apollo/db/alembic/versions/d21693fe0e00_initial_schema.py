"""initial_schema

Revision ID: d21693fe0e00
Revises: 
Create Date: 2026-06-02 09:54:24.944647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd21693fe0e00'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # pgcrypto provides gen_random_uuid() for server-side UUID generation
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        'corpus_record',
        sa.Column(
            'id',
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column('target_statement', sa.String(), nullable=False),
        sa.Column('parameter_name', sa.String(), nullable=False),
        sa.Column('is_control_target', sa.Boolean(), nullable=False),
        sa.Column('age_in_hours', sa.Integer(), nullable=True),
        sa.Column('admin_awareness_tier', sa.String(), nullable=False),
        sa.Column('admin_psychological_context', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('corpus_record')
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
