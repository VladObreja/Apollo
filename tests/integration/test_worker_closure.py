"""Integration tests for worker Phase 5 — closure ceremony dispatch (Story 3.2).

Tests the full closure cycle using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - FakeSMTPClient to capture closure ceremony emails
  - CorpusRecordFactory + ValidationRecordFactory to seed validated sessions

Verifies:
  - 1 pending session → (1, True), closed_at set, smtp sent
  - Second call returns (0, False) because closed_at is now set
  - interval_days=7 with no prior ceremony → runs (last_sent=None)
  - interval_days=7 with recent ceremony → returns (0, False)
  - No validation_records → (0, False)
  - SMTP failure → (0, False), closed_at remains NULL
  - Full tick() with validated un-closed record → closed_at set after tick
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from apollo.db.models import CorpusRecord, ValidationRecord
from tests.factories import CorpusRecordFactory, ValidationRecordFactory
from tests.utils import (
    FakeEnvDataClient,
    FakeIMAPClient,
    FakeLLM,
    FakeMarketDataClient,
    FakeSMTPClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_closed_awaiting_corpus(
    db_session,  # type: ignore[no-untyped-def]
) -> tuple[CorpusRecord, ValidationRecord]:
    """Seed a sealed CorpusRecord with a linked un-closed ValidationRecord."""
    record = CorpusRecordFactory(
        status="sealed",
        double_blind_coordinate="AAAA/BBBB",
        parameter_name="VAD",
        target_statement="Gold futures will rise",
        raw_hash=uuid4().hex * 2,
        sealed_at=datetime.now(UTC),
        seal_agent_version="0.1.0",
        dispatched_at=datetime.now(UTC) - timedelta(hours=2),
        dispatch_agent_version="0.1.0",
    )
    db_session.flush()
    vr = ValidationRecordFactory(
        corpus_record_id=record.id,
        validation_status="hit",
        param_value=75.0,
        actual_change_pct=10.0,
        predicted_positive=True,
        actual_positive=True,
    )
    db_session.flush()
    return record, vr  # type: ignore[return-value]


def _make_closure_service_factory(patched_db_url: str):  # type: ignore[no-untyped-def]
    import apollo.db.session as sess_mod
    from apollo.db.session import get_session_factory

    # Reset singleton so the factory always binds to the test container URL,
    # not a previously-initialized production engine.
    sess_mod._engine = None
    sess_mod._SessionFactory = None
    return get_session_factory()


def _make_env():  # type: ignore[no-untyped-def]
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    templates_dir = Path(__file__).parent.parent.parent / "src" / "apollo" / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)


def _tick(**kwargs):  # type: ignore[no-untyped-def]
    from apollo.services.worker import tick

    tick(
        smtp_client=kwargs.pop("smtp_client", FakeSMTPClient()),
        llm_client=FakeLLM([]),
        imap_client=FakeIMAPClient([]),
        env_client=FakeEnvDataClient(),
        market_client=FakeMarketDataClient(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Direct ClosureService integration tests
# ---------------------------------------------------------------------------


class TestClosureServiceIntegration:
    def test_one_pending_session_closes_and_sends(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """1 pending session → (1, True), closed_at set, smtp sent once."""
        from apollo.services.closure import ClosureService

        _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        count, sent = ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )

        assert count == 1
        assert sent is True
        assert len(smtp.sent) == 1
        assert smtp.sent[0]["to"] == "asset@test.com"

        db_session.expire_all()
        vr = db_session.execute(select(ValidationRecord)).scalar_one()
        assert vr.closed_at is not None
        assert vr.closed_at.tzinfo is not None

    def test_second_call_returns_zero_already_closed(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """After first ceremony, second call with interval_days=None returns (0, False)."""
        from apollo.services.closure import ClosureService

        _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )
        db_session.expire_all()

        count, sent = ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )

        assert count == 0
        assert sent is False
        assert len(smtp.sent) == 1  # Only one email total

    def test_interval_days_no_prior_ceremony_runs(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """interval_days=7, no prior ceremony → last_sent=None → runs."""
        from apollo.services.closure import ClosureService

        _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        count, sent = ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=7
        )

        assert count == 1
        assert sent is True

    def test_interval_days_recent_ceremony_skipped(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """interval_days=7, ceremony just run → closed_at is now → skip."""
        from apollo.services.closure import ClosureService

        _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        # Run ceremony now — this sets closed_at to now
        ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )
        db_session.expire_all()

        # Seed a second record that is still open
        _seed_closed_awaiting_corpus(db_session)

        # With interval_days=7, last_sent = just now → elapsed < 7 → skip
        count, sent = ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=7
        )

        assert count == 0
        assert sent is False

    def test_no_validation_records_returns_zero(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Empty validation_record table → (0, False), no smtp sent."""
        from apollo.services.closure import ClosureService

        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        count, sent = ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )

        assert count == 0
        assert sent is False
        assert len(smtp.sent) == 0

    def test_smtp_failure_leaves_closed_at_null(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """SMTP raises OSError → (0, False), closed_at remains NULL."""
        from apollo.services.closure import ClosureService

        _, vr = _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient(raise_on_nth=1)
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        count, sent = ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )

        assert count == 0
        assert sent is False

        db_session.expire_all()
        fresh_vr = db_session.get(ValidationRecord, vr.id)
        assert fresh_vr is not None
        assert fresh_vr.closed_at is None

    def test_closure_email_body_contains_target_statement(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Double-blind lifted at closure — target_statement appears in email body."""
        from apollo.services.closure import ClosureService

        record, _ = _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )

        assert record.target_statement in smtp.sent[0]["body"]
        assert record.double_blind_coordinate in smtp.sent[0]["body"]

    def test_closure_email_subject_starts_with_apollo(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        from apollo.services.closure import ClosureService

        _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()
        factory = _make_closure_service_factory(patched_db_url)
        env = _make_env()

        ClosureService.close_pending(
            factory, smtp, env, "asset@test.com", interval_days=None
        )

        assert smtp.sent[0]["subject"].startswith("Apollo Closure Ceremony")


# ---------------------------------------------------------------------------
# Full tick() integration tests
# ---------------------------------------------------------------------------


class TestWorkerClosureIntegration:
    def test_tick_closes_validated_record_when_interval_zero(
        self,
        db_session,
        patched_db_url,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        """Full tick() with CLOSURE_CEREMONY_INTERVAL_DAYS=0 → closed_at set after tick."""
        import apollo.db.session as sess_mod

        monkeypatch.setenv("CLOSURE_CEREMONY_INTERVAL_DAYS", "0")
        # Reset cached Settings instance to pick up new env var
        import apollo.config as cfg_mod

        monkeypatch.setattr(cfg_mod, "settings", cfg_mod.Settings())
        # Reset session factory to use test container (already patched by patched_db_url)
        sess_mod._engine = None
        sess_mod._SessionFactory = None

        _, vr = _seed_closed_awaiting_corpus(db_session)
        smtp = FakeSMTPClient()

        _tick(smtp_client=smtp)
        db_session.expire_all()

        fresh_vr = db_session.get(ValidationRecord, vr.id)
        assert fresh_vr is not None
        assert fresh_vr.closed_at is not None
        assert len(smtp.sent) >= 1

    def test_tick_phase5_is_fail_operational(
        self,
        db_session,
        patched_db_url,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        """Phase 5 crash (smtp failure) must not crash tick()."""
        import apollo.db.session as sess_mod
        import apollo.config as cfg_mod

        monkeypatch.setenv("CLOSURE_CEREMONY_INTERVAL_DAYS", "0")
        monkeypatch.setattr(cfg_mod, "settings", cfg_mod.Settings())
        sess_mod._engine = None
        sess_mod._SessionFactory = None

        _seed_closed_awaiting_corpus(db_session)
        # smtp raises on 1st send (Phase 2 has no dispatched records, so Phase 5 uses call 1)
        smtp = FakeSMTPClient(raise_on_nth=1)

        _tick(smtp_client=smtp)  # Must NOT raise

        db_session.expire_all()
        vr = db_session.execute(select(ValidationRecord)).scalar_one()
        assert vr.closed_at is None  # SMTP failed → record stays open
