"""Unit tests for worker.py pure helper functions — no DB, no IO."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError as SaIntegrityError

from apollo.services.worker import (
    _CONCURRENT_SEAL_CONSTRAINT,
    _extract_measurement_timestamp,
    _is_concurrent_seal_collision,
)
from tests.utils import FakeOrig


def _make_integrity_error(orig: BaseException) -> SaIntegrityError:
    return SaIntegrityError("duplicate key", {}, orig)


class TestIsConcurrentSealCollision:
    def test_matching_constraint_is_concurrent_seal(self) -> None:
        exc = _make_integrity_error(FakeOrig(_CONCURRENT_SEAL_CONSTRAINT))

        assert _is_concurrent_seal_collision(exc) is True

    def test_other_constraint_is_not_concurrent_seal(self) -> None:
        exc = _make_integrity_error(FakeOrig("some_other_constraint"))

        assert _is_concurrent_seal_collision(exc) is False

    def test_orig_without_diag_attribute_does_not_crash(self) -> None:
        """`.orig` may be a plain Exception with no `.diag` (e.g. test mocks)."""
        exc = _make_integrity_error(Exception("plain"))

        assert _is_concurrent_seal_collision(exc) is False

    def test_orig_none_does_not_crash(self) -> None:
        exc = SaIntegrityError("duplicate key", {}, None)  # type: ignore[arg-type]

        assert _is_concurrent_seal_collision(exc) is False


class TestExtractMeasurementTimestamp:
    def test_none_payload_returns_none(self) -> None:
        assert _extract_measurement_timestamp(None) is None

    def test_missing_key_returns_none(self) -> None:
        assert _extract_measurement_timestamp({"param_value": 50.0}) is None

    def test_null_value_returns_none(self) -> None:
        assert (
            _extract_measurement_timestamp(
                {"param_value": 50.0, "measurement_timestamp": None}
            )
            is None
        )

    def test_z_suffixed_string_parsed(self) -> None:
        result = _extract_measurement_timestamp(
            {"measurement_timestamp": "2026-06-06T10:00:00Z"}
        )
        assert result == datetime(2026, 6, 6, 10, 0, tzinfo=UTC)

    def test_offset_string_parsed(self) -> None:
        result = _extract_measurement_timestamp(
            {"measurement_timestamp": "2026-06-06T10:00:00+00:00"}
        )
        assert result == datetime(2026, 6, 6, 10, 0, tzinfo=UTC)
