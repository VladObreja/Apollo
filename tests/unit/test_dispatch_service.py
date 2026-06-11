"""Unit tests for DispatchService — pure logic, no real DB or SMTP.

Uses hand-rolled fakes to test:
  - Jinja2 template rendering correctness and double-blind safety
  - mark_dispatched field mutations
  - fetch_queued_for_dispatch query shape
  - Per-record SMTP failure isolation
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from tests.utils import FakeSMTPClient


# ---------------------------------------------------------------------------
# Helpers & fakes
# ---------------------------------------------------------------------------


def _make_record(
    coordinate: str = "8A2F/9B4C",
    parameter_name: str = "vad",
    target_statement: str = "Gold price will increase by >9% tomorrow",
) -> MagicMock:
    """Build a minimal CorpusRecord-like mock."""
    record = MagicMock()
    record.id = uuid4()
    record.double_blind_coordinate = coordinate
    record.parameter_name = parameter_name
    record.target_statement = target_statement
    record.status = "queued"
    record.dispatched_at = None
    record.dispatch_agent_version = None
    return record


def _make_session(query_results: list[Any] | None = None) -> MagicMock:
    """Build a SQLAlchemy session mock."""
    session = MagicMock()
    query_mock = session.query.return_value
    filter_mock = query_mock.filter.return_value
    order_mock = filter_mock.order_by.return_value
    order_mock.all.return_value = query_results or []
    return session


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------


class TestRenderTaskingEmail:
    def _render(
        self, coordinate: str = "8A2F/9B4C", parameter: str = "vad"
    ) -> tuple[str, str]:
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        from apollo.services.dispatch import DispatchService

        templates_dir = (
            Path(__file__).parent.parent.parent / "src" / "apollo" / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
        record = _make_record(coordinate=coordinate, parameter_name=parameter)
        return DispatchService.render_tasking_email(record, env)

    def test_subject_contains_coordinate(self) -> None:
        subject, _ = self._render(coordinate="8A2F/9B4C")
        assert "8A2F/9B4C" in subject

    def test_body_contains_coordinate(self) -> None:
        _, body = self._render(coordinate="8A2F/9B4C")
        assert "8A2F/9B4C" in body

    def test_body_contains_parameter(self) -> None:
        _, body = self._render(parameter="vad")
        assert "vad" in body

    def test_body_does_not_contain_target_statement(self) -> None:
        """Double-blind: target identity must never appear in the email."""
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        from apollo.services.dispatch import DispatchService

        templates_dir = (
            Path(__file__).parent.parent.parent / "src" / "apollo" / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
        record = _make_record(
            target_statement="SUPERSECRET: Gold price increases 9% tomorrow",
            coordinate="1234/5678",
            parameter_name="vad",
        )
        _, body = DispatchService.render_tasking_email(record, env)
        assert "SUPERSECRET" not in body
        assert "Gold price" not in body

    def test_body_contains_all_six_measurement_fields(self) -> None:
        _, body = self._render()
        for field in [
            "PARAM",
            "Time of measurement",
            "Location",
            "Sleep quality",
            "Psychological state",
            "Social Field",
        ]:
            assert field in body, f"Missing field: {field!r}"

    def test_render_returns_tuple_of_two_strings(self) -> None:
        result = self._render()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(s, str) for s in result)


# ---------------------------------------------------------------------------
# mark_dispatched tests
# ---------------------------------------------------------------------------


class TestMarkDispatched:
    def test_sets_status_to_dispatched(self) -> None:
        from apollo.services.dispatch import DispatchService

        record = _make_record()
        session = MagicMock()
        DispatchService.mark_dispatched(record, session, "0.1.0")
        assert record.status == "dispatched"

    def test_sets_dispatched_at_to_utc_now(self) -> None:
        from apollo.services.dispatch import DispatchService

        record = _make_record()
        session = MagicMock()
        before = datetime.now(UTC)
        DispatchService.mark_dispatched(record, session, "0.1.0")
        after = datetime.now(UTC)
        assert record.dispatched_at is not None
        assert record.dispatched_at.tzinfo is not None, (
            "dispatched_at must be UTC-aware"
        )
        assert before <= record.dispatched_at <= after

    def test_sets_dispatch_agent_version(self) -> None:
        from apollo.services.dispatch import DispatchService

        record = _make_record()
        session = MagicMock()
        DispatchService.mark_dispatched(record, session, "1.2.3")
        assert record.dispatch_agent_version == "1.2.3"

    def test_calls_session_add(self) -> None:
        from apollo.services.dispatch import DispatchService

        record = _make_record()
        session = MagicMock()
        DispatchService.mark_dispatched(record, session, "0.1.0")
        session.add.assert_called_once_with(record)


# ---------------------------------------------------------------------------
# fetch_queued_for_dispatch tests
# ---------------------------------------------------------------------------


class TestFetchQueuedForDispatch:
    def test_returns_empty_when_no_queued(self) -> None:
        from apollo.services.dispatch import DispatchService

        session = _make_session(query_results=[])
        result = DispatchService.fetch_queued_for_dispatch(session)
        assert result == []

    def test_returns_records_from_db(self) -> None:
        from apollo.services.dispatch import DispatchService

        records = [_make_record(), _make_record()]
        session = _make_session(query_results=records)
        result = DispatchService.fetch_queued_for_dispatch(session)
        assert len(result) == 2

    def test_calls_filter_on_session(self) -> None:
        from apollo.services.dispatch import DispatchService

        session = _make_session(query_results=[])
        DispatchService.fetch_queued_for_dispatch(session)
        session.query.assert_called_once()
        assert session.query.return_value.filter.called


# ---------------------------------------------------------------------------
# Settings defaults test
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    def test_smtp_defaults_are_set(self) -> None:
        """Settings must have SMTP fields with Proton Bridge defaults."""
        import os

        # Temporarily clear any SMTP env vars that might be set
        smtp_vars = [
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_FROM_ADDRESS",
            "ASSET_EMAIL_ADDRESS",
            "SMTP_USE_TLS",
        ]
        saved = {k: os.environ.pop(k, None) for k in smtp_vars}
        try:
            # Reload settings to pick up cleared env
            # Create a fresh Settings instance (don't rely on cached singleton)
            from apollo.config import Settings

            s = Settings()
            assert s.smtp_host == "127.0.0.1"
            assert s.smtp_port == 1025
            assert s.smtp_use_tls is False
            assert "@" in s.smtp_from_address
            assert "@" in s.asset_email_address
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_imap_defaults_are_set(self) -> None:
        """Settings must have IMAP fields with Proton Bridge defaults."""
        import os

        imap_vars = [
            "IMAP_HOST",
            "IMAP_PORT",
            "IMAP_PASSWORD",
            "IMAP_MAILBOX",
            "IMAP_USE_SSL",
        ]
        saved = {k: os.environ.pop(k, None) for k in imap_vars}

        # We MUST provide both required fields
        saved_user = os.environ.get("IMAP_USERNAME")
        os.environ["IMAP_USERNAME"] = "test_user@proton.me"
        saved_digest = os.environ.get("OLLAMA_MODEL_DIGEST")
        os.environ["OLLAMA_MODEL_DIGEST"] = "sha256:dummy"

        try:
            from apollo.config import Settings

            s = Settings()
            assert s.imap_host == "127.0.0.1"
            assert s.imap_port == 1143
            assert s.imap_mailbox == "INBOX"
            assert s.imap_use_ssl is False
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

            if saved_user is not None:
                os.environ["IMAP_USERNAME"] = saved_user
            else:
                os.environ.pop("IMAP_USERNAME", None)
            if saved_digest is not None:
                os.environ["OLLAMA_MODEL_DIGEST"] = saved_digest
            else:
                os.environ.pop("OLLAMA_MODEL_DIGEST", None)

    def test_imap_use_ssl_false_logs_startup_warning(self, caplog: Any) -> None:
        """A startup warning is logged when imap_use_ssl is False (the default)."""
        import logging
        import os

        saved_ssl = os.environ.pop("IMAP_USE_SSL", None)
        saved_user = os.environ.get("IMAP_USERNAME")
        os.environ["IMAP_USERNAME"] = "test_user@proton.me"
        saved_digest = os.environ.get("OLLAMA_MODEL_DIGEST")
        os.environ["OLLAMA_MODEL_DIGEST"] = "sha256:dummy"

        try:
            from apollo.config import Settings

            with caplog.at_level(logging.WARNING, logger="apollo.config"):
                s = Settings()

            assert s.imap_use_ssl is False
            assert any(
                "imap_use_ssl" in r.message and r.levelno == logging.WARNING
                for r in caplog.records
            ), caplog.records
        finally:
            if saved_ssl is not None:
                os.environ["IMAP_USE_SSL"] = saved_ssl
            else:
                os.environ.pop("IMAP_USE_SSL", None)
            if saved_user is not None:
                os.environ["IMAP_USERNAME"] = saved_user
            else:
                os.environ.pop("IMAP_USERNAME", None)
            if saved_digest is not None:
                os.environ["OLLAMA_MODEL_DIGEST"] = saved_digest
            else:
                os.environ.pop("OLLAMA_MODEL_DIGEST", None)

    def test_imap_use_ssl_true_does_not_log_warning(self, caplog: Any) -> None:
        """No startup warning is logged when imap_use_ssl is True."""
        import logging
        import os

        saved_ssl = os.environ.get("IMAP_USE_SSL")
        os.environ["IMAP_USE_SSL"] = "true"
        saved_user = os.environ.get("IMAP_USERNAME")
        os.environ["IMAP_USERNAME"] = "test_user@proton.me"
        saved_digest = os.environ.get("OLLAMA_MODEL_DIGEST")
        os.environ["OLLAMA_MODEL_DIGEST"] = "sha256:dummy"

        try:
            from apollo.config import Settings

            with caplog.at_level(logging.WARNING, logger="apollo.config"):
                s = Settings()

            assert s.imap_use_ssl is True
            assert not any(
                "imap_use_ssl" in r.message and r.levelno == logging.WARNING
                for r in caplog.records
            ), caplog.records
        finally:
            if saved_ssl is not None:
                os.environ["IMAP_USE_SSL"] = saved_ssl
            else:
                os.environ.pop("IMAP_USE_SSL", None)
            if saved_user is not None:
                os.environ["IMAP_USERNAME"] = saved_user
            else:
                os.environ.pop("IMAP_USERNAME", None)
            if saved_digest is not None:
                os.environ["OLLAMA_MODEL_DIGEST"] = saved_digest
            else:
                os.environ.pop("OLLAMA_MODEL_DIGEST", None)

    def test_ollama_defaults_are_set(self) -> None:
        """Settings must have Ollama fields with sensible defaults."""
        import os

        ollama_vars = [
            "OLLAMA_BASE_URL",
            "OLLAMA_TIMEOUT_SECONDS",
        ]
        saved = {k: os.environ.pop(k, None) for k in ollama_vars}

        # We MUST provide both required fields
        saved_user = os.environ.get("IMAP_USERNAME")
        os.environ["IMAP_USERNAME"] = "test_user@proton.me"
        saved_digest = os.environ.get("OLLAMA_MODEL_DIGEST")
        os.environ["OLLAMA_MODEL_DIGEST"] = "sha256:dummy"

        try:
            from apollo.config import Settings

            s = Settings()
            assert s.ollama_base_url == "http://localhost:11434"
            assert s.ollama_timeout_seconds == 60
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)
            if saved_digest is not None:
                os.environ["OLLAMA_MODEL_DIGEST"] = saved_digest
            else:
                os.environ.pop("OLLAMA_MODEL_DIGEST", None)
            if saved_user is not None:
                os.environ["IMAP_USERNAME"] = saved_user
            else:
                os.environ.pop("IMAP_USERNAME", None)


# ---------------------------------------------------------------------------
# Worker tick dispatch tests
# ---------------------------------------------------------------------------


class TestWorkerTickDispatch:
    def test_smtp_failure_isolates_records(self) -> None:
        """If SMTP fails for one record, the next record is still processed."""
        from apollo.services.worker import tick
        from unittest.mock import patch

        fake_smtp = FakeSMTPClient(raise_on_nth=1)

        records = [_make_record(), _make_record()]

        with (
            patch("apollo.services.worker.get_session_factory") as mock_get_factory,
            patch("apollo.services.worker.DispatchService") as mock_dispatch,
        ):
            with patch("apollo.services.worker.count_available_slots", return_value=0):
                mock_dispatch.fetch_queued_for_dispatch.return_value = records
                mock_dispatch.render_tasking_email.return_value = (
                    "Subject: test",
                    "body",
                )

                # Mock session
                mock_session = MagicMock()
                mock_factory = MagicMock()
                mock_get_factory.return_value = mock_factory
                mock_factory.return_value.__enter__.return_value = mock_session
                mock_factory.begin.return_value.__enter__.return_value = mock_session

                # Mock fresh object retrieval
                fresh_record = MagicMock()
                fresh_record.status = "queued"
                mock_session.get.return_value = fresh_record

                from tests.utils import FakeIMAPClient

                tick(smtp_client=fake_smtp, imap_client=FakeIMAPClient([]))

                assert fake_smtp._call_count == 2
                assert len(fake_smtp.sent) == 1
