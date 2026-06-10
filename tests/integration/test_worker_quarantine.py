"""Integration tests for worker Phase 3 — quarantine path (Story 2.3).

Tests the full exception path using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - FakeIMAPClient with synthetic raw MIME emails
  - FakeLLM that always fails extraction (causes ExtractionSchemaError)
  - FakeSMTPClient to capture clarification emails

Verifies:
  - Failed extraction → quarantine_record created, corpus_record.raw_email_bytes cleared
  - Clarification email sent with coordinate but NOT target_statement
  - SMTP failure → quarantine_record exists, clarification_sent_at = None (fail-operational)
"""

from __future__ import annotations

import email.mime.text
from datetime import UTC, datetime, timedelta

from apollo.db.models import CorpusRecord, QuarantineRecord
from apollo.domain.types import TargetStatus
from apollo.services.dispatch import AGENT_VERSION
from tests.factories import CorpusRecordFactory
from tests.utils import (
    FakeEnvDataClient,
    FakeIMAPClient,
    FakeLLM,
    FakeMarketDataClient,
    FakeSMTPClient,
)


def _make_reply_email(coordinate: str, body: str) -> bytes:
    msg = email.mime.text.MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Re: Apollo Research Session — Target ID {coordinate}"
    msg["From"] = "asset@example.com"
    msg["To"] = "apollo@example.com"
    return msg.as_bytes()


def _seed_dispatched(
    session,  # type: ignore[no-untyped-def]
    coordinate: str,
    target_statement: str = "Gold rises > 9% by June 10",
) -> CorpusRecord:
    record = CorpusRecordFactory(
        status=TargetStatus.DISPATCHED.value,
        available_after=datetime.now(UTC) - timedelta(seconds=1),
        double_blind_coordinate=coordinate,
        target_statement=target_statement,
        queued_at=datetime.now(UTC) - timedelta(minutes=5),
        dispatched_at=datetime.now(UTC) - timedelta(minutes=4),
        dispatch_agent_version="0.1.0",
    )
    return record  # type: ignore[return-value]


class TestWorkerQuarantineIntegration:
    def test_failed_extraction_creates_quarantine_record(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Full exception path: tick() → extraction failure → quarantine_record created."""
        from apollo.services.worker import tick

        coordinate = "8A2F/9B4C"
        record = _seed_dispatched(db_session, coordinate)
        raw_bytes = _make_reply_email(coordinate, "VAD: not a number, cannot parse")

        # Two "{}" responses → ExtractionSchemaError after one retry (param_value missing)
        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient()
        imap = FakeIMAPClient([raw_bytes])

        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        # Quarantine record must exist
        qr = (
            db_session.query(QuarantineRecord)
            .filter_by(corpus_record_id=record.id)
            .first()
        )
        assert qr is not None
        assert qr.quarantine_reason == "extraction_schema_error"
        assert qr.quarantined_at is not None
        assert qr.quarantined_at.tzinfo is not None
        assert qr.raw_email_bytes is not None
        assert len(qr.raw_email_bytes) > 0

    def test_failed_extraction_clears_corpus_raw_email_bytes(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """After quarantine, corpus_record.raw_email_bytes = None for clarification re-intake."""
        from apollo.services.worker import tick

        coordinate = "8A2F/9B4C"
        record = _seed_dispatched(db_session, coordinate)
        raw_bytes = _make_reply_email(coordinate, "unparseable content")

        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient()
        imap = FakeIMAPClient([raw_bytes])

        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        fresh_record = db_session.get(CorpusRecord, record.id)
        assert fresh_record is not None
        assert fresh_record.raw_email_bytes is None

    def test_corpus_record_stays_dispatched_after_quarantine(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """corpus_record status must remain DISPATCHED (not changed) after quarantine."""
        from apollo.services.worker import tick

        coordinate = "8A2F/9B4C"
        record = _seed_dispatched(db_session, coordinate)
        raw_bytes = _make_reply_email(coordinate, "unparseable content")

        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient()
        imap = FakeIMAPClient([raw_bytes])

        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        fresh_record = db_session.get(CorpusRecord, record.id)
        assert fresh_record is not None
        assert fresh_record.status == TargetStatus.DISPATCHED.value

    def test_clarification_email_sent_with_coordinate(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Clarification email must be sent and must contain the coordinate."""
        from apollo.services.worker import tick

        coordinate = "8A2F/9B4C"
        _seed_dispatched(db_session, coordinate)
        raw_bytes = _make_reply_email(coordinate, "unparseable content")

        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient()
        imap = FakeIMAPClient([raw_bytes])

        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )

        assert len(smtp.sent) == 1
        assert coordinate in smtp.sent[0]["subject"]

    def test_clarification_email_excludes_target_statement(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Double-blind: clarification email body must NOT expose target_statement."""
        from apollo.services.worker import tick

        coordinate = "8A2F/9B4C"
        secret_target = "Gold price will increase by more than 9 percent tomorrow"
        _seed_dispatched(db_session, coordinate, target_statement=secret_target)
        raw_bytes = _make_reply_email(coordinate, "unparseable content")

        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient()
        imap = FakeIMAPClient([raw_bytes])

        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )

        assert len(smtp.sent) == 1
        body = smtp.sent[0]["body"]
        assert secret_target not in body
        assert "Gold price" not in body

    def test_clarification_sent_at_set_on_smtp_success(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """quarantine_record.clarification_sent_at must be set when SMTP succeeds."""
        from apollo.services.worker import tick

        coordinate = "8A2F/9B4C"
        record = _seed_dispatched(db_session, coordinate)
        raw_bytes = _make_reply_email(coordinate, "unparseable content")

        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient()
        imap = FakeIMAPClient([raw_bytes])

        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        qr = (
            db_session.query(QuarantineRecord)
            .filter_by(corpus_record_id=record.id)
            .first()
        )
        assert qr is not None
        assert qr.clarification_sent_at is not None
        assert qr.clarification_sent_at.tzinfo is not None
        assert qr.clarification_agent_version == AGENT_VERSION

    def test_smtp_failure_is_fail_operational(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """SMTP failure must not crash tick; quarantine_record exists, clarification_sent_at = None."""
        from apollo.services.worker import tick

        coordinate = "FAIL/SMTP"
        record = _seed_dispatched(db_session, coordinate)
        raw_bytes = _make_reply_email(coordinate, "unparseable content")

        llm = FakeLLM(responses=["{}", "{}"])
        smtp = FakeSMTPClient(raise_on_nth=1)  # First send raises OSError
        imap = FakeIMAPClient([raw_bytes])

        # Must not raise
        tick(
            imap_client=imap,
            llm_client=llm,
            smtp_client=smtp,
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        qr = (
            db_session.query(QuarantineRecord)
            .filter_by(corpus_record_id=record.id)
            .first()
        )
        assert qr is not None, "quarantine_record must exist even when SMTP fails"
        assert qr.clarification_sent_at is None
        assert qr.raw_email_bytes is not None

        # raw_email_bytes still cleared on corpus_record
        fresh_record = db_session.get(CorpusRecord, record.id)
        assert fresh_record is not None
        assert fresh_record.raw_email_bytes is None


class TestWorkerEmptyRawBytesDeadLetter:
    """AC5 — a `dispatched` record stuck with `raw_email_bytes == b""` (non-None but
    falsy, so the IMAP poller's `is not None` check permanently skips it) must be
    dead-lettered through QuarantineService rather than retried forever."""

    def test_stuck_empty_raw_bytes_record_is_dead_lettered(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        coordinate = "DEAD/0001"
        record = _seed_dispatched(db_session, coordinate)
        record.raw_email_bytes = b""
        db_session.add(record)
        db_session.commit()

        from apollo.services.worker import tick

        # No new IMAP replies — the dead-letter step must run independently of
        # the email-matching path.
        tick(
            imap_client=FakeIMAPClient([]),
            llm_client=FakeLLM(responses=["{}", "{}"]),
            smtp_client=FakeSMTPClient(),
            env_client=FakeEnvDataClient(),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        qr = (
            db_session.query(QuarantineRecord)
            .filter_by(corpus_record_id=record.id)
            .first()
        )
        assert qr is not None, (
            "a stuck b'' raw_email_bytes record must be dead-lettered to quarantine_record"
        )
        assert qr.raw_email_bytes == b""

        fresh_record = db_session.get(CorpusRecord, record.id)
        assert fresh_record is not None
        assert fresh_record.raw_email_bytes is None
        assert fresh_record.status == TargetStatus.DISPATCHED.value
