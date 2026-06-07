"""Unit tests for QuarantineService (Story 2.3).

Tests the quarantine + clarification flow in isolation:
  - No DB (mock sessionmaker)
  - No real SMTP (FakeSMTPClient)
  - No real Jinja2 rendering issues (uses real templates dir)

All tests operate on in-memory CorpusRecord objects — no Postgres required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from jinja2 import Environment, FileSystemLoader

from apollo.db.models import CorpusRecord, QuarantineRecord
from apollo.domain.exceptions import ExtractionSchemaError, QuarantineError
from apollo.domain.types import TargetStatus
from apollo.services.quarantine import QuarantineService
from tests.utils import FakeSMTPClient


def _make_env() -> Environment:
    templates_dir = Path(__file__).parent.parent.parent / "src" / "apollo" / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)


def _make_dispatched_record(
    raw_bytes: bytes | None = b"raw email bytes",
) -> CorpusRecord:
    record = CorpusRecord()
    record.id = uuid4()  # type: ignore[assignment]
    record.target_statement = "Gold rises > 9% by June 10"
    record.parameter_name = "VAD"
    record.is_control_target = False
    record.admin_awareness_tier = "TIER_1"
    record.admin_psychological_context = None
    record.created_at = datetime.now(UTC)
    record.status = TargetStatus.DISPATCHED.value
    record.available_after = datetime.now(UTC)
    record.double_blind_coordinate = "8A2F/9B4C"
    record.raw_email_bytes = raw_bytes
    return record


def _make_mock_session_factory(
    fresh_record: CorpusRecord | None, fresh_qr: QuarantineRecord | None = None
) -> MagicMock:
    """Build a mock sessionmaker whose .begin() context manager yields a mock session."""
    mock_session = MagicMock()

    call_count = [0]

    def side_effect_get(model_class: type, pk: object) -> object:
        call_count[0] += 1
        if model_class is CorpusRecord:
            return fresh_record
        if model_class is QuarantineRecord:
            return fresh_qr
        return None

    mock_session.get.side_effect = side_effect_get

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_session)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    mock_factory = MagicMock()
    mock_factory.begin.return_value = mock_ctx

    return mock_factory


class TestQuarantineServiceCreatesRecord:
    def test_quarantine_creates_quarantine_record(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("param_value missing")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        # Both add() calls happened: one for QuarantineRecord, one for the cleared CorpusRecord
        add_calls = factory.begin.return_value.__enter__.return_value.add.call_args_list
        added_types = [type(c.args[0]) for c in add_calls]
        assert QuarantineRecord in added_types
        assert CorpusRecord in added_types

    def test_quarantine_clears_raw_email_bytes(self) -> None:
        record = _make_dispatched_record(raw_bytes=b"original bytes")
        fresh = _make_dispatched_record(raw_bytes=b"original bytes")
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("bad json")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        assert fresh.raw_email_bytes is None

    def test_quarantine_copies_raw_bytes_to_quarantine_record(self) -> None:
        record = _make_dispatched_record(raw_bytes=b"original bytes")
        fresh = _make_dispatched_record(raw_bytes=b"original bytes")
        fresh.id = record.id

        captured_qr: list[QuarantineRecord] = []
        mock_session = MagicMock()

        def capture_add(obj: object) -> None:
            if isinstance(obj, QuarantineRecord):
                captured_qr.append(obj)

        mock_session.add.side_effect = capture_add
        mock_session.get.side_effect = lambda cls, pk: (
            fresh if cls is CorpusRecord else MagicMock()
        )

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        factory = MagicMock()
        factory.begin.return_value = mock_ctx

        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("bad json")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        assert len(captured_qr) == 1
        assert captured_qr[0].raw_email_bytes == b"original bytes"
        assert captured_qr[0].quarantine_reason == "extraction_schema_error"
        assert captured_qr[0].error_detail == "bad json"

    def test_quarantine_raises_on_missing_record(self) -> None:
        record = _make_dispatched_record()
        factory = _make_mock_session_factory(fresh_record=None)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("bad json")

        with pytest.raises(QuarantineError, match="not found"):
            QuarantineService.quarantine(record, exc, env, smtp, factory)

    def test_quarantine_raises_on_missing_raw_bytes(self) -> None:
        record = _make_dispatched_record(raw_bytes=None)
        fresh = _make_dispatched_record(raw_bytes=None)
        fresh.id = record.id

        factory = _make_mock_session_factory(fresh_record=fresh)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("bad json")

        with pytest.raises(QuarantineError, match="no raw_email_bytes"):
            QuarantineService.quarantine(record, exc, env, smtp, factory)


class TestQuarantineServiceClarificationEmail:
    def test_sends_clarification_email(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("param_value missing")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        assert len(smtp.sent) == 1
        assert smtp.sent[0]["to"] == "asset@test.com"

    def test_clarification_subject_contains_coordinate(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("param_value missing")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        assert "8A2F/9B4C" in smtp.sent[0]["subject"]

    def test_clarification_body_excludes_target_statement(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("param_value missing")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        body = smtp.sent[0]["body"]
        assert record.target_statement not in body
        assert "Gold rises" not in body

    def test_clarification_body_contains_coordinate_and_parameter(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient()
        env = _make_env()
        exc = ExtractionSchemaError("param_value missing")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        body = smtp.sent[0]["body"]
        assert "8A2F/9B4C" in body
        assert "VAD" in body


class TestQuarantineServiceSMTPFailure:
    def test_smtp_failure_is_fail_operational(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        fresh_qr = QuarantineRecord()
        fresh_qr.id = uuid4()  # type: ignore[assignment]

        factory = _make_mock_session_factory(fresh, fresh_qr)
        smtp = FakeSMTPClient(raise_on_nth=1)
        env = _make_env()
        exc = ExtractionSchemaError("bad json")

        # Must NOT raise — fail-operational
        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        # quarantine_record committed (Transaction 1 completed), no SMTP message in sent list
        assert len(smtp.sent) == 0

    def test_smtp_failure_skips_transaction_2(self) -> None:
        record = _make_dispatched_record()
        fresh = _make_dispatched_record()
        fresh.id = record.id

        factory = _make_mock_session_factory(fresh, fresh_qr=None)
        smtp = FakeSMTPClient(raise_on_nth=1)
        env = _make_env()
        exc = ExtractionSchemaError("bad json")

        with patch("apollo.config.settings") as mock_settings:
            mock_settings.asset_email_address = "asset@test.com"
            QuarantineService.quarantine(record, exc, env, smtp, factory)

        # .begin() called only once (Transaction 1); Transaction 2 skipped on SMTP failure
        assert factory.begin.call_count == 1


class TestClarificationTemplate:
    def test_template_renders_without_target_statement(self) -> None:
        """clarification.jinja must never expose the target statement."""
        env = _make_env()
        template = env.get_template("clarification.jinja")
        rendered = template.render(coordinate="ABCD/EFGH", parameter="VAD")

        assert "ABCD/EFGH" in rendered
        assert "VAD" in rendered
        # Ensure no template variable leaked as literal text
        assert "target_statement" not in rendered
        assert "{{" not in rendered

    def test_template_first_line_is_subject(self) -> None:
        env = _make_env()
        template = env.get_template("clarification.jinja")
        rendered = template.render(coordinate="ABCD/EFGH", parameter="VAD")
        lines = rendered.splitlines()
        assert lines[0].startswith("Subject: ")

    def test_template_subject_contains_coordinate(self) -> None:
        env = _make_env()
        template = env.get_template("clarification.jinja")
        rendered = template.render(coordinate="1234/5678", parameter="RVD")
        lines = rendered.splitlines()
        assert "1234/5678" in lines[0]
