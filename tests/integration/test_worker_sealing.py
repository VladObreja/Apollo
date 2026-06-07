"""Integration tests for worker Phase 3 — sealing path (Story 2.2).

Tests the full dispatched → sealed lifecycle using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - FakeIMAPClient with synthetic raw MIME emails
  - FakeLLM with canned JSON responses

Verifies:
  - Successful extraction → record sealed with raw_hash, extraction_payload, sealed_at
  - Failed extraction → record stays dispatched (no sealing)
"""

from __future__ import annotations

import email.mime.text
import hashlib
import json
from datetime import UTC, datetime, timedelta

from apollo.db.models import CorpusRecord
from apollo.domain.types import TargetStatus
from tests.utils import FakeIMAPClient, FakeLLM, FakeMarketDataClient, FakeSMTPClient


def _make_reply_email(coordinate: str, body: str) -> bytes:
    msg = email.mime.text.MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Re: Apollo Research Session — Target ID {coordinate}"
    msg["From"] = "asset@example.com"
    msg["To"] = "apollo@example.com"
    return msg.as_bytes()


def _valid_extraction_json(param_value: float = 75.0) -> str:
    return json.dumps({"param_value": param_value})


def _seed_dispatched(
    session,  # type: ignore[no-untyped-def]
    coordinate: str,
) -> CorpusRecord:
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


class TestWorkerSealingIntegration:
    def test_tick_seals_record_on_successful_extraction(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Full happy path: tick() → extraction → sealing → status = sealed."""
        coord = "8A2F/9B4C"
        _seed_dispatched(db_session, coordinate=coord)

        raw = _make_reply_email(
            coord, "VAD: 75\nTime of measurement (UTC): 2026-06-05T10:00:00Z"
        )
        imap_client = FakeIMAPClient([raw])
        llm_client = FakeLLM([_valid_extraction_json(75.0)])
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=imap_client,
            llm_client=llm_client,
            market_client=FakeMarketDataClient(),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.status == TargetStatus.SEALED.value
        assert record.raw_hash == hashlib.sha256(raw).hexdigest()
        assert isinstance(record.extraction_payload, dict)
        assert record.sealed_at is not None
        assert record.sealed_at.tzinfo is not None
        assert record.seal_agent_version is not None

    def test_tick_failed_extraction_leaves_record_dispatched(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Failure path: LLM always fails → status stays dispatched, raw_hash is None."""
        coord = "FAIL/9999"
        _seed_dispatched(db_session, coordinate=coord)

        raw = _make_reply_email(coord, "VAD: 75")
        imap_client = FakeIMAPClient([raw])
        llm_client = FakeLLM(["not json", "also not json"])
        fake_smtp = FakeSMTPClient()

        from apollo.services.worker import tick

        tick(
            smtp_client=fake_smtp,
            imap_client=imap_client,
            llm_client=llm_client,
            market_client=FakeMarketDataClient(),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.status == TargetStatus.DISPATCHED.value
        assert record.raw_hash is None
