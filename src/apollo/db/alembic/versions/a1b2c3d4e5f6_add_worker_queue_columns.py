"""add_worker_queue_columns

Adds worker queue columns to corpus_record:
  - status: lifecycle state machine (pending → queued → dispatched → sealed)
  - available_after: Age-In protocol gate (UTC datetime)
  - double_blind_coordinate: generated XXXX/YYYY blinded coordinate
  - queued_at: timestamp when coordinate was assigned

Also adds a Postgres NOTIFY trigger (AFTER INSERT) to broadcast new target
events on the 'apollo_jobs' channel.

Updates the immutability trigger from Story 1.1 to be column-selective:
the BEFORE UPDATE guard now only blocks mutations to the immutable core
columns (target identity and admin state), allowing the worker to advance
the mutable lifecycle columns (status, double_blind_coordinate, queued_at).

Revision ID: a1b2c3d4e5f6
Revises: b4c7e1f02a9d
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b4c7e1f02a9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Updated immutability trigger — now column-selective
# ---------------------------------------------------------------------------
_DROP_OLD_TRIGGER = (
    "DROP TRIGGER IF EXISTS corpus_record_immutability_trigger ON corpus_record;"
)
_DROP_OLD_FUNCTION = "DROP FUNCTION IF EXISTS enforce_corpus_record_immutability();"

_CREATE_UPDATED_IMMUTABILITY_FUNCTION = """
CREATE OR REPLACE FUNCTION enforce_corpus_record_immutability()
RETURNS TRIGGER AS $$
BEGIN
    -- Only guard the core immutable columns; worker lifecycle columns are mutable.
    IF (
        OLD.id                     IS DISTINCT FROM NEW.id                     OR
        OLD.target_statement       IS DISTINCT FROM NEW.target_statement       OR
        OLD.parameter_name         IS DISTINCT FROM NEW.parameter_name         OR
        OLD.is_control_target      IS DISTINCT FROM NEW.is_control_target      OR
        OLD.age_in_hours           IS DISTINCT FROM NEW.age_in_hours           OR
        OLD.admin_awareness_tier   IS DISTINCT FROM NEW.admin_awareness_tier   OR
        OLD.admin_psychological_context IS DISTINCT FROM NEW.admin_psychological_context OR
        OLD.created_at             IS DISTINCT FROM NEW.created_at
    ) THEN
        RAISE EXCEPTION
            'Immutable columns of corpus_record cannot be updated (row id: %)', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_CREATE_UPDATED_IMMUTABILITY_TRIGGER = """
CREATE TRIGGER corpus_record_immutability_trigger
BEFORE UPDATE ON corpus_record
FOR EACH ROW EXECUTE FUNCTION enforce_corpus_record_immutability();
"""

# Downgrade: restore the original blanket-immutability trigger from Story 1.1
_RESTORE_ORIGINAL_FUNCTION = """
CREATE OR REPLACE FUNCTION enforce_corpus_record_immutability()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'corpus_record rows are immutable and cannot be updated (row id: %)', OLD.id;
END;
$$ LANGUAGE plpgsql;
"""

_RESTORE_ORIGINAL_TRIGGER = """
CREATE TRIGGER corpus_record_immutability_trigger
BEFORE UPDATE ON corpus_record
FOR EACH ROW EXECUTE FUNCTION enforce_corpus_record_immutability();
"""

# ---------------------------------------------------------------------------
# NOTIFY trigger — fires on INSERT to broadcast new target events
# ---------------------------------------------------------------------------
_CREATE_NOTIFY_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_new_target()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify(
        'apollo_jobs',
        json_build_object('event_type', 'target_created', 'record_id', NEW.id)::text
    );
    RETURN NEW;
END;
$$;
"""

_CREATE_NOTIFY_TRIGGER = """
CREATE TRIGGER corpus_record_notify_insert
    AFTER INSERT ON corpus_record
    FOR EACH ROW EXECUTE FUNCTION notify_new_target();
"""

_DROP_NOTIFY_TRIGGER = (
    "DROP TRIGGER IF EXISTS corpus_record_notify_insert ON corpus_record;"
)
_DROP_NOTIFY_FUNCTION = "DROP FUNCTION IF EXISTS notify_new_target();"


def upgrade() -> None:
    """Add worker queue columns and update immutability/notify triggers."""
    # 1. Add new columns
    op.add_column(
        "corpus_record",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "corpus_record",
        sa.Column(
            "available_after",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.add_column(
        "corpus_record",
        sa.Column("double_blind_coordinate", sa.String(), nullable=True),
    )
    op.add_column(
        "corpus_record",
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add indexes for worker queue queries
    op.create_index(
        "ix_corpus_record_available_after",
        "corpus_record",
        ["available_after"],
    )
    op.create_index(
        "ix_corpus_record_queued_at",
        "corpus_record",
        ["queued_at"],
    )

    # 2. Replace blanket immutability trigger with column-selective version
    op.execute(_DROP_OLD_TRIGGER)
    op.execute(_DROP_OLD_FUNCTION)
    op.execute(_CREATE_UPDATED_IMMUTABILITY_FUNCTION)
    op.execute(_CREATE_UPDATED_IMMUTABILITY_TRIGGER)

    # 3. Add NOTIFY trigger for LISTEN/NOTIFY event bus
    op.execute(_CREATE_NOTIFY_FUNCTION)
    op.execute(_CREATE_NOTIFY_TRIGGER)


def downgrade() -> None:
    """Remove worker queue columns and restore original triggers."""
    # 1. Drop NOTIFY trigger and function
    op.execute(_DROP_NOTIFY_TRIGGER)
    op.execute(_DROP_NOTIFY_FUNCTION)

    # 2. Restore blanket immutability trigger (reverse order: trigger, function)
    op.execute(_DROP_OLD_TRIGGER)
    op.execute(_DROP_OLD_FUNCTION)
    op.execute(_RESTORE_ORIGINAL_FUNCTION)
    op.execute(_RESTORE_ORIGINAL_TRIGGER)

    # Drop indexes
    op.drop_index("ix_corpus_record_queued_at", table_name="corpus_record")
    op.drop_index("ix_corpus_record_available_after", table_name="corpus_record")

    # 3. Drop new columns (reverse order of addition)
    op.drop_column("corpus_record", "queued_at")
    op.drop_column("corpus_record", "double_blind_coordinate")
    op.drop_column("corpus_record", "available_after")
    op.drop_column("corpus_record", "status")
