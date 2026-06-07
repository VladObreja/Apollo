---
baseline_commit: aa909c8
---

# Story 2.3: Quarantine & Clarification Loop (Exception Path)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the System,
I want to isolate malformed extractions and autonomously request clarification from the Asset,
So that the pipeline doesn't crash and compartment isolation is preserved.

## Acceptance Criteria

1. **Given** a `ValidationError` during extraction (manifested as `ExtractionSchemaError`)
   **When** the Phase 3 exception handler fires
   **Then** a new row is created in `quarantine_record` containing: the corpus_record FK, raw email bytes (copied from the record), the quarantine reason string `"extraction_schema_error"`, the error detail string, and a `quarantined_at` UTC timestamp
   **And** `corpus_record.raw_email_bytes` is cleared to `None` in the same transaction — enabling the IMAP poller to accept Jane's clarification reply on the next tick

2. **Given** a successfully committed `quarantine_record`
   **When** the clarification email is rendered
   **Then** it uses `clarification.jinja` exclusively
   **And** the rendered email contains ONLY `{{ coordinate }}` and `{{ parameter }}` — `target_statement` is NEVER passed to the template renderer (double-blind isolation enforced at code level)

3. **Given** a rendered clarification email
   **When** it is dispatched via the existing `SMTPClient` protocol
   **Then** the email is sent to `settings.asset_email_address`
   **And** on SMTP success, `quarantine_record.clarification_sent_at` (UTC) and `quarantine_record.clarification_agent_version` are set in a second write transaction
   **And** if SMTP fails, the quarantine_record row still exists with `clarification_sent_at = None` (fail-operational — tick continues without crashing)

4. **Given** a `SealingError` in Phase 3
   **When** the exception is handled
   **Then** it is only logged — no quarantine is created (SealingError is a pre-condition guard failure, not a data quality issue requiring clarification)

## Tasks / Subtasks

- [x] DB Schema: Create `quarantine_record` table (AC: 1)
  - [x] Create new Alembic migration chained to `f6a7b8c9d0e1` — use revision ID `a2b3c4d5e6f7`
  - [x] Use `op.create_table("quarantine_record", ...)` with columns:
    - `id`: `postgresql.UUID(as_uuid=True)`, primary_key=True
    - `corpus_record_id`: `postgresql.UUID(as_uuid=True)`, `sa.ForeignKey("corpus_record.id", ondelete="CASCADE")`, nullable=False
    - `raw_email_bytes`: `sa.LargeBinary()`, nullable=False
    - `quarantine_reason`: `sa.String()`, nullable=False
    - `error_detail`: `sa.String()`, nullable=False
    - `quarantined_at`: `sa.DateTime(timezone=True)`, nullable=False
    - `clarification_sent_at`: `sa.DateTime(timezone=True)`, nullable=True
    - `clarification_agent_version`: `sa.String()`, nullable=True
  - [x] Create index `ix_quarantine_record_corpus_record_id` on `corpus_record_id`
  - [x] Create index `ix_quarantine_record_quarantined_at` on `quarantined_at`
  - [x] `downgrade()`: drop indexes first, then `op.drop_table("quarantine_record")`
  - [x] Migration file imports: `import sqlalchemy as sa`, `from alembic import op`, `from sqlalchemy.dialects import postgresql`

- [x] ORM Model: Add `QuarantineRecord` to `db/models.py` (AC: 1)
  - [x] Add `ForeignKey` to the `from sqlalchemy import ...` line
  - [x] Add `QuarantineRecord(Base)` class after `CorpusRecord`:
    - `__tablename__ = "quarantine_record"`
    - `id: MappedColumn[UUID]` — `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
    - `corpus_record_id: MappedColumn[UUID]` — `mapped_column(UUID(as_uuid=True), ForeignKey("corpus_record.id", ondelete="CASCADE"), nullable=False)`
    - `raw_email_bytes: MappedColumn[bytes]` — `mapped_column(LargeBinary, nullable=False)`
    - `quarantine_reason: MappedColumn[str]` — `mapped_column(String, nullable=False)`
    - `error_detail: MappedColumn[str]` — `mapped_column(String, nullable=False)`
    - `quarantined_at: MappedColumn[datetime]` — `mapped_column(DateTime(timezone=True), nullable=False)`
    - `clarification_sent_at: MappedColumn[datetime | None]` — `mapped_column(DateTime(timezone=True), nullable=True)`
    - `clarification_agent_version: MappedColumn[str | None]` — `mapped_column(String, nullable=True)`
  - [x] Do NOT add any `relationship()` back-reference to `CorpusRecord` — the DB-level CASCADE handles cleanup

- [x] Domain Exception: `QuarantineError` (AC: 3)
  - [x] Add `QuarantineError(Exception)` to `src/apollo/domain/exceptions.py`
  - [x] Docstring: "Raised when quarantine pre-conditions fail (record not found, raw_email_bytes missing, or template/rendering failure). Caught in worker.tick() Phase 3 per-record loop. Non-fatal — logged and tick continues."

- [x] Jinja2 Template: `clarification.jinja` (AC: 2)
  - [x] Create `src/apollo/templates/clarification.jinja`
  - [x] First line MUST be `Subject: Re: Apollo Research Session — Target ID {{ coordinate }}`
  - [x] Body receives ONLY `{{ coordinate }}` and `{{ parameter }}` variables — no other context
  - [x] Template body asks Jane to re-send her measurements for the same fields as `extraction.jinja`

- [x] `QuarantineService` (AC: 1, 2, 3)
  - [x] Create `src/apollo/services/quarantine.py`
  - [x] Add module-level `logger = logging.getLogger(__name__)`
  - [x] Import `AGENT_VERSION` from `apollo.services.dispatch` — never redeclare
  - [x] Import `SMTPClient` from `apollo.services.dispatch`
  - [x] Implement `QuarantineService` static class with one method:
    - [x] `quarantine(record: CorpusRecord, exc: ExtractionSchemaError, env: Environment, smtp_client: SMTPClient, session_factory: sessionmaker[Session], agent_version: str = AGENT_VERSION) -> None`
    - [x] Decorate with `@requires(Compartment.EXTRACTION_WRITE)`
    - [x] **Step 1 — Transaction 1** (write, atomic): open `session_factory.begin()` as write_session
    - [x] **Step 2 — Render** (no IO): `env.get_template("clarification.jinja").render(coordinate=coordinate, parameter=parameter)`
    - [x] **Step 3 — SMTP** (fail-operational, outside any transaction)
    - [x] **Step 4 — Transaction 2** (only if SMTP succeeded)

- [x] Worker Update: Activate Quarantine in Phase 3 (AC: 1, 2, 3, 4)
  - [x] Add `from apollo.services.quarantine import QuarantineService` import
  - [x] Add `from apollo.domain.exceptions import ..., QuarantineError` (add to existing import)
  - [x] Split `ExtractionSchemaError` and `SealingError` into separate handlers; inner try/except for QuarantineError
  - [x] The `except Exception` outer catch remains unchanged after both new handlers

- [x] `tests/factories.py`: Add `QuarantineRecordFactory` (AC: 1)
  - [x] Add `from uuid import uuid4` if not already present
  - [x] Import `QuarantineRecord` from `apollo.db.models`
  - [x] Add `QuarantineRecordFactory(SQLAlchemyModelFactory)`

- [x] `tests/conftest.py`: Bind `QuarantineRecordFactory` session in `db_session` fixture
  - [x] Add `from tests.factories import CorpusRecordFactory, QuarantineRecordFactory`
  - [x] Add `QuarantineRecordFactory._meta.sqlalchemy_session = session` after the existing `CorpusRecordFactory` binding

- [x] Unit Tests (AC: 1, 2, 3, 4)
  - [x] Create `tests/unit/test_quarantine_service.py` (14 tests, all passing)

- [x] Integration Test: Full Exception Path (AC: 1, 2, 3)
  - [x] Create `tests/integration/test_worker_quarantine.py` (7 tests, all passing)

## Dev Notes

### Critical: The Two-Transaction Pattern

This story uses the same two-transaction pattern as `SealingService` (Story 2.2):

**Transaction 1** — atomic, inside `session_factory.begin()`:
- Re-fetch corpus_record with `write_session.get(CorpusRecord, record.id)` (never operate on the detached record from the closed read_session)
- Copy `raw_email_bytes` into new `QuarantineRecord`
- Set `fresh.raw_email_bytes = None` — CRITICAL: this allows the IMAP poller to accept Jane's correction on the next tick
- Commit both atomically

SMTP send happens between Transaction 1 and Transaction 2.

**Transaction 2** — only on SMTP success:
- Re-fetch `QuarantineRecord` by its cached `quarantine_id`
- Set `clarification_sent_at` and `clarification_agent_version`

### Critical: Why raw_email_bytes Must Be Cleared

`EmailPollerService.fetch_new_session_emails()` (`email_poller.py:198-199`) has this idempotency guard:
```python
if fresh.raw_email_bytes is not None:
    continue  # Skip — bytes already stored
```
If the corpus_record still has `raw_email_bytes`, Jane's clarification reply (a new IMAP UNSEEN email) will be silently skipped. Clearing `raw_email_bytes = None` in Transaction 1 resets the corpus_record for the next intake. The original failed bytes are preserved in `quarantine_record.raw_email_bytes` for audit.

**This also means:** if extraction fails again on Jane's second reply, a second `quarantine_record` is created. That's intentional — the loop repeats until extraction succeeds.

### Critical: Double-Blind Isolation in `clarification.jinja`

The template MUST NOT receive `target_statement`. The `QuarantineService.quarantine()` passes ONLY:
```python
template.render(coordinate=coordinate, parameter=parameter)
```
`coordinate` and `parameter` are cached INSIDE Transaction 1 from `fresh.double_blind_coordinate` and `fresh.parameter_name` (not from the stale detached `record` object passed in). This prevents any accidental stale state.

### Template Convention: First Line = Subject

Follow the exact pattern from `extraction.jinja` and `DispatchService.render_tasking_email()` (`dispatch.py:127-134`):
```
Subject: Re: Apollo Research Session — Target ID {{ coordinate }}

[Body text here...]
```
Parse with:
```python
lines = rendered.splitlines()
subject = lines[0].removeprefix("Subject: ").strip()
body = "\n".join(lines[1:]).lstrip("\n")
```

### ORM UUID Import Note

`db/models.py` already imports `UUID` from `sqlalchemy.dialects.postgresql`. Use the same import for `QuarantineRecord.corpus_record_id`. Add `ForeignKey` to the existing SQLAlchemy core imports line.

### Migration Import: `postgresql` for UUID

The migration must import `from sqlalchemy.dialects import postgresql` to use `postgresql.UUID(as_uuid=True)` in `op.create_table(...)`. Unlike the sealing migration, no JSONB is needed here.

### `ON DELETE CASCADE` Handles conftest.py Cleanup

With `ForeignKey("corpus_record.id", ondelete="CASCADE")` in the migration, the existing `tests/conftest.py` cleanup (`DELETE FROM corpus_record`) will automatically cascade to delete all quarantine records. No additional DELETE statement needed in conftest. Only the `QuarantineRecordFactory` session binding needs to be added.

### FakeLLM for Extraction Failure

`ExtractionService.extract()` tries once, appends validation error, then retries once. Two bad responses trigger `ExtractionSchemaError`:
```python
FakeLLM(responses=["{}", "{}"])  # {} fails pydantic ExtractionResultSchema (missing param_value)
```
Both responses are consumed on the single `tick()` call for one failed email.

### Worker Imports After Refactor

After the split, `worker.py` imports look like:
```python
from apollo.domain.exceptions import ExtractionSchemaError, QuarantineError, SealingError
from apollo.services.quarantine import QuarantineService
```
`IntegrityError` catch block remains ABOVE the `ExtractionSchemaError` handler (no change to order).

### QuarantineService Full Import Block

```python
from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from jinja2 import Environment
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import CorpusRecord, QuarantineRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import ExtractionSchemaError, QuarantineError
from apollo.services.dispatch import AGENT_VERSION, SMTPClient

logger = logging.getLogger(__name__)
```

Lazy config import INSIDE the method body: `from apollo.config import settings as _settings`

### Established Patterns (carry forward)

1. `SessionFactory.begin()` for write transactions — never `session.commit()` manually
2. Re-fetch with `write_session.get(Model, id)` before writing — never operate on detached objects
3. `@requires(Compartment.EXTRACTION_WRITE)` on all write methods
4. `mypy --strict` — use `X | None` syntax, no `Optional[X]`
5. `ruff format .` + `ruff check .` before commit
6. `session.expire_all()` after `tick()` in integration tests
7. `FakeSMTPClient`, `FakeLLM`, `FakeIMAPClient` from `tests/utils.py`
8. `datetime.now(UTC)` — never `datetime.utcnow()`
9. Import `AGENT_VERSION` from `apollo.services.dispatch`, never redeclare
10. Alembic: never modify existing revisions, always chain new ones from `f6a7b8c9d0e1`
11. `module`-scoped testcontainer, `function`-scoped `db_session` with `DELETE + commit` cleanup

### Files to CREATE (NEW)

- `src/apollo/db/alembic/versions/a2b3c4d5e6f7_add_quarantine_record_table.py`
- `src/apollo/services/quarantine.py`
- `src/apollo/templates/clarification.jinja`
- `tests/unit/test_quarantine_service.py`
- `tests/integration/test_worker_quarantine.py`

### Files to UPDATE (EXISTING)

- `src/apollo/db/models.py` — add `QuarantineRecord` class; add `ForeignKey` import
- `src/apollo/domain/exceptions.py` — add `QuarantineError`
- `src/apollo/services/worker.py` — split exception handler; add `QuarantineService` + `QuarantineError` imports
- `tests/factories.py` — add `QuarantineRecordFactory`
- `tests/conftest.py` — bind `QuarantineRecordFactory._meta.sqlalchemy_session` in `db_session` fixture

### Files NOT to Touch

- `src/apollo/services/email_poller.py` — raw_email_bytes guard is correct as-is; clearing happens in quarantine service
- `src/apollo/services/extract.py` — no changes; ExtractionSchemaError is already raised correctly
- `src/apollo/services/seal.py` — no changes
- `src/apollo/services/dispatch.py` — AGENT_VERSION and SMTPClient imported from here
- `src/apollo/domain/types.py` — no new status needed (corpus_record stays DISPATCHED through quarantine)
- `src/apollo/domain/compartments.py` — EXTRACTION_WRITE already defined
- `src/apollo/mcp/` — no changes
- Existing Alembic migrations — never modify, only chain

### References

- Architecture (Quarantine Boundary, Process Patterns): `_bmad-output/planning-artifacts/architecture.md`
- Epics (Story 2.3 AC): `_bmad-output/planning-artifacts/epics.md`
- PRD (UJ-3 Clarification Loop): `_bmad-output/planning-artifacts/prds/prd-Apollo-2026-06-01/prd.md`
- Project Context (Double-Blind rule, Quarantine boundary): `_bmad-output/project-context.md`
- Previous Story patterns: `_bmad-output/implementation-artifacts/2-2-epistemological-sealing-ledger-commit-happy-path.md`
- Worker Phase 3 hook point: `src/apollo/services/worker.py:256`
- SMTPClient Protocol + AGENT_VERSION + template-parse pattern: `src/apollo/services/dispatch.py:38-43, 127-134`
- raw_email_bytes guard (why clearing is required): `src/apollo/services/email_poller.py:197-199`
- Two-transaction pattern reference: `src/apollo/services/seal.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Patch target for lazy settings import must be `patch("apollo.config.settings")` not `patch("apollo.services.quarantine.settings")` — the module attribute doesn't exist because the import is inside the method body.
- Regression in `test_worker_email_phase.py::test_tick_extraction_failure_does_not_raise` — assertion updated from `raw_email_bytes is not None` to `raw_email_bytes is None` because Story 2.3 quarantine correctly clears it to allow clarification reply ingestion.
- mypy UUID assignment errors in unit tests (`record.id = uuid4()` on real ORM instances) — fixed with `# type: ignore[assignment]`; pre-existing pattern across codebase (no SQLAlchemy mypy plugin configured).

### Completion Notes List

- All 4 ACs satisfied: quarantine_record created (AC1), double-blind isolation enforced in template (AC2), fail-operational SMTP + clarification_sent_at set on success (AC3), SealingError only logged (AC4).
- Two-transaction pattern: Transaction 1 atomically creates quarantine_record + clears raw_email_bytes; SMTP outside transactions; Transaction 2 sets clarification_sent_at only on SMTP success.
- ON DELETE CASCADE FK eliminates need for explicit DELETE in conftest.py cleanup.
- 123/123 tests pass (96 unit + 27 integration). `src/` passes `mypy --strict` with zero errors. `ruff check .` clean.

### File List

#### Created
- `src/apollo/db/alembic/versions/a2b3c4d5e6f7_add_quarantine_record_table.py`
- `src/apollo/services/quarantine.py`
- `src/apollo/templates/clarification.jinja`
- `tests/unit/test_quarantine_service.py`
- `tests/integration/test_worker_quarantine.py`

#### Modified
- `src/apollo/db/models.py` — added `QuarantineRecord` class + `ForeignKey` import
- `src/apollo/domain/exceptions.py` — added `QuarantineError`
- `src/apollo/services/worker.py` — split exception handlers; added `QuarantineService` + `QuarantineError` imports
- `tests/factories.py` — added `QuarantineRecordFactory`
- `tests/conftest.py` — bound `QuarantineRecordFactory._meta.sqlalchemy_session` in `db_session` fixture
- `tests/integration/test_worker_email_phase.py` — regression fix: updated `raw_email_bytes` assertion after quarantine behavior change

## Change Log

| Date | Change |
|------|--------|
| 2026-06-05 | Story implemented: quarantine_record table, QuarantineRecord ORM, QuarantineError, clarification.jinja template, QuarantineService (two-transaction pattern), worker Phase 3 exception handler split, 21 new tests (14 unit + 7 integration), regression fix in test_worker_email_phase.py |

## Review Findings

### Decision Needed

- [x] [Review][Defer] Unbounded quarantine retry loop — no max-attempt guard per `corpus_record_id`; Jane can receive infinite clarification emails if her responses are consistently unextractable. [worker.py + quarantine.py] — deferred, single trusted Asset, volume too low to matter

### Patches

- [x] [Review][Patch] Post-T1 coordinate guard: `if not coordinate:` check fires after T1 commits, leaving `raw_email_bytes=None` and a committed `quarantine_record` with no clarification email ever sent — record stuck permanently [quarantine.py:94-97]
- [x] [Review][Patch] Non-QuarantineError from `quarantine()` escapes `ExtractionSchemaError` handler and aborts Phase 3 for-loop — `ValueError`, `TemplateNotFound`, or `IntegrityError` inside `quarantine()` are not caught by inner `except QuarantineError:`, propagate up, and skip all remaining records in the tick batch [worker.py:ExtractionSchemaError handler]
- [x] [Review][Patch] Transaction 2 silent drop: if `fresh_qr = None` after SMTP success (e.g. CASCADE delete between T1 and T2), `clarification_sent_at` is never set and no warning is logged — audit trail silently incorrect [quarantine.py:138-144]
- [x] [Review][Patch] `IntegrityError` catch omits counter increment — when a concurrent seal fires, neither `extraction_success` nor `extraction_failed` is incremented; tick summary total < `len(matched_pairs)` [worker.py:IntegrityError handler]
- [x] [Review][Patch] `clarification_agent_version` value never asserted against `AGENT_VERSION` in integration test — only `is not None` checked; a bug setting it to `""` would pass all tests [tests/integration/test_worker_quarantine.py:203]

### Deferred

- [x] [Review][Defer] SIGKILL between T1 commit and SMTP send: `clarification_sent_at=NULL` is indistinguishable from intentional SMTP failure; no retry-clarification mechanism [quarantine.py] — deferred, design limitation of two-transaction pattern
- [x] [Review][Defer] `IntegrityError` catch scope too broad: catches any SQLAlchemy `IntegrityError`, not just the concurrent-seal unique constraint — future DB constraint violations silently misattributed as concurrent seals [worker.py:IntegrityError handler] — deferred, design choice
- [x] [Review][Defer] `QuarantineRecordFactory` generates dangling `corpus_record_id` (random UUID, no parent `CorpusRecord`) — FK violation if factory used standalone; dormant because factory is not used in any current test [tests/factories.py:30] — deferred, unused in current tests
- [x] [Review][Defer] SMTP counter fragility: `raise_on_nth=1` in `FakeSMTPClient` coupled to assumption that Phase 2 makes no SMTP calls; brittle to future test changes [tests/integration/test_worker_quarantine.py] — deferred, not currently failing
