---
baseline_commit: 362ebf5
---

# Story 2.2: Epistemological Sealing & Ledger Commit (Happy Path)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the System,
I want to cryptographically seal successfully extracted sessions into the ledger,
So that the raw data is permanently immutable and ready for calibration.

## Acceptance Criteria

1. **Given** a successfully extracted `ExtractionResultSchema` (Happy Path — LLM returned valid JSON)
   **When** the pipeline seals the record
   **Then** `raw_hash = sha256(record.raw_email_bytes).hexdigest()` is computed and stored on the record
   **And** `extraction_payload` (the full `ExtractionResultSchema` serialised as JSON) is stored on the record
   **And** the record status advances from `dispatched` → `sealed`
   **And** `sealed_at` (UTC) and `seal_agent_version` (Apollo package version) are recorded

2. **Given** the sealing operation is complete
   **When** the structured provenance log is emitted
   **Then** it includes `record_id`, `raw_hash`, `seal_agent_version`, `real_money_at_stake`, `asset_financial_awareness` in a single structured JSON log line

3. **Given** a corpus_record that is NOT in `dispatched` status, or whose `raw_email_bytes` is `None`
   **When** `SealingService.seal()` is called
   **Then** it raises `SealingError` (domain exception) without modifying the record

4. **Given** the Admin calls `configure_target` via MCP
   **When** the 2x2 Stakes Matrix fields are provided
   **Then** `real_money_at_stake` (bool, default `False`) and `asset_financial_awareness` (bool | None, default `None`) are persisted on the `corpus_record`

## Tasks / Subtasks

- [x] DB Schema: Add Sealing + 2x2 Matrix Columns (AC: 1, 2, 4)
  - [x] Create new Alembic migration chained to `e5f6a7b8c9d0` — use revision ID `f6a7b8c9d0e1`
  - [x] Add `extraction_payload`: JSONB, `nullable=True` (stores `ExtractionResultSchema.model_dump(mode="json")`)
  - [x] Add `raw_hash`: String(64), `nullable=True`, `unique=True` (SHA-256 hex digest of raw_email_bytes)
  - [x] Add `sealed_at`: `DateTime(timezone=True)`, `nullable=True`
  - [x] Add `seal_agent_version`: String, `nullable=True`
  - [x] Add `real_money_at_stake`: Boolean, `nullable=True`, `server_default=sa.text('false')`
  - [x] Add `asset_financial_awareness`: Boolean, `nullable=True`
  - [x] Create index `ix_corpus_record_sealed_at` on `sealed_at`
  - [x] Create index `ix_corpus_record_raw_hash` on `raw_hash`
  - [x] Ensure `downgrade()` drops indexes first, then columns in reverse order
  - [x] **No trigger update needed** — column-selective trigger (`a1b2c3d4e5f6`) guards only the 8 immutable identity columns; all new columns are mutable lifecycle columns by design

- [x] ORM Model: Update CorpusRecord (AC: 1, 4)
  - [x] Add `from typing import Any` and `from sqlalchemy.dialects.postgresql import JSONB` to `db/models.py`
  - [x] Add `extraction_payload: MappedColumn[dict[str, Any] | None]` — `mapped_column(JSONB, nullable=True)`
  - [x] Add `raw_hash: MappedColumn[str | None]` — `mapped_column(String(64), nullable=True)`
  - [x] Add `sealed_at: MappedColumn[datetime | None]` — `mapped_column(DateTime(timezone=True), nullable=True)`
  - [x] Add `seal_agent_version: MappedColumn[str | None]` — `mapped_column(String, nullable=True)`
  - [x] Add `real_money_at_stake: MappedColumn[bool | None]` — `mapped_column(Boolean, nullable=True)`
  - [x] Add `asset_financial_awareness: MappedColumn[bool | None]` — `mapped_column(Boolean, nullable=True)`

- [x] Domain Exception: SealingError (AC: 3)
  - [x] Add `SealingError(Exception)` to `src/apollo/domain/exceptions.py`
  - [x] Docstring: "Raised when sealing preconditions fail (wrong status or missing raw bytes). Caught in worker.tick() Phase 3 per-record loop."

- [x] Domain Model: 2x2 Matrix Fields on TargetConfiguration (AC: 4)
  - [x] Add `real_money_at_stake: bool = Field(default=False, description="...")` to `TargetConfiguration` in `domain/models.py`
  - [x] Add `asset_financial_awareness: bool | None = Field(default=None, description="...")` to `TargetConfiguration`

- [x] MCP Tool: Expose 2x2 Matrix to Admin (AC: 4)
  - [x] Add `real_money_at_stake: bool = False` optional param to `configure_target` in `mcp/tools.py`
  - [x] Add `asset_financial_awareness: Optional[bool] = None` optional param to `configure_target`
  - [x] Pass both fields through to `TargetConfiguration`
  - [x] Update docstring with new param descriptions

- [x] Target Service: Persist 2x2 Matrix (AC: 4)
  - [x] Pass `real_money_at_stake=config.real_money_at_stake` and `asset_financial_awareness=config.asset_financial_awareness` to `CorpusRecord(...)` constructor in `services/target.py`

- [x] SealingService (AC: 1, 2, 3)
  - [x] Create `src/apollo/services/seal.py`
  - [x] Import `AGENT_VERSION` using the same pattern as `dispatch.py` (`importlib.metadata`)
  - [x] Implement `SealingService` static class:
    - [x] `seal(record: CorpusRecord, extraction: ExtractionResultSchema, session: Session, agent_version: str = AGENT_VERSION) -> str`
      - Guard: raise `SealingError` if `record.status != TargetStatus.DISPATCHED.value`
      - Guard: raise `SealingError` if `not record.raw_email_bytes`
      - Compute: `raw_hash = hashlib.sha256(record.raw_email_bytes).hexdigest()`
      - Write: `record.extraction_payload = extraction.model_dump(mode="json")`
      - Write: `record.raw_hash = raw_hash`
      - Write: `record.status = TargetStatus.SEALED.value`
      - Write: `record.sealed_at = datetime.now(UTC)`
      - Write: `record.seal_agent_version = agent_version`
      - Call: `session.add(record)`
      - Return: `raw_hash`
  - [x] Decorate `seal` with `@requires(Compartment.EXTRACTION_WRITE)`
  - [x] Unit tests in `tests/unit/test_seal_service.py` (see Testing section)

- [x] Worker Tick: Activate Sealing in Phase 3 (AC: 1, 2)
  - [x] Add `from apollo.services.seal import SealingService` to `services/worker.py`
  - [x] Add `from apollo.domain.exceptions import SealingError` (already imported — verify)
  - [x] Replace `# Story 2.2: SealingService.seal(record, raw_bytes, _result) goes here` with sealing call:
    - [x] Open `SessionFactory.begin()` write session
    - [x] Re-fetch: `fresh = write_session.get(CorpusRecord, record.id)`
    - [x] Guard: if `fresh is None or fresh.status != TargetStatus.DISPATCHED.value`: log warning, skip
    - [x] Call: `raw_hash = SealingService.seal(fresh, _result, write_session)`
    - [x] Log: structured JSON with `record_id`, `raw_hash`, `seal_agent_version=AGENT_VERSION`, `real_money_at_stake=fresh.real_money_at_stake`, `asset_financial_awareness=fresh.asset_financial_awareness`
  - [x] Catch `SealingError` in the per-record `except` block alongside `ExtractionSchemaError`
  - [x] Import `AGENT_VERSION` from `apollo.services.dispatch` (already imported — reuse, do not re-declare)
  - [x] **CRITICAL REGRESSION:** Update `except Exception` outer catch to distinguish `SealingError` from unexpected crashes

- [x] **CRITICAL REGRESSION FIX:** Update Existing Integration Tests (AC: 1)
  - [x] In `tests/integration/test_worker_email_phase.py`:
    - [x] Update success-path assertion from `status == TargetStatus.DISPATCHED.value` to `status == TargetStatus.SEALED.value`
    - [x] Add assertion: `record.raw_hash` is not None and equals `hashlib.sha256(raw_email_bytes).hexdigest()`
    - [x] Add assertion: `record.extraction_payload` is not None
    - [x] Add assertion: `record.sealed_at` is not None and is UTC-aware
    - [x] Keep failure-path assertion unchanged: `ExtractionSchemaError` caught → status stays `dispatched`

- [x] Unit Tests (AC: 1, 2, 3)
  - [x] `tests/unit/test_seal_service.py`:
    - [x] `test_seal_success` — dispatched record with raw bytes; assert returns hex string, status sealed, extraction_payload set, sealed_at UTC-aware
    - [x] `test_seal_raw_hash_is_sha256_of_bytes` — seed known bytes, assert returned hash equals `hashlib.sha256(known_bytes).hexdigest()`
    - [x] `test_seal_extraction_payload_matches_schema` — assert `record.extraction_payload == extraction.model_dump(mode="json")`
    - [x] `test_seal_raises_on_wrong_status` — queued record → `SealingError`
    - [x] `test_seal_raises_on_missing_raw_bytes` — dispatched record with `raw_email_bytes=None` → `SealingError`
    - [x] `test_seal_sealed_at_is_utc_aware` — assert `record.sealed_at.tzinfo is not None`

- [x] Integration Test: Full Sealing Path (AC: 1, 2)
  - [x] Create `tests/integration/test_worker_sealing.py`
  - [x] Use `patched_db_url` + `db_session` fixtures (exact pattern from `test_worker_email_phase.py`)
  - [x] Seed 1 dispatched `CorpusRecord` with `double_blind_coordinate="8A2F/9B4C"` via `CorpusRecordFactory`
  - [x] Supply `FakeIMAPClient` with 1 synthetic email matching that coordinate
  - [x] Supply `FakeLLM` returning valid `ExtractionResultSchema` JSON
  - [x] Call `tick(imap_client=..., llm_client=..., smtp_client=FakeSMTPClient())`
  - [x] Call `session.expire_all()` to force fresh DB reads
  - [x] Assert: `record.status == TargetStatus.SEALED.value`
  - [x] Assert: `record.raw_hash == hashlib.sha256(synthetic_raw_bytes).hexdigest()`
  - [x] Assert: `record.extraction_payload` is a dict (not None)
  - [x] Assert: `record.sealed_at` is not None and `record.sealed_at.tzinfo is not None`
  - [x] Assert: `record.seal_agent_version` is not None
  - [x] Failure path: `FakeLLM` always fails extraction → status stays `dispatched`, `raw_hash` is None

### Review Findings

- [x] [Review][Patch] extraction_failed not incremented in None/wrong-status sealing branches [HIGH] [src/apollo/services/worker.py]
- [x] [Review][Patch] IntegrityError not caught for concurrent double-seal race condition [HIGH] [src/apollo/services/worker.py]
- [x] [Review][Patch] AGENT_VERSION re-declared in seal.py instead of imported from dispatch.py [LOW] [src/apollo/services/seal.py]
- [x] [Review][Patch] real_money_at_stake ORM column missing Python-side default=False [LOW] [src/apollo/db/models.py]
- [x] [Review][Patch] Unit test missing seal_agent_version assertion [LOW] [tests/unit/test_seal_service.py]
- [x] [Review][Defer] b"" empty bytes causes permanent retry loop for stuck DISPATCHED records [src/apollo/services/seal.py] — deferred, architectural (needs dead-letter queue or per-record retry limit)
- [x] [Review][Defer] model_dump PydanticSerializationError not wrapped in SealingError [src/apollo/services/seal.py:63] — deferred, caught by outer except Exception, functional
- [x] [Review][Defer] datetime.now(UTC) not injectable for frozen-time testing [src/apollo/services/seal.py] — deferred, test hardness improvement, not a bug
- [x] [Review][Defer] Test helper deduplication (_make_reply_email, _seed_dispatched not in tests/utils.py) [tests/] — deferred, DRY cleanup, not a bug

## Dev Notes

### Critical: Immutability Trigger Pattern

The column-selective immutability trigger (migration `a1b2c3d4e5f6`) only guards these 8 columns:
`id`, `target_statement`, `parameter_name`, `is_control_target`, `age_in_hours`, `admin_awareness_tier`, `admin_psychological_context`, `created_at`

All sealing columns (`extraction_payload`, `raw_hash`, `sealed_at`, `seal_agent_version`) and 2x2 matrix columns (`real_money_at_stake`, `asset_financial_awareness`) are mutable lifecycle columns — **no trigger modification needed**. Simply add them in the migration; the existing trigger will not reject updates to them.

### Critical: JSONB Import

`JSONB` is Postgres-specific and is NOT in core SQLAlchemy. The `db/models.py` file currently does not import it. You MUST add:
```python
from typing import Any
from sqlalchemy.dialects.postgresql import JSONB
```
Then declare the column:
```python
extraction_payload: MappedColumn[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
```
`mypy --strict` accepts `dict[str, Any]` — it's the canonical JSON annotation.

### Critical: Test Regression

`tests/integration/test_worker_email_phase.py` currently asserts that a successfully extracted record remains in `dispatched` status with the comment "sealing not in scope for 2.1". After Story 2.2, successful extraction → sealing → status becomes `sealed`. **You MUST update these assertions or CI will fail.**

### SealingService Implementation Sketch (`services/seal.py`)

```python
"""Epistemological sealing service.

Implements the dispatched → sealed lifecycle transition: hashes raw email bytes,
stores the validated extraction payload, and writes provenance columns.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from apollo.db.models import CorpusRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import SealingError
from apollo.domain.models import ExtractionResultSchema
from apollo.domain.types import TargetStatus

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version
    AGENT_VERSION: str = _pkg_version("apollo")
except PackageNotFoundError:
    AGENT_VERSION = "0.0.0"


class SealingService:
    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def seal(
        record: CorpusRecord,
        extraction: ExtractionResultSchema,
        session: Session,
        agent_version: str = AGENT_VERSION,
    ) -> str:
        """Seal a corpus_record: hash raw bytes, store extraction, advance to 'sealed'.

        Args:
            record: A dispatched CorpusRecord with raw_email_bytes set.
            extraction: Validated ExtractionResultSchema from the LLM.
            session: Active SQLAlchemy session within a transaction.
            agent_version: Apollo package version string.

        Returns:
            raw_hash: SHA-256 hex digest of raw_email_bytes.

        Raises:
            SealingError: If record is not dispatched or raw_email_bytes is missing.
        """
        if record.status != TargetStatus.DISPATCHED.value:
            raise SealingError(
                f"Cannot seal record {record.id}: expected 'dispatched', got '{record.status}'"
            )
        if not record.raw_email_bytes:
            raise SealingError(
                f"Cannot seal record {record.id}: raw_email_bytes is missing"
            )

        raw_hash = hashlib.sha256(record.raw_email_bytes).hexdigest()

        record.extraction_payload = extraction.model_dump(mode="json")
        record.raw_hash = raw_hash
        record.status = TargetStatus.SEALED.value
        record.sealed_at = datetime.now(UTC)
        record.seal_agent_version = agent_version
        session.add(record)

        return raw_hash
```

### Worker Phase 3 Update Sketch (`services/worker.py`)

Replace the `# Story 2.2` comment block in the Phase 3 extraction loop:

```python
# Before the loop, add import at top of file:
from apollo.services.seal import SealingService

# Replace the success log + Story 2.2 comment with:
        try:
            _result = ExtractionService.extract(record, body, llm_client, env)
            # Seal the record in its own transaction (pattern mirrors Phase 2 dispatch)
            with SessionFactory.begin() as write_session:
                fresh: CorpusRecord | None = write_session.get(CorpusRecord, record.id)
                if fresh is None:
                    logger.warning(
                        "apollo.worker.tick: record vanished before sealing",
                        extra={"record_id": str(record.id)},
                    )
                elif fresh.status != TargetStatus.DISPATCHED.value:
                    logger.warning(
                        "apollo.worker.tick: record no longer dispatched before sealing",
                        extra={"record_id": str(record.id), "status": fresh.status},
                    )
                else:
                    raw_hash = SealingService.seal(fresh, _result, write_session)
                    extraction_success += 1
                    logger.info(
                        "apollo.worker.tick: record sealed",
                        extra={
                            "record_id": str(record.id),
                            "raw_hash": raw_hash,
                            "seal_agent_version": AGENT_VERSION,
                            "real_money_at_stake": fresh.real_money_at_stake,
                            "asset_financial_awareness": fresh.asset_financial_awareness,
                        },
                    )
        except (ExtractionSchemaError, SealingError) as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: extraction/sealing failed",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
            # Story 2.3: QuarantineService.quarantine(...) goes here
        except Exception as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: extraction crashed unexpectedly",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
```

Note: `AGENT_VERSION` is already imported into `worker.py` via `from apollo.services.dispatch import AGENT_VERSION, ...`. Do NOT re-declare it.

Note: `TargetStatus` is already imported inside the Phase 2 block as a local import. Move it to the top-of-function import group or module level so Phase 3 can use it without duplication.

### Alembic Migration Details (`f6a7b8c9d0e1`)

```python
revision: str = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"

def upgrade() -> None:
    op.add_column("corpus_record", sa.Column("extraction_payload", postgresql.JSONB(), nullable=True))
    op.add_column("corpus_record", sa.Column("raw_hash", sa.String(64), nullable=True))
    op.add_column("corpus_record", sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("corpus_record", sa.Column("seal_agent_version", sa.String(), nullable=True))
    op.add_column("corpus_record", sa.Column("real_money_at_stake", sa.Boolean(), nullable=True, server_default=sa.text("false")))
    op.add_column("corpus_record", sa.Column("asset_financial_awareness", sa.Boolean(), nullable=True))
    op.create_index("ix_corpus_record_sealed_at", "corpus_record", ["sealed_at"])
    op.create_index("ix_corpus_record_raw_hash", "corpus_record", ["raw_hash"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_corpus_record_raw_hash", table_name="corpus_record")
    op.drop_index("ix_corpus_record_sealed_at", table_name="corpus_record")
    op.drop_column("corpus_record", "asset_financial_awareness")
    op.drop_column("corpus_record", "real_money_at_stake")
    op.drop_column("corpus_record", "seal_agent_version")
    op.drop_column("corpus_record", "sealed_at")
    op.drop_column("corpus_record", "raw_hash")
    op.drop_column("corpus_record", "extraction_payload")
```

Migration must import: `from sqlalchemy.dialects import postgresql` for `postgresql.JSONB()`.

### 2x2 Matrix Domain + MCP + Service Updates

**`domain/models.py` — append to `TargetConfiguration`:**
```python
real_money_at_stake: bool = Field(
    default=False,
    description=(
        "2x2 Stakes Matrix: Whether real capital is objectively at stake for this session. "
        "Tracked for psi-interference analysis (capital weight may affect Asset performance)."
    ),
)
asset_financial_awareness: bool | None = Field(
    default=None,
    description=(
        "2x2 Stakes Matrix: Whether the Asset subjectively believes capital is at stake. "
        "None means not disclosed to Admin. Isolates performance anxiety from objective capital."
    ),
)
```

**`mcp/tools.py` — add to `configure_target` signature:**
```python
real_money_at_stake: bool = False,
asset_financial_awareness: Optional[bool] = None,
```
Pass them through: `config = TargetConfiguration(..., real_money_at_stake=real_money_at_stake, asset_financial_awareness=asset_financial_awareness)`

**`services/target.py` — add to `CorpusRecord(...)` constructor:**
```python
real_money_at_stake=config.real_money_at_stake,
asset_financial_awareness=config.asset_financial_awareness,
```

### Architecture Rules for This Story

- **Layer isolation is absolute:** `services/seal.py` imports from `db/models.py`, `domain/models.py`, `domain/compartments.py`, `domain/exceptions.py`. It MUST NOT import from `mcp/` or `services/extract.py`.
- **`model_dump(mode="json")`** — not `model_dump()`. The `mode="json"` flag serialises `datetime` objects to ISO-8601 strings, which Postgres JSONB requires. Without it, `datetime` objects will raise a `TypeError` during JSONB insertion.
- **Re-fetch before write** — the sealing write transaction re-fetches the record (same pattern as Phase 2 dispatch). Do NOT operate on the stale `record` object from the Phase 3 read session.
- **`SealingError` is a domain exception** — it must be caught in the Phase 3 per-record loop alongside `ExtractionSchemaError`. Both are non-fatal: they increment `extraction_failed` and log the error; they do NOT crash the tick.
- **`AGENT_VERSION` is already imported** — it's brought in by `from apollo.services.dispatch import AGENT_VERSION, ...`. Do not re-declare it in `worker.py`.
- **`TargetStatus` local import** — currently imported inside the Phase 2 `if` block. Move it to the module-level imports so Phase 3 can also use it cleanly.
- **`raw_hash` unique constraint** — enforced at DB level. The `DISPATCHED` guard ensures a record can only be sealed once, making duplicate hash violations impossible under normal operation.

### Testing Strategy

**Unit tests (no DB, no IO) — `tests/unit/test_seal_service.py`:**
- Use `MagicMock()` for the SQLAlchemy session (just assert `session.add(record)` was called)
- Build `CorpusRecord` objects directly (no DB needed — ORM models are plain Python dataclasses for unit tests)
- Build `ExtractionResultSchema` with `ExtractionResultSchema(param_value=75.0)`
- Use `hashlib.sha256(b"test bytes").hexdigest()` to assert the returned hash

**Integration tests (testcontainers Postgres):**
- Copy exact `patched_db_url` monkeypatch pattern from `test_worker_email_phase.py`
- `CorpusRecordFactory(status="dispatched", double_blind_coordinate="8A2F/9B4C")` — factory_boy handles DB insert
- Build synthetic raw MIME bytes using stdlib `email.mime.text.MIMEText` (same as existing tests)
- Valid `FakeLLM` response: `'{"param_value": 75.0, "measurement_timestamp": null, "asset_location": null, "sleep_quality": null, "psychological_state": null, "social_field": null, "asset_notes": null}'`

### FakeIMAPClient Synthetic Email Pattern (carry from Story 2.1)

```python
from email.mime.text import MIMEText

msg = MIMEText("VAD: 75\nTime of measurement (UTC): 2026-06-05T10:00:00Z", "plain")
msg["Subject"] = "Re: Apollo Research Session — Target ID 8A2F/9B4C"
msg["From"] = "asset@example.com"
msg["To"] = "apollo@example.com"
raw_email_bytes = msg.as_bytes()
```

### Established Patterns (carry forward from Stories 1.1–2.1)

1. `SessionFactory.begin()` for write transactions — never `session.commit()` manually
2. `get_session_factory()` lazy factory — all services use it
3. `@requires(Compartment.EXTRACTION_WRITE)` on all write methods
4. `mypy --strict` must pass — `X | None` syntax, no `Optional[X]`
5. `ruff format .` + `ruff check .` before any commit
6. `session.expire_all()` after `tick()` in integration tests
7. Factory: `CorpusRecordFactory` in `tests/factories.py` — use it, never raw SQL
8. `FakeSMTPClient`, `FakeLLM`, `FakeIMAPClient` all live in `tests/utils.py`
9. `datetime.now(UTC)` — never `datetime.utcnow()`
10. Table name is singular `corpus_record`
11. Alembic: never modify existing revisions, always chain new ones
12. `module`-scoped testcontainer, `function`-scoped `db_session` with `DELETE + commit`

### Deferred Items from Story 2.1 (awareness, no action required in 2.2)

- `db_session` fixture rollback teardown is a no-op — pre-existing
- `FakeSMTPClient` deduplication — still pending
- IMAP connection pooling — deferred
- `raw_email_bytes` can be silently overwritten on non-DISPATCHED record — still open (Story 2.2 adds the status guard in SealingService but the EmailPollerService bug remains)
- Phase 3 `env` construction placement — deferred

### Files to CREATE (NEW)

- `src/apollo/db/alembic/versions/f6a7b8c9d0e1_add_sealing_columns.py` — Alembic migration
- `src/apollo/services/seal.py` — `SealingService` with `seal()` method
- `tests/unit/test_seal_service.py` — unit tests for SealingService
- `tests/integration/test_worker_sealing.py` — integration test for full sealing path

### Files to UPDATE (EXISTING)

- `src/apollo/db/models.py` — add 6 columns to `CorpusRecord`; add `JSONB` + `Any` imports
- `src/apollo/domain/exceptions.py` — add `SealingError`
- `src/apollo/domain/models.py` — add `real_money_at_stake`, `asset_financial_awareness` to `TargetConfiguration`
- `src/apollo/mcp/tools.py` — add optional 2x2 matrix params to `configure_target`
- `src/apollo/services/target.py` — pass 2x2 matrix fields to `CorpusRecord` constructor
- `src/apollo/services/worker.py` — implement sealing call; import `SealingService`; move `TargetStatus` to module-level; catch `SealingError`
- `tests/integration/test_worker_email_phase.py` — **CRITICAL**: update success-path assertions (`dispatched` → `sealed`, add `raw_hash`/`extraction_payload`/`sealed_at` assertions)

### Files NOT to Touch

- `src/apollo/domain/types.py` — `TargetStatus.SEALED` already defined
- `src/apollo/domain/compartments.py` — `EXTRACTION_WRITE` already defined
- `src/apollo/services/extract.py` — no changes; extraction logic is complete
- `src/apollo/services/email_poller.py` — no changes
- `src/apollo/services/dispatch.py` — no changes; `AGENT_VERSION` imported from here
- `src/apollo/services/queue.py` — no changes
- `src/apollo/mcp/server.py` — no changes
- `src/apollo/templates/` — no changes
- Existing Alembic migrations — never modify, only chain

### References

- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Structure Patterns, Immutable Ledger, Process Patterns)
- Epics (Story 2.2 AC): `_bmad-output/planning-artifacts/epics.md`
- Epistemological Schema: `_bmad-output/planning-artifacts/epistemological-schema-architecture.md` (2x2 Stakes Matrix, raw_hash immutability)
- Project Context: `_bmad-output/project-context.md` (Selective Immutability rule, Testing Rules)
- Previous Story (2.1): `_bmad-output/implementation-artifacts/2-1-inbound-email-ingestion-parsing.md` (Dev Notes, Established Patterns)
- Dispatch Service (AGENT_VERSION pattern): `src/apollo/services/dispatch.py`
- Immutability Trigger: `src/apollo/db/alembic/versions/a1b2c3d4e5f6_add_worker_queue_columns.py`
- Worker (Phase 3 hook point): `src/apollo/services/worker.py:209` (Story 2.2 comment)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

### Completion Notes List

- Implemented epistemological sealing: dispatched → sealed lifecycle transition via `SealingService.seal()` with SHA-256 raw_hash, validated extraction_payload (JSONB), sealed_at (UTC), and seal_agent_version.
- Created Alembic migration `f6a7b8c9d0e1` adding 6 new columns and 2 indexes (sealed_at, raw_hash unique). No trigger modification needed — immutability trigger only guards 8 identity columns.
- Added 2x2 Stakes Matrix fields (`real_money_at_stake`, `asset_financial_awareness`) end-to-end: domain model → MCP tool → target service → DB column.
- Worker Phase 3 now completes the full dispatched → sealed cycle. `TargetStatus` moved to module-level import. `SealingError` caught alongside `ExtractionSchemaError`.
- Critical regression test updated: success-path now asserts `status == SEALED` with raw_hash, extraction_payload, and sealed_at assertions.
- Fixed pre-existing ruff/mypy errors from Story 2.1 (`email_poller.py`, `extract.py`, `test_e2e`, `test_email_poller`, `test_extract_service`, `test_templates`) as part of CI gate compliance.
- Final: 102/102 tests pass, ruff clean, mypy clean.

### File List

**Created:**
- `src/apollo/db/alembic/versions/f6a7b8c9d0e1_add_sealing_columns.py`
- `src/apollo/services/seal.py`
- `tests/unit/test_seal_service.py`
- `tests/integration/test_worker_sealing.py`

**Modified:**
- `src/apollo/db/models.py`
- `src/apollo/domain/exceptions.py`
- `src/apollo/domain/models.py`
- `src/apollo/mcp/tools.py`
- `src/apollo/services/target.py`
- `src/apollo/services/worker.py`
- `src/apollo/services/email_poller.py` (pre-existing ruff fixes)
- `src/apollo/services/extract.py` (pre-existing ruff fix)
- `tests/integration/test_worker_email_phase.py`
- `tests/e2e/test_epic2_e2e.py` (pre-existing ruff/mypy fixes)
- `tests/unit/test_email_poller.py` (pre-existing ruff fix)
- `tests/unit/test_extract_service.py` (pre-existing ruff fix)
- `tests/unit/test_templates.py` (pre-existing ruff fix)

## Change Log

- 2026-06-05: Story 2.2 implementation complete. Alembic migration `f6a7b8c9d0e1` adds sealing + 2x2 matrix columns. `SealingService` implements dispatched → sealed lifecycle. Worker Phase 3 activates sealing. 102/102 tests pass, ruff + mypy clean. Status → review.
