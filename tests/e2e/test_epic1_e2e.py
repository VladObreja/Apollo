"""E2E tests for Epic 1: Target Configuration, Coordinate Generation, and Email Dispatch.

Verifies the full pipeline end-to-end using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - Real Mailpit SMTP at 127.0.0.1:1025 (docker-compose service)
  - Mailpit HTTP API at 127.0.0.1:8025 to assert delivered email content

Prerequisites: ``docker-compose up mailpit`` must be running before these tests.
Tests are automatically skipped if Mailpit is unreachable.
"""

from __future__ import annotations

import json
import re
import urllib.error
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
from tests.utils import FakeIMAPClient

# ---------------------------------------------------------------------------
# Mailpit API helpers
# ---------------------------------------------------------------------------

_MAILPIT_API = "http://127.0.0.1:8025/api/v1"


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


def _message_body(message_id: str) -> str:
    with urllib.request.urlopen(
        f"{_MAILPIT_API}/message/{message_id}", timeout=5
    ) as resp:
        data: dict = json.loads(resp.read())
    return str(data.get("Text", ""))


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
    """Real SMTPClientImpl explicitly wired to Mailpit (overrides any .env settings)."""
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
    age_in_hours: int | None = None,
    is_control: bool = False,
) -> TargetConfiguration:
    return TargetConfiguration(
        target=TargetStatement(statement=statement),
        parameter=TargetParameter(name=parameter),
        target_metadata=TargetMetadata(
            is_control_target=is_control,
            age_in_hours=age_in_hours,
        ),
        admin_state=AdminStateSnapshot(
            awareness_tier="tier1",
            psychological_context="calm and focused",
        ),
    )


# ---------------------------------------------------------------------------
# Story 1.1 — Target Configuration
# ---------------------------------------------------------------------------


class TestEpic1TargetConfiguration:
    def test_configure_target_persists_pending_record(
        self, db_session, patched_db_url
    ) -> None:
        """TargetService.create_target_configuration persists a 'pending' corpus_record."""
        config = _make_config()
        TargetService.create_target_configuration(config)

        db_session.expire_all()
        record = db_session.query(CorpusRecord).filter_by(id=config.id).first()
        assert record is not None
        assert record.status == TargetStatus.PENDING.value
        assert record.target_statement == config.target.statement
        assert record.parameter_name == config.parameter.name
        assert record.admin_awareness_tier == config.admin_state.awareness_tier
        assert (
            record.admin_psychological_context
            == config.admin_state.psychological_context
        )
        assert record.double_blind_coordinate is None
        assert record.dispatched_at is None

    def test_configure_target_captures_admin_state(
        self, db_session, patched_db_url
    ) -> None:
        """Admin state snapshot (tier + context) is stored immutably on the record."""
        config = _make_config(
            statement="Oil futures drop > 10% next month",
            parameter="rvd",
        )
        TargetService.create_target_configuration(config)

        db_session.expire_all()
        record = db_session.query(CorpusRecord).filter_by(id=config.id).first()
        assert record is not None
        assert record.admin_awareness_tier == "tier1"
        assert record.admin_psychological_context == "calm and focused"

    def test_configure_target_age_in_gate_sets_available_after(
        self, db_session, patched_db_url
    ) -> None:
        """age_in_hours=24 sets available_after to approximately now + 24h."""
        before = datetime.now(UTC)
        config = _make_config(age_in_hours=24)
        TargetService.create_target_configuration(config)

        db_session.expire_all()
        record = db_session.query(CorpusRecord).filter_by(id=config.id).first()
        assert record is not None
        assert record.available_after > before
        assert record.available_after > datetime.now(UTC)

    def test_configure_control_target_flag(self, db_session, patched_db_url) -> None:
        """is_control_target=True is stored correctly on the record."""
        config = _make_config(is_control=True)
        TargetService.create_target_configuration(config)

        db_session.expire_all()
        record = db_session.query(CorpusRecord).filter_by(id=config.id).first()
        assert record is not None
        assert record.is_control_target is True


# ---------------------------------------------------------------------------
# Story 1.2 — Coordinate Generation
# ---------------------------------------------------------------------------

_COORD_RE = re.compile(r"^[0-9A-F]{4}/[0-9A-F]{4}$")


class TestEpic1CoordinateGeneration:
    def test_tick_assigns_coordinate_after_configure(
        self, db_session, patched_db_url
    ) -> None:
        """tick() assigns a well-formed coordinate and advances status to 'queued'."""
        from tests.utils import FakeSMTPClient

        config = _make_config()
        TargetService.create_target_configuration(config)

        tick(smtp_client=FakeSMTPClient(), imap_client=FakeIMAPClient([]))

        db_session.expire_all()
        record = db_session.query(CorpusRecord).filter_by(id=config.id).first()
        assert record is not None
        assert record.status == TargetStatus.DISPATCHED.value
        assert record.double_blind_coordinate is not None
        assert _COORD_RE.match(record.double_blind_coordinate), (
            f"Malformed coordinate: {record.double_blind_coordinate!r}"
        )

    def test_coordinates_are_unique_across_targets(
        self, db_session, patched_db_url
    ) -> None:
        """Each target gets a distinct double-blind coordinate."""
        from tests.utils import FakeSMTPClient

        for i in range(3):
            TargetService.create_target_configuration(
                _make_config(statement=f"Unique target {i}")
            )

        tick(smtp_client=FakeSMTPClient(), imap_client=FakeIMAPClient([]))

        db_session.expire_all()
        records = db_session.query(CorpusRecord).all()
        coords = [
            r.double_blind_coordinate for r in records if r.double_blind_coordinate
        ]
        assert len(coords) == 3
        assert len(set(coords)) == 3, f"Duplicate coordinates detected: {coords}"

    def test_target_not_yet_available_skipped_by_tick(
        self, db_session, patched_db_url
    ) -> None:
        """A target with age_in_hours=24 must not be claimed or coordinated in the current tick."""
        from tests.utils import FakeSMTPClient

        config = _make_config(age_in_hours=24)
        TargetService.create_target_configuration(config)

        tick(smtp_client=FakeSMTPClient(), imap_client=FakeIMAPClient([]))

        db_session.expire_all()
        record = db_session.query(CorpusRecord).filter_by(id=config.id).first()
        assert record is not None
        assert record.status == TargetStatus.PENDING.value
        assert record.double_blind_coordinate is None


# ---------------------------------------------------------------------------
# Story 1.3 — Email Dispatch (Mailpit integration)
# ---------------------------------------------------------------------------


class TestEpic1EmailDispatch:
    def test_full_pipeline_delivers_email_to_mailpit(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """configure → tick → exactly one email delivered to Mailpit inbox."""
        TargetService.create_target_configuration(_make_config())

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 1, f"Expected 1 email in Mailpit, got {len(messages)}"

    def test_email_recipient_is_asset_address(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Dispatched email is addressed to the configured asset email address."""
        from apollo.config import settings

        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 1
        recipients = [t["Address"] for t in messages[0].get("To", [])]
        assert settings.asset_email_address in recipients, (
            f"Expected {settings.asset_email_address!r} in recipients {recipients}"
        )

    def test_email_subject_contains_coordinate(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Email subject must contain the exact double-blind coordinate."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .first()
        )
        assert record is not None
        coord = record.double_blind_coordinate
        assert coord is not None

        messages = _list_messages()
        assert len(messages) == 1
        assert coord in messages[0]["Subject"], (
            f"Coordinate {coord!r} missing from subject: {messages[0]['Subject']!r}"
        )

    def test_email_body_coordinate_matches_db_record(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Coordinate in the email body exactly matches the DB double_blind_coordinate."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .first()
        )
        assert record is not None
        coord = record.double_blind_coordinate
        assert coord is not None

        messages = _list_messages()
        body = _message_body(messages[0]["ID"])
        assert coord in body, f"Coordinate {coord!r} not found in email body"

    def test_email_body_is_double_blind(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Email body must NOT reveal the target statement (double-blind enforcement)."""
        secret_statement = "CLASSIFIED: Uranium futures spike 40% before November"
        TargetService.create_target_configuration(
            _make_config(statement=secret_statement)
        )
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 1
        body = _message_body(messages[0]["ID"])
        assert "CLASSIFIED" not in body, "Target identity leaked in email body"
        assert "Uranium" not in body, "Target identity leaked in email body"
        assert "spike" not in body.lower(), "Target identity leaked in email body"

    def test_email_body_contains_all_measurement_fields(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Email body must contain all six measurement prompt fields from extraction.jinja."""
        TargetService.create_target_configuration(_make_config())
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 1
        body = _message_body(messages[0]["ID"])

        for field in [
            "PARAM",
            "Time of measurement",
            "Location",
            "Sleep quality",
            "Psychological state",
            "Social Field",
        ]:
            assert field in body, f"Measurement field {field!r} missing from email body"

    def test_email_body_contains_parameter_name(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Email body must include the parameter name (e.g. 'rvd')."""
        TargetService.create_target_configuration(_make_config(parameter="rvd"))
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        body = _message_body(messages[0]["ID"])
        assert "rvd" in body, "Parameter name 'rvd' not found in email body"

    def test_db_record_has_dispatch_provenance(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """After dispatch: record is 'dispatched' with non-null dispatched_at (UTC) and agent version."""
        TargetService.create_target_configuration(_make_config())
        before = datetime.now(UTC)
        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))
        after = datetime.now(UTC)

        db_session.expire_all()
        record = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .first()
        )
        assert record is not None
        assert record.dispatched_at is not None, "dispatched_at must be set"
        assert record.dispatched_at.tzinfo is not None, (
            "dispatched_at must be UTC-aware"
        )
        assert before <= record.dispatched_at <= after
        assert record.dispatch_agent_version is not None
        assert len(record.dispatch_agent_version) > 0


# ---------------------------------------------------------------------------
# Epic 1 End-to-End scenarios
# ---------------------------------------------------------------------------


class TestEpic1EndToEnd:
    def test_multiple_targets_each_deliver_unique_email(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Three configured targets → three emails in Mailpit, each with a unique coordinate."""
        for i in range(3):
            TargetService.create_target_configuration(
                _make_config(
                    statement=f"E2E multi-target statement {i}", parameter="vad"
                )
            )

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 3, f"Expected 3 emails, got {len(messages)}"

        subjects = [m["Subject"] for m in messages]
        coords_in_subjects = [
            re.search(r"[0-9A-F]{4}/[0-9A-F]{4}", s) for s in subjects
        ]
        extracted = [m.group(0) for m in coords_in_subjects if m]
        assert len(extracted) == 3, "Each email subject must contain a coordinate"
        assert len(set(extracted)) == 3, (
            f"Duplicate coordinates in email subjects: {extracted}"
        )

    def test_age_in_gate_prevents_early_dispatch(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """A target with age_in_hours=24 must produce zero emails during the current tick."""
        TargetService.create_target_configuration(_make_config(age_in_hours=24))

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 0, (
            f"Expected 0 emails (target in Age-In window), got {len(messages)}"
        )

    def test_second_tick_does_not_redispatch(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Running tick twice must not re-send an already-dispatched email."""
        TargetService.create_target_configuration(_make_config())

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))
        _clear_mailpit()

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 0, (
            f"Second tick re-dispatched an already-dispatched record: {len(messages)} emails"
        )

    def test_daily_cap_enforced_at_five(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Seven pending targets → at most 5 emails dispatched (daily cap enforced)."""
        for i in range(7):
            TargetService.create_target_configuration(
                _make_config(statement=f"Daily cap test target {i}")
            )

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) <= 5, (
            f"Daily cap of 5 exceeded: {len(messages)} emails dispatched"
        )

        db_session.expire_all()
        dispatched_count = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.DISPATCHED.value)
            .count()
        )
        pending_count = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.PENDING.value)
            .count()
        )
        assert dispatched_count <= 5
        assert dispatched_count + pending_count == 7

    def test_mixed_available_and_gated_targets(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Mix of immediately available and age-gated targets: only available ones are dispatched."""
        for i in range(2):
            TargetService.create_target_configuration(
                _make_config(statement=f"Available target {i}")
            )
        for i in range(3):
            TargetService.create_target_configuration(
                _make_config(statement=f"Gated target {i}", age_in_hours=48)
            )

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 2, (
            f"Expected 2 emails (3 gated targets skipped), got {len(messages)}"
        )

        db_session.expire_all()
        pending_count = (
            db_session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.PENDING.value)
            .count()
        )
        assert pending_count == 3, "Gated targets must remain in pending status"

    def test_parameters_preserved_in_dispatched_emails(
        self, db_session, patched_db_url, mailpit_smtp
    ) -> None:
        """Each dispatched email body must include the correct parameter for that target."""
        configs = [
            _make_config(statement="VAD target", parameter="vad"),
            _make_config(statement="RVD target", parameter="rvd"),
        ]
        for cfg in configs:
            TargetService.create_target_configuration(cfg)

        tick(smtp_client=mailpit_smtp, imap_client=FakeIMAPClient([]))

        messages = _list_messages()
        assert len(messages) == 2

        all_bodies = [_message_body(m["ID"]) for m in messages]
        combined = "\n".join(all_bodies)
        assert "vad" in combined, "Parameter 'vad' missing from dispatched emails"
        assert "rvd" in combined, "Parameter 'rvd' missing from dispatched emails"
