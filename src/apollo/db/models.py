"""SQLAlchemy ORM models for Apollo.

DDL is the single source of truth — driven exclusively by Alembic migrations.
Column definitions here must mirror the migration files exactly.

Mutable worker-state columns (status, available_after, double_blind_coordinate,
queued_at) are excluded from the immutability trigger (see migration
a1b2c3d4e5f6). Core identity columns remain permanently immutable.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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

    # Dispatch provenance columns (set on queued → dispatched transition)
    dispatched_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispatch_agent_version: MappedColumn[str | None] = mapped_column(
        String, nullable=True
    )

    # Email ingestion columns (set on dispatched → extraction attempt, Story 2.1)
    raw_email_bytes: MappedColumn[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    received_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Sealing columns (set on dispatched → sealed transition, Story 2.2)
    extraction_payload: MappedColumn[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    raw_hash: MappedColumn[str | None] = mapped_column(String(64), nullable=True)
    sealed_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seal_agent_version: MappedColumn[str | None] = mapped_column(String, nullable=True)

    # 2x2 Stakes Matrix columns (set at configure_target time, Story 2.2)
    real_money_at_stake: MappedColumn[bool | None] = mapped_column(
        Boolean, nullable=True, default=False
    )
    asset_financial_awareness: MappedColumn[bool | None] = mapped_column(
        Boolean, nullable=True
    )

    # Market validation columns (set at configure_target time, Story 3.1)
    ticker: MappedColumn[str | None] = mapped_column(String, nullable=True)
    expiry_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    threshold_pct: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    threshold_direction: MappedColumn[str | None] = mapped_column(String, nullable=True)


class QuarantineRecord(Base):
    """Holds raw email bytes from failed extractions (exception path, Story 2.3).

    Physically separates corrupted/unvalidatable extractions from the primary
    corpus_record ledger. Cascade-deletes when the parent corpus_record is removed.

    Lifecycle:
        created on ExtractionSchemaError in worker Phase 3
        clarification_sent_at set after successful SMTP dispatch
    """

    __tablename__ = "quarantine_record"

    id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    corpus_record_id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        ForeignKey("corpus_record.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_email_bytes: MappedColumn[bytes] = mapped_column(LargeBinary, nullable=False)
    quarantine_reason: MappedColumn[str] = mapped_column(String, nullable=False)
    error_detail: MappedColumn[str] = mapped_column(String, nullable=False)
    quarantined_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    clarification_sent_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    clarification_agent_version: MappedColumn[str | None] = mapped_column(
        String, nullable=True
    )


class EnvFingerprint(Base):
    """Environmental context snapshot for a sealed corpus_record (Story 2.4).

    One-to-one with CorpusRecord. Created post-seal by FingerprintService.attach().
    retrieval_status reflects completeness of external NOAA API fetches:
      'ok' = both metrics fetched, 'partial' = one failed, 'pending' = both failed.
    """

    __tablename__ = "env_fingerprint"

    id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    corpus_record_id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        ForeignKey("corpus_record.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    fingerprinted_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    measurement_timestamp: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    local_sidereal_time: MappedColumn[float | None] = mapped_column(
        Float, nullable=True
    )
    kp_index: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    solar_wind_speed: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    retrieval_status: MappedColumn[str] = mapped_column(
        String, nullable=False, default="pending"
    )
    retrieval_notes: MappedColumn[str | None] = mapped_column(String, nullable=True)


class ValidationRecord(Base):
    """Ground-truth market outcome for a sealed corpus_record (Story 3.1).

    One-to-one with CorpusRecord via UNIQUE FK. Created by ValidationService.validate_pending().
    Never modifies corpus_record — purely a derived, append-only record.
    validation_status: 'hit' | 'miss' | 'offset' (fetched >2h past expiry)
    """

    __tablename__ = "validation_record"

    id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    corpus_record_id: MappedColumn[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        ForeignKey("corpus_record.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    validated_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    validation_status: MappedColumn[str] = mapped_column(String, nullable=False)
    param_value: MappedColumn[float] = mapped_column(Float, nullable=False)
    actual_open: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    actual_close: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    actual_change_pct: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    threshold_pct_snapshot: MappedColumn[float | None] = mapped_column(
        Float, nullable=True
    )
    threshold_direction_snapshot: MappedColumn[str | None] = mapped_column(
        String, nullable=True
    )
    predicted_positive: MappedColumn[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    actual_positive: MappedColumn[bool | None] = mapped_column(Boolean, nullable=True)
    fetch_delay_seconds: MappedColumn[float | None] = mapped_column(
        Float, nullable=True
    )
    validation_agent_version: MappedColumn[str | None] = mapped_column(
        String, nullable=True
    )
    fetch_error: MappedColumn[str | None] = mapped_column(String, nullable=True)
    closed_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
