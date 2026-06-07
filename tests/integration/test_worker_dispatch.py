"""Integration tests for worker dispatch — real Postgres via testcontainers.

Tests the full dispatch cycle end-to-end:
  - queued records → dispatched after tick with FakeSMTPClient
  - Dispatch provenance fields (dispatched_at, dispatch_agent_version) are set
  - Email body contains the record's coordinate
  - SMTP failure for one record leaves it queued; others still dispatched
  - Already-dispatched records are not re-dispatched
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


from apollo.db.models import CorpusRecord
from apollo.domain.types import TargetStatus


# ---------------------------------------------------------------------------
# FakeSMTPClient
# ---------------------------------------------------------------------------


from tests.utils import FakeIMAPClient, FakeMarketDataClient, FakeSMTPClient


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


def _seed_queued(
    session,  # type: ignore[no-untyped-def]
    count: int,
    coordinate_prefix: str = "TEST",
) -> list[CorpusRecord]:
    """Insert ``count`` corpus_record rows in 'queued' status with coordinates."""
    from tests.factories import CorpusRecordFactory

    records: list[CorpusRecord] = []
    for i in range(count):
        coord = f"{coordinate_prefix}{i:04d}/ABCD"
        record = CorpusRecordFactory(
            status=TargetStatus.QUEUED.value,
            available_after=datetime.now(UTC) - timedelta(seconds=1),
            double_blind_coordinate=coord,
            queued_at=datetime.now(UTC),
        )
        records.append(record)  # type: ignore[arg-type]
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerDispatchIntegration:
    def test_tick_dispatches_queued_records(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """tick() with FakeSMTPClient dispatches all queued records."""
        _seed_queued(db_session, count=2)
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=FakeIMAPClient([]),
            market_client=FakeMarketDataClient(),
        )

        db_session.expire_all()
        dispatched = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .all()
        )
        assert len(dispatched) == 2, f"Expected 2 dispatched, got {len(dispatched)}"
        assert len(fake_smtp.sent) == 2

        from apollo.config import settings

        for e in fake_smtp.sent:
            assert e["to"] == settings.asset_email_address

    def test_dispatched_records_have_provenance(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Dispatched records must have non-null dispatched_at (UTC) and dispatch_agent_version."""
        _seed_queued(db_session, count=2)
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=FakeIMAPClient([]),
            market_client=FakeMarketDataClient(),
        )

        db_session.expire_all()
        records = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .all()
        )
        assert len(records) == 2
        for record in records:
            assert record.dispatched_at is not None, "dispatched_at must be set"
            assert record.dispatched_at.tzinfo is not None, (
                "dispatched_at must be UTC-aware"
            )
            assert record.dispatch_agent_version is not None, (
                "dispatch_agent_version must be set"
            )
            assert len(record.dispatch_agent_version) > 0

    def test_email_body_contains_coordinate(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Each dispatched email body must contain the record's coordinate."""
        records = _seed_queued(db_session, count=2, coordinate_prefix="DISP")
        expected_coords = {
            r.double_blind_coordinate for r in records if r.double_blind_coordinate
        }
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=FakeIMAPClient([]),
            market_client=FakeMarketDataClient(),
        )

        for coord in expected_coords:
            assert any(
                coord in e["subject"] or coord in e["body"] for e in fake_smtp.sent
            ), f"Coordinate {coord!r} not found in any sent email"

    def test_smtp_failure_leaves_record_queued(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """If SMTP fails for one record, that record stays 'queued'; others become 'dispatched'."""
        _seed_queued(db_session, count=2)
        # Raise on the first send only
        fake_smtp = FakeSMTPClient(raise_on_nth=1)

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=FakeIMAPClient([]),
            market_client=FakeMarketDataClient(),
        )

        db_session.expire_all()
        dispatched_count = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .count()
        )
        queued_count = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .count()
        )
        assert dispatched_count == 1, (
            f"Expected 1 dispatched (SMTP failed for 1), got {dispatched_count}"
        )
        assert queued_count == 1, f"Expected 1 still queued, got {queued_count}"
        # Only one email was successfully sent
        assert len(fake_smtp.sent) == 1

    def test_tick_does_not_redispatch_already_dispatched(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Records already in 'dispatched' status must not generate new emails."""
        # Seed 1 already-dispatched + 1 queued
        dispatched_record = CorpusRecord(
            target_statement="Already done target",
            parameter_name="rvd",
            is_control_target=False,
            age_in_hours=None,
            admin_awareness_tier="tier1",
            admin_psychological_context=None,
            status=TargetStatus.DISPATCHED.value,
            available_after=datetime.now(UTC) - timedelta(seconds=1),
            double_blind_coordinate="XXXX/YYYY",
            queued_at=datetime.now(UTC) - timedelta(minutes=5),
            dispatched_at=datetime.now(UTC) - timedelta(minutes=4),
            dispatch_agent_version="0.1.0",
        )
        db_session.add(dispatched_record)
        _seed_queued(db_session, count=1)
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=FakeIMAPClient([]),
            market_client=FakeMarketDataClient(),
        )

        # Only 1 new email for the newly queued record
        assert len(fake_smtp.sent) == 1, (
            f"Expected 1 email (re-dispatch prevented), got {len(fake_smtp.sent)}"
        )
