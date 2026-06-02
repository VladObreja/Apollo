"""Integration tests for the worker tick — real Postgres via testcontainers.

Tests the full tick() cycle end-to-end:
  - Daily cap enforcement (max 5 targets per day)
  - FOR UPDATE SKIP LOCKED idempotency (second tick claims 0 new records)
  - Age-In protocol (available_after in the future = not claimed)
  - Coordinate format validation on saved records
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pytest

from apollo.db.models import CorpusRecord
from apollo.domain.types import TargetStatus

_COORD_RE = re.compile(r"^[0-9A-F]{4}/[0-9A-F]{4}$")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


def _seed_records(
    session,  # type: ignore[no-untyped-def]
    count: int,
    status: str = TargetStatus.PENDING.value,
    available_after_offset_seconds: int = -1,
    queued_at: datetime | None = None,
) -> list[CorpusRecord]:
    """Insert ``count`` CorpusRecord rows with given status."""
    from tests.factories import CorpusRecordFactory

    records: list[CorpusRecord] = []
    for _ in range(count):
        record = CorpusRecordFactory(
            status=status,
            available_after=datetime.now(UTC)
            + timedelta(seconds=available_after_offset_seconds),
            queued_at=queued_at,
        )
        records.append(record)  # type: ignore[arg-type]
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerTickIntegration:
    def test_tick_assigns_coordinates_to_pending_records(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Basic tick: 5 pending records → all 5 get queued with coordinates."""
        _seed_records(db_session, count=5)

        from apollo.services.worker import tick

        tick()

        db_session.expire_all()
        queued = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .all()
        )
        assert len(queued) == 5
        for record in queued:
            assert record.double_blind_coordinate is not None
            assert _COORD_RE.match(record.double_blind_coordinate), (
                f"Invalid coord format: {record.double_blind_coordinate}"
            )
            assert record.queued_at is not None

    def test_tick_respects_daily_cap(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """With 2 already dispatched today, only 3 more can be claimed."""
        today = datetime.now(UTC)
        _seed_records(
            db_session,
            count=2,
            status=TargetStatus.DISPATCHED.value,
            queued_at=today,
        )
        _seed_records(db_session, count=7)  # 7 pending, only 3 slots remain

        from apollo.services.worker import tick

        tick()

        db_session.expire_all()
        newly_queued = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .all()
        )
        assert len(newly_queued) == 3, (
            f"Expected 3 queued (cap=5, 2 already dispatched), got {len(newly_queued)}"
        )

    def test_tick_is_idempotent(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Running tick twice should not claim additional records on second run."""
        _seed_records(db_session, count=3)

        from apollo.services.worker import tick

        tick()

        db_session.expire_all()
        after_first = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .count()
        )
        assert after_first == 3

        tick()

        db_session.expire_all()
        after_second = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .count()
        )
        assert after_second == 3, "Second tick must not claim already-queued records"

    def test_tick_skips_records_not_yet_available(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Records with available_after in the future must not be claimed."""
        _seed_records(db_session, count=2)  # immediately available
        _seed_records(
            db_session,
            count=3,
            available_after_offset_seconds=3600,  # available 1 hour from now
        )

        from apollo.services.worker import tick

        tick()

        db_session.expire_all()
        queued = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .all()
        )
        assert len(queued) == 2, (
            f"Only 2 records should be claimed (others still in Age-In window), got {len(queued)}"
        )
        pending = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.PENDING.value)
            .count()
        )
        assert pending == 3

    def test_tick_when_daily_cap_already_reached(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """If 5 already dispatched today, tick must claim 0 additional records."""
        today = datetime.now(UTC)
        _seed_records(
            db_session,
            count=5,
            status=TargetStatus.DISPATCHED.value,
            queued_at=today,
        )
        _seed_records(db_session, count=3)  # pending, but cap reached

        from apollo.services.worker import tick

        tick()

        db_session.expire_all()
        queued = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .count()
        )
        assert queued == 0, "No records should be queued once daily cap is reached"

    def test_coordinate_uniqueness_across_records(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Each claimed record must receive a unique coordinate."""
        _seed_records(db_session, count=5)

        from apollo.services.worker import tick

        tick()

        db_session.expire_all()
        queued = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .all()
        )
        coords = [r.double_blind_coordinate for r in queued]
        assert len(coords) == len(set(coords)), (
            f"Duplicate coordinates detected: {coords}"
        )

    def test_immutability_trigger_allows_status_update(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """The column-selective immutability trigger must not block status updates."""
        _seed_records(db_session, count=1)

        # tick() calls session.add() + commit which triggers BEFORE UPDATE
        # If trigger is still blanket-immutable this will raise an exception
        from apollo.services.worker import tick

        tick()  # Should not raise

        db_session.expire_all()
        record = db_session.query(CorpusRecord).first()
        assert record is not None
        assert record.status == TargetStatus.QUEUED.value

    def test_immutability_trigger_still_blocks_identity_update(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Updating an immutable column (target_statement) must still raise."""
        from sqlalchemy.exc import SQLAlchemyError

        _seed_records(db_session, count=1)
        record = db_session.query(CorpusRecord).first()
        assert record is not None

        record.target_statement = "TAMPERED"
        with pytest.raises(SQLAlchemyError):
            db_session.flush()
