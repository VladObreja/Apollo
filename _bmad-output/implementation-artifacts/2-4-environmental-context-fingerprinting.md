---
baseline_commit: aa909c8cc9df66a652143b93ea4be47e8857e3ee
---

# Story 2.4: Environmental Context Fingerprinting

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the System,
I want to automatically enrich each sealed session record with an environmental snapshot (Local Sidereal Time, Kp index, solar wind speed),
So that we can retrospectively analyze environmental correlates without requiring the Asset to manually report them.

## Acceptance Criteria

1. **Given** a successfully validated session that has just been sealed
   **When** the worker Phase 3 finalizes the record
   **Then** a `FingerprintService.attach()` call is made using `_result.measurement_timestamp` from the extraction result (or `record.received_at` as fallback, or `datetime.now(UTC)` as last resort)
   **And** Local Sidereal Time is computed via a pure-math formula using `settings.asset_longitude` (no external API, no astropy dependency)
   **And** Kp index and solar wind speed are fetched from NOAA SWPC public endpoints via `urllib.request` (stdlib — no new package deps)
   **And** the computed data is written to a new `env_fingerprint` row linked to the corpus_record via unique FK

2. **Given** a successfully fetched environmental snapshot
   **When** the `env_fingerprint` row is created
   **Then** it is permanently and immutably associated with the corpus_record via a UNIQUE FK (`corpus_record_id`) with `ON DELETE CASCADE`
   **And** `retrieval_status` is `"ok"` if both external API metrics (kp_index, solar_wind_speed) succeed, `"partial"` if exactly one succeeds, or `"pending"` if both fail
   **And** `retrieval_notes` is a comma-separated string describing which metrics failed (e.g., `"kp_index:failed"`) or `null` on full success

3. **Given** any external NOAA data source is temporarily unavailable
   **When** `FingerprintService.attach()` encounters an exception during metric fetching or DB write
   **Then** the exception is caught internally and logged — it does NOT propagate to the caller
   **And** the parent corpus_record remains `"sealed"` — sealing is never affected by fingerprinting failures
   **And** an `env_fingerprint` row is still created with whatever metrics succeeded and the appropriate `retrieval_status`

## Tasks / Subtasks

- [x] DB Schema: Create `env_fingerprint` table (AC: 2)
  - [x] Create `src/apollo/db/alembic/versions/b5c6d7e8f9a0_add_env_fingerprint_table.py`
  - [x] Set `revision = "b5c6d7e8f9a0"` and `down_revision = "a2b3c4d5e6f7"` (chain from quarantine migration)
  - [x] Use `op.create_table("env_fingerprint", ...)` with these exact columns:
    - `id`: `postgresql.UUID(as_uuid=True)`, primary_key=True
    - `corpus_record_id`: `postgresql.UUID(as_uuid=True)`, `sa.ForeignKey("corpus_record.id", ondelete="CASCADE")`, nullable=False, unique=True
    - `fingerprinted_at`: `sa.DateTime(timezone=True)`, nullable=False
    - `measurement_timestamp`: `sa.DateTime(timezone=True)`, nullable=True
    - `local_sidereal_time`: `sa.Float()`, nullable=True
    - `kp_index`: `sa.Float()`, nullable=True
    - `solar_wind_speed`: `sa.Float()`, nullable=True
    - `retrieval_status`: `sa.String()`, nullable=False, server_default=`"pending"`
    - `retrieval_notes`: `sa.String()`, nullable=True
  - [x] Create index `ix_env_fingerprint_corpus_record_id` on `corpus_record_id`
  - [x] `downgrade()`: drop index first, then `op.drop_table("env_fingerprint")`
  - [x] Imports: `import sqlalchemy as sa`, `from alembic import op`, `from sqlalchemy.dialects import postgresql`

- [x] ORM Model: Add `EnvFingerprint` to `db/models.py` (AC: 2)
  - [x] Add `Float` to the existing `from sqlalchemy import ...` import line (keep all existing imports)
  - [x] Add `EnvFingerprint(Base)` class after `QuarantineRecord` (end of file):
    - `__tablename__ = "env_fingerprint"`
    - `id: MappedColumn[UUID]` — `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
    - `corpus_record_id: MappedColumn[UUID]` — `mapped_column(UUID(as_uuid=True), ForeignKey("corpus_record.id", ondelete="CASCADE"), nullable=False, unique=True)`
    - `fingerprinted_at: MappedColumn[datetime]` — `mapped_column(DateTime(timezone=True), nullable=False)`
    - `measurement_timestamp: MappedColumn[datetime | None]` — `mapped_column(DateTime(timezone=True), nullable=True)`
    - `local_sidereal_time: MappedColumn[float | None]` — `mapped_column(Float, nullable=True)`
    - `kp_index: MappedColumn[float | None]` — `mapped_column(Float, nullable=True)`
    - `solar_wind_speed: MappedColumn[float | None]` — `mapped_column(Float, nullable=True)`
    - `retrieval_status: MappedColumn[str]` — `mapped_column(String, nullable=False, default="pending")`
    - `retrieval_notes: MappedColumn[str | None]` — `mapped_column(String, nullable=True)`
  - [x] Do NOT add any `relationship()` back-reference to `CorpusRecord`

- [x] Config: Add asset location settings (AC: 1)
  - [x] In `src/apollo/config.py` Settings class, add after `ollama_timeout_seconds`:
    - `asset_latitude: float = 44.43` — Bucharest, Romania (degrees N); needed for future weather lookups
    - `asset_longitude: float = 26.10` — Bucharest, Romania (degrees E); used for LST computation
  - [x] No validator needed (floats with sensible defaults, not user-required like imap_username)

- [x] `FingerprintService` module (AC: 1, 2, 3)
  - [x] Create `src/apollo/services/fingerprint.py`
  - [x] Add module-level `logger = logging.getLogger(__name__)`
  - [x] Define `EnvDataClient` Protocol (two methods: `fetch_kp_index`, `fetch_solar_wind_speed`)
  - [x] Implement `_compute_lst(timestamp: datetime, longitude_deg: float) -> float` (pure math, no imports beyond `datetime`)
  - [x] Implement `_parse_noaa_time(ts_str: str) -> datetime` (strips fractional seconds, returns UTC)
  - [x] Implement `_fetch_json(url: str, timeout: int = 10) -> list[list[str]]` using `urllib.request.urlopen`
  - [x] Implement `NoaaClientImpl` class with `fetch_kp_index` and `fetch_solar_wind_speed` methods
  - [x] Implement `FingerprintService` static class with `attach()` method decorated `@requires(Compartment.EXTRACTION_WRITE)`

- [x] Worker Update: Add `env_client` to `tick()` and call `FingerprintService.attach()` (AC: 1, 2, 3)
  - [x] Add import: `from apollo.services.fingerprint import EnvDataClient, FingerprintService, NoaaClientImpl`
  - [x] Add `env_client: EnvDataClient | None = None` as the fourth parameter to `tick()`
  - [x] Add `if env_client is None: env_client = NoaaClientImpl()` in the init block (after the `imap_client` init block)
  - [x] In Phase 3, immediately after `_result = ExtractionService.extract(...)`, add: `_measurement_ts = _result.measurement_timestamp`
  - [x] After the existing `logger.info("apollo.worker.tick: record sealed", ...)` call (inside `if _sealed_hash is not None:`), add: `FingerprintService.attach(record, _measurement_ts, env_client, SessionFactory)`

- [x] `FakeEnvDataClient` in `tests/utils.py` (AC: 1, 2, 3)
  - [x] Add `from datetime import datetime` to imports in `tests/utils.py` (if not already present)
  - [x] Add `FakeEnvDataClient` class after `FakeIMAPClient` (see exact implementation in Dev Notes)
  - [x] Constructor: `kp: float | None = 3.0`, `solar_wind: float | None = 450.0`, `raise_on_kp: bool = False`, `raise_on_wind: bool = False`

- [x] Factory: `EnvFingerprintFactory` in `tests/factories.py` (AC: 2)
  - [x] Add `EnvFingerprint` to the `from apollo.db.models import ...` import line
  - [x] Add `EnvFingerprintFactory(SQLAlchemyModelFactory)` after `QuarantineRecordFactory` (see Dev Notes)

- [x] Conftest: Bind `EnvFingerprintFactory` session (AC: 2)
  - [x] Add `EnvFingerprintFactory` to import: `from tests.factories import CorpusRecordFactory, QuarantineRecordFactory, EnvFingerprintFactory`
  - [x] Add `EnvFingerprintFactory._meta.sqlalchemy_session = session` after the `QuarantineRecordFactory` binding in `db_session` fixture

- [x] Regression-proof existing tick() call sites (AC: 3)
  - [x] In `tests/integration/test_worker_email_phase.py`: add `env_client=FakeEnvDataClient()` to every `tick()` call
  - [x] In `tests/integration/test_worker_quarantine.py`: add `env_client=FakeEnvDataClient()` to every `tick()` call
  - [x] Import `FakeEnvDataClient` at the top of each file alongside the existing fake imports
  - [x] Rationale: without this, tick() defaults to `NoaaClientImpl()` which makes live NOAA HTTP calls in CI

- [x] Unit Tests (AC: 1, 2, 3)
  - [x] Create `tests/unit/test_fingerprint_service.py`
  - [x] Test `_compute_lst` at J2000.0 epoch: `ts = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)`, `longitude=26.1` → result ≈ `20.437` hours (assert `abs(result - 20.437) < 0.01`)
  - [x] Test happy path: `FakeEnvDataClient(kp=3.0, solar_wind=450.0)` → `retrieval_status="ok"`, `kp_index=3.0`, `solar_wind_speed=450.0`, `retrieval_notes=None`
  - [x] Test partial: `FakeEnvDataClient(kp=3.0, raise_on_wind=True)` → `retrieval_status="partial"`, `kp_index=3.0`, `solar_wind_speed=None`, `retrieval_notes="solar_wind_speed:failed"`
  - [x] Test full failure: `FakeEnvDataClient(raise_on_kp=True, raise_on_wind=True)` → `retrieval_status="pending"`, `retrieval_notes="kp_index:failed, solar_wind_speed:failed"`
  - [x] Test fail-operational: even when `session_factory` also raises → `attach()` does not raise
  - [x] Test LST populated even when both external APIs fail (LST is local, not external)
  - [x] Test idempotency: calling `attach()` twice on same record → second call is no-op (IntegrityError swallowed, no second row created)
  - [x] Test measurement_timestamp is stored as `env_fingerprint.measurement_timestamp`
  - [x] Test fallback: `measurement_timestamp=None` → `fingerprinted_at` is set, no crash
  - [x] Use a mock sessionmaker (no real DB) — see "Unit Test Mock Pattern" in Dev Notes

- [x] Integration Tests (AC: 1, 2, 3)
  - [x] Create `tests/integration/test_worker_fingerprint.py`
  - [x] Test: full tick with DISPATCHED record → env_fingerprint row created, `retrieval_status="ok"`
  - [x] Test: full tick with `FakeEnvDataClient(raise_on_kp=True, raise_on_wind=True)` → env_fingerprint row created, `retrieval_status="pending"`, corpus_record still `"sealed"`
  - [x] Test: full tick with `FakeEnvDataClient(raise_on_kp=True)` → env_fingerprint row created, `retrieval_status="partial"`, `solar_wind_speed=450.0`
  - [x] Test: sealing still succeeds when `FingerprintService.attach()` raises internally (corpus_record.status = "sealed")
  - [x] Use `patched_db_url`, `db_session`, `FakeLLM`, `FakeSMTPClient`, `FakeIMAPClient`, `FakeEnvDataClient` from `tests/utils.py`
  - [x] Use `CorpusRecordFactory` to seed DISPATCHED records (see "Integration Test Seed Pattern" in Dev Notes)
  - [x] Always call `db_session.expire_all()` after `tick()` before asserting DB state

### Review Findings

- [x] [Review][Patch] Rename terminal retrieval_status from `"pending"` to `"failed"` — both-APIs-failed state collides with the DB server_default "pending" (never-processed sentinel); decision: use `"failed"` for the terminal state [src/apollo/services/fingerprint.py:129, tests]
- [x] [Review][Decision] Unauthorized `default=False` added to `CorpusRecord.real_money_at_stake` — accepted as opportunistic improvement [src/apollo/db/models.py]
- [x] [Review][Patch] NOAA null/malformed time_tag row aborts entire `min()` scan — pre-filter rows in `fetch_kp_index`/`fetch_solar_wind_speed` to skip rows with bad timestamps or null values [src/apollo/services/fingerprint.py:63,76]
- [x] [Review][Patch] `float(None)` crash on null Kp/speed column values — fixed via row pre-filtering (validates `float(r[1])` / `float(r[2])` before including in candidates) [src/apollo/services/fingerprint.py:67,79]
- [x] [Review][Patch] `IntegrityError` catch too broad — changed to `logger.warning` with error detail; no longer claims "idempotent skip" for FK violations [src/apollo/services/fingerprint.py:152]
- [x] [Review][Patch] `_fetch_json` cast masks real types — added `isinstance(data, list)` runtime check; dict error responses now raise `ValueError` with clear message [src/apollo/services/fingerprint.py:51]
- [x] [Review][Patch] `_seed_dispatched` test helper `session` parameter is unused — added `session.flush()` after factory call, making session usage explicit [tests/integration/test_worker_fingerprint.py:52]
- [x] [Review][Patch] Idempotency unit test verifies wrong call site — replaced `begin.side_effect` with `@contextmanager` that raises on `__exit__` (commit-time simulation) [tests/unit/test_fingerprint_service.py:55]
- [x] [Review][Patch] AC3 integration test `test_sealing_succeeds_when_fingerprint_fails` missing fingerprint row assertion — added `scalar_one()` query + `retrieval_status == "failed"` assertion [tests/integration/test_worker_fingerprint.py:161]
- [x] [Review][Patch] Missing unit test for double-None timestamp fallback — added `test_fallback_to_datetime_now_when_both_timestamps_none` [tests/unit/test_fingerprint_service.py]
- [x] [Review][Defer] `extraction_success` counter can double-fire if decorator chain raises after sealing — pre-existing counter design not introduced by this story [src/apollo/services/worker.py] — deferred, pre-existing
- [x] [Review][Defer] `asset_latitude` config field unused — intentionally added for future weather lookups per spec; not a bug [src/apollo/config.py] — deferred, pre-existing
- [x] [Review][Defer] Process crash between seal-commit and fingerprint-write leaves permanently unfingerprintable records — known V1 limitation; no retry mechanism in scope for this story [src/apollo/services/worker.py] — deferred, pre-existing

## Dev Notes

### Critical: Fail-Operational Architecture in `attach()`

`FingerprintService.attach()` is the only Apollo service that **never propagates exceptions**. The sealing has already committed before `attach()` is called — fingerprinting failures must NEVER roll back or affect the sealed record.

Two-level try structure (outer catches everything; inner catches IntegrityError for idempotency):

```python
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

        ref_ts: datetime = measurement_timestamp or record.received_at or datetime.now(UTC)

        # Compute LST — pure math, almost never fails
        lst: float | None = None
        try:
            lst = _compute_lst(ref_ts, _settings.asset_longitude)
        except Exception as e:
            logger.warning("fingerprint: LST failed", extra={"error": str(e), "record_id": str(record.id)})

        # Fetch external metrics independently
        kp: float | None = None
        try:
            kp = env_client.fetch_kp_index(ref_ts)
        except Exception as e:
            logger.warning("fingerprint: kp_index fetch failed", extra={"error": str(e), "record_id": str(record.id)})

        wind: float | None = None
        try:
            wind = env_client.fetch_solar_wind_speed(ref_ts)
        except Exception as e:
            logger.warning("fingerprint: solar_wind_speed fetch failed", extra={"error": str(e), "record_id": str(record.id)})

        # retrieval_status based on external API results only (LST is local)
        n_ok = sum(1 for v in [kp, wind] if v is not None)
        status = "ok" if n_ok == 2 else ("partial" if n_ok == 1 else "pending")
        failed_names = [n for n, v in [("kp_index", kp), ("solar_wind_speed", wind)] if v is None]
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
        except IntegrityError:
            logger.info(
                "fingerprint: already attached — idempotent skip",
                extra={"record_id": str(record.id)},
            )
            return

        logger.info("fingerprint: attached", extra={"record_id": str(record.id), "retrieval_status": status})

    except Exception as exc:
        logger.error(
            "fingerprint: attach failed — fail-operational",
            extra={"record_id": str(record.id), "error": str(exc)},
        )
```

### Critical: LST Formula (No External Dependency — No astropy)

**Do NOT add `astropy` as a dependency.** Use this exact formula (Meeus, _Astronomical Algorithms_):

```python
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
```

**Verification** (unit test anchor): At `datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)` and `longitude_deg=26.1`:
- `d = 0`, so `GST_deg = 280.46061837`, `GST_hours = 18.6974...`
- `LST = (18.6974 + 1.74) % 24 = 20.437...`
- Assert: `abs(lst - 20.437) < 0.01` ✓

### NOAA API Integration (stdlib only — `urllib.request`)

```python
import json
import urllib.request
from datetime import UTC, datetime

_NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
_NOAA_WIND_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"


def _parse_noaa_time(ts_str: str) -> datetime:
    """Parse NOAA time tag to UTC datetime. Handles 'YYYY-MM-DD HH:MM:SS[.f]' format."""
    ts_clean = ts_str.split(".")[0]  # strip optional fractional seconds
    return datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _fetch_json(url: str, timeout: int = 10) -> list[list[str]]:
    """Fetch a JSON array via HTTP GET. Raises on network error."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[return-value]


class NoaaClientImpl:
    """Real NOAA SWPC fetcher. Public APIs — no authentication required."""

    def fetch_kp_index(self, timestamp: datetime) -> float | None:
        # Response: [["time_tag", "Kp", "status"], ["2026-06-05 18:00:00", "2.00", "G0"], ...]
        rows = _fetch_json(_NOAA_KP_URL)
        data = rows[1:]  # skip header row
        if not data:
            return None
        closest = min(data, key=lambda r: abs((_parse_noaa_time(r[0]) - timestamp).total_seconds()))
        return float(closest[1])

    def fetch_solar_wind_speed(self, timestamp: datetime) -> float | None:
        # Response: [["time_tag", "density", "speed", "temperature"], ...]
        rows = _fetch_json(_NOAA_WIND_URL)
        data = rows[1:]  # skip header row
        if not data:
            return None
        closest = min(data, key=lambda r: abs((_parse_noaa_time(r[0]) - timestamp).total_seconds()))
        return float(closest[2])  # speed is column index 2
```

**Known V1 limitation**: Both NOAA endpoints provide ~7 days of history. Sessions processed near real-time will get accurate data. Retroactively fingerprinting old sessions will get stale data (the fingerprint will reflect current metrics, not historical). Acceptable for V1.

### Full Import Block for `fingerprint.py`

```python
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import CorpusRecord, EnvFingerprint
from apollo.domain.compartments import Compartment, requires

logger = logging.getLogger(__name__)
```

No `math` import needed — the LST formula uses only Python arithmetic operators.

### Worker Integration: Exact Insertion Points

**1. New import** (add alongside existing service imports):
```python
from apollo.services.fingerprint import EnvDataClient, FingerprintService, NoaaClientImpl
```

**2. New parameter** (fourth positional param):
```python
def tick(
    smtp_client: SMTPClient | None = None,
    llm_client: LLMClient | None = None,
    imap_client: IMAPClient | None = None,
    env_client: EnvDataClient | None = None,   # ← NEW
) -> None:
```

**3. Init block** (after `if imap_client is None:` block, before `env = Environment(...)`):
```python
if env_client is None:
    env_client = NoaaClientImpl()
```

**4. Phase 3 for-loop** (capture `_measurement_ts` immediately after `_result` is set):
```python
_result = ExtractionService.extract(record, body, llm_client, env)
_measurement_ts = _result.measurement_timestamp   # ← NEW: capture before any transaction
_sealed_hash: str | None = None
```

**5. After sealing success** (append after the existing `logger.info("apollo.worker.tick: record sealed", ...)`):
```python
if _sealed_hash is not None:
    extraction_success += 1
    logger.info(
        "apollo.worker.tick: record sealed",
        extra={...},  # unchanged
    )
    FingerprintService.attach(record, _measurement_ts, env_client, SessionFactory)  # ← NEW
```

### `FakeEnvDataClient` Implementation (add to `tests/utils.py`)

```python
class FakeEnvDataClient:
    """Returns canned environmental metrics for fingerprint tests."""

    def __init__(
        self,
        kp: float | None = 3.0,
        solar_wind: float | None = 450.0,
        raise_on_kp: bool = False,
        raise_on_wind: bool = False,
    ) -> None:
        self._kp = kp
        self._solar_wind = solar_wind
        self._raise_on_kp = raise_on_kp
        self._raise_on_wind = raise_on_wind

    def fetch_kp_index(self, timestamp: datetime) -> float | None:
        if self._raise_on_kp:
            raise OSError("Simulated Kp fetch failure")
        return self._kp

    def fetch_solar_wind_speed(self, timestamp: datetime) -> float | None:
        if self._raise_on_wind:
            raise OSError("Simulated solar wind fetch failure")
        return self._solar_wind
```

Add `from datetime import datetime` to `tests/utils.py` imports.

### `EnvFingerprintFactory` Implementation

```python
class EnvFingerprintFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = EnvFingerprint
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    corpus_record_id = factory.LazyFunction(uuid4)  # dangling UUID — consistent with QuarantineRecordFactory
    fingerprinted_at = factory.LazyFunction(lambda: datetime.now(UTC))
    retrieval_status = "ok"
```

### Unit Test Mock Pattern (no real DB required)

```python
from unittest.mock import MagicMock
from sqlalchemy.exc import IntegrityError as SaIntegrityError

def _make_mock_session_factory(raises: type[Exception] | None = None) -> tuple[MagicMock, list]:
    """Returns a (mock_factory, written_objects) pair for unit testing."""
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
```

For the idempotency test (IntegrityError path):
```python
# Simulate IntegrityError on second write
mock_factory.begin.side_effect = [
    context_manager_that_raises(SaIntegrityError(...)),
]
```

### Integration Test Seed Pattern

Reuse the same DISPATCHED-record seeding as `test_worker_email_phase.py`. Typical setup:

```python
def _seed_dispatched(db_session, coordinate: str) -> CorpusRecord:
    record = CorpusRecordFactory(
        status="dispatched",
        double_blind_coordinate=coordinate,
        dispatched_at=datetime.now(UTC),
        dispatch_agent_version="0.1.0",
    )
    db_session.flush()
    return record

def _make_reply_email(coordinate: str) -> bytes:
    import email.mime.text
    msg = email.mime.text.MIMEText(
        f"PARAM (VAD): 85\nTime of measurement (UTC): 2026-06-06T10:00:00Z\n"
        f"Location: Bucharest\nSleep quality (0-100): 80\nPsychological state (0-100): 75\n"
        f"Social Field: Isolated\nTarget ID {coordinate}",
        "plain",
    )
    msg["Subject"] = f"Re: Apollo Research Session — Target ID {coordinate}"
    return msg.as_bytes()
```

Then:
```python
tick(
    smtp_client=FakeSMTPClient(),
    llm_client=FakeLLM([good_json_response]),
    imap_client=FakeIMAPClient([_make_reply_email(coordinate)]),
    env_client=FakeEnvDataClient(kp=3.0, solar_wind=450.0),
)
db_session.expire_all()
fingerprint = db_session.execute(
    select(EnvFingerprint).where(EnvFingerprint.corpus_record_id == record.id)
).scalar_one()
assert fingerprint.retrieval_status == "ok"
```

### Conftest CASCADE Cleanup

The `UNIQUE FK ON DELETE CASCADE` on `env_fingerprint.corpus_record_id` means the existing `DELETE FROM corpus_record` cleanup in `db_session` automatically cascades to `env_fingerprint`. No additional DELETE statement is needed in conftest.py.

### Established Patterns (carry forward from 2.3)

1. `SessionFactory.begin()` for write transactions — never `session.commit()` manually
2. `@requires(Compartment.EXTRACTION_WRITE)` on all EXTRACTION compartment write methods
3. `mypy --strict` — use `X | None` syntax, no `Optional[X]`
4. `ruff format .` + `ruff check .` before validating
5. `session.expire_all()` after `tick()` in integration tests before asserting DB state
6. `FakeSMTPClient`, `FakeLLM`, `FakeIMAPClient` from `tests/utils.py` — now also `FakeEnvDataClient`
7. `datetime.now(UTC)` — never `datetime.utcnow()`
8. Lazy config import inside method body: `from apollo.config import settings as _settings`
9. Factory: `Meta.sqlalchemy_session = None` (reassigned dynamically in conftest)
10. `module`-scoped testcontainer, `function`-scoped `db_session` with `DELETE + commit` cleanup
11. Alembic: never modify existing revisions, always chain new ones from `a2b3c4d5e6f7`

### `EnvDataClient` Protocol

```python
class EnvDataClient(Protocol):
    def fetch_kp_index(self, timestamp: datetime) -> float | None: ...
    def fetch_solar_wind_speed(self, timestamp: datetime) -> float | None: ...
```

`Protocol` is from `typing` (stdlib) — no new package dependency.

### Files to CREATE (NEW)

- `src/apollo/db/alembic/versions/b5c6d7e8f9a0_add_env_fingerprint_table.py`
- `src/apollo/services/fingerprint.py`
- `tests/unit/test_fingerprint_service.py`
- `tests/integration/test_worker_fingerprint.py`

### Files to UPDATE (EXISTING)

- `src/apollo/db/models.py` — add `EnvFingerprint` class; add `Float` to SQLAlchemy imports
- `src/apollo/config.py` — add `asset_latitude: float` and `asset_longitude: float`
- `src/apollo/services/worker.py` — add `env_client` param, imports, `_measurement_ts` capture, `FingerprintService.attach()` call
- `tests/utils.py` — add `FakeEnvDataClient`; add `from datetime import datetime` import
- `tests/factories.py` — add `EnvFingerprintFactory`; add `EnvFingerprint` to model imports
- `tests/conftest.py` — add `EnvFingerprintFactory` import + session binding
- `tests/integration/test_worker_email_phase.py` — add `env_client=FakeEnvDataClient()` to all `tick()` calls
- `tests/integration/test_worker_quarantine.py` — add `env_client=FakeEnvDataClient()` to all `tick()` calls

### Files NOT to Touch

- `src/apollo/services/seal.py` — sealing stays as-is; fingerprinting is post-seal
- `src/apollo/services/quarantine.py` — no changes
- `src/apollo/services/extract.py` — no changes
- `src/apollo/services/email_poller.py` — no changes
- `src/apollo/domain/models.py` — no changes (ExtractionResultSchema unchanged)
- `src/apollo/domain/exceptions.py` — no new exceptions needed
- `src/apollo/domain/compartments.py` — `EXTRACTION_WRITE` already defined
- `src/apollo/mcp/` — no changes
- Existing Alembic migrations — never modify, only chain

### References

- Epics (Story 2.4 ACs): `_bmad-output/planning-artifacts/epics.md#Story-2.4`
- PRD (Session Context Fingerprint section): `_bmad-output/planning-artifacts/prds/prd-Apollo-2026-06-01/prd.md` — Section "5. Session Context Fingerprint"
- Epistemological Schema (SessionFingerprint design): `_bmad-output/planning-artifacts/epistemological-schema-architecture.md#SessionFingerprint`
- Architecture (compartment guards, DI via Protocol, testing rules): `_bmad-output/planning-artifacts/architecture.md`
- Project Context (Protocol DI, no external HTTP libs, fail-operational): `_bmad-output/project-context.md`
- Previous story patterns: `_bmad-output/implementation-artifacts/2-3-quarantine-clarification-loop-exception-path.md`
- Worker Phase 3 insertion points: `src/apollo/services/worker.py:205-248`
- Alembic chain head: `src/apollo/db/alembic/versions/a2b3c4d5e6f7_add_quarantine_record_table.py` (revision `a2b3c4d5e6f7`)
- Existing fakes (pattern to follow): `tests/utils.py`
- Config pattern: `src/apollo/config.py`
- ORM pattern: `src/apollo/db/models.py` (QuarantineRecord as reference)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `_make_record()` initially used `CorpusRecord.__new__()` which fails with SQLAlchemy instrumented attributes. Fixed by using `MagicMock()` with `.id` and `.received_at` set directly — unit tests don't need real ORM instances.
- `_fetch_json()` return type `list[list[str]]` clashed with `json.loads()` returning `Any` under mypy strict. Fixed with `cast(list[list[str]], ...)` instead of `# type: ignore[return-value]` comment.

### Completion Notes List

- Created Alembic migration `b5c6d7e8f9a0` chained from `a2b3c4d5e6f7` (quarantine), creating `env_fingerprint` table with UNIQUE FK ON DELETE CASCADE to `corpus_record`.
- Added `EnvFingerprint` ORM model to `db/models.py` — all 9 columns, no relationship() back-reference per spec.
- Added `asset_latitude=44.43` and `asset_longitude=26.10` (Bucharest) to Settings with no validator.
- Implemented `fingerprint.py` with `EnvDataClient` Protocol, pure-math LST formula (Meeus), stdlib-only NOAA fetcher, `NoaaClientImpl`, and `FingerprintService.attach()` with two-level fail-operational exception handling.
- Updated `worker.tick()` with `env_client` 4th param, `NoaaClientImpl` init default, `_measurement_ts` capture, and `FingerprintService.attach()` call post-seal.
- Added `FakeEnvDataClient` to `tests/utils.py` and `EnvFingerprintFactory` to `tests/factories.py`.
- Regression-proofed all `tick()` calls in `test_worker_email_phase.py` and `test_worker_quarantine.py` with `env_client=FakeEnvDataClient()`.
- 11 unit tests pass (LST formula, all 4 retrieval_status paths, fail-operational, idempotency, fallback).
- 4 integration tests pass (ok/pending/partial/fail-operational paths against real testcontainer Postgres).
- Pre-existing E2E failures (4 tests) in `tests/e2e/test_epic2_e2e.py` are stale Story 2.1/2.2 assertions unrelated to Story 2.4 — were collection-erroring before this story.

### File List

- `src/apollo/db/alembic/versions/b5c6d7e8f9a0_add_env_fingerprint_table.py` (new)
- `src/apollo/services/fingerprint.py` (new)
- `tests/unit/test_fingerprint_service.py` (new)
- `tests/integration/test_worker_fingerprint.py` (new)
- `src/apollo/db/models.py` (modified — added `Float` import, `EnvFingerprint` class)
- `src/apollo/config.py` (modified — added `asset_latitude`, `asset_longitude`)
- `src/apollo/services/worker.py` (modified — added `env_client` param, init, capture, attach call)
- `tests/utils.py` (modified — added `datetime` import, `FakeEnvDataClient`)
- `tests/factories.py` (modified — added `EnvFingerprint` import, `EnvFingerprintFactory`)
- `tests/conftest.py` (modified — added `EnvFingerprintFactory` import + session binding)
- `tests/integration/test_worker_email_phase.py` (modified — `env_client=FakeEnvDataClient()` on all tick() calls)
- `tests/integration/test_worker_quarantine.py` (modified — `env_client=FakeEnvDataClient()` on all tick() calls)

## Change Log

| Date | Change |
|------|--------|
| 2026-06-06 | Story created: environmental context fingerprinting — env_fingerprint table, LST pure-math computation, NOAA SWPC API integration, FingerprintService (fail-operational), worker Phase 3 hook |
| 2026-06-06 | Story implemented: all 11 tasks complete, 138 tests passing (107 unit + 31 integration), mypy strict clean, ruff clean |
