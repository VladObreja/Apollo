# Deferred Work

## 2026-06-10: Triaged via Correct Course

All 40 items previously tracked here (from code reviews of Stories 1.1–3.3) have been dispositioned via `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-10.md`:

- 8 items were already resolved by Story 1.4 (verified in code).
- 6 items were already accepted in the Epic 3 retrospective register (`epic-3-retro-2026-06-09.md`).
- 17 items (+ retro actions A1/A2) were scheduled as **Epic 4: Hardening & Tech Debt**, Stories 4.1–4.4 in `epics.md` / `sprint-status.yaml`.
- 9 items were moved to the "Known Limitations / Accepted Risk (V1)" section of `architecture.md`.

New deferred items from future code reviews should be appended below.

## Deferred from: code review of story-4.1 (2026-06-10)

- **W1**: `_is_concurrent_seal_collision` and the `validate.py` constraint check both collapse "constraint name absent" and "constraint name present but different" into the same branch with no log differentiation [worker.py:_is_concurrent_seal_collision; validate.py:_validate_one] — both cases correctly result in "unexpected/fail-loud" handling per AC2/AC3; differentiating the log message is a minor observability refinement, not a correctness issue.
- **W2**: No test explicitly asserts `extraction_success`/`extraction_failed` are unaffected by the new Phase 3b dead-letter path [tests/integration/test_worker_quarantine.py::TestWorkerEmptyRawBytesDeadLetter] — Phase 3b is structurally outside the Phase 3 counters' scope so AC4 holds by construction; explicit coverage would be a nice-to-have.
- **W3**: `SealingService.fetch_stuck_empty_bytes_records` is decorated `@requires(Compartment.EXTRACTION_WRITE)` for a read-only `SELECT` [seal.py:fetch_stuck_empty_bytes_records] — no `EXTRACTION_READ` compartment exists and `@requires` is currently a non-functional stub; pre-existing compartment-naming gap.
- **W4**: Phase 3b reads stuck records in one session then calls `QuarantineService.quarantine()` per-record (with a per-record SMTP send) outside that session — a SIGKILL mid-loop could permanently skip the clarification email for a record with no retry path [worker.py: Phase 3b; quarantine.py:quarantine] — mirrors existing Story 2.3 quarantine semantics for the Phase 3 `ExtractionSchemaError` path; not a new regression.

## Deferred from: code review of story-4.2 (2026-06-11)

- **W1**: `tests/integration/test_worker_fingerprint.py::test_does_not_reprocess_already_fingerprinted_record` doesn't assert `solar_wind_speed`/`retrieval_status` are unchanged after Phase 3c skips an already-fingerprinted record, only `fingerprinted_at`/`kp_index` — test-coverage enhancement.
- **W2**: `tests/integration/test_worker_fingerprint.py::test_backfills_record_with_minimal_extraction_payload` asserts `measurement_timestamp is not None` but doesn't verify the documented `received_at`/`now()` fallback was actually used — test-coverage enhancement.
- **W3**: Phase 3c's `fetch_sealed_records_missing_fingerprint(limit=100)` has no backlog-size logging if more than 100 sealed records lack fingerprints in a single tick [fingerprint.py:112-136; worker.py Phase 3c] — relies on the next tick to continue (consistent with AC3's "subsequent tick" wording), but a "more than N pending" log would aid ops.
- **W4**: New AC1 tests in `test_dispatch_service.py` (`test_imap_use_ssl_false_logs_startup_warning`, `test_imap_use_ssl_true_does_not_log_warning`) duplicate ~30 lines of env-var save/restore boilerplate per test — `monkeypatch.setenv` would simplify; follows existing file convention so left as-is.
