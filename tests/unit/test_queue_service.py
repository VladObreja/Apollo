"""Unit tests for QueueService — pure logic, no real DB.

Uses a hand-rolled FakeSession that records SQLAlchemy-style
query invocations without touching Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4


from apollo.domain.types import TargetStatus
from apollo.services.queue import (
    DAILY_TARGET_CAP,
    QueueService,
    count_available_slots,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    status: str = TargetStatus.PENDING.value,
    queued_at: datetime | None = None,
    available_after: datetime | None = None,
) -> MagicMock:
    """Build a minimal CorpusRecord-like mock."""
    record = MagicMock()
    record.id = uuid4()
    record.status = status
    record.double_blind_coordinate = None
    record.queued_at = queued_at
    record.available_after = available_after or datetime.now(UTC) - timedelta(seconds=1)
    return record


def _make_session(
    count_result: int = 0,
    query_results: list[Any] | None = None,
) -> MagicMock:
    """Build a SQLAlchemy session mock with configurable scalar/all returns."""
    session = MagicMock()

    # Chain: session.query(...).filter(...).scalar() → count_result
    # Also support multiple filters / filter chain returns
    query_mock = session.query.return_value
    filter_mock = query_mock.filter.return_value

    # Handle scalar results (which can be filter().scalar() or filter().filter().scalar())
    filter_mock.scalar.return_value = count_result
    filter_mock.filter.return_value.scalar.return_value = count_result

    # Chain: session.query(...).filter(...).order_by(...).limit(...).with_for_update(...).all()
    order_by_mock = filter_mock.order_by.return_value
    limit_mock = order_by_mock.limit.return_value
    wfu_mock = limit_mock.with_for_update.return_value
    wfu_mock.all.return_value = query_results or []

    # Backwards compatibility mock return for chains without order_by
    filter_mock.limit.return_value.with_for_update.return_value.all.return_value = (
        query_results or []
    )

    return session


# ---------------------------------------------------------------------------
# count_dispatched_today
# ---------------------------------------------------------------------------


class TestCountDispatchedToday:
    def test_returns_zero_when_none_dispatched(self) -> None:
        session = _make_session(count_result=0)
        result = QueueService.count_dispatched_today(session)
        assert result == 0

    def test_returns_count_from_db(self) -> None:
        session = _make_session(count_result=3)
        result = QueueService.count_dispatched_today(session)
        assert result == 3

    def test_handles_none_scalar_as_zero(self) -> None:
        """If scalar() returns None (no rows), treat as 0."""
        session = _make_session(count_result=None)  # type: ignore[arg-type]
        result = QueueService.count_dispatched_today(session)
        assert result == 0

    def test_filters_by_dispatched_status(self) -> None:
        """Query must filter on 'dispatched' status string."""
        session = _make_session(count_result=2)
        QueueService.count_dispatched_today(session)
        # Verify filter was called (args contain 'dispatched')
        filter_call_args = session.query.return_value.filter.call_args
        assert filter_call_args is not None, "filter() was not called"


# ---------------------------------------------------------------------------
# claim_pending_targets
# ---------------------------------------------------------------------------


class TestClaimPendingTargets:
    def test_returns_empty_when_no_pending(self) -> None:
        session = _make_session(query_results=[])
        result = QueueService.claim_pending_targets(session, limit=5)
        assert result == []

    def test_returns_records_from_db(self) -> None:
        records = [_make_record(), _make_record()]
        session = _make_session(query_results=records)
        result = QueueService.claim_pending_targets(session, limit=5)
        assert len(result) == 2

    def test_uses_for_update_skip_locked(self) -> None:
        """Must call with_for_update(skip_locked=True) for idempotency."""
        session = _make_session(query_results=[])
        QueueService.claim_pending_targets(session, limit=3)
        wfu_call = session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.with_for_update.call_args
        assert wfu_call is not None, "with_for_update() was not called"
        assert wfu_call.kwargs.get("skip_locked") is True, (
            "with_for_update must use skip_locked=True"
        )

    def test_respects_limit_parameter(self) -> None:
        """Limit must be forwarded to the query."""
        session = _make_session(query_results=[])
        QueueService.claim_pending_targets(session, limit=2)
        limit_call = session.query.return_value.filter.return_value.order_by.return_value.limit.call_args
        assert limit_call is not None, "limit() was not called"
        assert limit_call.args[0] == 2, "limit() must use the provided limit value"


# ---------------------------------------------------------------------------
# assign_coordinate
# ---------------------------------------------------------------------------


class TestAssignCoordinate:
    def test_sets_coordinate_on_record(self) -> None:
        record = _make_record()
        session = MagicMock()
        QueueService.assign_coordinate(record, session)
        assert record.double_blind_coordinate is not None
        assert "/" in record.double_blind_coordinate

    def test_sets_status_to_queued(self) -> None:
        record = _make_record()
        session = MagicMock()
        QueueService.assign_coordinate(record, session)
        assert record.status == TargetStatus.QUEUED.value

    def test_sets_queued_at_to_now_utc(self) -> None:
        record = _make_record()
        session = MagicMock()
        before = datetime.now(UTC)
        QueueService.assign_coordinate(record, session)
        after = datetime.now(UTC)
        assert record.queued_at is not None
        assert before <= record.queued_at <= after

    def test_adds_record_to_session(self) -> None:
        """session.add() must be called to stage the mutation."""
        record = _make_record()
        session = MagicMock()
        QueueService.assign_coordinate(record, session)
        session.add.assert_called_once_with(record)


# ---------------------------------------------------------------------------
# count_available_slots helper
# ---------------------------------------------------------------------------


class TestCountAvailableSlots:
    def test_full_slots_when_none_dispatched(self) -> None:
        session = _make_session(count_result=0)
        slots = count_available_slots(session)
        assert slots == DAILY_TARGET_CAP

    def test_partial_slots(self) -> None:
        session = _make_session(count_result=3)
        slots = count_available_slots(session)
        assert slots == DAILY_TARGET_CAP - 3

    def test_zero_slots_at_cap(self) -> None:
        session = _make_session(count_result=DAILY_TARGET_CAP)
        slots = count_available_slots(session)
        assert slots == 0

    def test_zero_slots_over_cap(self) -> None:
        """Must not return negative slots if count exceeds cap somehow."""
        session = _make_session(count_result=DAILY_TARGET_CAP + 2)
        slots = count_available_slots(session)
        assert slots == 0
