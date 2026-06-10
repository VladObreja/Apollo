"""Unit tests for ValidationService (Story 3.1).

Pure domain logic tests — NO database, NO real network calls.
Uses mock sessionmaker to test DB interaction paths.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError as SaIntegrityError

from apollo.services.validate import (
    OHLCVResult,
    ValidationService,
    _day_unix_range,
)
from tests.utils import FakeMarketDataClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    ticker: str | None = "GC=F",
    expiry_at: datetime | None = None,
    threshold_pct: float | None = 9.0,
    threshold_direction: str | None = "UP",
    status: str = "sealed",
    param_value: float = 85.0,
) -> MagicMock:
    record = MagicMock()
    record.id = uuid4()
    record.ticker = ticker
    record.expiry_at = expiry_at or datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
    record.threshold_pct = threshold_pct
    record.threshold_direction = threshold_direction
    record.status = status
    record.extraction_payload = {
        "param_value": param_value,
        "measurement_timestamp": None,
    }
    return record


def _make_ohlcv(
    open_price: float = 3000.0,
    close_price: float = 3300.0,
    fetch_offset_hours: float = 0.5,
    expiry_at: datetime | None = None,
) -> OHLCVResult:
    base = expiry_at or datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
    return OHLCVResult(
        open=open_price,
        close=close_price,
        high=max(open_price, close_price),
        low=min(open_price, close_price),
        fetch_timestamp=base + timedelta(hours=fetch_offset_hours),
    )


def _make_mock_session_factory(
    raises: type[Exception] | None = None,
) -> tuple[MagicMock, list]:
    written: list = []
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


class _FakeDiag:
    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name


class _FakeOrig(Exception):
    def __init__(self, constraint_name: str | None) -> None:
        super().__init__("duplicate key")
        self.diag = _FakeDiag(constraint_name)


def _make_integrity_error_factory(
    constraint_name: str = "validation_record_corpus_record_id_key",
) -> MagicMock:
    @contextmanager
    def _raising_begin():  # type: ignore[no-untyped-def]
        yield MagicMock()
        raise SaIntegrityError("duplicate key", {}, _FakeOrig(constraint_name))

    mock_factory = MagicMock()
    mock_factory.begin = _raising_begin
    return mock_factory


# ---------------------------------------------------------------------------
# _day_unix_range tests
# ---------------------------------------------------------------------------


class TestDayUnixRange:
    def test_known_day(self) -> None:
        """datetime(2026,6,10,21,0,0,UTC) → day start = 2026-06-10 00:00 UTC."""
        import calendar

        dt = datetime(2026, 6, 10, 21, 0, 0, tzinfo=UTC)
        p1, p2 = _day_unix_range(dt)
        expected_p1 = int(calendar.timegm((2026, 6, 10, 0, 0, 0, 0, 0, 0)))
        expected_p2 = int(calendar.timegm((2026, 6, 11, 0, 0, 0, 0, 0, 0)))
        assert p1 == expected_p1
        assert p2 == expected_p2

    def test_p2_is_p1_plus_one_day(self) -> None:
        dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1, p2 = _day_unix_range(dt)
        assert p2 - p1 == 86400


# ---------------------------------------------------------------------------
# ValidationService._validate_one tests
# ---------------------------------------------------------------------------


class TestValidateOne:
    def test_happy_path_hit(self) -> None:
        """Gold +10%, threshold 9% UP, param_value=85 → hit, predicted_positive=True, actual_positive=True."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(
            ticker="GC=F",
            expiry_at=expiry,
            threshold_pct=9.0,
            threshold_direction="UP",
            param_value=85.0,
        )
        ohlcv = _make_ohlcv(3000.0, 3300.0, expiry_at=expiry)
        client = FakeMarketDataClient({"GC=F": ohlcv})
        mock_factory, written = _make_mock_session_factory()

        ValidationService._validate_one(record, datetime.now(UTC), client, mock_factory)

        assert len(written) == 1
        vr = written[0]
        assert vr.validation_status == "hit"
        assert vr.predicted_positive is True
        assert vr.actual_positive is True
        assert abs(vr.actual_change_pct - 10.0) < 0.01

    def test_miss(self) -> None:
        """param_value=20 → predicted_positive=False, actual_positive=True → miss."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(
            ticker="GC=F",
            expiry_at=expiry,
            threshold_pct=9.0,
            threshold_direction="UP",
            param_value=20.0,
        )
        ohlcv = _make_ohlcv(3000.0, 3300.0, expiry_at=expiry)
        client = FakeMarketDataClient({"GC=F": ohlcv})
        mock_factory, written = _make_mock_session_factory()

        ValidationService._validate_one(record, datetime.now(UTC), client, mock_factory)

        assert len(written) == 1
        vr = written[0]
        assert vr.validation_status == "miss"
        assert vr.predicted_positive is False
        assert vr.actual_positive is True

    def test_offset_when_fetched_late(self) -> None:
        """fetch_timestamp > expiry_at + 2h → validation_status='offset'."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(ticker="GC=F", expiry_at=expiry, param_value=85.0)
        ohlcv = _make_ohlcv(3000.0, 3300.0, fetch_offset_hours=3.0, expiry_at=expiry)
        client = FakeMarketDataClient({"GC=F": ohlcv})
        mock_factory, written = _make_mock_session_factory()

        ValidationService._validate_one(record, datetime.now(UTC), client, mock_factory)

        assert len(written) == 1
        assert written[0].validation_status == "offset"

    def test_down_direction(self) -> None:
        """DOWN direction: close=2700, open=3000 → actual_change_pct=-10, actual_positive=True (falls ≥ 9%)."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(
            ticker="GC=F",
            expiry_at=expiry,
            threshold_pct=9.0,
            threshold_direction="DOWN",
            param_value=85.0,
        )
        ohlcv = _make_ohlcv(3000.0, 2700.0, expiry_at=expiry)
        client = FakeMarketDataClient({"GC=F": ohlcv})
        mock_factory, written = _make_mock_session_factory()

        ValidationService._validate_one(record, datetime.now(UTC), client, mock_factory)

        assert len(written) == 1
        vr = written[0]
        assert abs(vr.actual_change_pct - (-10.0)) < 0.01
        assert vr.actual_positive is True
        assert vr.validation_status == "hit"

    def test_idempotency_integrity_error_swallowed(self) -> None:
        """Second call raises IntegrityError at commit — silently swallowed, no exception."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(ticker="GC=F", expiry_at=expiry)
        ohlcv = _make_ohlcv(expiry_at=expiry)
        client = FakeMarketDataClient({"GC=F": ohlcv})
        mock_factory = _make_integrity_error_factory()

        # Must NOT raise
        ValidationService._validate_one(record, datetime.now(UTC), client, mock_factory)

    def test_unexpected_integrity_error_propagates(self) -> None:
        """An IntegrityError on a different constraint must NOT be swallowed as 'already validated'."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(ticker="GC=F", expiry_at=expiry)
        ohlcv = _make_ohlcv(expiry_at=expiry)
        client = FakeMarketDataClient({"GC=F": ohlcv})
        mock_factory = _make_integrity_error_factory(
            constraint_name="some_other_constraint"
        )

        with pytest.raises(SaIntegrityError):
            ValidationService._validate_one(
                record, datetime.now(UTC), client, mock_factory
            )

    def test_market_data_error_propagates(self) -> None:
        """MarketDataError from client must propagate to caller (caught in validate_pending)."""
        from apollo.domain.exceptions import MarketDataError

        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(ticker="GC=F", expiry_at=expiry)
        client = FakeMarketDataClient(raise_always=True)
        mock_factory, _ = _make_mock_session_factory()

        with pytest.raises(MarketDataError):
            ValidationService._validate_one(
                record, datetime.now(UTC), client, mock_factory
            )


# ---------------------------------------------------------------------------
# ValidationService.validate_pending tests (with mock session)
# ---------------------------------------------------------------------------


class TestValidatePending:
    def _make_session_with_records(self, records: list) -> MagicMock:
        """Build a mock session_factory() that returns `records` from scalars().all()."""
        scalars = MagicMock()
        scalars.all = MagicMock(return_value=records)
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=scalars)
        session = MagicMock()
        session.__enter__ = lambda s: s
        session.__exit__ = MagicMock(return_value=False)
        session.execute = MagicMock(return_value=execute_result)

        mock_factory = MagicMock()
        mock_factory.return_value = session
        # Also need begin() for _validate_one writes
        mock_write_session = MagicMock()
        mock_write_session.__enter__ = lambda s: s
        mock_write_session.__exit__ = MagicMock(return_value=False)
        mock_write_session.add = MagicMock()
        mock_factory.begin.return_value = mock_write_session
        return mock_factory

    def test_outage_returns_skipped(self) -> None:
        """FakeMarketDataClient(raise_always=True) → (0, 1), no exception."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(ticker="GC=F", expiry_at=expiry)
        mock_factory = self._make_session_with_records([record])
        client = FakeMarketDataClient(raise_always=True)

        validated, skipped = ValidationService.validate_pending(mock_factory, client)

        assert validated == 0
        assert skipped == 1

    def test_success_returns_validated(self) -> None:
        """One eligible record, fetch succeeds → (1, 0)."""
        expiry = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)
        record = _make_record(ticker="GC=F", expiry_at=expiry)
        mock_factory = self._make_session_with_records([record])
        client = FakeMarketDataClient({"GC=F": _make_ohlcv(expiry_at=expiry)})

        validated, skipped = ValidationService.validate_pending(mock_factory, client)

        assert validated == 1
        assert skipped == 0

    def test_no_records_returns_zeros(self) -> None:
        """Empty eligible list → (0, 0)."""
        mock_factory = self._make_session_with_records([])
        client = FakeMarketDataClient()

        validated, skipped = ValidationService.validate_pending(mock_factory, client)

        assert validated == 0
        assert skipped == 0
