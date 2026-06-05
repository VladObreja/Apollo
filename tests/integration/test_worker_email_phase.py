"""Integration tests for worker Phase 3 — email ingestion & extraction.

Tests the full Phase 3 cycle using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - FakeIMAPClient with synthetic raw MIME emails
  - FakeLLM with canned JSON responses

Verifies:
  - Matched emails → raw_email_bytes and received_at persisted on corpus_record
  - Status advances to 'sealed' after successful extraction (Story 2.2)
  - ExtractionSchemaError is caught per-record; tick does not raise
  - Failed extractions leave the record in 'dispatched' status
"""

from __future__ import annotations

import email.mime.multipart
import email.mime.text
import hashlib
import json
from datetime import UTC, datetime, timedelta

from apollo.db.models import CorpusRecord
from apollo.domain.types import TargetStatus
from tests.utils import FakeIMAPClient, FakeLLM, FakeSMTPClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reply_email(coordinate: str, body: str) -> bytes:
    """Build a synthetic plain-text reply email with the given coordinate in subject."""
    msg = email.mime.text.MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Re: Apollo Research Session — Target ID {coordinate}"
    msg["From"] = "asset@proton.me"
    msg["To"] = "apollo@proton.me"
    return msg.as_bytes()


def _valid_extraction_json(param_value: float = 75.0) -> str:
    return json.dumps({"param_value": param_value})


def _seed_dispatched(
    session,  # type: ignore[no-untyped-def]
    coordinate: str,
) -> CorpusRecord:
    """Insert a corpus_record in 'dispatched' status with the given coordinate."""
    from tests.factories import CorpusRecordFactory

    record = CorpusRecordFactory(
        status=TargetStatus.DISPATCHED.value,
        available_after=datetime.now(UTC) - timedelta(seconds=1),
        double_blind_coordinate=coordinate,
        queued_at=datetime.now(UTC) - timedelta(minutes=5),
        dispatched_at=datetime.now(UTC) - timedelta(minutes=4),
        dispatch_agent_version="0.1.0",
    )
    return record  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerEmailPhaseIntegration:
    def test_tick_stores_raw_email_bytes_on_matched_record(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """tick() Phase 3: matched email → raw_email_bytes and received_at stored."""
        coord = "8A2F/9B4C"
        _seed_dispatched(db_session, coordinate=coord)

        raw = _make_reply_email(coord, "PARAM (vad): 75")
        imap_client = FakeIMAPClient([raw])
        llm_client = FakeLLM([_valid_extraction_json(75.0)])
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(smtp_client=fake_smtp, imap_client=imap_client, llm_client=llm_client)

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.raw_email_bytes is not None, "raw_email_bytes must be stored"
        assert len(record.raw_email_bytes) > 0

    def test_tick_sets_received_at_as_utc_datetime(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """received_at must be a non-null UTC-aware datetime after Phase 3."""
        coord = "AAAA/BBBB"
        _seed_dispatched(db_session, coordinate=coord)

        raw = _make_reply_email(coord, "PARAM (vad): 80")
        imap_client = FakeIMAPClient([raw])
        llm_client = FakeLLM([_valid_extraction_json(80.0)])
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(smtp_client=fake_smtp, imap_client=imap_client, llm_client=llm_client)

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.received_at is not None, "received_at must be set"
        assert record.received_at.tzinfo is not None, "received_at must be UTC-aware"

    def test_tick_seals_record_on_successful_extraction(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Status must advance to 'sealed' after successful extraction (Story 2.2)."""
        coord = "CCCC/DDDD"
        _seed_dispatched(db_session, coordinate=coord)

        raw = _make_reply_email(coord, "PARAM (rvd): 60")
        imap_client = FakeIMAPClient([raw])
        llm_client = FakeLLM([_valid_extraction_json(60.0)])
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(smtp_client=fake_smtp, imap_client=imap_client, llm_client=llm_client)

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.status == TargetStatus.SEALED.value, (
            f"Expected 'sealed', got '{record.status}'"
        )
        assert record.raw_hash is not None
        assert record.raw_hash == hashlib.sha256(raw).hexdigest()
        assert record.extraction_payload is not None
        assert record.sealed_at is not None
        assert record.sealed_at.tzinfo is not None

    def test_tick_extraction_failure_does_not_raise(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """tick() must not raise even if extraction fails after retry — fail-operational."""
        coord = "EEEE/FFFF"
        _seed_dispatched(db_session, coordinate=coord)

        raw = _make_reply_email(coord, "PARAM (vad): 90")
        imap_client = FakeIMAPClient([raw])
        # FakeLLM returns invalid JSON twice → ExtractionSchemaError raised and caught
        llm_client = FakeLLM(["not json", "also not json"])
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        # Must NOT raise — ExtractionSchemaError is caught per-record
        tick(smtp_client=fake_smtp, imap_client=imap_client, llm_client=llm_client)

        # Record must still exist with raw bytes stored
        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        # raw bytes were stored before the failed LLM call
        assert record.raw_email_bytes is not None
        # Status stays dispatched (Story 2.3 will quarantine)
        assert record.status == TargetStatus.DISPATCHED.value

    def test_tick_ignores_email_with_unrecognised_coordinate(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Email with unknown coordinate must not cause errors or DB writes."""
        coord = "GGGG/HHHH"
        _seed_dispatched(db_session, coordinate=coord)

        # Email with a coordinate that doesn't match any record
        raw = _make_reply_email("ZZZZ/9999", "PARAM (vad): 50")
        imap_client = FakeIMAPClient([raw])
        llm_client = FakeLLM([])  # Should not be called
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(smtp_client=fake_smtp, imap_client=imap_client, llm_client=llm_client)

        # Our record must be untouched
        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.raw_email_bytes is None, (
            "Unmatched email must not write to record"
        )
        assert record.received_at is None
        # LLM must not have been called
        assert llm_client._call_count == 0
