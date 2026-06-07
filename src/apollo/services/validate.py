from __future__ import annotations

import calendar
import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from sqlalchemy import and_, not_, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import CorpusRecord, ValidationRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import MarketDataError

logger = logging.getLogger(__name__)

VALIDATION_AGENT_VERSION = "0.1.0"
OFFSET_THRESHOLD_SECONDS = 7200.0
POSITIVE_CONVICTION_THRESHOLD = 50.0
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1d"


@dataclass(frozen=True)
class OHLCVResult:
    open: float
    close: float
    high: float
    low: float
    fetch_timestamp: datetime


class MarketDataClient(Protocol):
    def fetch_ohlcv(self, ticker: str, expiry_at: datetime) -> OHLCVResult:
        """Fetch OHLCV for the day containing expiry_at.

        Raises MarketDataError if data unavailable (weekend, holiday, network error).
        Never returns None — raise instead.
        """
        ...


def _day_unix_range(dt: datetime) -> tuple[int, int]:
    day_start = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return int(calendar.timegm(day_start.timetuple())), int(
        calendar.timegm(day_end.timetuple())
    )


class YahooFinanceClientImpl:
    def fetch_ohlcv(self, ticker: str, expiry_at: datetime) -> OHLCVResult:
        p1, p2 = _day_unix_range(expiry_at)
        url = YAHOO_CHART_URL.format(
            ticker=urllib.parse.quote(ticker, safe=""), p1=p1, p2=p2
        )
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise MarketDataError(f"HTTP fetch failed for {ticker}: {exc}") from exc

        try:
            result = raw["chart"]["result"]
            if not result:
                raise MarketDataError(
                    f"Yahoo Finance returned empty result for {ticker}"
                )
            quote = result[0]["indicators"]["quote"][0]
            opens = [v for v in (quote.get("open") or []) if v is not None]
            closes = [v for v in (quote.get("close") or []) if v is not None]
            highs = [v for v in (quote.get("high") or []) if v is not None]
            lows = [v for v in (quote.get("low") or []) if v is not None]
            if not opens or not closes:
                raise MarketDataError(
                    f"No OHLCV data for {ticker} on {expiry_at.date()}"
                )
            if not highs or not lows:
                raise MarketDataError(
                    f"No high/low data for {ticker} on {expiry_at.date()}"
                )
            return OHLCVResult(
                open=float(opens[0]),
                close=float(closes[-1]),
                high=float(max(highs)),
                low=float(min(lows)),
                fetch_timestamp=datetime.now(UTC),
            )
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Yahoo Finance response parse failed for {ticker}: {exc}"
            ) from exc


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
        now = datetime.now(UTC)
        validated = 0
        skipped = 0

        with session_factory() as session:
            eligible = ValidationService._fetch_eligible(session, now, limit)

        for record in eligible:
            try:
                ValidationService._validate_one(
                    record, now, market_client, session_factory
                )
                validated += 1
            except MarketDataError as exc:
                skipped += 1
                logger.warning(
                    "apollo.worker.tick: validation pending — market data unavailable",
                    extra={
                        "record_id": str(record.id),
                        "ticker": record.ticker,
                        "error": str(exc),
                    },
                )
            except Exception as exc:
                skipped += 1
                logger.error(
                    "apollo.worker.tick: validation crashed unexpectedly",
                    extra={"record_id": str(record.id), "error": str(exc)},
                )

        return validated, skipped

    @staticmethod
    def _fetch_eligible(
        session: Session, now: datetime, limit: int
    ) -> list[CorpusRecord]:
        """Query sealed records past expiry with no validation record."""
        stmt = (
            select(CorpusRecord)
            .where(
                and_(
                    CorpusRecord.status == "sealed",
                    CorpusRecord.expiry_at.is_not(None),
                    CorpusRecord.ticker.is_not(None),
                    CorpusRecord.threshold_pct.is_not(None),
                    CorpusRecord.threshold_direction.is_not(None),
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
        ohlcv = market_client.fetch_ohlcv(record.ticker, record.expiry_at)

        fetch_delay_seconds = (
            ohlcv.fetch_timestamp - record.expiry_at.astimezone(UTC)
        ).total_seconds()
        if ohlcv.open == 0.0:
            raise MarketDataError(
                f"Cannot compute change pct for {record.ticker}: open price is zero"
            )
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
            status = (
                "hit" if fetch_delay_seconds <= OFFSET_THRESHOLD_SECONDS else "offset"
            )

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
