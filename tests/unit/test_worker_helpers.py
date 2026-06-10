"""Unit tests for worker.py pure helper functions — no DB, no IO."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError as SaIntegrityError

from apollo.services.worker import (
    _CONCURRENT_SEAL_CONSTRAINT,
    _is_concurrent_seal_collision,
)


class _FakeDiag:
    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name


class _FakeOrig(Exception):
    def __init__(self, constraint_name: str | None) -> None:
        super().__init__("duplicate key")
        self.diag = _FakeDiag(constraint_name)


def _make_integrity_error(orig: BaseException) -> SaIntegrityError:
    return SaIntegrityError("duplicate key", {}, orig)


class TestIsConcurrentSealCollision:
    def test_matching_constraint_is_concurrent_seal(self) -> None:
        exc = _make_integrity_error(_FakeOrig(_CONCURRENT_SEAL_CONSTRAINT))

        assert _is_concurrent_seal_collision(exc) is True

    def test_other_constraint_is_not_concurrent_seal(self) -> None:
        exc = _make_integrity_error(_FakeOrig("some_other_constraint"))

        assert _is_concurrent_seal_collision(exc) is False

    def test_orig_without_diag_attribute_does_not_crash(self) -> None:
        """`.orig` may be a plain Exception with no `.diag` (e.g. test mocks)."""
        exc = _make_integrity_error(Exception("plain"))

        assert _is_concurrent_seal_collision(exc) is False

    def test_orig_none_does_not_crash(self) -> None:
        exc = SaIntegrityError("duplicate key", {}, None)  # type: ignore[arg-type]

        assert _is_concurrent_seal_collision(exc) is False
