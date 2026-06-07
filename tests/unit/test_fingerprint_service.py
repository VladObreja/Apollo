"""Unit tests for FingerprintService (Story 2.4).

Pure domain logic tests — NO database, NO network calls.
Uses mock sessionmaker to test DB interaction paths.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError as SaIntegrityError

from apollo.db.models import EnvFingerprint
from apollo.services.fingerprint import FingerprintService, _compute_lst
from tests.utils import FakeEnvDataClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(received_at: datetime | None = None) -> MagicMock:
    """Build a minimal CorpusRecord stub (no DB required)."""
    from uuid import uuid4

    record = MagicMock()
    record.id = uuid4()
    record.received_at = received_at
    return record


def _make_mock_session_factory(
    raises: type[Exception] | None = None,
) -> tuple[MagicMock, list[EnvFingerprint]]:
    """Return a (mock_factory, written_objects) pair for unit testing."""
    written: list[EnvFingerprint] = []
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: s
    mock_session.__exit__ = MagicMock(return_value=False)
    if raises:
        mock_session.add = MagicMock(side_effect=raises("Simulated DB error"))
    else:
        mock_session.add = lambda obj: written.append(obj)
    mock_factory = MagicMock()
    mock_factory.begin.return_value = mock_session
    return mock_factory, written


def _make_integrity_error_factory() -> MagicMock:
    """Return a mock factory whose session raises IntegrityError on commit (context exit)."""

    @contextmanager
    def _raising_begin() -> Generator[MagicMock, None, None]:
        yield MagicMock()
        raise SaIntegrityError("duplicate key", {}, Exception())

    mock_factory = MagicMock()
    mock_factory.begin = _raising_begin
    return mock_factory


# ---------------------------------------------------------------------------
# _compute_lst tests
# ---------------------------------------------------------------------------


class TestComputeLst:
    def test_j2000_epoch_bucharest(self) -> None:
        """At J2000.0 and longitude=26.1°E, LST should be ≈ 20.437 hours."""
        ts = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = _compute_lst(ts, longitude_deg=26.1)
        assert abs(result - 20.437) < 0.01, f"Expected ≈20.437, got {result}"

    def test_result_in_valid_range(self) -> None:
        """LST must always be in [0, 24)."""
        ts = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)
        result = _compute_lst(ts, longitude_deg=26.1)
        assert 0.0 <= result < 24.0


# ---------------------------------------------------------------------------
# FingerprintService.attach() — status / notes logic
# ---------------------------------------------------------------------------


class TestFingerprintServiceAttach:
    def test_happy_path_ok_status(self) -> None:
        """Both metrics succeed → retrieval_status='ok', notes=None."""
        record = _make_record()
        mock_factory, written = _make_mock_session_factory()
        ts = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        FingerprintService.attach(
            record, ts, FakeEnvDataClient(kp=3.0, solar_wind=450.0), mock_factory
        )

        assert len(written) == 1
        fp = written[0]
        assert fp.retrieval_status == "ok"
        assert fp.kp_index == 3.0
        assert fp.solar_wind_speed == 450.0
        assert fp.retrieval_notes is None

    def test_partial_wind_fails(self) -> None:
        """Kp succeeds, wind fails → retrieval_status='partial', notes includes solar_wind_speed."""
        record = _make_record()
        mock_factory, written = _make_mock_session_factory()
        ts = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        FingerprintService.attach(
            record, ts, FakeEnvDataClient(kp=3.0, raise_on_wind=True), mock_factory
        )

        assert len(written) == 1
        fp = written[0]
        assert fp.retrieval_status == "partial"
        assert fp.kp_index == 3.0
        assert fp.solar_wind_speed is None
        assert fp.retrieval_notes == "solar_wind_speed:failed"

    def test_partial_kp_fails(self) -> None:
        """Wind succeeds, Kp fails → retrieval_status='partial', notes includes kp_index."""
        record = _make_record()
        mock_factory, written = _make_mock_session_factory()
        ts = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        FingerprintService.attach(
            record,
            ts,
            FakeEnvDataClient(solar_wind=450.0, raise_on_kp=True),
            mock_factory,
        )

        assert len(written) == 1
        fp = written[0]
        assert fp.retrieval_status == "partial"
        assert fp.kp_index is None
        assert fp.solar_wind_speed == 450.0
        assert fp.retrieval_notes == "kp_index:failed"

    def test_full_failure_failed_status(self) -> None:
        """Both metrics fail → retrieval_status='failed', notes lists both."""
        record = _make_record()
        mock_factory, written = _make_mock_session_factory()
        ts = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        FingerprintService.attach(
            record,
            ts,
            FakeEnvDataClient(raise_on_kp=True, raise_on_wind=True),
            mock_factory,
        )

        assert len(written) == 1
        fp = written[0]
        assert fp.retrieval_status == "failed"
        assert fp.kp_index is None
        assert fp.solar_wind_speed is None
        assert fp.retrieval_notes == "kp_index:failed, solar_wind_speed:failed"

    def test_lst_populated_even_when_both_apis_fail(self) -> None:
        """LST is computed locally — must be set even when both external APIs fail."""
        record = _make_record()
        mock_factory, written = _make_mock_session_factory()
        ts = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)

        FingerprintService.attach(
            record,
            ts,
            FakeEnvDataClient(raise_on_kp=True, raise_on_wind=True),
            mock_factory,
        )

        assert len(written) == 1
        fp = written[0]
        assert fp.local_sidereal_time is not None
        assert 0.0 <= fp.local_sidereal_time < 24.0

    def test_measurement_timestamp_stored(self) -> None:
        """measurement_timestamp from extraction result is stored on the fingerprint."""
        record = _make_record()
        mock_factory, written = _make_mock_session_factory()
        ts = datetime(2026, 6, 6, 10, 30, 0, tzinfo=UTC)

        FingerprintService.attach(record, ts, FakeEnvDataClient(), mock_factory)

        assert len(written) == 1
        assert written[0].measurement_timestamp == ts

    def test_fallback_when_measurement_timestamp_none(self) -> None:
        """When measurement_timestamp=None, fingerprinted_at is set and no crash."""
        received = datetime(2026, 6, 6, 9, 0, 0, tzinfo=UTC)
        record = _make_record(received_at=received)
        mock_factory, written = _make_mock_session_factory()

        FingerprintService.attach(record, None, FakeEnvDataClient(), mock_factory)

        assert len(written) == 1
        fp = written[0]
        assert fp.fingerprinted_at is not None
        # Falls back to record.received_at
        assert fp.measurement_timestamp == received

    def test_fail_operational_db_raises(self) -> None:
        """attach() must not propagate when session_factory raises unexpectedly."""
        record = _make_record()
        bad_factory = MagicMock()
        bad_factory.begin.side_effect = RuntimeError("Catastrophic DB failure")

        # Must NOT raise
        FingerprintService.attach(record, None, FakeEnvDataClient(), bad_factory)

    def test_idempotency_integrity_error_swallowed(self) -> None:
        """Second attach() on same record raises IntegrityError at commit — swallowed silently."""
        record = _make_record()
        mock_factory = _make_integrity_error_factory()

        # Must NOT raise
        FingerprintService.attach(record, None, FakeEnvDataClient(), mock_factory)

    def test_fallback_to_datetime_now_when_both_timestamps_none(self) -> None:
        """When measurement_timestamp and received_at are both None, falls back to datetime.now(UTC)."""
        record = _make_record(received_at=None)
        mock_factory, written = _make_mock_session_factory()

        before = datetime.now(UTC)
        FingerprintService.attach(record, None, FakeEnvDataClient(), mock_factory)
        after = datetime.now(UTC)

        assert len(written) == 1
        fp = written[0]
        assert fp.fingerprinted_at is not None
        assert before <= fp.measurement_timestamp <= after
