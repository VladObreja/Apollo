---
baseline_commit: 60cd44584f88440050a192b58c3664a255fe8c50
---

# Story 4.1: Worker Resilience & E2E Repair

Status: review

## Story

As a Developer,
I want the worker's error-handling paths to be precise and the E2E suite to be trustworthy,
so that failure modes are correctly counted and CI red actually means something.

## Acceptance Criteria

1. **The 4 failing tests in `tests/e2e/test_epic2_e2e.py` are fixed to match Story 2.2/2.3 sealing + quarantine behavior and pass.**
   - `TestEpic2InboundIngestion::test_full_pipeline_status_stays_dispatched`
   - `TestEpic2InboundIngestion::test_raw_bytes_stored_even_when_llm_extraction_fails`
   - `TestEpic2InboundIngestion::test_second_tick_phase3_does_not_reingest_already_stored_reply`
   - `TestEpic2MultiSessionPipeline::test_extraction_failures_are_caught_tick_does_not_raise`

2. **The `IntegrityError` catch in worker Phase 3 sealing (`worker.py`) is scoped to the specific concurrent-seal unique constraint** (`ix_corpus_record_raw_hash`); any other `IntegrityError` propagates or is logged distinctly (not silently treated as "already sealed").

3. **The `IntegrityError` catch in `_validate_one` (`validate.py`) is scoped to the `validation_record.corpus_record_id` UNIQUE constraint**; other constraint violations are not silently logged as "already validated".

4. **`extraction_success` is no longer inflated** by concurrent-seal `IntegrityError` handling or by decorator-chain re-raises after a successful seal.

5. **`b""` empty `raw_email_bytes` no longer causes a permanent DISPATCHED retry loop** — a per-record retry limit or dead-letter mechanism is added (`seal.py`).

## Tasks / Subtasks

- [x] **Task 1 — Fix the 4 failing E2E tests** (AC: 1)
  - [x] `test_full_pipeline_status_stays_dispatched`: the docstring/assertion predates Story 2.2. Update to assert `record.status == TargetStatus.SEALED.value` (sealing now happens in Phase 3) and rename/update the docstring to reflect actual behavior.
  - [x] `test_raw_bytes_stored_even_when_llm_extraction_fails`: the docstring/assertion predates Story 2.3's quarantine design, which **intentionally clears `corpus_record.raw_email_bytes` to `None`** and copies the bytes into a new `quarantine_record` row (see `quarantine.py:94`, `db/models.py:150`). Update the test to query `QuarantineRecord` (filter by `corpus_record_id`) and assert `quarantine_record.raw_email_bytes is not None` instead. Also update the trailing `assert record.status == TargetStatus.DISPATCHED.value` — that part is still correct (quarantine does not advance status) and should stay.
  - [x] `test_second_tick_phase3_does_not_reingest_already_stored_reply`: same root cause as test 1 — after the first tick the record is `sealed`, not `dispatched`. Update `record_after_second.status` assertion to `TargetStatus.SEALED.value`. Strengthen the idempotency assertion: since the second tick's `fetch_new_session_emails` query filters on `status == DISPATCHED` (email_poller.py:182-186), the now-`sealed` record will simply not match on the second tick — assert that `record_after_first` and `record_after_second` have **identical** `raw_hash`, `extraction_payload`, and `sealed_at` (proving no re-sealing/duplication occurred), not just that status is unchanged.
  - [x] `test_extraction_failures_are_caught_tick_does_not_raise`: same fix as test 2 — assert against `QuarantineRecord.raw_email_bytes` (one per coordinate, via `corpus_record_id` FK) instead of `record.raw_email_bytes`. Keep `assert record.status == TargetStatus.DISPATCHED.value` (still correct post-quarantine).
  - [x] Run `tests/e2e/test_epic2_e2e.py` (requires `docker-compose up mailpit`, see Dev Notes) and confirm all 11 tests pass.

- [x] **Task 2 — Scope the Phase 3 sealing `IntegrityError` catch** (AC: 2, 4)
  - [x] In `worker.py` (~line 295-308), replace the heuristic `"corpus_record" in str(exc).lower() or "unique" in str(exc).lower()` check with an explicit check against the `ix_corpus_record_raw_hash` constraint name (the only unique constraint whose violation can occur during a concurrent seal — see Dev Notes for how to read the constraint name safely from `exc.orig`).
  - [x] If the constraint name does **not** match `ix_corpus_record_raw_hash`, treat it as an unexpected error: increment `extraction_failed` and `logger.error(...)` (do not silently warn).
  - [x] Verify (and add a test if missing) that `extraction_success` is incremented **only** when `SealingService.seal()` AND the enclosing `with SessionFactory.begin()` commit both succeed for *this* tick's call — i.e. a concurrent-seal `IntegrityError` on commit must never land in the `extraction_success` count. Trace the `_sealed_hash` variable lifecycle in `worker.py:241-336` to confirm this holds after your refactor (see Dev Notes for the exact control-flow concern).

- [x] **Task 3 — Scope the `_validate_one` `IntegrityError` catch** (AC: 3)
  - [x] In `validate.py` (~line 236-244), replace the bare `except IntegrityError:` with a check against the `validation_record.corpus_record_id` unique constraint name (verify the actual Postgres-generated name — see Dev Notes).
  - [x] If the constraint name doesn't match, re-raise (let it propagate to `validate_pending`'s generic `except Exception` handler at line 137-142, which already logs as `skipped` with `extraction crashed unexpectedly` — confirm this is the desired behavior or log distinctly before re-raising).
  - [x] **Critical**: `tests/unit/test_validate_service.py::test_idempotency_integrity_error_swallowed` (line 204) builds `SaIntegrityError("duplicate key", {}, Exception())` — `.orig` is a plain `Exception()` with **no `.diag` attribute**. Your constraint-name check must not crash (`AttributeError`) on this mock. Either read the constraint name defensively (`getattr`), or update `_make_integrity_error_factory()` in that test file to construct a mock `.orig` with a `.diag.constraint_name` matching the real constraint (preferred — makes the test actually exercise the new scoping logic). The same pattern exists in `tests/unit/test_fingerprint_service.py:54-60` for `fingerprint.py` — that file is **out of scope** for this story (not in the AC list), but don't let your `validate.py` change accidentally affect it.

- [x] **Task 4 — Fix the `b""` empty `raw_email_bytes` permanent-stuck case** (AC: 5)
  - [x] Read Dev Notes "AC5 investigation" carefully — the exact reproduction path is not fully proven by static analysis; write a failing test first (unit test on `SealingService.seal()` and/or an integration test seeding a `dispatched` record with `raw_email_bytes=b""`) to confirm the stuck state, then fix it.
  - [x] Implement either: (a) a per-record retry counter that, once exceeded, routes the record through `QuarantineService` (or a new dead-letter status) clearing `raw_email_bytes` so the record stops blocking; or (b) treat `raw_email_bytes == b""` the same as a quarantine-worthy extraction failure immediately (no retry needed) by extending `SealingService`/`worker.py`'s `SealingError` handling to call `QuarantineService.quarantine(...)` for this specific case.
  - [x] If a new DB column is needed (e.g. `extraction_attempts`), add an Alembic migration with `down_revision = "d2e3f4a5b6c7"` (current head — verify with `alembic heads` before starting, since Story 4.3 may also be in flight) and prove `upgrade head` → `downgrade base` → `upgrade head` per project convention.

- [ ] **Task 5 — Full verification** (AC: 1-5)
  - [ ] `uv run ruff check . && uv run ruff format --check .`
  - [ ] `uv run mypy src/ tests/`
  - [ ] `uv run pytest tests/unit/`
  - [ ] `uv run pytest tests/integration/` (requires Postgres testcontainer / Docker)
  - [ ] `docker-compose up -d mailpit && uv run pytest tests/e2e/`
  - [ ] If a migration was added: `uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head`

## Dev Notes

### Why these 4 E2E tests fail (confirmed by running the suite)

Ran `tests/e2e/test_epic2_e2e.py` (via `.venv/Scripts/python.exe -m pytest`, Mailpit was reachable): **4 failed, 7 passed**. All 4 failures are **stale assertions written before Story 2.2 (sealing) and Story 2.3 (quarantine) existed** — the production code is behaving per the now-finalized Story 2.2/2.3 contracts; the tests were never updated. This is not a production bug for AC1 — it is a test-maintenance task. Specifically:

- `test_full_pipeline_status_stays_dispatched` docstring literally says *"sealing transition belongs to Story 2.2"* — Story 2.2 is now done, so status correctly becomes `'sealed'`.
- `test_raw_bytes_stored_even_when_llm_extraction_fails` and `test_extraction_failures_are_caught_tick_does_not_raise` assert `corpus_record.raw_email_bytes is not None` after a quarantine — but `quarantine.py:94` (`fresh.raw_email_bytes = None`) is the **documented Story 2.3 design** ("Clears corpus_record.raw_email_bytes = None so the IMAP poller accepts Jane's reply", `quarantine.py:6`). The bytes live on durably on `quarantine_record.raw_email_bytes` (`db/models.py:150`, `nullable=False`) instead.
- `test_second_tick_phase3_does_not_reingest_already_stored_reply` has the same status-naming issue as test 1, plus its idempotency check is currently weak (just re-checks the stale `DISPATCHED` status). Strengthen per Task 1.

### IntegrityError scoping — reading the constraint name safely

`sqlalchemy.exc.IntegrityError.orig` is the underlying DBAPI exception. For psycopg2 unique-violation errors (`psycopg2.errors.UniqueViolation`), `exc.orig.diag.constraint_name` gives the Postgres constraint/index name. Pattern:

```python
constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
if constraint_name == "ix_corpus_record_raw_hash":
    ...  # expected concurrent-seal collision
else:
    ...  # unexpected — log distinctly / propagate
```

Constraint names confirmed from migrations:
- `ix_corpus_record_raw_hash` — unique index on `corpus_record.raw_hash` (`f6a7b8c9d0e1_add_sealing_columns.py:64`). This is the **only** constraint that can fire on a concurrent Phase 3 seal commit (two ticks both compute the same SHA-256 of identical `raw_email_bytes` and both attempt to set `raw_hash`).
- `validation_record.corpus_record_id` has `unique=True` set inline on the column in `op.create_table` (`c1d2e3f4a5b6_add_market_validation.py:36-41`), with no explicit constraint name → Postgres auto-generates `validation_record_corpus_record_id_key`. **Verify this exact string** against the real test DB before hardcoding it (e.g. temporarily `print(exc.orig.diag.constraint_name)` in a failing idempotency test, or query `information_schema.table_constraints` in the testcontainers Postgres) — auto-generated names are a Postgres convention, not an SQLAlchemy guarantee, and could differ if the table was created differently than expected.

### AC4 — extraction_success counting (worker.py:238-344)

Trace through `worker.py`'s per-record Phase 3 loop:
- `_sealed_hash` is set **inside** `with SessionFactory.begin() as write_session:` (line 269), but the actual **commit** happens at the `with` block's `__exit__` (after the `else` branch completes).
- `if _sealed_hash is not None: extraction_success += 1` (line 274) runs **after** the `with` block exits successfully.
- If the commit itself raises `IntegrityError` (e.g., the `ix_corpus_record_raw_hash` collision), the exception propagates from the `with` block's `__exit__` directly to `except IntegrityError as exc:` (line 295), **skipping** line 274 entirely — so today, `extraction_success` is *not* incremented in that case.

Today's code therefore appears correct on this specific point — but the AC explicitly calls out this risk, likely because **Task 2's refactor must preserve this property**. When you restructure the `except IntegrityError` branch, double-check that no code path can set `_sealed_hash` to non-None *and* fall through to line 274 *and* still hit a constraint violation on commit. Add a unit/integration test that simulates the concurrent-seal `IntegrityError` (two sequential `tick()` calls racing on the same dispatched record, or a mocked session that raises `IntegrityError` on commit after `seal()` mutated the in-memory record) and assert `extraction_success == 0` / `extraction_failed == 0` for that record (the "warn and skip" outcome — neither counter should move for a benign concurrent-seal collision).

### AC5 investigation — `b""` raw_email_bytes (open design question, needs a repro test first)

The original deferred note (code review of Story 2.2, 2026-06-05) says: *"b"" empty bytes causes permanent DISPATCHED retry loop — `if not raw_email_bytes` guard raises SealingError but the record stays DISPATCHED and retries on every tick forever."*

What's confirmed by reading the current code:
- `seal.py:49-52`: `if not record.raw_email_bytes: raise SealingError(...)`. Since `b""` is falsy in Python, `b""` and `None` hit this guard identically.
- `worker.py`'s `except SealingError as exc:` (line 324-329) increments `extraction_failed`, logs, and leaves the record `dispatched` with whatever `raw_email_bytes` it had (not cleared, unlike the quarantine path).
- `email_poller.py:198`: `if fresh.raw_email_bytes is not None: continue` — once `raw_email_bytes` is **any** non-`None` value (including `b""`), `fetch_new_session_emails` will never again select this record into `matched_pairs`, because it never re-stores bytes for it.

**What's NOT yet confirmed**: how `raw_email_bytes` becomes `b""` in the first place via the normal poller path. `EmailPollerService.fetch_new_session_emails` parses the email's `Subject` header to find a coordinate (`_COORD_RE`) before ever matching a record — `BytesParser().parsebytes(b"")` produces a message with no `Subject` header, so `coord` would be `None` and the email is skipped before `store_raw_email` is ever called. So a literal `b""` from `IMAPClientImpl.fetch_unseen_emails()` likely can't reach `store_raw_email` through today's matching logic.

**Recommendation**: don't try to reverse-engineer the exact production trigger from first principles — write the repro test directly:
1. Unit test: `SealingService.seal()` called with `record.raw_email_bytes = b""` → confirm `SealingError` raised (this part definitely already happens).
2. Integration test: seed a `dispatched` `CorpusRecord` with `raw_email_bytes=b""` already set (via factory, bypassing the poller — simulating "however it got there"), run `tick()`, and confirm the record is **permanently unrecoverable** (stays `dispatched` with `raw_email_bytes=b""` forever, no further ticks change anything).
3. Once the stuck state is reproduced, fix it via Task 4's option (a) or (b). Option (b) (route straight to `QuarantineService` for `b""`/empty bytes, same as an `ExtractionSchemaError`) is likely simpler and more consistent with the existing Story 2.3 pattern — but `QuarantineService.quarantine` currently requires `exc: ExtractionSchemaError` as a parameter type and raises `QuarantineError` if `raw_email_bytes is None` (it does NOT check for `b""` — `b"" is not None` is `True`, so it would proceed and write `quarantine_record.raw_email_bytes = b""`, which is schema-valid since the column is `nullable=False` not "non-empty"). You may need to adjust `quarantine.py`'s signature/call site or add a small adapter.

### Files this story touches (per sprint-change-proposal-2026-06-10.md Technical Impact)

- `src/apollo/services/worker.py` (Phase 3 IntegrityError scoping, AC2/AC4)
- `src/apollo/services/validate.py` (`_validate_one` IntegrityError scoping, AC3)
- `src/apollo/services/seal.py` (b"" handling, AC5 — likely also `worker.py` and possibly `quarantine.py`)
- `tests/e2e/test_epic2_e2e.py` (AC1)
- Possibly a new Alembic migration under `src/apollo/db/alembic/versions/` (AC5, only if a retry-counter column is the chosen design)

**Do not touch** `src/apollo/services/fingerprint.py` — it has a similar `except IntegrityError` pattern (line 171) but is explicitly **not** in this story's scope (it's covered by the Epic 3 retro's "already accepted" register).

### Architecture / project-context constraints relevant to this story

- **Domain-Specific Exceptions**: continue using `SealingError`, `QuarantineError`, `ExtractionSchemaError` — never bare `Exception`/`ValueError` (project-context.md "Critical Implementation Rules").
- **Structured Logging**: every new/changed log line in the Phase 3 loop must include `record_id` (and `session_id` if available) — follow the existing `extra={...}` pattern.
- **Strict Typing**: `mypy --strict` must pass — `exc.orig` is typed as `BaseException | None`; use `getattr` (not direct attribute access) when reading `.diag.constraint_name` to satisfy mypy without `# type: ignore`.
- **Testing**: unit tests (`tests/unit/`) — no DB/IO. Integration tests (`tests/integration/`) — real Postgres via testcontainers, no SQLite. E2E tests (`tests/e2e/`) require `docker-compose up mailpit` and are auto-skipped if Mailpit (127.0.0.1:8025) is unreachable.
- **CI note**: `.github/workflows/ci.yml` runs `tests/unit/` and `tests/integration/` but does **not** invoke `tests/e2e/` (no Mailpit service in CI). AC1's "pass in CI" should be read as "pass when run" — do not expand the CI workflow as part of this story (out of scope; flag as a new deferred item for Story 4.4/4.2 if you think it's warranted).

### Reference docs

- `_bmad-output/planning-artifacts/epics.md` — Epic 4 / Story 4.1 (source ACs)
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-10.md` — full triage rationale, "Technical Impact" section for file scope
- `_bmad-output/implementation-artifacts/epic-3-retro-2026-06-09.md` — retro that motivated this epic (A1/A3 actions)
- `_bmad-output/planning-artifacts/architecture.md` — "Known Limitations / Accepted Risk (V1)" section (9 items NOT in scope for this story)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4-6)

### Debug Log References

- Initial e2e run (`tests/e2e/test_epic2_e2e.py`, via Mailpit on 127.0.0.1:8025): 4 failed, 7 passed — confirmed AC1's expected starting state, all 4 failures were stale pre-Story-2.2/2.3 assertions.
- `docker exec apollo-db-1 psql` against `pg_constraint` confirmed `validation_record_corpus_record_id_key` is the real auto-generated Postgres unique constraint name for AC3.
- Final full suite: `tests/unit/` 167 passed, `tests/integration/` 59 passed, `tests/e2e/` 32 passed (Mailpit reachable). `ruff check`/`ruff format --check` clean for all files touched by this story. `mypy --strict` shows only pre-existing errors in out-of-scope files (`validate.py:185/188` predates this story per `git stash` diff; `mcp/tools.py`, `calibration.py`, `test_calibration_service.py`, `test_worker_calibration.py` untouched).

### Completion Notes List

- **AC1**: Updated 4 stale e2e assertions in `test_epic2_e2e.py` to match the finalized Story 2.2 (sealed status) and Story 2.3 (quarantine_record carries raw_email_bytes, corpus_record.raw_email_bytes cleared) contracts. Strengthened the second-tick idempotency test to compare `raw_hash`/`extraction_payload`/`sealed_at` across both ticks, not just status. All 11 tests in the file pass (32/32 across `tests/e2e/`).
- **AC2/AC4**: Added `_is_concurrent_seal_collision()` helper in `worker.py` reading `exc.orig.diag.constraint_name` defensively via `getattr`, scoped to `ix_corpus_record_raw_hash`. Non-matching `IntegrityError`s now increment `extraction_failed` and log at ERROR instead of being silently warned. Added `tests/unit/test_worker_helpers.py` (4 tests) and a new integration test (`TestWorkerConcurrentSealCollisionIntegration`) that seeds a colliding `raw_hash` and asserts the warn-and-rollback path, plus that no "unexpected integrity error" is logged. Confirmed via code trace + the new integration test that `extraction_success`/`extraction_failed` are both unaffected by a benign concurrent-seal collision (the commit-time `IntegrityError` propagates from `with SessionFactory.begin()`'s `__exit__` directly to the handler, skipping the success-counter line entirely — this property was preserved, not changed).
- **AC3**: Scoped `validate.py::_validate_one`'s `IntegrityError` catch to `validation_record_corpus_record_id_key` (verified against the live Postgres `pg_constraint` table). Non-matching violations now `raise` and propagate to `validate_pending`'s generic handler (logged as "validation crashed unexpectedly", counted as skipped). Updated `_make_integrity_error_factory()` in `test_validate_service.py` to build a realistic `.orig.diag.constraint_name` mock and added `test_unexpected_integrity_error_propagates`.
- **AC5**: Investigated the `b""` raw_email_bytes stuck-record scenario per Dev Notes. Wrote a failing integration test first (`TestWorkerEmptyRawBytesDeadLetter::test_stuck_empty_raw_bytes_record_is_dead_lettered` in `test_worker_quarantine.py`) that seeds a `dispatched` record with `raw_email_bytes=b""` and confirms it was previously permanently stuck (no quarantine_record, status/bytes unchanged after `tick()`). Implemented option (b) from the Dev Notes: added `SealingService.fetch_stuck_empty_bytes_records()` (queries `dispatched` + `raw_email_bytes == b""`) and a new Phase 3b step in `worker.py::tick()` that routes each found record through the existing `QuarantineService.quarantine()` with a synthetic `ExtractionSchemaError`. This creates a durable `quarantine_record` (`raw_email_bytes=b""`, valid since the column is `nullable=False` not "non-empty"), clears `corpus_record.raw_email_bytes` back to `None` (un-sticking the poller's `is not None` check), and leaves `status = dispatched` — consistent with existing Story 2.3 quarantine semantics. No new DB column or Alembic migration was needed.
- All 5 ACs verified; full regression suite green (unit 167, integration 59, e2e 32).

### File List

- `src/apollo/services/worker.py` — AC2/AC4 IntegrityError scoping (`_is_concurrent_seal_collision`, `_CONCURRENT_SEAL_CONSTRAINT`); AC5 new Phase 3b dead-letter step
- `src/apollo/services/validate.py` — AC3 IntegrityError scoping (`_VALIDATION_RECORD_UNIQUE_CONSTRAINT`)
- `src/apollo/services/seal.py` — AC5 new `SealingService.fetch_stuck_empty_bytes_records()`
- `tests/e2e/test_epic2_e2e.py` — AC1 fixes to 4 stale assertions
- `tests/unit/test_worker_helpers.py` — new file, AC2 unit tests for `_is_concurrent_seal_collision`
- `tests/unit/test_validate_service.py` — AC3 updated integrity-error mock + new propagation test
- `tests/integration/test_worker_sealing.py` — AC2/AC4 new concurrent-seal collision integration test
- `tests/integration/test_worker_quarantine.py` — AC5 new dead-letter integration test

### Change Log

- 2026-06-10: Implemented Story 4.1 (Worker Resilience & E2E Repair) — fixed 4 stale e2e assertions, scoped two `IntegrityError` catches to explicit constraint names, and added a dead-letter mechanism for `b""` raw_email_bytes records. All ACs satisfied; full suite green.
