"""Unit tests for ClosureService (Story 3.2).

Tests the closure ceremony flow in isolation:
  - No DB (mock sessionmaker via unittest.mock)
  - No real SMTP (FakeSMTPClient)
  - Real Jinja2 templates (from src/apollo/templates/)

All tests are pure — no Postgres required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from jinja2 import Environment, FileSystemLoader

from apollo.services.closure import ClosureService, ClosureSessionSummary
from tests.utils import FakeSMTPClient


def _make_env() -> Environment:
    templates_dir = Path(__file__).parent.parent.parent / "src" / "apollo" / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)


def _make_summary(**kwargs: object) -> ClosureSessionSummary:
    defaults: dict[str, object] = dict(
        validation_record_id=uuid4(),
        coordinate="AAAA/BBBB",
        parameter_name="VAD",
        target_statement="Gold futures will rise",
        param_value=75.0,
        validation_status="hit",
        actual_change_pct=10.0,
        actual_positive=True,
        predicted_positive=True,
        validated_at=datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC),
    )
    defaults.update(kwargs)
    return ClosureSessionSummary(**defaults)  # type: ignore[arg-type]


def _make_mock_factory(
    last_sent: datetime | None = None,
    pending: list[ClosureSessionSummary] | None = None,
) -> MagicMock:
    """Build a mock sessionmaker supporting both session_factory() and session_factory.begin()."""
    mock_factory = MagicMock()

    # session_factory() as read context manager
    mock_read_session = MagicMock()
    mock_read_ctx = MagicMock()
    mock_read_ctx.__enter__ = MagicMock(return_value=mock_read_session)
    mock_read_ctx.__exit__ = MagicMock(return_value=False)
    mock_factory.return_value = mock_read_ctx

    # session_factory.begin() as write context manager
    mock_write_session = MagicMock()
    mock_write_ctx = MagicMock()
    mock_write_ctx.__enter__ = MagicMock(return_value=mock_write_session)
    mock_write_ctx.__exit__ = MagicMock(return_value=False)
    mock_factory.begin.return_value = mock_write_ctx

    return mock_factory


# ---------------------------------------------------------------------------
# _render_email tests
# ---------------------------------------------------------------------------


class TestRenderEmail:
    def test_happy_path_single_session(self) -> None:
        env = _make_env()
        summary = _make_summary()
        now = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        subject, body = ClosureService._render_email([summary], env, now)

        assert subject.startswith("Apollo Closure Ceremony")
        assert "1 Session(s)" in subject
        assert summary.coordinate in body
        assert summary.target_statement in body
        assert "HIT" in body

    def test_subject_contains_session_count(self) -> None:
        env = _make_env()
        summaries = [_make_summary(), _make_summary(coordinate="CCCC/DDDD")]
        now = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        subject, _ = ClosureService._render_email(summaries, env, now)

        assert "2 Session(s)" in subject

    def test_body_contains_target_statement(self) -> None:
        env = _make_env()
        summary = _make_summary(target_statement="EURUSD will fall below 1.05")
        now = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        _, body = ClosureService._render_email([summary], env, now)

        assert "EURUSD will fall below 1.05" in body

    def test_body_contains_actual_change_pct(self) -> None:
        env = _make_env()
        summary = _make_summary(actual_change_pct=12.34)
        now = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        _, body = ClosureService._render_email([summary], env, now)

        assert "12.34" in body

    def test_raises_on_missing_subject_header(self) -> None:
        summary = _make_summary()
        now = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        bad_template = MagicMock()
        bad_template.render.return_value = "No subject line here\nBody text."
        bad_env = MagicMock()
        bad_env.get_template.return_value = bad_template

        with pytest.raises(ValueError, match="Subject:"):
            ClosureService._render_email([summary], bad_env, now)

    def test_raises_on_empty_body(self) -> None:
        summary = _make_summary()
        now = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        empty_body_template = MagicMock()
        empty_body_template.render.return_value = "Subject: Test\n\n   \n"
        bad_env = MagicMock()
        bad_env.get_template.return_value = empty_body_template

        with pytest.raises(ValueError, match="empty"):
            ClosureService._render_email([summary], bad_env, now)


# ---------------------------------------------------------------------------
# close_pending — interval logic
# ---------------------------------------------------------------------------


class TestClosePendingInterval:
    def test_interval_not_elapsed_returns_zero(self) -> None:
        """3 days elapsed, interval=7 → skip."""
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()
        last_sent = datetime.now(UTC) - timedelta(days=3)

        with patch.object(
            ClosureService, "_get_last_ceremony_timestamp", return_value=last_sent
        ):
            result = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=7
            )

        assert result == (0, False)
        assert len(smtp.sent) == 0

    def test_interval_elapsed_proceeds(self) -> None:
        """8 days elapsed, interval=7 → proceed."""
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()
        last_sent = datetime.now(UTC) - timedelta(days=8)
        pending = [_make_summary()]

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=last_sent
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed"),
        ):
            count, sent = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=7
            )

        assert count == 1
        assert sent is True
        assert len(smtp.sent) == 1

    def test_interval_none_bypasses_check(self) -> None:
        """interval_days=None → interval check skipped entirely."""
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()
        pending = [_make_summary()]

        with (
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed"),
        ):
            count, sent = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=None
            )

        assert count == 1
        assert sent is True

    def test_last_sent_none_always_proceeds(self) -> None:
        """last_sent=None (never run) → interval check bypassed, proceeds."""
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()
        pending = [_make_summary()]

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=None
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed"),
        ):
            count, sent = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=7
            )

        assert count == 1
        assert sent is True


# ---------------------------------------------------------------------------
# close_pending — no pending sessions
# ---------------------------------------------------------------------------


class TestClosePendingNoPending:
    def test_no_pending_returns_zero_false(self) -> None:
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=None
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=[]),
        ):
            result = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=None
            )

        assert result == (0, False)
        assert len(smtp.sent) == 0


# ---------------------------------------------------------------------------
# close_pending — happy path
# ---------------------------------------------------------------------------


class TestClosePendingHappyPath:
    def test_two_sessions_returns_two_true(self) -> None:
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()
        pending = [_make_summary(), _make_summary(coordinate="CCCC/DDDD")]

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=None
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed") as mock_mark,
        ):
            count, sent = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=None
            )

        assert count == 2
        assert sent is True
        assert len(smtp.sent) == 1
        mock_mark.assert_called_once()

    def test_smtp_called_with_recipient(self) -> None:
        factory = _make_mock_factory()
        smtp = FakeSMTPClient()
        env = _make_env()
        pending = [_make_summary()]

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=None
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed"),
        ):
            ClosureService.close_pending(
                factory, smtp, env, "ceremony@test.com", interval_days=None
            )

        assert smtp.sent[0]["to"] == "ceremony@test.com"


# ---------------------------------------------------------------------------
# close_pending — SMTP failure
# ---------------------------------------------------------------------------


class TestClosePendingSMTPFailure:
    def test_smtp_failure_returns_zero_false(self) -> None:
        factory = _make_mock_factory()
        smtp = FakeSMTPClient(raise_on_nth=1)
        env = _make_env()
        pending = [_make_summary()]

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=None
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed") as mock_mark,
        ):
            count, sent = ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=None
            )

        assert count == 0
        assert sent is False
        mock_mark.assert_not_called()

    def test_smtp_failure_does_not_raise(self) -> None:
        factory = _make_mock_factory()
        smtp = FakeSMTPClient(raise_on_nth=1)
        env = _make_env()
        pending = [_make_summary()]

        with (
            patch.object(
                ClosureService, "_get_last_ceremony_timestamp", return_value=None
            ),
            patch.object(ClosureService, "_fetch_pending", return_value=pending),
            patch.object(ClosureService, "_mark_closed"),
        ):
            # Must not raise
            ClosureService.close_pending(
                factory, smtp, env, "asset@test.com", interval_days=None
            )
