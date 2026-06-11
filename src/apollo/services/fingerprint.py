from __future__ import annotations

import json
import logging
import urllib.request
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import CorpusRecord, EnvFingerprint
from apollo.domain.compartments import Compartment, requires
from apollo.domain.types import TargetStatus

logger = logging.getLogger(__name__)

_NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
_NOAA_WIND_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"


class EnvDataClient(Protocol):
    def fetch_kp_index(self, timestamp: datetime) -> float | None: ...
    def fetch_solar_wind_speed(self, timestamp: datetime) -> float | None: ...


def _compute_lst(timestamp: datetime, longitude_deg: float) -> float:
    """Compute Local Sidereal Time in decimal hours (0–24).

    Formula: GST via days since J2000.0 (Meeus Chapter 12), then add longitude offset.
    """
    j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)
    d = (timestamp - j2000).total_seconds() / 86400.0  # days since J2000.0

    # Greenwich Mean Sidereal Time in degrees
    GST_deg = 280.46061837 + 360.98564736629 * d + 0.000387933 * (d / 36525.0) ** 2
    GST_hours = (GST_deg % 360.0) / 15.0

    return (GST_hours + longitude_deg / 15.0) % 24.0


def _parse_noaa_time(ts_str: str) -> datetime:
    """Parse NOAA time tag to UTC datetime. Handles 'YYYY-MM-DD HH:MM:SS[.f]' format."""
    ts_clean = ts_str.split(".")[0]  # strip optional fractional seconds
    return datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _fetch_json(url: str, timeout: int = 10) -> list[list[str]]:
    """Fetch a JSON array via HTTP GET. Raises on network error or unexpected format."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Unexpected NOAA response format: {type(data).__name__}")
    return cast(list[list[str]], data)


class NoaaClientImpl:
    """Real NOAA SWPC fetcher. Public APIs — no authentication required."""

    def fetch_kp_index(self, timestamp: datetime) -> float | None:
        # Response: [["time_tag", "Kp", "status"], ["2026-06-05 18:00:00", "2.00", "G0"], ...]
        rows = _fetch_json(_NOAA_KP_URL)
        valid: list[list[str]] = []
        for r in rows[1:]:
            try:
                _parse_noaa_time(r[0])
                if r[1] is not None:
                    float(r[1])
                    valid.append(r)
            except Exception:
                continue
        if not valid:
            return None
        closest = min(
            valid,
            key=lambda r: abs((_parse_noaa_time(r[0]) - timestamp).total_seconds()),
        )
        return float(closest[1])

    def fetch_solar_wind_speed(self, timestamp: datetime) -> float | None:
        # Response: [["time_tag", "density", "speed", "temperature"], ...]
        rows = _fetch_json(_NOAA_WIND_URL)
        valid: list[list[str]] = []
        for r in rows[1:]:
            try:
                _parse_noaa_time(r[0])
                if r[2] is not None:
                    float(r[2])
                    valid.append(r)
            except Exception:
                continue
        if not valid:
            return None
        closest = min(
            valid,
            key=lambda r: abs((_parse_noaa_time(r[0]) - timestamp).total_seconds()),
        )
        return float(closest[2])  # speed is column index 2


class FingerprintService:
    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def fetch_sealed_records_missing_fingerprint(
        session: Session, limit: int = 100
    ) -> list[CorpusRecord]:
        """Find sealed records with no corresponding env_fingerprint row.

        These are records that were sealed but never received an environmental
        fingerprint (e.g. a crash between seal-commit and fingerprint-write).
        Used by worker.py Phase 3c to backfill them on a subsequent tick.
        """
        stmt = (
            select(CorpusRecord)
            .outerjoin(
                EnvFingerprint, EnvFingerprint.corpus_record_id == CorpusRecord.id
            )
            .where(
                and_(
                    CorpusRecord.status == TargetStatus.SEALED.value,
                    EnvFingerprint.id.is_(None),
                )
            )
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def attach(
        record: CorpusRecord,
        measurement_timestamp: datetime | None,
        env_client: EnvDataClient,
        session_factory: sessionmaker[Session],
    ) -> None:
        try:
            from apollo.config import settings as _settings

            ref_ts: datetime = (
                measurement_timestamp or record.received_at or datetime.now(UTC)
            )

            # Compute LST — pure math, almost never fails
            lst: float | None = None
            try:
                lst = _compute_lst(ref_ts, _settings.asset_longitude)
            except Exception as e:
                logger.warning(
                    "fingerprint: LST failed",
                    extra={"error": str(e), "record_id": str(record.id)},
                )

            # Fetch external metrics independently
            kp: float | None = None
            try:
                kp = env_client.fetch_kp_index(ref_ts)
            except Exception as e:
                logger.warning(
                    "fingerprint: kp_index fetch failed",
                    extra={"error": str(e), "record_id": str(record.id)},
                )

            wind: float | None = None
            try:
                wind = env_client.fetch_solar_wind_speed(ref_ts)
            except Exception as e:
                logger.warning(
                    "fingerprint: solar_wind_speed fetch failed",
                    extra={"error": str(e), "record_id": str(record.id)},
                )

            # retrieval_status based on external API results only (LST is local)
            n_ok = sum(1 for v in [kp, wind] if v is not None)
            status = "ok" if n_ok == 2 else ("partial" if n_ok == 1 else "failed")
            failed_names = [
                n
                for n, v in [("kp_index", kp), ("solar_wind_speed", wind)]
                if v is None
            ]
            notes: str | None = ", ".join(f"{n}:failed" for n in failed_names) or None

            fp = EnvFingerprint(
                id=uuid4(),
                corpus_record_id=record.id,
                fingerprinted_at=datetime.now(UTC),
                measurement_timestamp=ref_ts,
                local_sidereal_time=lst,
                kp_index=kp,
                solar_wind_speed=wind,
                retrieval_status=status,
                retrieval_notes=notes,
            )

            try:
                with session_factory.begin() as write_session:
                    write_session.add(fp)
            except IntegrityError as exc:
                logger.warning(
                    "fingerprint: integrity error on write — skipping",
                    extra={"record_id": str(record.id), "error": str(exc)},
                )
                return

            logger.info(
                "fingerprint: attached",
                extra={"record_id": str(record.id), "retrieval_status": status},
            )

        except Exception as exc:
            logger.error(
                "fingerprint: attach failed — fail-operational",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
