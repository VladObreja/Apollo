"""E2E tests for Epic 2: Inbound Email Ingestion & Parsing.

Cross-epic pipeline verification:
  1. Configure target  (Story 1.1)
  2. tick() Phase 1+2: coordinate generated + email dispatched via real Mailpit SMTP
     (Stories 1.2–1.3) — proves a real email with a real coordinate lands in Mailpit
  3. Extract the coordinate from the Mailpit HTTP API — no hardcoding
  4. Construct a synthetic Asset reply email keyed on that real coordinate
  5. tick() Phase 3: FakeIMAPClient delivers the reply → raw bytes stored → FakeLLM
     extracts  (Story 2.1)

This file differs from tests/integration/test_worker_email_phase.py in one critical
way: integration tests seed a pre-built "dispatched" record with a hardcoded
coordinate and test Phase 3 in isolation.  These E2E tests run the full pipeline
from ``TargetService.create_target_configuration()`` through SMTP dispatch (real
Mailpit) and verify that the coordinate extracted from the actual dispatched email
correctly drives Phase 3 matching and raw-byte storage.

Note — full IMAP E2E: Mailpit exposes IMAP on port 1143 by default.  Exposing that
port in docker-compose.yml and using ``IMAPClientImpl`` pointed at Mailpit would
allow fully live Phase 3 testing without FakeIMAPClient.  That is left as a
follow-up once Story 2.2 (sealing) ships and an end-to-end IMAP inbox is needed.

Prerequisites: ``docker-compose up mailpit`` must be running before these tests.
Tests are automatically skipped if Mailpit is unreachable.
"""

from __future__ import annotations

import email.mime.text
import json
import re
import urllib.request
from datetime import UTC, datetime

import pytest

from apollo.config import Settings
from apollo.db.models import CorpusRecord
from apollo.domain.models import (
    AdminStateSnapshot,
    TargetConfiguration,
    TargetMetadata,
    TargetParameter,
    TargetStatement,
)
from apollo.domain.types import TargetStatus
from apollo.services.dispatch import SMTPClientImpl
from apollo.services.target import TargetService
from apollo.services.worker import tick
from tests.utils import FakeIMAPClient, FakeLLM, FakeSMTPClient

# ---------------------------------------------------------------------------
# Mailpit API helpers
# ---------------------------------------------------------------------------

_MAILPIT_API = "http://127.0.0.1:8025/api/v1"
_COORD_RE = re.compile(r"[0-9A-F]{4}/[0-9A-F]{4}")


def _mailpit_available() -> bool:
    try:
        urllib.request.urlopen(f"{_MAILPIT_API}/messages", timeout=2)
        return True
    except Exception:
        return False


def _clear_mailpit() -> None:
    req = urllib.request.Request(f"{_MAILPIT_API}/messages", method="DELETE")
    urllib.request.urlopen(req, timeout=5)


def _list_messages() -> list[dict]:
    with urllib.request.urlopen(f"{_MAILPIT_API}/messages", timeout=5) as resp:
        data: dict = json.loads(resp.read())
    return data.get("messages") or []


def _extract_coordinate_from_subject(subject: str) -> str | None:
    m = _COORD_RE.search(subject)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Module-level skip guard
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not _mailpit_available(),
    reason="Mailpit not running at 127.0.0.1:8025 — run `docker-compose up mailpit` first",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_mailpit_inbox() -> None:
    """Delete all Mailpit messages before each test for isolation."""
    _clear_mailpit()


@pytest.fixture()
def mailpit_smtp() -> SMTPClientImpl:
    """Real SMTPClientImpl wired to Mailpit (overrides any .env settings)."""
    s = Settings(
        smtp_host="127.0.0.1",
        smtp_port=1025,
        smtp_use_tls=False,
        smtp_username="",
        smtp_password="",  # type: ignore[arg-type]
    )
    return SMTPClientImpl(s)


def _make_config(
    statement: str = "Gold price increases more than 5% this week",
    parameter: str = "vad",
) -> TargetConfiguration:
    return TargetConfiguration(
        target=TargetStatement(statement=statement),
        parameter=TargetParameter(name=parameter),
        target_metadata=TargetMetadata(is_control_target=False),
        admin_state=AdminStateSnapshot(
            awareness_tier="tier1",
            psychological_context="calm and focused",
        ),
    )


def _make_reply_email(coordinate: str, body: str) -> bytes:
    """Build a synthetic plain-text Asset reply with the given coordinate in subject."""
    msg = email.mime.text.MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Re: Apollo Research Session — Target ID {coordinate}"
    msg["From"] = "asset@proton.me"
    msg["To"] = "apollo@proton.me"
    return msg.as_bytes()


def _valid_llm_json(param_value: float = 75.0) -> str:
    return json.dumps({"param_value": param_value})


# ---------------------------------------------------------------------------
# Story 2.1 — Ingestion pipeline (cross-epic)
# ---------------------------------------------------------------------------


class TestEpic2InboundIngestion:
    def test_full_pipeline_stores_raw_bytes_on_matched_record(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Full pipeline: configure → dispatch (real Mailpit) → ingest reply → raw_email_bytes stored."""
        TargetService.create_target_configuration(_make_config())

        # Phase 1+2: coordinate generated, email dispatched to real Mailpit
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 1, (
            f"Expected 1 dispatch email in Mailpit, got {len(messages)}"
        )
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None, (
            f"No coordinate found in subject: {messages[0]['Subject']!r}"
        )

        # Construct a realistic Asset reply keyed on the real dispatched coordinate
        reply = _make_reply_email(
            coord,
            "PARAM (vad): 72\nTime of measurement (UTC): 2026-06-02T08:00:00Z",
        )

        # Phase 3: ingest the reply
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(72.0)]),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.raw_email_bytes is not None, (
            "raw_email_bytes must be stored after ingestion"
        )
        assert len(record.raw_email_bytes) > 0

    def test_full_pipeline_received_at_is_utc_aware(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """received_at is non-null and UTC-aware after the full dispatch → ingest cycle."""
        TargetService.create_target_configuration(_make_config(parameter="rvd"))
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None

        before = datetime.now(UTC)
        reply = _make_reply_email(coord, "PARAM (rvd): 55")
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(55.0)]),
        )
        after = datetime.now(UTC)

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.received_at is not None, "received_at must be set after ingestion"
        assert record.received_at.tzinfo is not None, "received_at must be UTC-aware"
        assert before <= record.received_at <= after

    def test_full_pipeline_status_stays_dispatched(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Status stays 'dispatched' after Phase 3 — sealing transition belongs to Story 2.2."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None

        reply = _make_reply_email(coord, "PARAM (vad): 88")
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(88.0)]),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.status == TargetStatus.DISPATCHED.value, (
            f"Expected 'dispatched', got '{record.status}' — sealing is Story 2.2"
        )

    def test_raw_bytes_stored_even_when_llm_extraction_fails(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Fail-operational: raw_email_bytes are durable even when LLM fails both attempts."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None

        reply = _make_reply_email(coord, "PARAM (vad): 60")
        # Always-failing LLM — ExtractionSchemaError is caught inside tick(), must not propagate
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM(["not json", "also not json"]),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.raw_email_bytes is not None, (
            "raw_email_bytes must survive LLM extraction failure (stored before LLM call)"
        )
        assert record.status == TargetStatus.DISPATCHED.value

    def test_second_tick_phase3_does_not_reingest_already_stored_reply(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Running Phase 3 twice with the same reply must not duplicate or corrupt raw bytes."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None

        reply = _make_reply_email(coord, "PARAM (vad): 65")

        # First Phase 3 pass — ingests the reply
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(65.0)]),
        )

        db_session.expire_all()
        record_after_first = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record_after_first is not None
        # Second Phase 3 pass — FakeIMAPClient returns the same email again
        # (simulating idempotency: in production the SEEN flag prevents re-fetch)
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(65.0)]),
        )

        db_session.expire_all()
        record_after_second = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record_after_second is not None
        # Record must still be in dispatched state — not corrupted
        assert record_after_second.status == TargetStatus.DISPATCHED.value
        # raw_email_bytes must still be present
        assert record_after_second.raw_email_bytes is not None


# ---------------------------------------------------------------------------
# Story 2.1 — Double-blind integrity under real dispatch conditions
# ---------------------------------------------------------------------------


class TestEpic2DoubleBlindIntegrity:
    def test_dispatch_email_does_not_leak_target_statement(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """The Mailpit-delivered dispatch email body must not reveal the target statement."""
        secret = "CLASSIFIED: Palladium supply crashes 30% before Q4"
        TargetService.create_target_configuration(_make_config(statement=secret))
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 1

        # Retrieve plain-text body from Mailpit
        with urllib.request.urlopen(
            f"{_MAILPIT_API}/message/{messages[0]['ID']}", timeout=5
        ) as resp:
            body = str(json.loads(resp.read()).get("Text", ""))

        assert "CLASSIFIED" not in body, "Target identity leaked in dispatch email body"
        assert "Palladium" not in body, "Target identity leaked in dispatch email body"
        assert "crashes" not in body.lower(), (
            "Target identity leaked in dispatch email body"
        )

    def test_reply_body_stored_verbatim_in_raw_bytes(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """raw_email_bytes must contain the Asset's original reply content verbatim."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None

        reply_body = "PARAM (vad): 65\nSocial Field: Isolated\nLocation: Home office"
        reply = _make_reply_email(coord, reply_body)

        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(65.0)]),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.raw_email_bytes is not None
        # Parse body via the same logic the poller uses — MIME may use base64 transfer encoding
        from apollo.services.email_poller import EmailPollerService

        body = EmailPollerService.parse_email_body(record.raw_email_bytes)
        assert "Social Field: Isolated" in body, (
            "raw_email_bytes must contain the Asset's reply content verbatim"
        )
        assert "Location: Home office" in body

    def test_coordinate_in_reply_subject_matches_db_coordinate(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """The coordinate used to build the Asset reply must match the DB record exactly."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord_from_mailpit = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord_from_mailpit is not None

        reply = _make_reply_email(coord_from_mailpit, "PARAM (vad): 70")
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([reply]),
            llm_client=FakeLLM([_valid_llm_json(70.0)]),
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord_from_mailpit)
            .first()
        )
        assert record is not None
        assert record.double_blind_coordinate == coord_from_mailpit, (
            "DB coordinate must exactly match the coordinate extracted from the dispatched email"
        )


# ---------------------------------------------------------------------------
# Story 2.1 — Multi-session pipeline
# ---------------------------------------------------------------------------


class TestEpic2MultiSessionPipeline:
    def test_two_targets_each_ingested_to_correct_record(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Two distinct targets dispatched → each reply matched and ingested to the correct record."""
        cfg1 = _make_config(
            statement="Target A: Gold price drops > 5%", parameter="vad"
        )
        cfg2 = _make_config(
            statement="Target B: Silver price spikes > 10%", parameter="rvd"
        )
        TargetService.create_target_configuration(cfg1)
        TargetService.create_target_configuration(cfg2)

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 2, f"Expected 2 dispatch emails, got {len(messages)}"

        coords = [_extract_coordinate_from_subject(m["Subject"]) for m in messages]
        assert all(c is not None for c in coords), (
            "Both subjects must contain a coordinate"
        )
        assert len(set(coords)) == 2, f"Coordinates must be unique; got: {coords}"

        # Build one reply per dispatched coordinate
        replies = [
            _make_reply_email(c, f"PARAM: {70 + i}")  # type: ignore[arg-type]
            for i, c in enumerate(coords)
        ]
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient(replies),
            llm_client=FakeLLM([_valid_llm_json(70.0), _valid_llm_json(71.0)]),
        )

        db_session.expire_all()
        for coord in coords:
            record = (
                db_session.query(CorpusRecord)
                .filter(CorpusRecord.double_blind_coordinate == coord)
                .first()
            )
            assert record is not None
            assert record.raw_email_bytes is not None, (
                f"raw_email_bytes not stored for coordinate {coord}"
            )
            assert record.received_at is not None, (
                f"received_at not set for coordinate {coord}"
            )

    def test_reply_with_wrong_coordinate_does_not_corrupt_dispatched_record(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """A reply with an unrecognised coordinate must be silently ignored; no DB write occurs."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        coord = _extract_coordinate_from_subject(messages[0]["Subject"])
        assert coord is not None

        # Reply with a coordinate that matches no dispatched record
        spurious_reply = _make_reply_email("ZZZZ/9999", "PARAM (vad): 50")
        llm = FakeLLM([])  # Must not be called

        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient([spurious_reply]),
            llm_client=llm,
        )

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.double_blind_coordinate == coord)
            .first()
        )
        assert record is not None
        assert record.raw_email_bytes is None, (
            "Spurious reply must not write raw_email_bytes to an unrelated dispatched record"
        )
        assert record.received_at is None
        assert llm._call_count == 0, (
            "LLM must not be called for an unmatched coordinate"
        )

    def test_extraction_failures_are_caught_tick_does_not_raise(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Fail-operational: ExtractionSchemaError for all records must not propagate from tick()."""
        cfg1 = _make_config(statement="Target A: always-failing LLM", parameter="vad")
        cfg2 = _make_config(
            statement="Target B: also always-failing LLM", parameter="rvd"
        )
        TargetService.create_target_configuration(cfg1)
        TargetService.create_target_configuration(cfg2)

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 2
        coords = [_extract_coordinate_from_subject(m["Subject"]) for m in messages]
        assert all(c is not None for c in coords)

        replies = [_make_reply_email(c, "PARAM: 60") for c in coords]  # type: ignore[arg-type]
        # 2 records × 2 LLM attempts each = 4 invalid responses
        tick(
            smtp_client=FakeSMTPClient(),
            imap_client=FakeIMAPClient(replies),
            llm_client=FakeLLM(["bad", "bad", "bad", "bad"]),
        )

        db_session.expire_all()
        for coord in coords:
            record = (
                db_session.query(CorpusRecord)
                .filter(CorpusRecord.double_blind_coordinate == coord)
                .first()
            )
            assert record is not None
            # raw bytes stored before the LLM call — must survive extraction failure
            assert record.raw_email_bytes is not None, (
                f"raw_email_bytes must be durable even after LLM failure for {coord}"
            )
            assert record.status == TargetStatus.DISPATCHED.value
