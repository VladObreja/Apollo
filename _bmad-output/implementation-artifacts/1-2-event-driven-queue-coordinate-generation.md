---
baseline_commit: 3a4c701e3b7af0dd08b1c29883badbf78318d614
---
# Story 1.2: Event-Driven Queue & Coordinate Generation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the System Daemon,
I want to fetch pending targets up to a strict daily cap and generate blinded coordinates,
so that tasks are ready for dispatch without exposing the true target identity.

## Acceptance Criteria

1. **Given** there are pending targets in the database
   **When** the worker daemon executes an `apollo tick`
   **Then** it fetches a maximum of 5 targets per day using a `SELECT ... WHERE available_after <= NOW() FOR UPDATE SKIP LOCKED` query (enforcing the Age-In protocol)
2. **And** it pairs each target with a parameter and generates a cryptographically randomized, unique double-blind coordinate (e.g., `8A2F/9B4C`)
3. **And** it ensures the coordinate cannot be reverse-engineered or correlated to previous sessions (even if the underlying target is identical)
4. **And** the generated coordinate is securely saved to the record.

## Tasks / Subtasks

- [x] Extend DB Schema for Worker Queue (AC: 1, 2, 3, 4)
  - [x] Add `status` column to `corpus_record` (enum: `pending`, `queued`, `dispatched`, `sealed`) — Alembic migration
  - [x] Add `available_after` column (UTC-aware `DateTime`, nullable=False, default `NOW()`) — Alembic migration
  - [x] Add `double_blind_coordinate` column (`String`, nullable=True) — Alembic migration
  - [x] Add `queued_at` column (UTC-aware `DateTime`, nullable=True) — Alembic migration
  - [x] Add Postgres `NOTIFY` trigger: on `corpus_record` INSERT, emit `NOTIFY apollo_jobs, '{"event_type":"target_created","record_id":"<uuid>"}'`
  - [x] Update `CorpusRecord` SQLAlchemy model to reflect new columns
  - [x] Ensure migration is reversible (`downgrade` drops columns and trigger in reverse order)

- [x] Implement Coordinate Generation (Pure Domain Logic) (AC: 2, 3)
  - [x] Create `src/apollo/domain/coordinates.py`
  - [x] Implement `generate_double_blind_coordinate() -> str` using `secrets.token_hex` — 8 hex chars split as `XXXX/YYYY` (4 chars each)
  - [x] Document: coordinate is stateless and session-agnostic — no seed from target identity
  - [x] Unit test: assert format matches `^[0-9A-F]{4}/[0-9A-F]{4}$` (uppercase)
  - [x] Unit test: assert two calls with identical inputs produce different outputs (cryptographic randomness)

- [x] Implement Daily Cap Service (AC: 1) (AC: 1)
  - [x] Create `src/apollo/services/queue.py` with `QueueService` class
  - [x] Implement `count_dispatched_today() -> int`: counts `corpus_record` rows where `status = 'dispatched'` and `queued_at::date = NOW()::date` in UTC
  - [x] Implement `claim_pending_targets(limit: int) -> list[CorpusRecord]`: executes `SELECT ... WHERE status = 'pending' AND available_after <= NOW() FOR UPDATE SKIP LOCKED LIMIT {limit}` within a transaction
  - [x] Implement `assign_coordinate(record: CorpusRecord, session: Session) -> None`: sets `double_blind_coordinate` and `status = 'queued'` and `queued_at = NOW()`
  - [x] Decorate `claim_pending_targets` and `assign_coordinate` with `@requires(Compartment.TARGET_WRITE)`
  - [x] Compute `available_slots = 5 - count_dispatched_today()` before claiming; if `<= 0`, log and return

- [x] Implement `apollo tick` Worker Entrypoint (AC: 1, 4)
  - [x] Create `src/apollo/services/worker.py` — stateless tick function, no in-memory queue
  - [x] Implement `def tick() -> None`:
    1. Open DB session
    2. Call `QueueService.count_dispatched_today()` — compute available slots
    3. If slots available, call `QueueService.claim_pending_targets(limit=slots)`
    4. For each claimed record, call `QueueService.assign_coordinate(record, session)` 
    5. Commit transaction
    6. Log how many coordinates were assigned
  - [x] Wire `tick()` as the `apollo tick` CLI entrypoint in `pyproject.toml` scripts section (the `apollo` script currently calls `apollo:main` — update `src/apollo/main.py` to dispatch `tick`)

- [x] Update `src/apollo/main.py` Entrypoint
  - [x] Import and call `tick()` from `apollo.services.worker`
  - [x] Support basic `sys.argv` dispatch: `apollo tick` → `worker.tick()`; `apollo mcp` → `mcp.server.run()`

- [x] Unit Tests (AC: 2, 3)
  - [x] `tests/unit/test_coordinates.py`: Test `generate_double_blind_coordinate` format, uniqueness, no-seed correlation
  - [x] `tests/unit/test_queue_service.py`: Test daily cap logic with mocked session (inject `FakeSession` — no real DB)

- [x] Integration Tests (AC: 1, 4)
  - [x] `tests/integration/test_worker_tick.py`: Use `testcontainers` Postgres
    - Seed 7 `pending` records (2 already `dispatched` today)
    - Run `tick()` 
    - Assert exactly 3 records were updated to `queued` status with non-null `double_blind_coordinate`
    - Assert `FOR UPDATE SKIP LOCKED` idempotency: run `tick()` again, assert 0 additional records move to `queued`

### Review Findings

- [x] [Review][Decision] Daily Cap Logic Contradiction — The daily cap currently counts targets in 'dispatched' status. However, because the tick moves records to 'queued' (and they are not 'dispatched' until the email is sent in Story 1.3), multiple ticks can run in a day and each claim 5 records, exceeding the daily cap. We need to decide whether the cap count should include 'queued' records.
- [x] [Review][Decision] Deterministic Pick Order — The claim query has no order_by clause, meaning targets are claimed in arbitrary DB order. We should decide on the queue priority order (e.g., oldest config first via available_after.asc()).
- [x] [Review][Patch] Postgres Timezone Cast in Cap Count [src/apollo/services/queue.py:48]
- [x] [Review][Patch] Guard Primary Key id in Immutability Trigger [src/apollo/db/alembic/versions/a1b2c3d4e5f6_add_worker_queue_columns.py:48]
- [x] [Review][Patch] Check for duplicate coordinate collisions [src/apollo/services/queue.py:96]
- [x] [Review][Patch] Missing index on worker queue queries [src/apollo/db/alembic/versions/a1b2c3d4e5f6_add_worker_queue_columns.py:118]
- [x] [Review][Defer] No structured logging initialization [src/apollo/main.py:13] — deferred, pre-existing

## Dev Notes

### Critical Architecture Rules

- **Layer isolation is absolute:** `src/apollo/domain/coordinates.py` must import ONLY from Python stdlib (`secrets`, `string`). Zero DB, zero service imports.
- **`QueueService` routes through `services/` only.** It imports `CorpusRecord` from `db/models.py` and the session from `db/session.py`. The `mcp/` layer must NEVER call `QueueService` directly for write operations without a corresponding MCP tool (none in this story).
- **`@requires(Compartment.TARGET_WRITE)` is mandatory** on every method in `QueueService` that writes. Pattern is established in `services/target.py` — follow it exactly.
- **UTC everywhere:** All datetime comparisons use `datetime.now(UTC)`. Database columns are `DateTime(timezone=True)`. Never use `datetime.utcnow()` (deprecated).

### Coordinate Format Specification

The double-blind coordinate format is `XXXX/YYYY` where X and Y are uppercase hex digits.

**Implementation:**
```python
import secrets

def generate_double_blind_coordinate() -> str:
    """Generate a cryptographically random double-blind coordinate.
    
    Format: 8A2F/9B4C (4 uppercase hex chars, slash, 4 uppercase hex chars)
    Stateless: output is independent of any target identity.
    """
    part_a = secrets.token_hex(2).upper()  # 4 hex chars
    part_b = secrets.token_hex(2).upper()  # 4 hex chars
    return f"{part_a}/{part_b}"
```

**Why `secrets` not `random`:** `random` is not cryptographically secure. `secrets` uses OS entropy (`/dev/urandom` on Linux). This ensures the coordinate cannot be reverse-engineered or correlated.

### Worker Tick Pattern

The `tick()` function is designed to be **perfectly idempotent**. Calling it N times has the same effect as calling it once if no new state has been inserted between calls. This is achieved via:

1. `FOR UPDATE SKIP LOCKED` — prevents double-claiming records already being processed.
2. Status state machine: `pending → queued → dispatched → sealed`. The `tick` in this story only advances `pending → queued`. A locked `queued` record is skipped by any concurrent tick.

```python
# services/worker.py sketch (NOT final code — agent must implement fully)
from apollo.db.session import get_session_factory
from apollo.services.queue import QueueService

DAILY_TARGET_CAP = 5

def tick() -> None:
    SessionFactory = get_session_factory()
    with SessionFactory.begin() as session:
        dispatched_today = QueueService.count_dispatched_today(session)
        available_slots = DAILY_TARGET_CAP - dispatched_today
        if available_slots <= 0:
            # structured log: daily cap reached
            return
        records = QueueService.claim_pending_targets(session, limit=available_slots)
        for record in records:
            QueueService.assign_coordinate(record, session)
        # commit is automatic on context manager exit (SessionFactory.begin())
```

### DB Schema Changes (New Migration)

The migration must be a **new Alembic revision** chained to the latest existing head (`b4c7e1f02a9d`). Do not modify the existing migrations.

**New columns on `corpus_record`:**

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `status` | `String` (enum: `pending/queued/dispatched/sealed`) | NOT NULL | `'pending'` | server_default = `'pending'` |
| `available_after` | `DateTime(timezone=True)` | NOT NULL | `NOW()` | server_default = `sa.text("NOW()")` |
| `double_blind_coordinate` | `String` | NULL | — | Set on `queued` transition |
| `queued_at` | `DateTime(timezone=True)` | NULL | — | Set on `queued` transition |

**Postgres NOTIFY trigger (add in same migration):**

```sql
CREATE OR REPLACE FUNCTION notify_new_target()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_notify(
    'apollo_jobs',
    json_build_object('event_type', 'target_created', 'record_id', NEW.id)::text
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER corpus_record_notify_insert
  AFTER INSERT ON corpus_record
  FOR EACH ROW EXECUTE FUNCTION notify_new_target();
```

Drop both in `downgrade()` (trigger first, then function, then columns).

### `available_after` and the Age-In Protocol

When `configure_target` is called with `age_in_hours=N`, the `available_after` should be set to `NOW() + interval 'N hours'`. This is the Age-In protocol: the target is not eligible for pickup until `N` hours have elapsed.

**Important:** The `TargetService.create_target_configuration` in `services/target.py` must be updated to calculate and store `available_after` based on `age_in_hours`:

```python
from datetime import timedelta
available_after = config.created_at + timedelta(hours=config.target_metadata.age_in_hours or 0)
record.available_after = available_after
```

This is a **required extension** to `services/target.py` — the worker cannot function correctly without it.

### Status Column: Use String, Not Postgres Enum

Use `sa.String` with application-level Pydantic validation, not a Postgres `ENUM` type. Reason: Alembic reversibility — adding values to a Postgres `ENUM` requires `ALTER TYPE ... ADD VALUE` which is not transactional and breaks the reversibility CI gate.

Define a domain-level `TargetStatus` Python `enum.Enum` in `src/apollo/domain/types.py` for type safety in application code.

### Daily Cap Counting Logic

```python
# Count dispatched_today using UTC date comparison
from datetime import datetime, UTC, date
from sqlalchemy import func, cast, Date

today_utc: date = datetime.now(UTC).date()
count = session.query(func.count(CorpusRecord.id)).filter(
    CorpusRecord.status == "dispatched",
    cast(CorpusRecord.queued_at, Date) == today_utc
).scalar() or 0
```

**Why `queued_at` not `created_at`:** Targets can be configured days in advance. The cap is on *how many are dispatched today*, not how many were created.

### Previous Story Learnings (Story 1.1)

From the Story 1.1 review, the following patterns are **established and must be followed**:

1. **`SessionFactory.begin()` context manager** — used in `TargetService`. Use the same pattern in `QueueService`. Do NOT use bare `session.commit()`.
2. **`get_session_factory()` lazy factory** — all services call this. Never instantiate `sessionmaker` directly in services.
3. **`@requires(Compartment.X)` stub is in place** in `src/apollo/domain/compartments.py`. Import from there. Do not add new compartments without the architecture team's approval.
4. **`Compartment.TARGET_WRITE`** is the correct compartment for all target mutation operations. This story's queue operations are target mutations.
5. **Migration server defaults:** Always specify `server_default=sa.text("NOW()")` for datetime columns and `server_default=sa.text("gen_random_uuid()")` for UUID PKs. Story 1.1 review caught this as a critical patch.
6. **`mypy --strict` must pass.** Every new function must have fully typed signatures. `Optional[X]` must use `X | None` in Python 3.12 style or `Optional` import.
7. **`ruff` formatting** — run `uv run ruff format .` and `uv run ruff check .` before committing.
8. **`tests/conftest.py` exists** — check it before adding test fixtures. Use the established `testcontainers` pattern.
9. **Table name is singular `corpus_record`** (reviewed and confirmed in story 1.1). Do not rename.

### Files to CREATE (NEW)

- `src/apollo/domain/coordinates.py` — coordinate generation function
- `src/apollo/domain/types.py` — `TargetStatus` enum (if not already exists)
- `src/apollo/services/queue.py` — `QueueService` class
- `src/apollo/services/worker.py` — `tick()` stateless function
- `src/apollo/db/alembic/versions/<rev_id>_add_worker_queue_columns.py` — new Alembic migration
- `tests/unit/test_coordinates.py` — coordinate unit tests
- `tests/unit/test_queue_service.py` — queue service unit tests (mocked session)
- `tests/integration/test_worker_tick.py` — integration test for full tick cycle

### Files to UPDATE (EXISTING)

- `src/apollo/db/models.py` — add `status`, `available_after`, `double_blind_coordinate`, `queued_at` columns to `CorpusRecord`
- `src/apollo/services/target.py` — calculate and set `available_after` on `CorpusRecord` insert
- `src/apollo/main.py` — dispatch `apollo tick` to `worker.tick()` and `apollo mcp` to `server.run()`
- `pyproject.toml` — verify `apollo` script entry; add `types-sqlalchemy` or similar to dev deps if `mypy` requires stubs

### Files NOT to Touch

- `src/apollo/domain/models.py` — Pydantic domain models are complete for this story
- `src/apollo/domain/compartments.py` — compartments are finalized for this story
- `src/apollo/mcp/tools.py` — no MCP changes in this story
- `src/apollo/mcp/server.py` — no changes
- Existing Alembic migrations — never modify, only chain

### Testing Strategy

**Unit (no DB, no IO):**
- `test_coordinates.py`: Pure function, assert format and randomness
- `test_queue_service.py`: Inject a `FakeSQLAlchemySession` that records what was called. Assert `SKIP LOCKED` query structure and coordinate assignment mutation

**Integration (real Postgres via testcontainers):**
- `test_worker_tick.py`: Full end-to-end `tick()` against a real schema
- Seed using SQLAlchemy ORM inserts (not raw SQL per architecture rules)
- Verify state transitions in DB after tick

### Project Structure Notes

All new files must respect the strict layering:
```
src/apollo/
├── domain/
│   ├── coordinates.py   ← NEW: secrets-based coord generation (no imports from db/services)
│   └── types.py         ← NEW (or extend): TargetStatus enum
├── db/
│   ├── models.py        ← UPDATE: add 4 new columns
│   └── alembic/versions/
│       └── <rev>_add_worker_queue_columns.py  ← NEW chained migration
├── services/
│   ├── queue.py         ← NEW: QueueService with SKIP LOCKED + daily cap
│   ├── worker.py        ← NEW: tick() stateless entrypoint
│   └── target.py        ← UPDATE: set available_after on record insert
└── main.py              ← UPDATE: CLI dispatch for tick/mcp
```

### References

- Project Context: [project-context.md](file:///c:/Apollo/_bmad-output/project-context.md)
- Architecture: [architecture.md](file:///c:/Apollo/_bmad-output/planning-artifacts/architecture.md)
- Epics: [epics.md](file:///c:/Apollo/_bmad-output/planning-artifacts/epics.md)
- Previous Story (1.1): [1-1-initialize-domain-target-configuration-mcp.md](file:///c:/Apollo/_bmad-output/implementation-artifacts/1-1-initialize-domain-target-configuration-mcp.md)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- **Root cause of test failure:** `alembic/env.py` unconditionally overwrote the Alembic config URL with `settings.database_url`, ignoring URLs set by the test fixture (testcontainers). Fixed by checking the existing URL before overriding.
- **Secondary fix:** `apollo/db/session.py` used the frozen `Settings` singleton (instantiated at import time) for the DB URL. Patching `DATABASE_URL` env var after import had no effect. Fixed by reading `os.environ.get("DATABASE_URL")` directly at engine-creation time.
- **Test isolation:** `db_session` fixture rolled back only its own uncommitted changes, but `_seed_records` committed directly and `tick()` used a separate session. Fixed by truncating `corpus_record` at the start of each test.

### Completion Notes List

- All 7 task groups implemented and passing: DB schema migration (4 columns + NOTIFY trigger + updated immutability trigger), coordinate generation, QueueService (daily cap, SKIP LOCKED, coordinate assignment), worker tick, main.py CLI dispatch, unit tests (19 tests), integration tests (8 tests).
- 33 tests pass total (25 unit + 8 integration). `mypy --strict` clean. `ruff check` and `ruff format` clean.
- Three infrastructure bugs resolved during this session (env.py URL override, session.py frozen-Settings bypass, test isolation via DELETE before each test).

### File List

- `src/apollo/domain/coordinates.py` — NEW: cryptographic coordinate generation
- `src/apollo/domain/types.py` — NEW: TargetStatus enum
- `src/apollo/services/queue.py` — NEW: QueueService with SKIP LOCKED + daily cap
- `src/apollo/services/worker.py` — NEW: stateless tick() entrypoint
- `src/apollo/main.py` — NEW: CLI dispatch for tick/mcp
- `src/apollo/db/models.py` — UPDATED: 4 new mutable lifecycle columns
- `src/apollo/services/target.py` — UPDATED: sets available_after from age_in_hours
- `src/apollo/db/alembic/versions/a1b2c3d4e5f6_add_worker_queue_columns.py` — NEW: chained Alembic migration
- `src/apollo/db/alembic/env.py` — UPDATED: don't override URL set by caller (test fixture fix)
- `src/apollo/db/session.py` — UPDATED: read DATABASE_URL from env at engine-creation time
- `tests/unit/test_coordinates.py` — NEW: 6 coordinate unit tests
- `tests/unit/test_queue_service.py` — NEW: 13 queue service unit tests (mocked session)
- `tests/integration/test_worker_tick.py` — NEW: 8 integration tests (testcontainers Postgres)
- `tests/integration/__init__.py` — NEW: package marker

### Change Log

- 2026-06-02: Implemented all tasks for Story 1.2 — DB schema extension (4 columns + triggers), coordinate generation, QueueService, worker tick, CLI dispatch, unit + integration tests. Fixed three test infrastructure bugs: alembic env.py URL override, frozen-Settings session bypass, inter-test isolation via DELETE truncation.
