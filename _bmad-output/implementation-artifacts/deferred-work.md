# Deferred Work

## Deferred from: code review of 1-1-initialize-domain-target-configuration-mcp (2026-06-02)

- Hardcoded DB URL default `postgresql://postgres:postgres@localhost:5432/apollo` in `config.py` — acceptable for local dev scaffold; must document in README that `.env` is required before any non-local deployment.
- No test factory pattern (`factory_boy`) — unit tests currently use direct model instantiation which is acceptable for Story 1.1 scope; integration tests will require factory patterns to protect against schema evolution breakage.
- Missing `docker-compose.yml` for local PostgreSQL — AC-WSL-1 infra qualification is a separate architecture concern; create as part of infrastructure setup story.
- Missing GitHub Actions CI pipeline `.github/workflows/ci.yml` — architecture mandates sequential gating (ruff → mypy → unit → integration → alembic reversibility); not in Story 1.1 acceptance criteria, create as a dedicated DevOps story.
- Table naming convention: `corpus_record` (singular) adopted going forward — architecture.md naming conventions section must be updated from "plural" to "singular" to align with the implemented convention.
- `awareness_tier` and `parameter_name` enums in `domain/types.py` — domain vocabulary (`vad`, `rvd`, `ebf`, tier levels) still being finalized; add `ParameterName` and `AwarenessTier` enums and update service/migration check constraints in a future story.

## Deferred from: code review of 1-2-event-driven-queue-coordinate-generation (2026-06-02)

- No structured logging initialization in the CLI entrypoint (`main.py`), so worker log messages are not printed or formatted as structured JSON. [main.py](file:///c:/Apollo/src/apollo/main.py#L13)

## Deferred from: code review of 1-3-task-email-dispatch (2026-06-02)

- Deduplicate FakeSMTPClient across test files [tests/integration/test_worker_dispatch.py] — deferred, pre-existing
- db_session fixture rollback teardown is a no-op [tests/integration/test_worker_dispatch.py] — deferred, pre-existing

## Deferred from: code review of 2-1-inbound-email-ingestion-parsing (2026-06-02)

- IMAP connection is opened and closed on every fetch_unseen_emails [services/email_poller.py]
- imap_use_ssl = False default has no security warning [src/apollo/config.py]
- FakeIMAPClient reused across tick calls causes all emails to be re-delivered [tests/utils.py]
- Prompt injection via unbounded email_body — The template inserts Asset-controlled email content verbatim into the LLM instruction context with autoescape=False. Deferred: we accept the risk of prompt injection from Assets for now. [_bmad-output/implementation-artifacts/2-1-inbound-email-ingestion-parsing.md]

## Deferred from: code review of 2-3-quarantine-clarification-loop-exception-path (2026-06-06)

- Unbounded quarantine retry loop: no max-attempt guard on `quarantine_record` per `corpus_record_id` — Jane receives infinite clarification emails if responses are consistently unextractable. Deferred: single trusted Asset, volume too low to matter. [src/apollo/services/worker.py + quarantine.py]
- SIGKILL between T1 commit and SMTP send: `clarification_sent_at=NULL` is indistinguishable from intentional SMTP failure; no retry-clarification mechanism exists to resend to Jane. [src/apollo/services/quarantine.py]
- `IntegrityError` catch in worker Phase 3 sealing path is not scoped to the concurrent-seal unique constraint — future DB constraint violations would be silently misattributed. [src/apollo/services/worker.py:IntegrityError handler]
- `QuarantineRecordFactory` generates a dangling `corpus_record_id` (random UUID with no parent `CorpusRecord`) — FK violation if factory is used standalone; dormant because factory is not used in any current test. [tests/factories.py:30]
- SMTP counter fragility: `FakeSMTPClient(raise_on_nth=1)` in SMTP-failure tests assumes Phase 2 makes zero SMTP calls before Phase 3; brittle to future test changes that seed QUEUED records alongside DISPATCHED ones. [tests/integration/test_worker_quarantine.py]

## Deferred from: code review of 2-4-environmental-context-fingerprinting (2026-06-06)

- `extraction_success` counter can double-fire if decorator chain raises after sealing — pre-existing counter design not introduced by this story. [src/apollo/services/worker.py]
- `asset_latitude` config field is unused — intentionally added for future weather lookups per spec; not wired to any computation. [src/apollo/config.py]
- Process crash between seal-commit and fingerprint-write leaves permanently unfingerprintable records — known V1 limitation; no retry mechanism exists for sealed records missing their fingerprint row. [src/apollo/services/worker.py]

## Deferred from: code review of 3-1-ground-truth-market-validation (2026-06-06)

- Detached ORM pattern: eligible records fetched in a session that closes before iteration — safe for current scalar-only schema but fragile if SQLAlchemy relationships are ever added to CorpusRecord. [validate.py, validate_pending]
- validated_at timestamp captured once at batch-entry time (up to 100 records share same timestamp) — bounded impact, acceptable for V1 audit trail. [validate.py, validate_pending]
- IntegrityError catch in _validate_one is not scoped to the corpus_record_id UNIQUE constraint — any future FK or NOT NULL constraint violation would be silently logged as "already validated". [validate.py, _validate_one]
- expiry_at ISO parsing in configure_target MCP tool handles only Z-suffix; date-only strings or non-UTC offset strings would produce naive or non-UTC datetimes. Python 3.12 handles most cases; edge case for V1. [mcp/tools.py]
- Worker IntegrityError for concurrent seal (Phase 3) increments extraction_success — design choice, inflates success counter by ≤1 per tick under concurrent worker scenario; not a V1 concern. [worker.py]

## Deferred from: code review of 3-2-flexible-closure-ceremony-dispatch (2026-06-07)

- **W1**: Interval proxy uses `max(closed_at)` as ceremony timestamp — no separate audit table for ceremony history. Design limitation acceptable for V1; a dedicated `ceremony_log` table would be more robust. [closure.py:_get_last_ceremony_timestamp]
- **W2**: Timezone-naive `last_sent` timestamp from a legacy row would crash interval subtraction with `TypeError`. `DateTime(timezone=True)` column prevents naive storage in practice; theoretical concern only. [closure.py:70]
- **W3**: Unit tests never exercise real SQLAlchemy session path — `_get_last_ceremony_timestamp` and `_fetch_pending` are always patched at class level; mock `session.execute` is never called. Pre-existing test design choice. [test_closure_service.py]
- **W4**: `trigger_closure_ceremony` MCP tool wires SMTP client, Jinja environment, and session factory inline — inconsistent with the `tick()` DI pattern but follows the established `quarantine.py` MCP tool precedent. [mcp/tools.py:trigger_closure_ceremony]

## Deferred from: code review of 3-3-statistical-calibration-scoring (2026-06-07)

- `NaN` `param_value` causes `ValueError` in `int()` conversion in `_param_bucket` / `_prob_bin` — deferred, `param_value` validated ≥0 by extraction Pydantic schema upstream. [src/apollo/services/calibration.py:34]
- Bucket label ambiguity at decade boundaries — `param_value=10.0` maps to bucket 1 ("10–20") but label "0–10" implies inclusion of 10; implementation is correct, label is cosmetic. [src/apollo/services/calibration.py:93]
- `computed_at` stamped after DB session closes — tiny time gap between query completion and timestamp; negligible for this use case. [src/apollo/services/calibration.py:162]
- Integration test seeds `extraction_payload` with calibration `param_value` — doesn't prove double-blind isolation; service query is provably isolated by code inspection; test improvement only. [tests/integration/test_worker_calibration.py]
- No `lazy="raise"` guard on `corpus_record` FK in `ValidationRecord` — future developer could silently break double-blind by accessing the relationship; architectural hardening. [src/apollo/db/models.py]
- `test_offset_rows_excluded_from_brier` only asserts score CHANGES when offset row is included, not the correct excluded value — exclusion correctly tested in `test_get_stats_excludes_offset`; test improvement only. [tests/unit/test_calibration_service.py]

## Deferred from: code review of 2-2-epistemological-sealing-ledger-commit-happy-path (2026-06-05)

- b"" empty bytes causes permanent DISPATCHED retry loop — `if not raw_email_bytes` guard raises SealingError but the record stays DISPATCHED and retries on every tick forever. Needs a dead-letter queue or per-record retry limit. [src/apollo/services/seal.py]
- model_dump PydanticSerializationError not wrapped in SealingError — already caught by outer `except Exception` and counted as extraction_failed, but not surfaced under the "sealing failed" log category. Cosmetic wrapping improvement for future. [src/apollo/services/seal.py:63]
- datetime.now(UTC) not injectable in SealingService.seal() — sealed_at cannot be frozen in unit tests. Clock injection via an injectable parameter (same pattern as agent_version) would improve test determinism. [src/apollo/services/seal.py]
- Test helper deduplication — _make_reply_email and _seed_dispatched helpers duplicated across integration test files, not consolidated in tests/utils.py. DRY cleanup deferred. [tests/]
