"""Integration tests for CalibrationService (Story 3.3).

Uses testcontainers PostgreSQL via shared conftest fixtures.
Seeds validation_record rows directly via factories (no corpus_record join needed).
Verifies Brier score, ECE, Wilson CI, and offset exclusion against real Postgres.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from apollo.db.models import ValidationRecord
from apollo.services.calibration import CalibrationService
from apollo.db.session import get_session_factory
from tests.factories import CorpusRecordFactory, ValidationRecordFactory


def _unique_hash() -> str:
    """Generate a unique 64-char hex string for raw_hash column."""
    return uuid4().hex * 2


def _seed_closed_vr(
    db_session,  # type: ignore[no-untyped-def]
    param_value: float,
    actual_positive: bool,
    status: str = "hit",
) -> ValidationRecord:
    """Seed a closed validation_record with a real parent corpus_record."""
    corpus = CorpusRecordFactory(
        status="sealed",
        ticker="GC=F",
        expiry_at=datetime(2026, 6, 1, 21, 0, 0, tzinfo=UTC),
        threshold_pct=9.0,
        threshold_direction="UP",
        extraction_payload={"param_value": param_value},
        raw_hash=_unique_hash(),
        sealed_at=datetime.now(UTC),
        seal_agent_version="0.1.0",
        double_blind_coordinate=f"{uuid4().hex[:4].upper()}/{uuid4().hex[:4].upper()}",
        dispatched_at=datetime.now(UTC),
        dispatch_agent_version="0.1.0",
    )
    db_session.flush()

    vr = ValidationRecordFactory(
        corpus_record_id=corpus.id,
        validation_status=status,
        param_value=param_value,
        predicted_positive=param_value >= 50.0,
        actual_positive=actual_positive,
        validated_at=datetime.now(UTC),
        closed_at=datetime.now(UTC),
    )
    db_session.flush()
    return vr  # type: ignore[return-value]


def _seed_open_vr(
    db_session,  # type: ignore[no-untyped-def]
    param_value: float = 70.0,
) -> ValidationRecord:
    """Seed an open (not-yet-closed) validation_record — must be excluded from stats."""
    corpus = CorpusRecordFactory(
        status="sealed",
        ticker="GC=F",
        expiry_at=datetime(2026, 6, 1, 21, 0, 0, tzinfo=UTC),
        threshold_pct=9.0,
        threshold_direction="UP",
        extraction_payload={"param_value": param_value},
        raw_hash=_unique_hash(),
        sealed_at=datetime.now(UTC),
        seal_agent_version="0.1.0",
        double_blind_coordinate=f"{uuid4().hex[:4].upper()}/{uuid4().hex[:4].upper()}",
        dispatched_at=datetime.now(UTC),
        dispatch_agent_version="0.1.0",
    )
    db_session.flush()

    vr = ValidationRecordFactory(
        corpus_record_id=corpus.id,
        validation_status="hit",
        param_value=param_value,
        predicted_positive=True,
        actual_positive=True,
        validated_at=datetime.now(UTC),
        closed_at=None,  # not closed — must be excluded
    )
    db_session.flush()
    return vr  # type: ignore[return-value]


class TestCalibrationServiceIntegration:
    def test_empty_corpus_returns_null_metrics(
        self, db_session, patched_db_url
    ) -> None:
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert stats.n_total == 0
        assert stats.n_scored == 0
        assert stats.n_offset == 0
        assert stats.brier_score is None
        assert stats.ece is None
        assert stats.hit_rate is None
        assert len(stats.conviction_buckets) == 10

    def test_open_sessions_excluded(self, db_session, patched_db_url) -> None:
        _seed_open_vr(db_session)
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert stats.n_total == 0

    def test_offset_excluded_from_scoring(self, db_session, patched_db_url) -> None:
        _seed_closed_vr(db_session, 70.0, True, status="hit")
        _seed_closed_vr(db_session, 70.0, True, status="offset")
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert stats.n_total == 2
        assert stats.n_offset == 1
        assert stats.n_scored == 1

    def test_brier_score_single_hit(self, db_session, patched_db_url) -> None:
        # param_value=80, actual_positive=True → (0.8-1)^2 = 0.04
        _seed_closed_vr(db_session, 80.0, True, status="hit")
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert stats.brier_score == pytest.approx(0.04, abs=1e-6)

    def test_hit_rate_and_wilson_ci(self, db_session, patched_db_url) -> None:
        # 3 hits, 1 miss → hit_rate = 0.75
        _seed_closed_vr(db_session, 80.0, True, status="hit")
        _seed_closed_vr(db_session, 70.0, True, status="hit")
        _seed_closed_vr(db_session, 75.0, True, status="hit")
        _seed_closed_vr(db_session, 60.0, False, status="miss")
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert stats.n_scored == 4
        assert stats.hit_rate == pytest.approx(0.75, abs=1e-6)
        assert stats.hit_rate_ci_lower is not None
        assert stats.hit_rate_ci_upper is not None
        assert stats.hit_rate_ci_lower < 0.75 < stats.hit_rate_ci_upper

    def test_conviction_buckets_count(self, db_session, patched_db_url) -> None:
        _seed_closed_vr(db_session, 80.0, True, status="hit")
        _seed_closed_vr(db_session, 85.0, False, status="miss")
        _seed_closed_vr(db_session, 55.0, True, status="hit")
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert len(stats.conviction_buckets) == 10
        # bucket index 8 = 80-90
        bucket_80 = stats.conviction_buckets[8]
        assert bucket_80.n == 2
        assert bucket_80.hit_rate == pytest.approx(0.5, abs=1e-6)
        # bucket index 5 = 50-60
        bucket_50 = stats.conviction_buckets[5]
        assert bucket_50.n == 1
        assert bucket_50.hit_rate == pytest.approx(1.0, abs=1e-6)

    def test_computed_at_is_utc_and_recent(self, db_session, patched_db_url) -> None:
        _seed_closed_vr(db_session, 70.0, True, status="hit")
        session_factory = get_session_factory()
        before = datetime.now(UTC)
        stats = CalibrationService.get_stats(session_factory)
        after = datetime.now(UTC)

        assert stats.computed_at.tzinfo is not None
        assert before <= stats.computed_at <= after

    def test_full_frozen_corpus_brier(self, db_session, patched_db_url) -> None:
        """Seed the same 10-session frozen corpus and assert Brier ≈ 0.19875."""
        corpus = [
            (80.0, True,  "hit"),
            (70.0, True,  "hit"),
            (60.0, False, "miss"),
            (90.0, True,  "hit"),
            (30.0, False, "miss"),
            (50.0, True,  "hit"),
            (55.0, True,  "hit"),
            (40.0, False, "miss"),
            (75.0, True,  "hit"),
            (85.0, False, "miss"),
        ]
        for pv, ap, st in corpus:
            _seed_closed_vr(db_session, pv, ap, status=st)

        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)

        assert stats.n_total == 10
        assert stats.n_offset == 0
        assert stats.n_scored == 10
        assert stats.brier_score == pytest.approx(0.19875, abs=1e-5)
        assert stats.ece == pytest.approx(0.355, abs=1e-5)
        assert stats.hit_rate == pytest.approx(0.6, abs=1e-5)
