"""SQLAlchemy ORM models for Apollo.

DDL is the single source of truth — driven exclusively by Alembic migrations.
Column definitions here must mirror the migration files exactly.

Mutable worker-state columns (status, available_after, double_blind_coordinate,
queued_at) are excluded from the immutability trigger (see migration
a1b2c3d4e5f6). Core identity columns remain permanently immutable.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column


class Base(DeclarativeBase):
    pass


class CorpusRecord(Base):
    """Primary event-sourced record for a remote viewing session.

    Lifecycle:
        pending → queued (coordinate assigned by worker tick)
        queued  → dispatched (tasking email sent, Story 1.3)
        dispatched → sealed (extraction committed, Epic 2)
    """

    __tablename__ = "corpus_record"

    # --- Immutable identity columns (protected by DB trigger) ---
    id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    target_statement: MappedColumn[str] = mapped_column(String, nullable=False)
    parameter_name: MappedColumn[str] = mapped_column(String, nullable=False)
    is_control_target: MappedColumn[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    age_in_hours: MappedColumn[int | None] = mapped_column(Integer, nullable=True)

    # Admin State — immutable once written
    admin_awareness_tier: MappedColumn[str] = mapped_column(String, nullable=False)
    admin_psychological_context: MappedColumn[str | None] = mapped_column(
        String, nullable=True
    )

    created_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # --- Mutable worker lifecycle columns ---
    # String (not Postgres ENUM) for Alembic reversibility.
    # Application-level type safety via domain.types.TargetStatus.
    status: MappedColumn[str] = mapped_column(String, nullable=False, default="pending")
    available_after: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    double_blind_coordinate: MappedColumn[str | None] = mapped_column(
        String, nullable=True
    )
    queued_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
