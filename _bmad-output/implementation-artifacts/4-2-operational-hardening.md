---
baseline_commit: 5afc82ba6be4141e453272d10962d0fd70239910
---

# Story 4.2: Operational Hardening

Status: review

## Story

As the Admin,
I want config and parsing edge cases handled,
so that the system degrades safely under real-world conditions.

## Acceptance Criteria

1. **A startup warning is logged when `imap_use_ssl=False`** (`config.py`).
2. **`expiry_at` ISO parsing in `configure_target` (`mcp/tools.py`) correctly handles non-Z-suffix offsets and date-only strings, producing UTC-aware datetimes.**
3. **Sealed records permanently missing their environmental fingerprint row (due to a crash between seal-commit and fingerprint-write) are detected and backfilled on a subsequent tick** (`worker.py`).

## Tasks / Subtasks

- [x] **Task 1 — `imap_use_ssl=False` startup warning** (AC: 1)
  - [x] In `src/apollo/config.py`, add `import logging` and a module-level `logger = logging.getLogger(__name__)`.
  - [x] Add a `model_post_init(self, __context: Any) -> None` method to `Settings` (Pydantic v2 lifecycle hook — runs once after the model is fully constructed, including for the module-level `settings = Settings()` singleton). `Any` is already imported from `typing`.
  - [x] Inside `model_post_init`, if `self.imap_use_ssl is False`, call `logger.warning(...)` with a clear message (e.g. `"apollo.config: IMAP connection is unencrypted (imap_use_ssl=False)"`) and structured `extra={"imap_use_ssl": False}` (project convention — every log line uses `extra={...}`, see Dev Notes).
  - [x] `model_post_init` only **reads** `self.*` — it must not assign new attributes, since `model_config = SettingsConfigDict(..., frozen=True)` forbids attribute mutation after init. Logging a warning does not mutate the model, so this is safe.
  - [x] Add a test to `tests/unit/test_dispatch_service.py::TestSettingsDefaults` (or a new class in the same file) that uses `caplog` to assert the warning is logged when `Settings()` is constructed with `imap_use_ssl` unset/False (the default), and that **no** warning is logged when `IMAP_USE_SSL=true`. Follow the existing env-var save/restore pattern used by `test_imap_defaults_are_set` (lines ~234-266) — set `caplog.set_level(logging.WARNING, logger="apollo.config")` before constructing `Settings()`.

- [x] **Task 2 — `expiry_at` ISO parsing handles date-only strings and non-Z offsets** (AC: 2)
  - [x] In `src/apollo/mcp/tools.py`, extract the existing `expiry_at` parsing block (lines 54-67) into a small private pure function, e.g. `_parse_expiry_at(expiry_at: str | None) -> datetime | None`, and call it from `configure_target`. This makes the parsing logic unit-testable without touching the DB (current `configure_target` always calls `TargetService.create_target_configuration`, which requires a DB).
  - [x] Inside `_parse_expiry_at`:
    - Keep `datetime.fromisoformat(expiry_at.replace("Z", "+00:00"))` — confirmed working on Python 3.12 for `Z`-suffixed AND non-`Z` offsets (`+02:00`, `-05:00`, `+0200` all parse correctly with `tzinfo` set; verified via direct interpreter test during story creation).
    - **Remove** the current `if parsed.tzinfo is None: raise ValueError("expiry_at must include a timezone offset...")` branch. This is the actual bug: `datetime.fromisoformat("2026-06-10")` (a date-only string) returns a **naive** `datetime(2026, 6, 10, 0, 0)`, which today is rejected outright.
    - **Replace** that rejection with: `if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=UTC)`. This makes date-only strings (`"2026-06-10"`) and naive full datetimes (`"2026-06-10T21:00:00"`) both resolve to UTC-aware datetimes (midnight UTC / as-given UTC respectively), consistent with NFR6 (UTC-Native Time Architecture) and this story's "degrade safely" framing.
    - Keep `expiry_dt = parsed.astimezone(UTC)` as the final step (a no-op for already-UTC values, correct conversion for non-UTC offsets).
    - Keep the `try/except ValueError` wrapping `fromisoformat` for genuinely malformed strings (e.g. `"not-a-date"`) — that error message is still correct and should still raise `ValueError`.
  - [x] Update the `expiry_at` docstring in `configure_target` to describe the new, more permissive behavior — e.g. "ISO-8601 datetime or date. Accepts `Z` suffix, explicit `+HH:MM`/`-HH:MM` offsets, or a bare date/naive datetime (assumed UTC)."
  - [x] Create `tests/unit/test_mcp_tools.py` and add a test class (e.g. `TestParseExpiryAt`) covering:
    - `None` → `None`
    - `"2026-06-10T21:00:00Z"` → `datetime(2026, 6, 10, 21, 0, tzinfo=UTC)`
    - `"2026-06-10T21:00:00+02:00"` → `datetime(2026, 6, 10, 19, 0, tzinfo=UTC)` (non-Z offset, converted to UTC)
    - `"2026-06-10T21:00:00-05:00"` → `datetime(2026, 6, 11, 2, 0, tzinfo=UTC)`
    - `"2026-06-10"` (date-only) → `datetime(2026, 6, 10, 0, 0, tzinfo=UTC)`
    - `"2026-06-10T21:00:00"` (naive datetime, no offset) → `datetime(2026, 6, 10, 21, 0, tzinfo=UTC)`
    - `"not-a-date"` → raises `ValueError`
    - All returned datetimes must have `.tzinfo is not None` (i.e. `result.tzinfo == UTC` or equivalent) — assert this explicitly since AC2 requires "UTC-aware datetimes".

- [x] **Task 3 — Backfill missing `env_fingerprint` rows for sealed records** (AC: 3)
  - [x] In `src/apollo/services/fingerprint.py`, add a new static method `FingerprintService.fetch_sealed_records_missing_fingerprint(session: Session, limit: int = 100) -> list[CorpusRecord]`. Decorate it `@requires(Compartment.EXTRACTION_WRITE)` — this matches the existing precedent in `seal.py::fetch_stuck_empty_bytes_records` (also a read-only `SELECT` decorated `EXTRACTION_WRITE`, flagged as deferred item W3 from Story 4.1 — **do not** introduce a new `EXTRACTION_READ` compartment as part of this story; follow the established pattern for consistency).
    - Query: `CorpusRecord` rows where `status == TargetStatus.SEALED.value` AND there is no matching `EnvFingerprint` row. Use a `select(CorpusRecord).outerjoin(EnvFingerprint, EnvFingerprint.corpus_record_id == CorpusRecord.id).where(and_(CorpusRecord.status == TargetStatus.SEALED.value, EnvFingerprint.id.is_(None))).limit(limit)`. `EnvFingerprint` is already imported in `fingerprint.py`; add new imports `from sqlalchemy import and_, select` and `from apollo.domain.types import TargetStatus` (mirrors `seal.py`'s existing import block, lines 12 and 19 — same pattern, different file).
  - [x] In `src/apollo/services/worker.py`, add a small private helper `_extract_measurement_timestamp(extraction_payload: dict[str, Any] | None) -> datetime | None`:
    - `extraction_payload` is the JSONB dict produced by `ExtractionResultSchema.model_dump(mode="json")` at seal time (`seal.py:57`) — `measurement_timestamp` is either `None` or an ISO-8601 string (e.g. `"2026-06-06T10:00:00Z"`).
    - If `extraction_payload` is `None`, return `None`.
    - Read `extraction_payload.get("measurement_timestamp")`. If it's a non-empty `str`, parse it with `datetime.fromisoformat(value.replace("Z", "+00:00"))` and return it (it will already be tz-aware per `ExtractionResultSchema.validate_tz`). Otherwise return `None`.
    - Use `isinstance(value, str)` as a type guard (mypy strict — `dict[str, Any].get(...)` returns `Any`).
    - `worker.py` currently has **no** `typing` or `datetime` imports at all — add both `from typing import Any` and `from datetime import datetime` near the top of the file (alongside the existing `import logging` / `from pathlib import Path` block, lines 15-16). `FingerprintService` is already imported (lines 35-39); no change needed there.
  - [x] Add a new **Phase 3c** in `tick()`, placed after the existing Phase 3b dead-letter block (~line 405) and before Phase 4 validation:
    - `with SessionFactory() as read_session: missing_fp_records = FingerprintService.fetch_sealed_records_missing_fingerprint(read_session)`
    - For each record: `measurement_ts = _extract_measurement_timestamp(record.extraction_payload)`, then `FingerprintService.attach(record, measurement_ts, env_client, SessionFactory)`.
    - `FingerprintService.attach` already (a) falls back to `record.received_at` then `datetime.now(UTC)` if `measurement_timestamp` is `None` (fingerprint.py:113-115), and (b) silently swallows `IntegrityError` on insert if a fingerprint row already exists (fingerprint.py:168-176, the same idempotency guard added in Story 4.1) — so this phase is safe to re-run every tick with no extra guards needed.
    - Add a per-record `logger.info("apollo.worker.tick: backfilling missing env_fingerprint", extra={"record_id": str(record.id)})` and a phase-summary log mirroring Phase 3b's pattern: `if missing_fp_records: logger.info("apollo.worker.tick: fingerprint backfill phase complete", extra={"backfilled": len(missing_fp_records)})`.
  - [x] Add an integration test in `tests/integration/test_worker_fingerprint.py` (new test class, e.g. `TestWorkerFingerprintBackfill`):
    - Seed a `CorpusRecord` directly via `CorpusRecordFactory` with `status=TargetStatus.SEALED.value`, `sealed_at=<now>`, `raw_hash=<some hex string>`, `extraction_payload={"param_value": 85.0, "measurement_timestamp": "2026-06-06T10:00:00+00:00", "asset_location": None, "sleep_quality": None, "psychological_state": None, "social_field": None, "asset_notes": None}` (matches `ExtractionResultSchema.model_dump(mode="json")` shape), and **no** `EnvFingerprint` row.
    - Run `tick(imap_client=FakeIMAPClient([]), llm_client=FakeLLM([]), smtp_client=FakeSMTPClient(), env_client=FakeEnvDataClient(kp=2.5, solar_wind=400.0), market_client=FakeMarketDataClient())` — empty `FakeLLM([])` is safe because no IMAP emails means `ExtractionService.extract` is never called.
    - Assert an `EnvFingerprint` row now exists for `record.id`, with `measurement_timestamp == datetime(2026, 6, 6, 10, 0, tzinfo=UTC)`, `kp_index == 2.5`, `solar_wind_speed == 400.0`, `retrieval_status == "ok"`.
    - Add a second test: a `SEALED` record that **already has** an `EnvFingerprint` row must **not** be touched again (no duplicate row, existing row's `fingerprinted_at` unchanged) — proves the `outerjoin`/`is_(None)` filter works and Phase 3c doesn't reprocess already-fingerprinted records.
    - Add a third test: a `SEALED` record with `extraction_payload={"param_value": 50.0}` (no `measurement_timestamp` key at all — older/minimal payload) must still get backfilled without crashing, falling back to `record.received_at`/`datetime.now(UTC)` per `FingerprintService.attach`'s existing fallback.
  - [x] Add unit tests for `_extract_measurement_timestamp` to `tests/unit/test_worker_helpers.py` (mirrors the existing `_is_concurrent_seal_collision` unit tests added in Story 4.1): `None` payload → `None`; payload with valid ISO string (`Z`-suffixed and offset forms) → correct tz-aware `datetime`; payload missing the key → `None`; payload with `"measurement_timestamp": null` → `None`.

- [x] **Task 4 — Full verification** (AC: 1-3)
  - [x] `uv run ruff check . && uv run ruff format --check .` — must be clean for all files touched by this story.
  - [x] `uv run mypy src/ tests/` — zero new errors in files touched by this story (pre-existing errors in untouched files, e.g. `closure.py`, are out of scope per Story 4.1's precedent).
  - [x] `uv run pytest tests/unit/` — all pass.
  - [x] `uv run pytest tests/integration/` (requires Postgres testcontainer / Docker) — all pass.
  - [x] `docker-compose up -d mailpit && uv run pytest tests/e2e/` — all pass (no e2e changes expected, but Phase 3c runs on every tick and must not break existing e2e flows).

## Dev Notes

### Scope and what NOT to touch

This story is **pure hardening** — no new DB tables, no new Alembic migration, no new MCP tools. Three small, independent changes across `config.py`, `mcp/tools.py`, and `fingerprint.py`/`worker.py`. Do not refactor unrelated code in these files.

- **Do not** touch `seal.py`'s `fetch_stuck_empty_bytes_records` or the Phase 3b dead-letter block (Story 4.1, done) beyond placing the new Phase 3c after it.
- **Do not** add a new `Compartment.EXTRACTION_READ` — the existing `fetch_stuck_empty_bytes_records` precedent (a read-only query decorated `EXTRACTION_WRITE`) is the established pattern; mirror it for `fetch_sealed_records_missing_fingerprint`. `@requires` is a non-functional stub (see `domain/compartments.py`) so this has no runtime effect either way — it's a documentation/consistency convention only.
- **Do not** expand `.github/workflows/ci.yml` — out of scope (same note as Story 4.1).

### AC1 — `imap_use_ssl` warning: why `model_post_init`

`Settings` is instantiated once at module import time (`config.py:49`, `settings = Settings()`), and `model_config` sets `frozen=True`. Pydantic v2's `model_post_init(self, __context: Any) -> None` hook runs automatically after `__init__` completes and is the idiomatic place for "derived/validation side-effects after full construction" — it does not require mutating `self`, so it's compatible with `frozen=True`. A `field_validator` would not work well here because it would need to validate `imap_use_ssl` in isolation without full model context, and validators run *during* construction (before all fields may be set) — `model_post_init` is simpler and correct.

```python
import logging
...
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    ...
    def model_post_init(self, __context: Any) -> None:
        if not self.imap_use_ssl:
            logger.warning(
                "apollo.config: IMAP connection is unencrypted (imap_use_ssl=False)",
                extra={"imap_use_ssl": False},
            )
```

Note: `caplog` in pytest captures log records regardless of whether `setup_logging()` (main.py) has run — propagation to the root logger is on by default, so `caplog.set_level(logging.WARNING, logger="apollo.config")` will see the warning even though `Settings()` is constructed at import time in test modules. If `Settings()` was already constructed once at `apollo.config` module import (before the test sets up `caplog`), the test must construct a **fresh** `Settings()` instance inside the test (as `test_imap_defaults_are_set` already does) — the module-level `settings` singleton's `model_post_init` will have already fired before `caplog` was attached.

### AC2 — confirmed parsing behavior on Python 3.12 (verified during story creation)

Ran the current `expiry_at.replace("Z", "+00:00")` + `datetime.fromisoformat(...)` against this project's pinned Python 3.12.3:

| Input | `fromisoformat` result | `tzinfo` |
|---|---|---|
| `"2026-06-10T21:00:00Z"` | `2026-06-10 21:00:00+00:00` | `UTC` |
| `"2026-06-10T21:00:00+02:00"` | `2026-06-10 21:00:00+02:00` | `UTC+02:00` |
| `"2026-06-10T21:00:00-05:00"` | `2026-06-10 21:00:00-05:00` | `UTC-05:00` |
| `"2026-06-10T21:00:00+0200"` (no colon) | `2026-06-10 21:00:00+02:00` | `UTC+02:00` |
| `"2026-06-10"` (date-only) | `2026-06-10 00:00:00` | **`None`** ← currently raises |
| `"2026-06-10T21:00:00"` (naive) | `2026-06-10 21:00:00` | **`None`** ← currently raises |

So **non-Z offsets already work correctly** today (the `.astimezone(UTC)` call converts them properly) — the AC's "non-Z-suffix offsets" clause is mostly about **locking this in with a regression test**, since it was flagged as an "edge case" in the original Story 3.1 deferred item (`3-1-ground-truth-market-validation.md:790`: *"expiry_at ISO parsing in MCP tool: only handles Z-suffix; edge cases for date-only or non-UTC offsets"*). The **actual bug** is the date-only / fully-naive cases, which currently hit the `if parsed.tzinfo is None: raise ValueError(...)` branch added later (Story 3.2 review patch P7, `3-2-flexible-closure-ceremony-dispatch.md:639`, which fixed a *different* problem — naive datetimes being silently stored and crashing later comparisons). Removing that `raise` and instead defaulting naive results to UTC fixes AC2 **without reintroducing P7's bug**, because the result is always made tz-aware before being stored (`parsed.replace(tzinfo=UTC)` then `.astimezone(UTC)`).

### AC3 — fingerprint backfill: data shapes and query pattern

- `corpus_record.extraction_payload` is a `JSONB` column (`db/models.py:101-103`) populated by `SealingService.seal()` via `extraction.model_dump(mode="json")` (`seal.py:57`), where `extraction: ExtractionResultSchema` (`domain/models.py:100-171`). The `measurement_timestamp` field is `datetime | None`, validated tz-aware by `ExtractionResultSchema.validate_tz` (`domain/models.py:126-130`) — so if present in `extraction_payload`, it is **guaranteed** to have been tz-aware at seal time, and `model_dump(mode="json")` serializes it to an ISO-8601 string with offset (e.g. `"2026-06-06T10:00:00Z"` or `"+00:00"`).
- `env_fingerprint.corpus_record_id` has `unique=True` (`db/models.py:179-184`) — one-to-one with `corpus_record`. The `outerjoin` + `EnvFingerprint.id.is_(None)` pattern is the standard SQLAlchemy "anti-join" / "find rows with no matching child" idiom.
- Reuse `FingerprintService.attach` as-is — **do not** duplicate its NOAA-fetch / LST / status-determination logic. Phase 3c's only job is to (a) find sealed records lacking a fingerprint, (b) recover the best-available `measurement_timestamp` from `extraction_payload`, and (c) call `attach`.
- `FingerprintService.attach` is itself fully fail-operational (outer `try/except Exception` at `fingerprint.py:110/183-187`) — Phase 3c does not need its own try/except around `attach` for the *fingerprint write* itself, but per worker.py convention, wrap the loop body in the same per-record `try/except Exception` style as Phase 3b if you want defense-in-depth against `_extract_measurement_timestamp` raising on a malformed payload (it shouldn't, given the `isinstance` guard, but matching the file's existing defensive style is consistent).

### Project-context constraints relevant to this story

- **Structured Logging**: every new/changed log line must use `extra={...}` and include `record_id` where applicable (project-context.md "Code Quality & Style Rules").
- **Strict Typing**: `mypy --strict` must pass. `extraction_payload: dict[str, Any] | None` — `.get(...)` returns `Any`; use `isinstance()` type guards, not casts, per "No Magic" rule.
- **Domain-Specific Exceptions**: not directly relevant to this story (no new exception types needed) — Phase 3c reuses existing fail-operational paths.
- **Testing**: unit tests (`tests/unit/`) — no DB/IO (the `_extract_measurement_timestamp` and `_parse_expiry_at` helpers are pure functions, perfect for unit tests). Integration tests (`tests/integration/`) — real Postgres via testcontainers for the `fetch_sealed_records_missing_fingerprint` query and full Phase 3c tick behavior. No SQLite shortcuts.
- **`@requires` decorator**: non-functional stub (`domain/compartments.py`) — apply it for documentation consistency, do not attempt to make it "work".

## Previous Story Intelligence (from Story 4.1)

- Story 4.1 (`4-1-worker-resilience-and-e2e-repair.md`, status `done`) added Phase 3b (dead-letter for `b""` raw_email_bytes) immediately after the Phase 3 extraction loop and before Phase 4 validation — **Phase 3c (this story) goes immediately after Phase 3b**, same position in the pipeline, same per-phase summary-log convention (`if <records>: logger.info("apollo.worker.tick: ... phase complete", extra={...})`).
- Story 4.1 established `tests/utils.py` as the shared home for cross-test fakes/helpers (`FakeDiag`, `FakeOrig`, `FakeEnvDataClient`, etc. — see `tests/utils.py`, consolidated during 4.1's review). If you need any new shared test helper for this story, add it there rather than duplicating in a single test file — though for this story's scope, existing fakes (`FakeEnvDataClient`, `FakeIMAPClient`, `FakeLLM`, `FakeSMTPClient`, `FakeMarketDataClient`) should be sufficient.
- Story 4.1's review caught several "counted twice" / "labeled wrong" issues (P1-P4) by being precise about *which* log line / counter / quarantine_reason a new code path uses. Apply the same precision here: Phase 3c must use its **own** distinct log messages (not reuse Phase 3's "fingerprint failed after sealing" message, which is for the *synchronous* post-seal path) so backfill volume is separately observable.
- Story 4.1 confirmed `tests/integration/test_worker_quarantine.py::TestWorkerEmptyRawBytesDeadLetter::test_stuck_empty_raw_bytes_record_is_dead_lettered` as the template for "seed a record directly via factory with a specific status, run `tick()` with empty IMAP/LLM inputs, assert the new phase's effect" — Task 3's integration tests follow this same shape.

## Git Intelligence Summary

Recent commits relevant to this story's files:
- `5afc82b feat(story-4.1): worker resilience & e2e repair` — added `_is_concurrent_seal_collision`, Phase 3b, `tests/unit/test_worker_helpers.py`, and the `tests/utils.py` consolidation (`FakeDiag`/`FakeOrig`). Follow this commit's patterns for: new `worker.py` phases, new `tests/unit/test_worker_helpers.py` test additions, and structured per-phase logging.
- `0413890 feat(epics-2-3): ...` — introduced `fingerprint.py`, `EnvFingerprint`, `FingerprintService.attach`, and `tests/integration/test_worker_fingerprint.py` / `tests/unit/test_fingerprint_service.py` (Story 2.4). This is the baseline being extended in Task 3.
- No commits have touched `config.py` or `mcp/tools.py` since `362ebf5` (Story 2.1 review patches) and `0413890` (Story 3.1's `expiry_at` addition) respectively — both files are otherwise stable.

## Project Context Reference

- `_bmad-output/planning-artifacts/epics.md` — Epic 4 / Story 4.2 (canonical ACs, reproduced above verbatim).
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-10.md` — triage rationale; "Technical Impact" confirms Story 4.2 touches `config.py`, `mcp/tools.py`, `worker.py` (this story additionally touches `fingerprint.py` for the new query method, and adds `tests/unit/test_mcp_tools.py`).
- `_bmad-output/planning-artifacts/architecture.md` — "Known Limitations / Accepted Risk (V1)" section: none of the 9 accepted-risk items overlap with this story's ACs.
- `_bmad-output/implementation-artifacts/4-1-worker-resilience-and-e2e-repair.md` — previous story; see "Previous Story Intelligence" above.
- `_bmad-output/implementation-artifacts/3-1-ground-truth-market-validation.md:790` and `_bmad-output/implementation-artifacts/3-2-flexible-closure-ceremony-dispatch.md:639` — origin of the AC2 deferred item and the P7 patch that introduced today's overly-strict naive-datetime rejection.

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4-6) — Amelia (Dev Agent)

### Debug Log References

- AC1: Added RED test (`test_imap_use_ssl_false_logs_startup_warning`) — confirmed failing (`AssertionError: []`) before implementing `Settings.model_post_init`. GREEN after implementation; both new tests pass (5/5 in `TestSettingsDefaults`).
- AC2: Added RED test suite `TestParseExpiryAt` — confirmed failing (`ImportError: cannot import name '_parse_expiry_at'`) before implementation. GREEN after adding `_parse_expiry_at` and wiring it into `configure_target` (7/7 pass).
- AC3 unit: Added RED test class `TestExtractMeasurementTimestamp` — confirmed failing (`ImportError: cannot import name '_extract_measurement_timestamp'`) before implementation. GREEN after adding the helper (9/9 pass in `test_worker_helpers.py`).
- AC3 integration: Added `TestWorkerFingerprintBackfill` (3 tests) to `test_worker_fingerprint.py`, exercising Phase 3c via `tick()` against a real Postgres testcontainer. All pass (7/7 in file, 62/62 full integration suite).
- mypy regression check: ran `mypy src/ tests/` before and after all changes (`git stash`/`git stash pop` diff). One new error was introduced by the integration test (`tests/integration/test_worker_fingerprint.py:318: "EnvFingerprintFactory" has no attribute "id"`, from `assert rows[0].id == existing.id`). Fixed by removing the redundant `.id` comparison — `len(rows) == 1` plus the unchanged `fingerprinted_at`/`kp_index` assertions already prove the existing row was not reprocessed. Net result: 29 errors (down from 30 baseline; one pre-existing placeholder error in `test_mcp_tools.py` resolved by AC2's implementation, one pre-existing `mcp/tools.py` line-number shift), zero new errors.
- Confirmed `ruff check .` (3 pre-existing E402 in `src/apollo/mcp/tools.py`) and `ruff format --check .` (4 pre-existing reformat targets: `mcp/tools.py`, `calibration.py`, `test_worker_calibration.py`, `test_calibration_service.py`) are unchanged before/after via `git stash` diff — all pre-existing, out of scope.
- Final full verification: `ruff check src tests` (3 pre-existing errors), `ruff format --check src tests` (4 pre-existing), `mypy src/ tests/` (29 pre-existing, 0 new), `pytest tests/unit/` (181 passed), `pytest tests/integration/` (62 passed), `pytest tests/e2e/` (32 passed, mailpit started via `docker-compose up -d mailpit`).

### Completion Notes List

- AC1: `Settings.model_post_init` logs a structured warning (`apollo.config: IMAP connection is unencrypted (imap_use_ssl=False)`) when `imap_use_ssl=False`. No warning when `True` (default).
- AC2: New `_parse_expiry_at` helper in `mcp/tools.py` normalizes `expiry_at` strings — handles `Z` suffix, explicit offsets, date-only strings, and naive datetimes (assumed UTC) — replacing the old inline parsing that raised `ValueError` on naive datetimes.
- AC3: `FingerprintService.fetch_sealed_records_missing_fingerprint` (new static method, `@requires(Compartment.EXTRACTION_WRITE)` per established `seal.py` precedent) finds `SEALED` records with no `env_fingerprint` row via an outer-join/`IS NULL` query. New worker helper `_extract_measurement_timestamp` parses `extraction_payload["measurement_timestamp"]`. New Phase 3c in `tick()` (after Phase 3b dead-letter, before Phase 4 validation) backfills these records via `FingerprintService.attach`, which already handles missing-timestamp fallback and idempotent re-runs.
- All three ACs implemented via TDD (RED confirmed before each implementation), with no regressions across unit/integration/e2e suites.

### File List

- `src/apollo/config.py` — AC1: added `model_post_init` startup warning for `imap_use_ssl=False`.
- `tests/unit/test_dispatch_service.py` — AC1: added `test_imap_use_ssl_false_logs_startup_warning` and `test_imap_use_ssl_true_does_not_log_warning`.
- `src/apollo/mcp/tools.py` — AC2: added `_parse_expiry_at` helper; replaced inline `expiry_at` parsing in `configure_target`.
- `tests/unit/test_mcp_tools.py` — AC2: new file, `TestParseExpiryAt` (7 tests).
- `src/apollo/services/fingerprint.py` — AC3: added `FingerprintService.fetch_sealed_records_missing_fingerprint`.
- `src/apollo/services/worker.py` — AC3: added `_extract_measurement_timestamp` helper and Phase 3c backfill block in `tick()`.
- `tests/unit/test_worker_helpers.py` — AC3: added `TestExtractMeasurementTimestamp` (5 tests).
- `tests/integration/test_worker_fingerprint.py` — AC3: added `_seed_sealed` helper and `TestWorkerFingerprintBackfill` (3 tests).

## Change Log

- 2026-06-11: Implemented Story 4.2 (AC1-3) — `imap_use_ssl=False` startup warning, `expiry_at` ISO parsing fix, and Phase 3c env_fingerprint backfill. Status → review.
