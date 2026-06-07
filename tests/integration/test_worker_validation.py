"""Integration tests for worker Phase 4 — ground-truth market validation (Story 3.1).

Tests the full validation cycle using:
  - testcontainers PostgreSQL (isolated, migrated) via shared conftest fixtures
  - FakeMarketDataClient with configurable OHLCV responses
  - CorpusRecordFactory to seed sealed records with ticker/expiry_at

Verifies:
  - Sealed record past expiry with ticker → validation_record created
  - Market data outage → no validation_record, corpus_record stays sealed, tick does not raise
  - Record without ticker → Phase 4 skips it
  - Record with future expiry_at → Phase 4 skips it
  - Offset status when fetch is >2h after expiry
  - Idempotency: calling tick twice → only one validation_record row
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from apollo.db.models import CorpusRecord, ValidationRecord
from apollo.services.validate import OHLCVResult
from tests.factories import CorpusRecordFactory
from tests.utils import (
    FakeEnvDataClient,
    FakeIMAPClient,
    FakeLLM,
    FakeMarketDataClient,
    FakeSMTPClient,
)

EXPIRY_PAST = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_sealed(
    db_session,  # type: ignore[no-untyped-def]
    ticker: str | None = "GC=F",
    expiry_at: datetime | None = None,
    threshold_pct: float | None = 9.0,
    threshold_direction: str | None = "UP",
    param_value: float = 85.0,
) -> CorpusRecord:
    record = CorpusRecordFactory(
        status="sealed",
        ticker=ticker,
        expiry_at=expiry_at if expiry_at is not None else EXPIRY_PAST,
        threshold_pct=threshold_pct,
        threshold_direction=threshold_direction,
        extraction_payload={"param_value": param_value, "measurement_timestamp": None},
        raw_hash="a" * 64,
        sealed_at=datetime.now(UTC) - timedelta(hours=1),
        seal_agent_version="0.1.0",
        double_blind_coordinate="AAAA/BBBB",
        dispatched_at=datetime.now(UTC) - timedelta(hours=2),
        dispatch_agent_version="0.1.0",
    )
    db_session.flush()
    return record  # type: ignore[return-value]


def _gold_ohlcv(
    open_price: float = 3000.0,
    close_price: float = 3300.0,
    fetch_offset_hours: float = 0.5,
) -> OHLCVResult:
    return OHLCVResult(
        open=open_price,
        close=close_price,
        high=max(open_price, close_price),
        low=min(open_price, close_price),
        fetch_timestamp=EXPIRY_PAST + timedelta(hours=fetch_offset_hours),
    )


def _tick(market_client=None, **kwargs):  # type: ignore[no-untyped-def]
    from apollo.services.worker import tick

    tick(
        smtp_client=FakeSMTPClient(),
        llm_client=FakeLLM([]),
        imap_client=FakeIMAPClient([]),
        env_client=FakeEnvDataClient(),
        market_client=market_client or FakeMarketDataClient(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerValidationIntegration:
    def test_validation_hit_created(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Sealed record with ticker + past expiry → validation_record created with status='hit'."""
        record = _seed_sealed(db_session, ticker="GC=F", param_value=85.0)
        client = FakeMarketDataClient({"GC=F": _gold_ohlcv(3000.0, 3300.0)})

        _tick(market_client=client)
        db_session.expire_all()

        vr = db_session.execute(
            select(ValidationRecord).where(
                ValidationRecord.corpus_record_id == record.id
            )
        ).scalar_one()
        assert vr.validation_status == "hit"
        assert abs(vr.actual_change_pct - 10.0) < 0.01
        assert vr.predicted_positive is True
        assert vr.actual_positive is True
        assert vr.fetch_delay_seconds is not None
        assert vr.fetch_delay_seconds >= 0

    def test_validation_miss_created(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """param_value=20 (predicted negative) + actual rise > 9% → miss."""
        record = _seed_sealed(db_session, ticker="GC=F", param_value=20.0)
        client = FakeMarketDataClient({"GC=F": _gold_ohlcv(3000.0, 3300.0)})

        _tick(market_client=client)
        db_session.expire_all()

        vr = db_session.execute(
            select(ValidationRecord).where(
                ValidationRecord.corpus_record_id == record.id
            )
        ).scalar_one()
        assert vr.validation_status == "miss"
        assert vr.predicted_positive is False
        assert vr.actual_positive is True

    def test_market_data_outage_no_validation_record(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """FakeMarketDataClient(raise_always=True) → no validation_record, corpus_record still sealed, tick does not raise."""
        record = _seed_sealed(db_session, ticker="GC=F")
        client = FakeMarketDataClient(raise_always=True)

        _tick(market_client=client)  # Must NOT raise
        db_session.expire_all()

        # No validation_record must be created
        vr = db_session.execute(
            select(ValidationRecord).where(
                ValidationRecord.corpus_record_id == record.id
            )
        ).scalar_one_or_none()
        assert vr is None

        # Corpus record must remain sealed
        fresh = db_session.get(CorpusRecord, record.id)
        assert fresh is not None
        assert fresh.status == "sealed"

    def test_record_without_ticker_skipped(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Sealed record without ticker → Phase 4 skips it (no validation_record)."""
        record = _seed_sealed(db_session, ticker=None)

        _tick(market_client=FakeMarketDataClient())
        db_session.expire_all()

        vr = db_session.execute(
            select(ValidationRecord).where(
                ValidationRecord.corpus_record_id == record.id
            )
        ).scalar_one_or_none()
        assert vr is None

    def test_record_with_future_expiry_skipped(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Sealed record with expiry_at in the future → Phase 4 skips it."""
        future_expiry = datetime.now(UTC) + timedelta(hours=1)
        record = _seed_sealed(db_session, expiry_at=future_expiry)

        _tick(market_client=FakeMarketDataClient({"GC=F": _gold_ohlcv()}))
        db_session.expire_all()

        vr = db_session.execute(
            select(ValidationRecord).where(
                ValidationRecord.corpus_record_id == record.id
            )
        ).scalar_one_or_none()
        assert vr is None

    def test_offset_status_when_fetch_late(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """fetch_timestamp > expiry_at + 2h → validation_status='offset'."""
        record = _seed_sealed(db_session, ticker="GC=F", param_value=85.0)
        late_ohlcv = _gold_ohlcv(fetch_offset_hours=3.0)
        client = FakeMarketDataClient({"GC=F": late_ohlcv})

        _tick(market_client=client)
        db_session.expire_all()

        vr = db_session.execute(
            select(ValidationRecord).where(
                ValidationRecord.corpus_record_id == record.id
            )
        ).scalar_one()
        assert vr.validation_status == "offset"
        assert vr.fetch_delay_seconds > 7200

    def test_idempotency_second_tick_no_duplicate(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """Calling tick() twice → only one validation_record (UNIQUE constraint idempotency)."""
        record = _seed_sealed(db_session, ticker="GC=F")
        client = FakeMarketDataClient({"GC=F": _gold_ohlcv()})

        _tick(market_client=client)
        _tick(market_client=client)  # Second call — must not raise or duplicate
        db_session.expire_all()

        count = (
            db_session.execute(
                select(ValidationRecord).where(
                    ValidationRecord.corpus_record_id == record.id
                )
            )
            .scalars()
            .all()
        )
        assert len(count) == 1, "Only one validation_record must exist after two ticks"

    def test_corpus_record_not_mutated_after_validation(
        self,
        db_session,
        patched_db_url,  # type: ignore[no-untyped-def]
    ) -> None:
        """After validation, corpus_record.status must still be 'sealed' (immutability preserved)."""
        record = _seed_sealed(db_session, ticker="GC=F")
        client = FakeMarketDataClient({"GC=F": _gold_ohlcv()})

        _tick(market_client=client)
        db_session.expire_all()

        fresh = db_session.get(CorpusRecord, record.id)
        assert fresh is not None
        assert fresh.status == "sealed"
