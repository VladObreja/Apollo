"""add_corpus_record_immutability_trigger

Adds a BEFORE UPDATE trigger on corpus_record that raises an exception
for any attempted modification. This enforces AC-2 of Story 1.1 —
Admin State Snapshots are permanently and immutably associated with
their record once written.

Revision ID: b4c7e1f02a9d
Revises: d21693fe0e00
Create Date: 2026-06-02

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b4c7e1f02a9d"
down_revision: Union[str, Sequence[str], None] = "d21693fe0e00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION enforce_corpus_record_immutability()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'corpus_record rows are immutable and cannot be updated (row id: %)', OLD.id;
END;
$$ LANGUAGE plpgsql;
"""

_CREATE_TRIGGER = """
CREATE TRIGGER corpus_record_immutability_trigger
BEFORE UPDATE ON corpus_record
FOR EACH ROW EXECUTE FUNCTION enforce_corpus_record_immutability();
"""

_DROP_TRIGGER = (
    "DROP TRIGGER IF EXISTS corpus_record_immutability_trigger ON corpus_record;"
)
_DROP_FUNCTION = "DROP FUNCTION IF EXISTS enforce_corpus_record_immutability();"


def upgrade() -> None:
    """Add immutability trigger to corpus_record."""
    op.execute(_CREATE_FUNCTION)
    op.execute(_CREATE_TRIGGER)


def downgrade() -> None:
    """Remove immutability trigger from corpus_record."""
    op.execute(_DROP_TRIGGER)
    op.execute(_DROP_FUNCTION)
