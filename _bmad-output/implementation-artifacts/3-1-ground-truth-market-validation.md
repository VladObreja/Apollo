---
baseline_commit: aa909c8cc9df66a652143b93ea4be47e8857e3ee
---

# Story 3.1: Ground-Truth Market Validation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the Calibration Engine,
I want to autonomously check the actual market outcome at the precise expiry time,
So that I can validate the Asset's sealed prediction against ground truth.

## Acceptance Criteria

1. **Given** a sealed corpus_record with `ticker`, `expiry_at`, `threshold_pct`, and `threshold_direction` set
   **When** `expiry_at <= NOW()` and no `validation_record` exists for this corpus_record
   **Then** a background Phase 4 in `tick()` queries for all such eligible records
   **And** for each record, fetches the OHLCV market data for the expiry day via the `MarketDataClient` Protocol
   **And** computes `actual_change_pct = (close - open) / open * 100` and compares it to `threshold_pct * direction`
   **And** inserts a new `validation_record` row with `validation_status = "hit"` or `"miss"` (never alters corpus_record)

2. **Given** market data is successfully fetched for an eligible sealed record
   **When** the `validation_record` is created
   **Then** it captures `actual_open`, `actual_close`, `actual_change_pct`, `predicted_positive` (param_value >= 50.0), `actual_positive`, and `fetch_delay_seconds` (how many seconds after expiry the data was fetched)
   **And** `validation_status = "offset"` if `fetch_delay_seconds > 7200` (2 hours), otherwise `"hit"` or `"miss"`

3. **Given** market data is temporarily unavailable (network error, weekend, holiday)
   **When** `MarketDataClient.fetch_ohlcv()` raises or returns `None`
   **Then** NO `validation_record` row is created for that corpus_record
   **And** the exception is caught and logged as `apollo.worker.tick: validation pending — market data unavailable`
   **And** `tick()` continues without crashing
   **And** the next tick automatically retries (because no validation_record exists yet)

4. **Given** a `configure_target` call with optional validation fields
   **When** `ticker`, `expiry_at`, `threshold_pct`, and `threshold_direction` are provided
   **Then** they are persisted to the four new nullable columns on `corpus_record`
   **And** corpus_records without these fields are silently skipped by Phase 4 (NOT a failure)

## Tasks / Subtasks

- [x] Add `Compartment.CALIBRATION_WRITE` to compartments (AC: 1, 2)
  - [x] In `src/apollo/domain/compartments.py`, add to `Compartment` enum:
    - `CALIBRATION_WRITE = "calibration_write"` (after `CALIBRATION_READ`)

- [x] Add `MarketDataError` to domain exceptions (AC: 3)
  - [x] In `src/apollo/domain/exceptions.py`, append:
    ```python
    class MarketDataError(Exception):
        """Raised when market data cannot be fetched or parsed for a validation record.

        Caught in ValidationService.validate_pending(). Never propagates to tick() caller.
        """
    ```

- [x] Extend `TargetConfiguration` domain model (AC: 4)
  - [x] In `src/apollo/domain/models.py`, add 4 optional fields to `TargetConfiguration` after `asset_financial_awareness`:
    ```python
    ticker: str | None = Field(
        default=None,
        description="Market symbol for ground-truth validation (e.g., 'GC=F' for Gold, 'EURUSD=X' for EUR/USD).",
    )
    expiry_at: datetime | None = Field(
        default=None,
        description="UTC datetime when the market outcome should be checked (e.g., market close time).",
    )
    threshold_pct: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Required percentage change for a positive outcome (e.g., 9.0 means 9%). "
            "Applied in the direction specified by threshold_direction."
        ),
    )
    threshold_direction: str | None = Field(
        default=None,
        description="Direction for a positive outcome: 'UP' (price rises ≥ threshold_pct) or 'DOWN' (price falls ≥ threshold_pct).",
    )
    ```

- [x] DB Schema: Add nullable validation columns to `corpus_record` and create `validation_record` table (AC: 1, 2, 4)
  - [x] Create `src/apollo/db/alembic/versions/c1d2e3f4a5b6_add_market_validation.py`
  - [x] Set `revision = "c1d2e3f4a5b6"` and `down_revision = "b5c6d7e8f9a0"` (chain from env_fingerprint)
  - [x] In `upgrade()`:
    - ADD nullable columns to `corpus_record`:
      ```python
      op.add_column("corpus_record", sa.Column("ticker", sa.String(), nullable=True))
      op.add_column("corpus_record", sa.Column("expiry_at", sa.DateTime(timezone=True), nullable=True))
      op.add_column("corpus_record", sa.Column("threshold_pct", sa.Float(), nullable=True))
      op.add_column("corpus_record", sa.Column("threshold_direction", sa.String(), nullable=True))
      ```
    - Create index: `op.create_index("ix_corpus_record_expiry_at", "corpus_record", ["expiry_at"])`
    - Create `validation_record` table:
      ```python
      op.create_table(
          "validation_record",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
          sa.Column("corpus_record_id", postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("corpus_record.id", ondelete="CASCADE"),
                    nullable=False, unique=True),
          sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("validation_status", sa.String(), nullable=False),  # "hit"|"miss"|"offset"
          sa.Column("param_value", sa.Float(), nullable=False),
          sa.Column("actual_open", sa.Float(), nullable=True),
          sa.Column("actual_close", sa.Float(), nullable=True),
          sa.Column("actual_change_pct", sa.Float(), nullable=True),
          sa.Column("threshold_pct_snapshot", sa.Float(), nullable=True),
          sa.Column("threshold_direction_snapshot", sa.String(), nullable=True),
          sa.Column("predicted_positive", sa.Boolean(), nullable=True),
          sa.Column("actual_positive", sa.Boolean(), nullable=True),
          sa.Column("fetch_delay_seconds", sa.Float(), nullable=True),
          sa.Column("validation_agent_version", sa.String(), nullable=True),
          sa.Column("fetch_error", sa.String(), nullable=True),
      )
      op.create_index("ix_validation_record_corpus_record_id", "validation_record", ["corpus_record_id"])
      ```
  - [x] In `downgrade()`:
    - Drop index and table: `op.drop_index("ix_validation_record_corpus_record_id", table_name="validation_record")` then `op.drop_table("validation_record")`
    - Drop index and columns: `op.drop_index("ix_corpus_record_expiry_at", table_name="corpus_record")` then `op.drop_column(...)` for all 4 new columns
  - [x] Imports: `import sqlalchemy as sa`, `from alembic import op`, `from sqlalchemy.dialects import postgresql`

- [x] ORM Model: Add new columns to `CorpusRecord` and add `ValidationRecord` to `db/models.py` (AC: 1, 2, 4)
  - [x] In `src/apollo/db/models.py`, add 4 new columns to `CorpusRecord` after `asset_financial_awareness`:
    ```python
    # Market validation columns (set at configure_target time, Story 3.1)
    ticker: MappedColumn[str | None] = mapped_column(String, nullable=True)
    expiry_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    threshold_pct: MappedColumn[float | None] = mapped_column(Float, nullable=True)
    threshold_direction: MappedColumn[str | None] = mapped_column(String, nullable=True)
    ```
  - [x] Add `ValidationRecord(Base)` class after `EnvFingerprint` (end of file):
    ```python
    class ValidationRecord(Base):
        """Ground-truth market outcome for a sealed corpus_record (Story 3.1).

        One-to-one with CorpusRecord via UNIQUE FK. Created by ValidationService.validate_pending().
        Never modifies corpus_record — purely a derived, append-only record.
        validation_status: 'hit' | 'miss' | 'offset' (fetched >2h past expiry)
        """

        __tablename__ = "validation_record"

        id: MappedColumn[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
        corpus_record_id: MappedColumn[UUID] = mapped_column(
            UUID(as_uuid=True), ForeignKey("corpus_record.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        )
        validated_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
        validation_status: MappedColumn[str] = mapped_column(String, nullable=False)
        param_value: MappedColumn[float] = mapped_column(Float, nullable=False)
        actual_open: MappedColumn[float | None] = mapped_column(Float, nullable=True)
        actual_close: MappedColumn[float | None] = mapped_column(Float, nullable=True)
        actual_change_pct: MappedColumn[float | None] = mapped_column(Float, nullable=True)
        threshold_pct_snapshot: MappedColumn[float | None] = mapped_column(Float, nullable=True)
        threshold_direction_snapshot: MappedColumn[str | None] = mapped_column(String, nullable=True)
        predicted_positive: MappedColumn[bool | None] = mapped_column(Boolean, nullable=True)
        actual_positive: MappedColumn[bool | None] = mapped_column(Boolean, nullable=True)
        fetch_delay_seconds: MappedColumn[float | None] = mapped_column(Float, nullable=True)
        validation_agent_version: MappedColumn[str | None] = mapped_column(String, nullable=True)
        fetch_error: MappedColumn[str | None] = mapped_column(String, nullable=True)
    ```
  - [x] Add `Boolean` to the existing `from sqlalchemy import ...` import line if not present (already present: check)
  - [x] Do NOT add any `relationship()` back-reference to `CorpusRecord`

- [x] `ValidationService` module (AC: 1, 2, 3)
  - [x] Create `src/apollo/services/validate.py`
  - [ ] Full import block:
    ```python
    from __future__ import annotations

    import calendar
    import json
    import logging
    import urllib.request
    from datetime import UTC, datetime, timedelta
    from typing import Protocol
    from uuid import uuid4

    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session, sessionmaker

    from apollo.db.models import CorpusRecord, ValidationRecord
    from apollo.domain.compartments import Compartment, requires
    from apollo.domain.exceptions import MarketDataError

    logger = logging.getLogger(__name__)

    VALIDATION_AGENT_VERSION = "0.1.0"
    OFFSET_THRESHOLD_SECONDS = 7200.0  # 2 hours
    POSITIVE_CONVICTION_THRESHOLD = 50.0  # VAD >= 50 = predicted positive (calibrated in Story 3.3)
    YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1d"
    ```
  - [x] Define `OHLCVResult` dataclass (stdlib only, no Pydantic needed for internal data):
    ```python
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class OHLCVResult:
        open: float
        close: float
        high: float
        low: float
        fetch_timestamp: datetime  # UTC time when data was fetched
    ```
  - [x] Define `MarketDataClient` Protocol:
    ```python
    class MarketDataClient(Protocol):
        def fetch_ohlcv(self, ticker: str, expiry_at: datetime) -> OHLCVResult:
            """Fetch OHLCV for the day containing expiry_at.

            Raises MarketDataError if data unavailable (weekend, holiday, network error).
            Never returns None — raise instead.
            """
            ...
    ```
  - [x] Implement `_day_unix_range(dt: datetime) -> tuple[int, int]` (pure function):
    ```python
    def _day_unix_range(dt: datetime) -> tuple[int, int]:
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        day_end = day_start + timedelta(days=1)
        return int(calendar.timegm(day_start.timetuple())), int(calendar.timegm(day_end.timetuple()))
    ```
  - [x] Implement `YahooFinanceClientImpl`:
    ```python
    class YahooFinanceClientImpl:
        def fetch_ohlcv(self, ticker: str, expiry_at: datetime) -> OHLCVResult:
            p1, p2 = _day_unix_range(expiry_at)
            url = YAHOO_CHART_URL.format(ticker=ticker, p1=p1, p2=p2)
            try:
                with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
                    raw = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                raise MarketDataError(f"HTTP fetch failed for {ticker}: {exc}") from exc

            try:
                result = raw["chart"]["result"]
                if not result:
                    raise MarketDataError(f"Yahoo Finance returned empty result for {ticker}")
                quote = result[0]["indicators"]["quote"][0]
                opens = [v for v in (quote.get("open") or []) if v is not None]
                closes = [v for v in (quote.get("close") or []) if v is not None]
                highs = [v for v in (quote.get("high") or []) if v is not None]
                lows = [v for v in (quote.get("low") or []) if v is not None]
                if not opens or not closes:
                    raise MarketDataError(f"No OHLCV data for {ticker} on {expiry_at.date()}")
                return OHLCVResult(
                    open=float(opens[0]),
                    close=float(closes[-1]),  # last close of the day
                    high=float(max(highs)),
                    low=float(min(lows)),
                    fetch_timestamp=datetime.now(UTC),
                )
            except MarketDataError:
                raise
            except Exception as exc:
                raise MarketDataError(f"Yahoo Finance response parse failed for {ticker}: {exc}") from exc
    ```
  - [x] Implement `ValidationService` static class:
    ```python
    class ValidationService:
        @staticmethod
        @requires(Compartment.CALIBRATION_WRITE)
        def validate_pending(
            session_factory: sessionmaker[Session],
            market_client: MarketDataClient,
            limit: int = 100,
        ) -> tuple[int, int]:
            """Find all sealed records past expiry with no validation record and process them.

            Returns: (validated_count, skipped_count)
            """
            from apollo.db.models import ValidationRecord

            now = datetime.now(UTC)
            validated = 0
            skipped = 0

            with session_factory() as session:
                eligible = ValidationService._fetch_eligible(session, now, limit)

            for record in eligible:
                try:
                    ValidationService._validate_one(record, now, market_client, session_factory)
                    validated += 1
                except MarketDataError as exc:
                    skipped += 1
                    logger.warning(
                        "apollo.worker.tick: validation pending — market data unavailable",
                        extra={"record_id": str(record.id), "ticker": record.ticker, "error": str(exc)},
                    )
                except Exception as exc:
                    skipped += 1
                    logger.error(
                        "apollo.worker.tick: validation crashed unexpectedly",
                        extra={"record_id": str(record.id), "error": str(exc)},
                    )

            return validated, skipped

        @staticmethod
        def _fetch_eligible(session: Session, now: datetime, limit: int) -> list[CorpusRecord]:
            """Query sealed records past expiry with no validation record."""
            from sqlalchemy import and_, not_, exists
            from apollo.db.models import ValidationRecord

            stmt = (
                select(CorpusRecord)
                .where(
                    and_(
                        CorpusRecord.status == "sealed",
                        CorpusRecord.expiry_at.is_not(None),
                        CorpusRecord.ticker.is_not(None),
                        CorpusRecord.expiry_at <= now,
                        not_(
                            exists().where(
                                ValidationRecord.corpus_record_id == CorpusRecord.id
                            )
                        ),
                    )
                )
                .order_by(CorpusRecord.expiry_at.asc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

        @staticmethod
        def _validate_one(
            record: CorpusRecord,
            now: datetime,
            market_client: MarketDataClient,
            session_factory: sessionmaker[Session],
        ) -> None:
            """Fetch market data and write validation_record. Raises MarketDataError on fetch failure."""
            assert record.expiry_at is not None  # guaranteed by _fetch_eligible query
            assert record.ticker is not None

            ohlcv = market_client.fetch_ohlcv(record.ticker, record.expiry_at)

            fetch_delay_seconds = (ohlcv.fetch_timestamp - record.expiry_at.astimezone(UTC)).total_seconds()
            actual_change_pct = (ohlcv.close - ohlcv.open) / ohlcv.open * 100.0

            direction = record.threshold_direction or "UP"
            threshold = record.threshold_pct or 0.0

            actual_positive: bool | None = None
            if record.threshold_pct is not None and record.threshold_direction is not None:
                if direction == "UP":
                    actual_positive = actual_change_pct >= threshold
                else:
                    actual_positive = actual_change_pct <= -threshold

            payload = record.extraction_payload or {}
            param_value = float(payload.get("param_value", 0.0))
            predicted_positive = param_value >= POSITIVE_CONVICTION_THRESHOLD

            if actual_positive is not None:
                if fetch_delay_seconds > OFFSET_THRESHOLD_SECONDS:
                    status = "offset"
                elif predicted_positive == actual_positive:
                    status = "hit"
                else:
                    status = "miss"
            else:
                status = "hit" if fetch_delay_seconds <= OFFSET_THRESHOLD_SECONDS else "offset"

            vr = ValidationRecord(
                id=uuid4(),
                corpus_record_id=record.id,
                validated_at=now,
                validation_status=status,
                param_value=param_value,
                actual_open=ohlcv.open,
                actual_close=ohlcv.close,
                actual_change_pct=actual_change_pct,
                threshold_pct_snapshot=record.threshold_pct,
                threshold_direction_snapshot=record.threshold_direction,
                predicted_positive=predicted_positive,
                actual_positive=actual_positive,
                fetch_delay_seconds=fetch_delay_seconds,
                validation_agent_version=VALIDATION_AGENT_VERSION,
                fetch_error=None,
            )

            try:
                with session_factory.begin() as write_session:
                    write_session.add(vr)
            except IntegrityError:
                logger.info(
                    "validate: already validated — idempotent skip",
                    extra={"record_id": str(record.id)},
                )
                return

            logger.info(
                "apollo.worker.tick: record validated",
                extra={
                    "record_id": str(record.id),
                    "ticker": record.ticker,
                    "validation_status": status,
                    "actual_change_pct": actual_change_pct,
                    "fetch_delay_seconds": fetch_delay_seconds,
                },
            )
    ```

- [x] Extend `TargetService` to persist new validation columns (AC: 4)
  - [x] In `src/apollo/services/target.py`, add 4 new fields to the `CorpusRecord(...)` constructor call inside `create_target_configuration`:
    ```python
    ticker=config.ticker,
    expiry_at=config.expiry_at,
    threshold_pct=config.threshold_pct,
    threshold_direction=config.threshold_direction,
    ```

- [x] Extend `configure_target` MCP tool (AC: 4)
  - [x] In `src/apollo/mcp/tools.py`, add 4 new optional params to `configure_target()`:
    ```python
    ticker: Optional[str] = None,
    expiry_at: Optional[str] = None,  # ISO-8601 UTC, e.g. "2026-06-10T21:00:00Z"
    threshold_pct: Optional[float] = None,
    threshold_direction: Optional[str] = None,  # "UP" or "DOWN"
    ```
  - [x] Add datetime parsing before building `TargetConfiguration`:
    ```python
    from datetime import datetime
    expiry_dt: datetime | None = None
    if expiry_at is not None:
        expiry_dt = datetime.fromisoformat(expiry_at.replace("Z", "+00:00"))
    ```
  - [x] Pass to `TargetConfiguration(...)`:
    ```python
    ticker=ticker,
    expiry_at=expiry_dt,
    threshold_pct=threshold_pct,
    threshold_direction=threshold_direction,
    ```
  - [x] Update the docstring to document the 4 new args

- [x] Worker Phase 4: add `market_client` param and validation phase to `tick()` (AC: 1, 2, 3)
  - [x] In `src/apollo/services/worker.py`, add import:
    ```python
    from apollo.services.validate import MarketDataClient, ValidationService, YahooFinanceClientImpl
    ```
  - [x] Add `market_client: MarketDataClient | None = None` as 5th param to `tick()`
  - [x] Add init block (after `if env_client is None:` block):
    ```python
    if market_client is None:
        market_client = YahooFinanceClientImpl()
    ```
  - [x] Update `tick()` docstring: add Phase 4 description:
    ```
    Phase 4 — Ground-Truth Validation (sealed, past expiry → validation_record):
        16. Query sealed records with ticker + expiry_at set, past expiry, no validation_record.
        17. Fetch OHLCV for each via MarketDataClient.
        18. Compute actual_change_pct; compare to threshold + direction.
        19. Write validation_record (new derived row, never alters corpus_record).
        20. If market data unavailable: log, skip, retry on next tick (no row = pending).
    ```
  - [x] Add Phase 4 block at the end of `tick()` (after existing Phase 3 logging):
    ```python
    # ------------------------------------------------------------------
    # Phase 4: ground-truth validation (sealed, past expiry → validation_record)
    # ------------------------------------------------------------------
    validated_count, skipped_count = ValidationService.validate_pending(
        SessionFactory, market_client
    )
    if validated_count > 0 or skipped_count > 0:
        logger.info(
            "apollo.worker.tick: validation phase complete",
            extra={"validated": validated_count, "skipped": skipped_count},
        )
    ```
  - [x] Add `market_client` to the `Args:` docstring in `tick()`

- [x] `FakeMarketDataClient` in `tests/utils.py` (AC: 1, 2, 3)
  - [x] Add import at top of `tests/utils.py`: `from apollo.services.validate import MarketDataError, OHLCVResult`
  - [x] Add `FakeMarketDataClient` class after `FakeEnvDataClient`:
    ```python
    class FakeMarketDataClient:
        """Returns canned OHLCVResult per ticker for validation tests.

        If ticker not in responses, raises MarketDataError.
        Set raise_always=True to always raise (simulates outage).
        """

        def __init__(
            self,
            responses: dict[str, OHLCVResult] | None = None,
            raise_always: bool = False,
        ) -> None:
            self._responses: dict[str, OHLCVResult] = responses or {}
            self._raise_always = raise_always

        def fetch_ohlcv(self, ticker: str, expiry_at: datetime) -> OHLCVResult:
            if self._raise_always:
                raise MarketDataError("Simulated market data outage")
            if ticker not in self._responses:
                raise MarketDataError(f"No canned response for ticker {ticker!r}")
            return self._responses[ticker]
    ```

- [x] Factory: `ValidationRecordFactory` in `tests/factories.py` (AC: 1, 2)
  - [x] Add `ValidationRecord` to the `from apollo.db.models import ...` import line
  - [x] Add `ValidationRecordFactory(SQLAlchemyModelFactory)` after `EnvFingerprintFactory`:
    ```python
    class ValidationRecordFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = ValidationRecord
            sqlalchemy_session = None
            sqlalchemy_session_persistence = "commit"

        corpus_record_id = factory.LazyFunction(uuid4)  # dangling UUID — consistent with other factories
        validated_at = factory.LazyFunction(lambda: datetime.now(UTC))
        validation_status = "hit"
        param_value = 75.0
    ```

- [x] Conftest: Bind `ValidationRecordFactory` session (AC: 1, 2)
  - [x] In `tests/conftest.py`, add `ValidationRecordFactory` to import:
    ```python
    from tests.factories import CorpusRecordFactory, EnvFingerprintFactory, QuarantineRecordFactory, ValidationRecordFactory
    ```
  - [x] Add `ValidationRecordFactory._meta.sqlalchemy_session = session` after `EnvFingerprintFactory` binding in `db_session` fixture
  - [x] Add `"DELETE FROM validation_record"` before `"DELETE FROM corpus_record"` in the `db_session` cleanup? No — validation_record CASCADE-deletes when corpus_record is deleted, so no extra DELETE needed.

- [x] Regression-proof existing `tick()` call sites (AC: 1)
  - [x] In `tests/integration/test_worker_email_phase.py`: add `market_client=FakeMarketDataClient()` to every `tick()` call
  - [x] In `tests/integration/test_worker_quarantine.py`: add `market_client=FakeMarketDataClient()` to every `tick()` call
  - [x] In `tests/integration/test_worker_fingerprint.py`: add `market_client=FakeMarketDataClient()` to every `tick()` call
  - [x] In `tests/integration/test_worker_dispatch.py`: add `market_client=FakeMarketDataClient()` to every `tick()` call (if any tick() calls exist)
  - [x] In `tests/integration/test_worker_sealing.py`: add `market_client=FakeMarketDataClient()` to every `tick()` call (if any tick() calls exist)
  - [x] In `tests/integration/test_worker_tick.py`: add `market_client=FakeMarketDataClient()` to every `tick()` call (if any tick() calls exist)
  - [x] Import `FakeMarketDataClient` at the top of each modified file alongside existing fake imports

- [x] Unit Tests (AC: 1, 2, 3)
  - [x] Create `tests/unit/test_validate_service.py`
  - [x] Test `_day_unix_range`: verified with calendar.timegm for correct 2026 timestamps
  - [x] Test `_validate_one` happy path hit: validation_status="hit", predicted_positive=True, actual_positive=True, actual_change_pct≈10.0
  - [x] Test `_validate_one` miss: param_value=20.0 → predicted_positive=False, validation_status="miss"
  - [x] Test `_validate_one` offset: fetch_timestamp = expiry_at + timedelta(hours=3) → validation_status="offset"
  - [x] Test `_validate_one` DOWN direction: close=2700, open=3000, threshold_pct=9.0, direction="DOWN" → actual_change_pct=-10.0, actual_positive=True
  - [x] Test `_validate_one` idempotency: calling twice → second call swallows IntegrityError, no exception
  - [x] Test `validate_pending` with market data outage: raises_always → returns (0, 1), no exception raised
  - [x] Test `validate_pending` skips records without ticker/expiry_at (via empty eligible list)
  - [x] Test `validate_pending` with no records → (0, 0)
  - [x] Use mock sessionmaker (same pattern as `test_fingerprint_service.py`)

- [x] Integration Tests (AC: 1, 2, 3)
  - [x] Create `tests/integration/test_worker_validation.py`
  - [x] Test: full tick with sealed record + past expiry → validation_record created hit/miss
  - [x] Test: full tick with FakeMarketDataClient(raise_always=True) → no validation_record, corpus_record sealed, tick does not raise
  - [x] Test: sealed record without ticker → Phase 4 skips it
  - [x] Test: sealed record with future expiry_at → Phase 4 skips it
  - [x] Test: offset status when fetch_timestamp > expiry_at + 2h
  - [x] Test: idempotency — tick() twice → only one validation_record row
  - [x] Test: corpus_record.status stays "sealed" after validation (immutability preserved)
  - [x] Used db_session.expire_all() after every tick() before asserting DB state

## Dev Notes

### Architecture: Why `validation_record` Is a Separate Table

The corpus_record immutability trigger (migration `b4c7e1f02a9d`) prevents UPDATEs on identity columns. The validation outcome is a **derived fact**, not part of the original sealed event. A separate `validation_record` table with a UNIQUE FK models this correctly — the original sealed prediction is never mutated, and the calibration engine can query the join to compute statistics.

### Critical: Fail-Operational Contract for Phase 4

Phase 4 must NEVER crash `tick()`. `ValidationService.validate_pending()` internally catches all exceptions per record. The outer `tick()` call only receives the `(validated_count, skipped_count)` tuple — never an exception. This is the same fail-operational contract as `FingerprintService.attach()`.

### Critical: No `validation_record` Row = Retry Automatically

When market data is unavailable (`MarketDataError` raised), do NOT create a `validation_record` row. The Phase 4 query finds records where NO `validation_record` exists — so the next `tick()` automatically retries. This is the correct idempotent retry mechanism.

### Critical: `corpus_record` Immutability Trigger

The migration `b4c7e1f02a9d` adds a Postgres immutability trigger that fires on UPDATE to certain `corpus_record` columns. The 4 new nullable columns (`ticker`, `expiry_at`, `threshold_pct`, `threshold_direction`) are set only at `INSERT` time (via `configure_target`) and NEVER updated later. The trigger protects existing columns — adding new nullable columns does not require trigger changes because they're set only on insert.

**Verify**: The trigger only fires on UPDATE, not INSERT. The 4 new columns are set at target creation time and never modified again. No changes to the trigger migration are needed.

### Yahoo Finance API Details

**URL pattern** (no API key required, public):
```
https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={unix_ts_start_of_day}&period2={unix_ts_end_of_day}&interval=1d
```

**Common tickers**:
- Gold futures: `GC=F`
- EUR/USD: `EURUSD=X`  
- S&P 500: `^GSPC`
- US 10Y Treasury: `^TNX`

**Response structure** (parse carefully — arrays may contain None for non-trading days):
```json
{
  "chart": {
    "result": [{
      "indicators": {
        "quote": [{
          "open":  [3230.40, null, ...],
          "close": [3245.80, null, ...],
          "high":  [3250.00, null, ...],
          "low":   [3220.10, null, ...]
        }]
      }
    }],
    "error": null
  }
}
```

Pre-filter None values before calling `float()` — same defensive pattern as `fingerprint.py` NOAA parsing.

**Network timeout**: 15 seconds (hardcoded in `YahooFinanceClientImpl`). Adjust via config if needed in future.

### Mock SessionFactory Pattern for Unit Tests

Reuse the exact pattern from `test_fingerprint_service.py`:
```python
from contextlib import contextmanager
from unittest.mock import MagicMock
from sqlalchemy.exc import IntegrityError as SaIntegrityError

def _make_mock_session_factory(raises: type[Exception] | None = None) -> tuple[MagicMock, list]:
    written: list = []
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: s
    mock_session.__exit__ = MagicMock(return_value=False)
    if raises:
        mock_session.add = MagicMock(side_effect=raises("simulated"))
    else:
        mock_session.add = lambda obj: written.append(obj)
    mock_factory = MagicMock()
    mock_factory.begin.return_value = mock_session
    return mock_factory, written
```

### Integration Test Seed Pattern for Sealed Records with Validation Fields

```python
from datetime import UTC, datetime, timedelta
from apollo.db.models import CorpusRecord
from tests.factories import CorpusRecordFactory
from tests.utils import FakeMarketDataClient, OHLCVResult

EXPIRY_PAST = datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC)  # a fixed past datetime

def _seed_validatable_sealed(db_session, ticker: str = "GC=F") -> CorpusRecord:
    record = CorpusRecordFactory(
        status="sealed",
        ticker=ticker,
        expiry_at=EXPIRY_PAST,
        threshold_pct=9.0,
        threshold_direction="UP",
        # Simulate extraction_payload with param_value set (normally set by SealingService)
        extraction_payload={"param_value": 85.0, "measurement_timestamp": None},
        raw_hash="a" * 64,
        sealed_at=datetime.now(UTC),
        seal_agent_version="0.1.0",
        double_blind_coordinate="AAAA/BBBB",
        dispatched_at=datetime.now(UTC) - timedelta(hours=2),
        dispatch_agent_version="0.1.0",
    )
    db_session.flush()
    return record

def _make_gold_ohlcv(open_price: float = 3000.0, close_price: float = 3300.0) -> OHLCVResult:
    from apollo.services.validate import OHLCVResult
    return OHLCVResult(
        open=open_price,
        close=close_price,
        high=close_price,
        low=open_price,
        fetch_timestamp=datetime.now(UTC),
    )
```

Typical test body:
```python
def test_validation_hit(patched_db_url, db_session):
    record = _seed_validatable_sealed(db_session)
    market_client = FakeMarketDataClient({"GC=F": _make_gold_ohlcv(3000.0, 3300.0)})
    
    tick(
        smtp_client=FakeSMTPClient(),
        llm_client=FakeLLM([]),
        imap_client=FakeIMAPClient([]),
        env_client=FakeEnvDataClient(),
        market_client=market_client,
    )
    db_session.expire_all()
    
    vr = db_session.execute(
        select(ValidationRecord).where(ValidationRecord.corpus_record_id == record.id)
    ).scalar_one()
    assert vr.validation_status == "hit"
    assert vr.actual_change_pct == pytest.approx(10.0, abs=0.01)
    assert vr.predicted_positive is True
    assert vr.actual_positive is True
```

### Established Patterns (carry forward from Story 2.4)

1. `SessionFactory.begin()` for write transactions — never `session.commit()` manually
2. `@requires(Compartment.CALIBRATION_WRITE)` on `validate_pending` — new compartment, add to enum
3. `mypy --strict` — use `X | None` syntax, no `Optional[X]`
4. `ruff format .` + `ruff check .` before validating
5. `session.expire_all()` after `tick()` in integration tests before asserting DB state
6. `from __future__ import annotations` at top of every new service file
7. `datetime.now(UTC)` — never `datetime.utcnow()`
8. Lazy config import inside method body: `from apollo.config import settings as _settings` (not used in validate.py but follow if needed)
9. Factory: `Meta.sqlalchemy_session = None` (reassigned dynamically in conftest)
10. `module`-scoped testcontainer, `function`-scoped `db_session` with CASCADE DELETE cleanup
11. Alembic: never modify existing revisions, always chain new ones from `b5c6d7e8f9a0`
12. `assert` statements are acceptable in private `_validate_one` method (internal invariants); always use proper domain exceptions for public API errors

### `OHLCVResult` Import in Tests

The `OHLCVResult` dataclass lives in `src/apollo/services/validate.py`. Import in tests:
```python
from apollo.services.validate import OHLCVResult
```

### Files to CREATE (NEW)

- `src/apollo/db/alembic/versions/c1d2e3f4a5b6_add_market_validation.py`
- `src/apollo/services/validate.py`
- `tests/unit/test_validate_service.py`
- `tests/integration/test_worker_validation.py`

### Files to UPDATE (EXISTING)

- `src/apollo/domain/compartments.py` — add `CALIBRATION_WRITE` to `Compartment` enum
- `src/apollo/domain/exceptions.py` — add `MarketDataError`
- `src/apollo/domain/models.py` — add `ticker`, `expiry_at`, `threshold_pct`, `threshold_direction` to `TargetConfiguration`
- `src/apollo/db/models.py` — add 4 new columns to `CorpusRecord`; add `ValidationRecord` class; add `Boolean` import if missing
- `src/apollo/services/target.py` — pass 4 new fields to `CorpusRecord(...)` constructor
- `src/apollo/services/worker.py` — add import, `market_client` param, init block, Phase 4 block
- `src/apollo/mcp/tools.py` — add 4 optional params to `configure_target`
- `tests/utils.py` — add `FakeMarketDataClient`; add `OHLCVResult` and `MarketDataError` imports
- `tests/factories.py` — add `ValidationRecord` import; add `ValidationRecordFactory`
- `tests/conftest.py` — add `ValidationRecordFactory` import + session binding
- `tests/integration/test_worker_email_phase.py` — add `market_client=FakeMarketDataClient()` to all `tick()` calls
- `tests/integration/test_worker_quarantine.py` — add `market_client=FakeMarketDataClient()` to all `tick()` calls
- `tests/integration/test_worker_fingerprint.py` — add `market_client=FakeMarketDataClient()` to all `tick()` calls
- `tests/integration/test_worker_dispatch.py` — add `market_client=FakeMarketDataClient()` if any `tick()` calls exist
- `tests/integration/test_worker_sealing.py` — add `market_client=FakeMarketDataClient()` if any `tick()` calls exist
- `tests/integration/test_worker_tick.py` — add `market_client=FakeMarketDataClient()` if any `tick()` calls exist

### Files NOT to Touch

- `src/apollo/db/alembic/versions/b5c6d7e8f9a0_add_env_fingerprint_table.py` — never modify existing migrations
- `src/apollo/services/seal.py` — sealing stays as-is; validation is post-seal
- `src/apollo/services/fingerprint.py` — no changes
- `src/apollo/services/quarantine.py` — no changes
- `src/apollo/services/extract.py` — no changes
- `src/apollo/services/email_poller.py` — no changes
- `src/apollo/domain/types.py` — no changes (TargetStatus stays as-is; corpus_record status remains "sealed" after validation)
- `src/apollo/mcp/server.py` — no changes

### References

- Epics (Story 3.1 ACs): `_bmad-output/planning-artifacts/epics.md#Story-3.1`
- PRD (UJ-4 Ground-Truth Validation, NFR-5 Fail-Operational): `_bmad-output/planning-artifacts/prds/prd-Apollo-2026-06-01/prd.md`
- Architecture (compartment guards, DI via Protocol, testing rules): `_bmad-output/planning-artifacts/architecture.md`
- Project Context (Protocol DI, fail-operational, no external HTTP libs): `_bmad-output/project-context.md`
- Previous story patterns: `_bmad-output/implementation-artifacts/2-4-environmental-context-fingerprinting.md`
- FingerprintService as pattern model: `src/apollo/services/fingerprint.py`
- Compartment definitions: `src/apollo/domain/compartments.py`
- Alembic chain head: `src/apollo/db/alembic/versions/b5c6d7e8f9a0_add_env_fingerprint_table.py` (revision `b5c6d7e8f9a0`)
- Existing fakes (pattern to follow): `tests/utils.py`
- Worker tick pattern: `src/apollo/services/worker.py`
- ORM models (CorpusRecord, EnvFingerprint as reference): `src/apollo/db/models.py`

### Review Findings

- [x] [Review][Patch] Division by zero when open price is 0.0 [validate.py, _validate_one] — fixed: raise MarketDataError before division
- [x] [Review][Patch] Missing guard for empty highs/lows before max()/min() [validate.py, YahooFinanceClientImpl] — fixed: explicit check added
- [x] [Review][Patch] _day_unix_range: replace() called before astimezone() — wrong day boundary for non-UTC input [validate.py] — fixed: swap order to astimezone(UTC) first
- [x] [Review][Patch] threshold_direction accepts any string; silently defaults to DOWN for invalid values [domain/models.py] — fixed: Literal["UP", "DOWN"] type applied
- [x] [Review][Patch] _fetch_eligible skips threshold_pct/direction filters — records with ticker+expiry but no threshold incorrectly get status="hit" [validate.py] — fixed: added is_not(None) filters
- [x] [Review][Patch] assert statements in production _validate_one fragile under -O flag (and redundant given _fetch_eligible filters) [validate.py] — fixed: asserts removed
- [x] [Review][Patch] ticker interpolated into Yahoo URL without URL-encoding — path injection risk [validate.py] — fixed: urllib.parse.quote() applied
- [x] [Review][Defer] Detached ORM pattern after session close — safe for current scalar-only schema but fragile if relationships added later [validate.py, validate_pending] — deferred, pre-existing
- [x] [Review][Defer] validated_at timestamp stale across batch (captured once at validate_pending entry) [validate.py] — deferred, pre-existing
- [x] [Review][Defer] IntegrityError catch too broad in _validate_one — safe with current schema (only one UNIQUE constraint) [validate.py] — deferred, pre-existing
- [x] [Review][Defer] expiry_at ISO parsing in MCP tool: only handles Z-suffix; edge cases for date-only or non-UTC offsets [mcp/tools.py] — deferred, pre-existing
- [x] [Review][Defer] Worker IntegrityError for concurrent seal increments extraction_success — design choice [worker.py] — deferred, pre-existing

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story spec had incorrect Unix timestamps for 2026-06-10 (off by one year). Fixed unit test to use `calendar.timegm` directly rather than hardcoded values.

### Completion Notes List

- Implemented full Phase 4 ground-truth validation pipeline. `ValidationService` with `MarketDataClient` Protocol, `YahooFinanceClientImpl`, `OHLCVResult` dataclass, and `_day_unix_range` pure function. Follows exact same DI and fail-operational contract as `FingerprintService`.
- Added `validation_record` table (UNIQUE FK on corpus_record, append-only, never modifies corpus_record) with full Alembic migration chained from `b5c6d7e8f9a0`.
- Extended `configure_target` MCP tool with 4 optional params (`ticker`, `expiry_at`, `threshold_pct`, `threshold_direction`) — ISO-8601 string parsed to `datetime` before passing to domain model.
- Phase 4 is fully fail-operational: per-record `MarketDataError` is caught and logged; tick() never raises. No validation_record row on failure = automatic retry on next tick.
- All 119 unit tests and 39 integration tests pass. 0 regressions. Ruff clean. mypy --strict clean (36 source files).
- 4 E2E tests in `tests/e2e/test_epic2_e2e.py` are pre-existing failures from Story 2.3 staged changes (quarantine clears `raw_email_bytes`; sealing advances status) — these tests were written for Story 2.1 behavior and must be updated as part of Story 2.3/2.4 review. Not introduced by Story 3.1.

### File List

**New files:**
- `src/apollo/db/alembic/versions/c1d2e3f4a5b6_add_market_validation.py`
- `src/apollo/services/validate.py`
- `tests/unit/test_validate_service.py`
- `tests/integration/test_worker_validation.py`

**Modified files:**
- `src/apollo/domain/compartments.py`
- `src/apollo/domain/exceptions.py`
- `src/apollo/domain/models.py`
- `src/apollo/db/models.py`
- `src/apollo/services/target.py`
- `src/apollo/services/worker.py`
- `src/apollo/mcp/tools.py`
- `tests/utils.py`
- `tests/factories.py`
- `tests/conftest.py`
- `tests/integration/test_worker_email_phase.py`
- `tests/integration/test_worker_quarantine.py`
- `tests/integration/test_worker_fingerprint.py`
- `tests/integration/test_worker_dispatch.py`
- `tests/integration/test_worker_sealing.py`
- `tests/integration/test_worker_tick.py`

## Change Log

- Added `Compartment.CALIBRATION_WRITE` to `Compartment` enum (2026-06-06)
- Added `MarketDataError` domain exception (2026-06-06)
- Extended `TargetConfiguration` Pydantic model with `ticker`, `expiry_at`, `threshold_pct`, `threshold_direction` fields (2026-06-06)
- Added Alembic migration `c1d2e3f4a5b6` adding 4 nullable columns to `corpus_record` and new `validation_record` table (2026-06-06)
- Added `ValidationRecord` ORM model and 4 new columns to `CorpusRecord` ORM model (2026-06-06)
- Created `ValidationService` with `validate_pending`, `_fetch_eligible`, `_validate_one` + `YahooFinanceClientImpl` + `MarketDataClient` Protocol (2026-06-06)
- Extended `TargetService.create_target_configuration` to persist 4 new validation columns (2026-06-06)
- Extended `configure_target` MCP tool with 4 optional params and ISO-8601 datetime parsing (2026-06-06)
- Added Phase 4 validation block to `worker.tick()` with `market_client` DI param (2026-06-06)
- Added `FakeMarketDataClient` to `tests/utils.py` (2026-06-06)
- Added `ValidationRecordFactory` to `tests/factories.py` and bound in `tests/conftest.py` (2026-06-06)
- Regression-proofed all 6 existing integration test files with `market_client=FakeMarketDataClient()` (2026-06-06)
