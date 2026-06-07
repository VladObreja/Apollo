"""Integration tests for worker Phase 3 — environmental fingerprinting (Story 2.4).

Tests the full fingerprint path using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - FakeEnvDataClient with configurable failure modes
  - FakeLLM + FakeIMAPClient for sealing the record first

Verifies:
  - Successful tick → env_fingerprint row created with retrieval_status='ok'
  - Both APIs fail → env_fingerprint created with retrieval_status='pending', corpus_record sealed
  - One API fails → env_fingerprint created with retrieval_status='partial'
  - Sealing succeeds even when FingerprintService raises internally
"""

from __future__ import annotations

import email.mime.text
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from apollo.db.models import CorpusRecord, EnvFingerprint
from apollo.domain.types import TargetStatus
from tests.factories import CorpusRecordFactory
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


def _make_reply_email(coordinate: str) -> bytes:
    msg = email.mime.text.MIMEText(
        f"PARAM (VAD): 85\nTime of measurement (UTC): 2026-06-06T10:00:00Z\n"
        f"Location: Bucharest\nSleep quality (0-100): 80\nPsychological state (0-100): 75\n"
        f"Social Field: Isolated\nTarget ID {coordinate}",
        "plain",
        "utf-8",
    )
    msg["Subject"] = f"Re: Apollo Research Session — Target ID {coordinate}"
    msg["From"] = "asset@proton.me"
    msg["To"] = "apollo@proton.me"
    return msg.as_bytes()


def _valid_extraction_json(param_value: float = 85.0) -> str:
    return json.dumps({"param_value": param_value})


def _seed_dispatched(session, coordinate: str) -> CorpusRecord:  # type: ignore[no-untyped-def]
    record = CorpusRecordFactory(
        status=TargetStatus.DISPATCHED.value,
        available_after=datetime.now(UTC) - timedelta(seconds=1),
        double_blind_coordinate=coordinate,
        queued_at=datetime.now(UTC) - timedelta(minutes=5),
        dispatched_at=datetime.now(UTC) - timedelta(minutes=4),
        dispatch_agent_version="0.1.0",
    )
    session.flush()
    return record  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerFingerprintIntegration:
    def test_full_tick_creates_fingerprint_ok(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Full tick with good env_client → env_fingerprint row created with retrieval_status='ok'."""
        from apollo.services.worker import tick

        coord = "FP01/AA01"
        record = _seed_dispatched(db_session, coord)

        tick(
            smtp_client=FakeSMTPClient(),
            llm_client=FakeLLM([_valid_extraction_json()]),
            imap_client=FakeIMAPClient([_make_reply_email(coord)]),
            env_client=FakeEnvDataClient(kp=3.0, solar_wind=450.0),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        fp = db_session.execute(
            select(EnvFingerprint).where(EnvFingerprint.corpus_record_id == record.id)
        ).scalar_one()
        assert fp.retrieval_status == "ok"
        assert fp.kp_index == 3.0
        assert fp.solar_wind_speed == 450.0
        assert fp.local_sidereal_time is not None
        assert fp.retrieval_notes is None

        # Corpus record must remain sealed
        fresh = db_session.get(CorpusRecord, record.id)
        assert fresh is not None
        assert fresh.status == TargetStatus.SEALED.value

    def test_both_apis_fail_creates_failed_fingerprint(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Both APIs fail → env_fingerprint created with retrieval_status='failed', corpus_record sealed."""
        from apollo.services.worker import tick

        coord = "FP02/BB02"
        record = _seed_dispatched(db_session, coord)

        tick(
            smtp_client=FakeSMTPClient(),
            llm_client=FakeLLM([_valid_extraction_json()]),
            imap_client=FakeIMAPClient([_make_reply_email(coord)]),
            env_client=FakeEnvDataClient(raise_on_kp=True, raise_on_wind=True),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        fp = db_session.execute(
            select(EnvFingerprint).where(EnvFingerprint.corpus_record_id == record.id)
        ).scalar_one()
        assert fp.retrieval_status == "failed"
        assert fp.kp_index is None
        assert fp.solar_wind_speed is None
        assert fp.local_sidereal_time is not None  # LST is local — always computed

        # Sealing must not be affected by fingerprint failure
        fresh = db_session.get(CorpusRecord, record.id)
        assert fresh is not None
        assert fresh.status == TargetStatus.SEALED.value

    def test_one_api_fail_creates_partial_fingerprint(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Kp fails, wind succeeds → retrieval_status='partial', solar_wind_speed set."""
        from apollo.services.worker import tick

        coord = "FP03/CC03"
        record = _seed_dispatched(db_session, coord)

        tick(
            smtp_client=FakeSMTPClient(),
            llm_client=FakeLLM([_valid_extraction_json()]),
            imap_client=FakeIMAPClient([_make_reply_email(coord)]),
            env_client=FakeEnvDataClient(raise_on_kp=True, solar_wind=450.0),
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        fp = db_session.execute(
            select(EnvFingerprint).where(EnvFingerprint.corpus_record_id == record.id)
        ).scalar_one()
        assert fp.retrieval_status == "partial"
        assert fp.kp_index is None
        assert fp.solar_wind_speed == 450.0

    def test_sealing_succeeds_when_fingerprint_fails(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Corpus record sealed even when fingerprint service fails completely (fail-operational)."""
        from unittest.mock import MagicMock

        from apollo.services.worker import tick

        coord = "FP04/DD04"
        record = _seed_dispatched(db_session, coord)

        # env_client that raises on every call — fingerprint will fail
        bad_env_client = MagicMock()
        bad_env_client.fetch_kp_index.side_effect = RuntimeError("total env failure")
        bad_env_client.fetch_solar_wind_speed.side_effect = RuntimeError(
            "total env failure"
        )

        # Must NOT raise — fail-operational
        tick(
            smtp_client=FakeSMTPClient(),
            llm_client=FakeLLM([_valid_extraction_json()]),
            imap_client=FakeIMAPClient([_make_reply_email(coord)]),
            env_client=bad_env_client,
            market_client=FakeMarketDataClient(),
        )
        db_session.expire_all()

        # Corpus record must still be sealed
        fresh = db_session.get(CorpusRecord, record.id)
        assert fresh is not None
        assert fresh.status == TargetStatus.SEALED.value

        # AC3: env_fingerprint row must be created even when both APIs fail
        fp = db_session.execute(
            select(EnvFingerprint).where(EnvFingerprint.corpus_record_id == record.id)
        ).scalar_one()
        assert fp.retrieval_status == "failed"
