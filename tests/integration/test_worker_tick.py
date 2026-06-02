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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from apollo.db.models import CorpusRecord
from apollo.domain.types import TargetStatus

_COORD_RE = re.compile(r"^[0-9A-F]{4}/[0-9A-F]{4}$")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def postgres_container():  # type: ignore[no-untyped-def]
    """Spin up a real Postgres container for the test module."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="module")
def db_engine(postgres_container: PostgresContainer):  # type: ignore[no-untyped-def]
    """Create engine + run all Alembic migrations against the container."""
    db_url = postgres_container.get_connection_url()
    engine = create_engine(db_url)

    # Run migrations via Alembic so the schema matches production exactly
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "src/apollo/db/alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):  # type: ignore[no-untyped-def]
    """Provide a clean-slate session per test.

    Truncates corpus_record before each test so that committed data from prior
    tests (seeding + tick() commits its own transaction) does not bleed through.
    Rollback on teardown handles any uncommitted changes in this session.
    """
    SessionFactory = sessionmaker(bind=db_engine)
    with SessionFactory() as session:
        session.execute(text("DELETE FROM corpus_record"))
        session.commit()
        yield session
        session.rollback()


@pytest.fixture()
def patched_db_url(
    postgres_container: PostgresContainer, monkeypatch: pytest.MonkeyPatch
):  # type: ignore[no-untyped-def]
    """Patch the app's settings so worker.tick() connects to the test container."""
    db_url = postgres_container.get_connection_url()
    monkeypatch.setenv("DATABASE_URL", db_url)
    # Reset the lazy session factory so it picks up the patched URL
    import apollo.db.session as sess_mod

    sess_mod._engine = None
    sess_mod._SessionFactory = None
    yield db_url
    # Teardown: reset again to avoid leaking state into other tests
    sess_mod._engine = None
    sess_mod._SessionFactory = None


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
    records = []
    for i in range(count):
        record = CorpusRecord(
            target_statement=f"Integration test target {i}",
            parameter_name="vad",
            is_control_target=False,
            age_in_hours=None,
            admin_awareness_tier="tier1",
            admin_psychological_context=None,
            status=status,
            available_after=datetime.now(UTC)
            + timedelta(seconds=available_after_offset_seconds),
            double_blind_coordinate=None,
            queued_at=queued_at,
        )
        session.add(record)
        records.append(record)
    session.commit()
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
        import pytest
        from sqlalchemy.exc import SQLAlchemyError

        _seed_records(db_session, count=1)
        record = db_session.query(CorpusRecord).first()
        assert record is not None

        record.target_statement = "TAMPERED"
        with pytest.raises(SQLAlchemyError):
            db_session.flush()
