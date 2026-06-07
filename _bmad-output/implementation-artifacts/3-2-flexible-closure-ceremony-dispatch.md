---
baseline_commit: aa909c8cc9df66a652143b93ea4be47e8857e3ee
---

# Story 3.2: Flexible Closure Ceremony Dispatch

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the System,
I want to aggregate validated sessions and send a definitive closure email based on a flexible schedule or an on-demand trigger,
so that the epistemological loop can be closed precisely when the Admin or Asset requires it (e.g., weekly, end-of-day, or immediately for testing).

## Acceptance Criteria

1. **Given** validated sessions with `closed_at = NULL` in `validation_record`
   **When** the configured interval has elapsed (e.g., 7 days since last closure ceremony) **OR** `trigger_closure_ceremony` MCP tool is invoked
   **Then** `ClosureService.close_pending()` aggregates all such un-closed `validation_record` rows via a JOIN with `corpus_record`

2. **Given** un-closed validated sessions are found
   **When** the ceremony runs
   **Then** it renders `closure.jinja` with full session outcome data (target statement revealed — the double-blind is lifted at closure)
   **And** sends the closure ceremony email to the Asset via SMTP
   **And** on SMTP success: batch-updates `closed_at = NOW()` on all included `validation_record` rows in one atomic transaction

3. **Given** the SMTP send fails (OSError)
   **When** `ClosureService.close_pending()` catches the exception
   **Then** NO `closed_at` timestamp is written (records remain open for retry on the next tick)
   **And** the error is logged and `close_pending()` returns `(0, False)`
   **And** `tick()` continues without crashing (Phase 5 is fail-operational)

4. **Given** the `closure_ceremony_interval_days` setting is respected
   **When** a closure ceremony was already sent within the configured interval window
   **Then** `close_pending(interval_days=N)` returns `(0, False)` without querying or sending
   **And** passing `interval_days=None` bypasses this check (used by MCP on-demand tool)

5. **Given** the Admin calls `trigger_closure_ceremony()` MCP tool
   **When** there are un-closed validated sessions
   **Then** the ceremony runs immediately regardless of the interval schedule
   **And** returns a confirmation string with the count of sessions closed

## Tasks / Subtasks

- [x] Alembic migration: add `closed_at` to `validation_record` (AC: 1, 2)
  - [x] Create `src/apollo/db/alembic/versions/d2e3f4a5b6c7_add_closed_at_to_validation_record.py`
  - [x] Set `revision = "d2e3f4a5b6c7"` and `down_revision = "c1d2e3f4a5b6"` (chain from market validation)
  - [x] In `upgrade()`:
    ```python
    op.add_column(
        "validation_record",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_validation_record_closed_at", "validation_record", ["closed_at"])
    ```
  - [x] In `downgrade()`:
    ```python
    op.drop_index("ix_validation_record_closed_at", table_name="validation_record")
    op.drop_column("validation_record", "closed_at")
    ```
  - [x] Imports: `import sqlalchemy as sa` and `from alembic import op`

- [x] ORM: add `closed_at` to `ValidationRecord` in `db/models.py` (AC: 1, 2)
  - [x] Add after `fetch_error` column:
    ```python
    closed_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ```
  - [x] No new imports needed (`datetime` and `DateTime` already imported)

- [x] Config: add `closure_ceremony_interval_days` to `Settings` (AC: 4)
  - [x] In `src/apollo/config.py`, add after the existing fields:
    ```python
    closure_ceremony_interval_days: int = 7
    ```

- [x] Jinja2 template: `src/apollo/templates/closure.jinja` (AC: 2)
  - [x] Create the file. First line MUST be `Subject: ...` (same convention as extraction.jinja):
    ```jinja
    Subject: Apollo Closure Ceremony — {{ sessions | length }} Session(s) Closed

    Closure Ceremony
    Generated: {{ generated_at }}

    The following sessions have been validated against ground truth and are now epistemologically closed.

    {% for s in sessions %}
    ——————————————————————————————————
    Session ID:    {{ s.coordinate }}
    Parameter:     {{ s.parameter_name }}
    Target:        {{ s.target_statement }}
    Your reading:  {{ s.param_value | round(1) }} ({{ "Positive" if s.predicted_positive else "Negative" }})
    Outcome:       {{ s.validation_status | upper }}{% if s.actual_change_pct is not none %} (actual move: {{ "%.2f" | format(s.actual_change_pct) }}%){% endif %}

    {% endfor %}
    ——————————————————————————————————

    Total: {{ sessions | length }} session(s) epistemologically closed.

    Apollo Research System
    This is an automated research communication.
    ```

- [x] Create `ClosureService` in `src/apollo/services/closure.py` (AC: 1–4)
  - [x] Full import block:
    ```python
    from __future__ import annotations

    import logging
    from dataclasses import dataclass
    from datetime import UTC, datetime
    from uuid import UUID

    from jinja2 import Environment
    from sqlalchemy import func, select, update as sa_update
    from sqlalchemy.orm import Session, sessionmaker

    from apollo.db.models import CorpusRecord, ValidationRecord
    from apollo.domain.compartments import Compartment, requires
    from apollo.services.dispatch import SMTPClient

    logger = logging.getLogger(__name__)
    ```
  - [x] Define `ClosureSessionSummary` dataclass (stdlib only, no Pydantic needed):
    ```python
    @dataclass(frozen=True)
    class ClosureSessionSummary:
        validation_record_id: UUID
        coordinate: str
        parameter_name: str
        target_statement: str
        param_value: float
        validation_status: str
        actual_change_pct: float | None
        actual_positive: bool | None
        predicted_positive: bool | None
        validated_at: datetime
    ```
  - [x] Implement `ClosureService` static class:
    ```python
    class ClosureService:
        @staticmethod
        @requires(Compartment.CALIBRATION_WRITE)
        def close_pending(
            session_factory: sessionmaker[Session],
            smtp_client: SMTPClient,
            env: Environment,
            recipient: str,
            interval_days: int | None = None,
            limit: int = 500,
        ) -> tuple[int, bool]:
            """Aggregate un-closed validated sessions and send closure ceremony email.

            Two-step fail-operational pattern:
                1. Fetch pending sessions and check interval (read-only).
                2. Render closure.jinja and send SMTP.
                3. On SMTP success: batch-commit closed_at in one transaction.
                On SMTP failure: log, return (0, False) — records remain open for retry.

            Returns: (closed_count, email_sent)
            """
            now = datetime.now(UTC)

            with session_factory() as session:
                if interval_days is not None:
                    last_sent = ClosureService._get_last_ceremony_timestamp(session)
                    if last_sent is not None:
                        elapsed_days = (now - last_sent).total_seconds() / 86400.0
                        if elapsed_days < interval_days:
                            return 0, False

                pending = ClosureService._fetch_pending(session, limit)

            if not pending:
                return 0, False

            subject, body = ClosureService._render_email(pending, env, now)

            try:
                smtp_client.send_message(to=recipient, subject=subject, body=body)
            except OSError as exc:
                logger.error(
                    "apollo.closure: SMTP send failed — sessions remain open for retry",
                    extra={"pending_count": len(pending), "error": str(exc)},
                )
                return 0, False

            ids = [s.validation_record_id for s in pending]
            with session_factory.begin() as write_session:
                ClosureService._mark_closed(ids, write_session, now)

            logger.info(
                "apollo.closure: closure ceremony dispatched",
                extra={"closed_count": len(pending)},
            )
            return len(pending), True

        @staticmethod
        def _get_last_ceremony_timestamp(session: Session) -> datetime | None:
            """Return the most recent closed_at value, or None if nothing has ever been closed."""
            return session.execute(
                select(func.max(ValidationRecord.closed_at))
            ).scalar_one_or_none()

        @staticmethod
        def _fetch_pending(session: Session, limit: int) -> list[ClosureSessionSummary]:
            """JOIN validation_record with corpus_record to fetch un-closed sessions."""
            stmt = (
                select(ValidationRecord, CorpusRecord)
                .join(CorpusRecord, ValidationRecord.corpus_record_id == CorpusRecord.id)
                .where(ValidationRecord.closed_at.is_(None))
                .order_by(ValidationRecord.validated_at.asc())
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            return [
                ClosureSessionSummary(
                    validation_record_id=vr.id,
                    coordinate=cr.double_blind_coordinate or "(no coordinate)",
                    parameter_name=cr.parameter_name,
                    target_statement=cr.target_statement,
                    param_value=vr.param_value,
                    validation_status=vr.validation_status,
                    actual_change_pct=vr.actual_change_pct,
                    actual_positive=vr.actual_positive,
                    predicted_positive=vr.predicted_positive,
                    validated_at=vr.validated_at,
                )
                for vr, cr in rows
            ]

        @staticmethod
        def _mark_closed(
            validation_ids: list[UUID],
            session: Session,
            now: datetime,
        ) -> None:
            """Batch-update closed_at for all validation records in one statement."""
            session.execute(
                sa_update(ValidationRecord)
                .where(ValidationRecord.id.in_(validation_ids))
                .values(closed_at=now)
            )

        @staticmethod
        def _render_email(
            sessions: list[ClosureSessionSummary],
            env: Environment,
            now: datetime,
        ) -> tuple[str, str]:
            """Render closure.jinja and extract subject + body (same convention as dispatch.py)."""
            generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
            template = env.get_template("closure.jinja")
            rendered = template.render(sessions=sessions, generated_at=generated_at)

            lines = rendered.splitlines()
            subject_line = lines[0] if lines else ""
            if not subject_line.startswith("Subject: "):
                raise ValueError("closure.jinja did not produce a valid 'Subject: ' header")

            subject = subject_line.removeprefix("Subject: ").strip()
            body = "\n".join(lines[1:]).lstrip("\n")

            if not body.strip():
                raise ValueError("closure.jinja rendered an empty email body")

            return subject, body
    ```

- [x] Worker Phase 5: add closure ceremony to `tick()` in `src/apollo/services/worker.py` (AC: 1–4)
  - [x] Add import at top:
    ```python
    from apollo.services.closure import ClosureService
    ```
  - [x] Update `tick()` docstring — add Phase 5 section after Phase 4:
    ```
    Phase 5 — Closure Ceremony (validated, un-closed → closed, email dispatched):
        21. Check if interval constraint satisfied (elapsed >= closure_ceremony_interval_days).
        22. Fetch all validation_records with closed_at=NULL via JOIN with corpus_record.
        23. Render closure.jinja with full outcome data (target revealed — double-blind lifted).
        24. Send closure ceremony email to Asset via SMTP.
        25. On success: batch-update closed_at for all included validation_records atomically.
        26. On SMTP failure: log, leave records un-closed for retry on next tick.
    ```
  - [x] Add `closure_ceremony_interval_days` to `tick()` docstring Args section:
    ```
    (No new tick() parameter — closure uses the existing smtp_client and reads settings internally.)
    ```
  - [x] Add Phase 5 block at the end of `tick()` (after Phase 4 logging):
    ```python
    # ------------------------------------------------------------------
    # Phase 5: closure ceremony (validated, un-closed → closed + email)
    # ------------------------------------------------------------------
    try:
        closed_count, email_sent = ClosureService.close_pending(
            SessionFactory,
            smtp_client,
            env,
            _settings.asset_email_address,
            interval_days=_settings.closure_ceremony_interval_days,
        )
        if email_sent:
            logger.info(
                "apollo.worker.tick: closure ceremony dispatched",
                extra={"closed_count": closed_count},
            )
    except Exception as exc:
        logger.error(
            "apollo.worker.tick: closure ceremony crashed",
            extra={"error": str(exc)},
        )
    ```
  - [x] No new `tick()` parameter — `smtp_client` and `env` are already available; `_settings` already imported lazily inside `tick()`

- [x] MCP tool: `trigger_closure_ceremony()` in `src/apollo/mcp/tools.py` (AC: 5)
  - [x] Add after the existing `configure_target` tool:
    ```python
    @mcp.tool()
    def trigger_closure_ceremony() -> str:
        """Trigger an immediate closure ceremony, ignoring the configured interval.

        Aggregates all validated-but-not-yet-closed sessions and dispatches
        the definitive outcomes email to the Asset. Can be called at any time
        regardless of when the last scheduled ceremony was sent.

        Returns:
            Confirmation string with count of sessions closed, or status message
            if nothing was pending or SMTP failed.
        """
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader

        from apollo.config import settings as _settings
        from apollo.db.session import get_session_factory
        from apollo.services.closure import ClosureService
        from apollo.services.dispatch import SMTPClientImpl

        smtp_client = SMTPClientImpl(_settings)
        env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent.parent / "templates")),
            autoescape=False,
        )
        session_factory = get_session_factory()

        closed_count, email_sent = ClosureService.close_pending(
            session_factory,
            smtp_client,
            env,
            _settings.asset_email_address,
            interval_days=None,  # On-demand: bypass interval check
        )

        if email_sent:
            return f"Closure ceremony dispatched: {closed_count} session(s) epistemologically closed."
        return "No validated sessions pending closure (or SMTP failed — check logs)."
    ```

- [x] Unit tests: `tests/unit/test_closure_service.py` (AC: 1–5)
  - [x] Create the file with helper to build `ClosureSessionSummary` list and mock sessionmaker.
  - [x] Pattern for building test summaries:
    ```python
    from uuid import uuid4
    from datetime import UTC, datetime, timedelta
    from apollo.services.closure import ClosureService, ClosureSessionSummary

    def _make_summary(**kwargs) -> ClosureSessionSummary:
        defaults = dict(
            validation_record_id=uuid4(),
            coordinate="AAAA/BBBB",
            parameter_name="VAD",
            target_statement="Gold futures will rise",
            param_value=75.0,
            validation_status="hit",
            actual_change_pct=10.0,
            actual_positive=True,
            predicted_positive=True,
            validated_at=datetime(2026, 6, 5, 21, 0, 0, tzinfo=UTC),
        )
        defaults.update(kwargs)
        return ClosureSessionSummary(**defaults)
    ```
  - [x] Test `_render_email`:
    - Happy path: single session → subject starts with "Subject: Apollo Closure Ceremony", body contains coordinate, target_statement, "HIT"
    - Missing subject line: monkeypatch template to return empty → raises ValueError
  - [x] Test `close_pending` with `interval_days=7`, last_sent 3 days ago → returns `(0, False)`, smtp not called
    - Mock: `ClosureService._get_last_ceremony_timestamp` returns `datetime.now(UTC) - timedelta(days=3)`
  - [x] Test `close_pending` with `interval_days=7`, last_sent 8 days ago → interval satisfied, proceeds
  - [x] Test `close_pending` with `interval_days=None` (on-demand) → interval check skipped entirely
  - [x] Test `close_pending` with no pending sessions → `(0, False)`, smtp not called
    - Mock: `ClosureService._fetch_pending` returns `[]`
  - [x] Test `close_pending` happy path, 2 sessions → `(2, True)`, smtp called once, `_mark_closed` called
    - Mock: `_fetch_pending` returns 2 summaries; verify smtp.sent has 1 message
  - [x] Test `close_pending` SMTP failure (OSError) → `(0, False)`, `_mark_closed` NOT called
    - Use `FakeSMTPClient(raise_on_nth=1)` or a simple class that raises

- [x] Integration tests: `tests/integration/test_worker_closure.py` (AC: 1–5)
  - [x] Seed helper:
    ```python
    from datetime import UTC, datetime, timedelta
    from apollo.db.models import CorpusRecord, ValidationRecord
    from tests.factories import CorpusRecordFactory, ValidationRecordFactory

    def _seed_closed_awaiting_corpus(db_session) -> tuple[CorpusRecord, ValidationRecord]:
        """Seed a sealed CorpusRecord with a linked un-closed ValidationRecord."""
        record = CorpusRecordFactory(
            status="sealed",
            double_blind_coordinate="AAAA/BBBB",
            parameter_name="VAD",
            target_statement="Gold futures will rise",
            raw_hash="a" * 64,
            sealed_at=datetime.now(UTC),
            seal_agent_version="0.1.0",
            dispatched_at=datetime.now(UTC) - timedelta(hours=2),
            dispatch_agent_version="0.1.0",
        )
        db_session.flush()
        vr = ValidationRecordFactory(
            corpus_record_id=record.id,
            validation_status="hit",
            param_value=75.0,
            actual_change_pct=10.0,
            predicted_positive=True,
            actual_positive=True,
        )
        db_session.flush()
        return record, vr
    ```
  - [x] Test: `ClosureService.close_pending` directly with real DB session — 1 pending → `(1, True)`, `closed_at` set, smtp sent
  - [x] Test: `close_pending` twice — second call returns `(0, False)` because `closed_at` is now set (interval_days=None both times)
  - [x] Test: `close_pending` with interval_days=7, no prior ceremony → runs (last_sent=None)
  - [x] Test: `close_pending` with interval_days=7, ceremony was just run → returns `(0, False)` (last_sent = now)
  - [x] Test: `close_pending` with no validation_records → `(0, False)`
  - [x] Test: SMTP failure path — seed 1 pending record, use `FakeSMTPClient(raise_on_nth=1)` → `(0, False)`, `closed_at` remains NULL
  - [x] Test: full `tick()` with validated un-closed record and `interval_days=0` equivalent (force run) — assert `closed_at` is set after tick
    - Note: `tick()` uses `_settings.closure_ceremony_interval_days` from env. Patch `CLOSURE_CEREMONY_INTERVAL_DAYS=0` via `monkeypatch.setenv` to bypass interval in test, OR seed records and use `ClosureService.close_pending` directly with `interval_days=None` (bypass tick for direct tests)
  - [x] Use `db_session.expire_all()` before asserting DB state after any tick() or service call

## Dev Notes

### Critical: SMTPClient Import Pattern

`ClosureService` imports `SMTPClient` Protocol from `apollo.services.dispatch` — NOT redefined. This is identical to `quarantine.py`:
```python
from apollo.services.dispatch import SMTPClient
```
Do NOT define a new Protocol in `closure.py`.

### Critical: No New `tick()` Parameter

Phase 5 reuses the existing `smtp_client` parameter already in `tick()`. There is NO new injectable client for closures. The `env` (Jinja2 Environment) already in `tick()` is also reused. No changes to the `tick()` function signature.

### Critical: ValidationRecord is Mutable (No Immutability Trigger)

The Postgres immutability trigger (`b4c7e1f02a9d` migration) protects **only `corpus_record` identity columns**. `validation_record` has NO such trigger — bulk-updating `closed_at` via `sa_update(...).values(closed_at=now)` is safe and correct.

### Critical: Double-Blind Lift at Closure

The closure template DOES reveal `target_statement` to the Asset. This is intentional — the double-blind protocol requires that the Asset NOT know the target during the prediction phase, but the closure ceremony IS the reveal event. The Jinja2 template correctly includes `s.target_statement` in the rendered output.

### Critical: JOIN Query — No Relationship Attribute

`ValidationRecord` has no `relationship()` to `CorpusRecord` (by design, per Story 3.1 dev notes). The `_fetch_pending` method uses an explicit `select(ValidationRecord, CorpusRecord).join(...)` JOIN query — do NOT attempt `vr.corpus_record` attribute access.

### Critical: Fail-Operational Contract for Phase 5

Phase 5 in `tick()` is wrapped in `try/except Exception` — any uncaught error (template missing, DB error, etc.) logs and tick() continues. The SMTP failure path in `ClosureService.close_pending()` is additionally handled internally (catches `OSError`). These are two separate layers:
1. Inner: `close_pending` handles `OSError` from SMTP
2. Outer: `tick()` Phase 5 `try/except` handles anything else (template bugs, DB errors)

### Critical: Interval Logic When `last_sent=None`

When `_get_last_ceremony_timestamp()` returns `None` (nothing ever closed), the interval check is bypassed and the ceremony runs. This is the correct behavior — the first ceremony should always run when sessions are available.

```python
if last_sent is not None:  # None means "never run" → always proceed
    elapsed_days = (now - last_sent).total_seconds() / 86400.0
    if elapsed_days < interval_days:
        return 0, False
```

### Alembic Chain

Current head: `c1d2e3f4a5b6` (add_market_validation)
New: `d2e3f4a5b6c7` → `down_revision = "c1d2e3f4a5b6"`

Never modify existing migrations. Always chain from the current head.

### Regression: Phase 5 in Existing Integration Tests

Phase 5 is now always called in `tick()`. Existing integration test files that call `tick()` are NOT affected as long as they don't seed `ValidationRecord` rows with `closed_at=NULL`:
- `test_worker_dispatch.py` — seeds pending/queued records only: no ValidationRecord → Phase 5 is no-op ✓
- `test_worker_email_phase.py` — no ValidationRecord seeds → Phase 5 is no-op ✓
- `test_worker_sealing.py` — seals records but no ValidationRecord → Phase 5 no-op ✓
- `test_worker_quarantine.py` — no ValidationRecord → Phase 5 no-op ✓
- `test_worker_fingerprint.py` — no ValidationRecord → Phase 5 no-op ✓
- `test_worker_tick.py` — no ValidationRecord → Phase 5 no-op ✓
- `test_worker_validation.py` — seeds validatable records, Phase 4 creates ValidationRecord with `closed_at=NULL`, **then Phase 5 may close them** using `FakeSMTPClient`. This adds a closure ceremony email to `smtp_client.sent` but tests don't assert on smtp_client.sent length in validation tests → no regression.

**No existing integration test files need modification for Phase 5.**

### Config: `CLOSURE_CEREMONY_INTERVAL_DAYS` env override

`closure_ceremony_interval_days: int = 7` follows the standard `pydantic-settings` 12-factor pattern. Override via env: `CLOSURE_CEREMONY_INTERVAL_DAYS=0` to force ceremony on every tick (useful for testing without monkeypatching).

### MCP Tool Path for Templates

The `trigger_closure_ceremony()` MCP tool needs the templates directory. Pattern from quarantine.py:
```python
Path(__file__).parent.parent / "templates"
```
`__file__` is `src/apollo/mcp/tools.py`, so `.parent.parent` = `src/apollo/` → `src/apollo/templates/` ✓

### Bulk UPDATE Pattern

The `_mark_closed` method uses SQLAlchemy Core `update()` with `in_()`:
```python
session.execute(
    sa_update(ValidationRecord)
    .where(ValidationRecord.id.in_(validation_ids))
    .values(closed_at=now)
)
```
This requires `from sqlalchemy import update as sa_update`. Import aliased to `sa_update` to avoid collision with Python builtins.

### `func.max()` returns None on empty table

`select(func.max(ValidationRecord.closed_at)).scalar_one_or_none()` returns `None` when the table is empty or all `closed_at` are NULL. This is the correct sentinel for "never had a closure ceremony".

### Established Patterns (carry forward from Story 3.1)

1. `from __future__ import annotations` at top of every new file
2. `@requires(Compartment.CALIBRATION_WRITE)` on `close_pending`
3. `session_factory.begin()` for write transactions — never `session.commit()` manually
4. `datetime.now(UTC)` — never `datetime.utcnow()`
5. `mypy --strict` — use `X | None`, no `Optional[X]`
6. `ruff format .` + `ruff check .` before validating
7. `session.expire_all()` in integration tests after tick() before asserting DB state
8. Factory `Meta.sqlalchemy_session = None` (bound dynamically in conftest)
9. `module`-scoped testcontainer, `function`-scoped `db_session` with DELETE cleanup

### Project Structure Notes

```
src/apollo/
├── config.py                                    UPDATE: add closure_ceremony_interval_days
├── db/
│   ├── alembic/versions/
│   │   └── d2e3f4a5b6c7_add_closed_at_*.py     NEW
│   └── models.py                                UPDATE: add closed_at to ValidationRecord
├── services/
│   ├── closure.py                               NEW
│   └── worker.py                                UPDATE: import ClosureService, add Phase 5
├── mcp/
│   └── tools.py                                 UPDATE: add trigger_closure_ceremony
└── templates/
    └── closure.jinja                            NEW
tests/
├── unit/
│   └── test_closure_service.py                  NEW
└── integration/
    └── test_worker_closure.py                   NEW
```

### Files NOT to Touch

- All existing Alembic migrations — never modify existing revisions
- `src/apollo/db/alembic/versions/c1d2e3f4a5b6_add_market_validation.py` — this is the chain parent
- `src/apollo/services/validate.py` — no changes to ValidationService
- `src/apollo/domain/compartments.py` — `CALIBRATION_WRITE` compartment already exists from Story 3.1
- `src/apollo/domain/exceptions.py` — no new exceptions needed for V1
- `tests/conftest.py` — no new factory bindings needed (no new factory class)
- `tests/factories.py` — `ValidationRecordFactory` already exists and needs no change
- All existing integration test files — no tick() signature changes, no regression updates needed

### References

- Story AC source: `_bmad-output/planning-artifacts/epics.md#Story-3.2`
- Alembic chain head: `src/apollo/db/alembic/versions/c1d2e3f4a5b6_add_market_validation.py` (revision `c1d2e3f4a5b6`)
- SMTPClient Protocol (import, do NOT redefine): `src/apollo/services/dispatch.py`
- Two-transaction email pattern: `src/apollo/services/quarantine.py`
- Template convention (Subject: line): `src/apollo/templates/extraction.jinja` and `clarification.jinja`
- ValidationRecord ORM (no relationship): `src/apollo/db/models.py`
- tick() Phase 4 as pattern for Phase 5: `src/apollo/services/worker.py:319-329`
- ValidationService as structural pattern: `src/apollo/services/validate.py`
- ValidationRecordFactory (reuse in tests): `tests/factories.py`
- Mock sessionmaker pattern: `_bmad-output/implementation-artifacts/3-1-ground-truth-market-validation.md#Mock-SessionFactory-Pattern`
- FakeSMTPClient (reuse): `tests/utils.py`
- Project-context rules: `_bmad-output/project-context.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Integration test `test_interval_days_recent_ceremony_skipped` failed on first run due to unique constraint violation on `raw_hash` when `_seed_closed_awaiting_corpus` was called twice in the same test with hardcoded `"a" * 64`. Fixed by using `uuid4().hex * 2` to generate a unique hash per call.
- Pre-existing e2e test failures in `tests/e2e/test_epic2_e2e.py` (4 tests) — unrelated to Story 3.2. These fail because Story 2.2 sealing and Story 2.3 quarantine were implemented after those e2e tests were written (the assertion messages explicitly reference "sealing is Story 2.2").

### Completion Notes List

- Implemented complete closure ceremony pipeline: Alembic migration (`d2e3f4a5b6c7`), ORM column, `closure_ceremony_interval_days` config field, `closure.jinja` template, `ClosureService`, Phase 5 in `tick()`, and `trigger_closure_ceremony()` MCP tool.
- `ClosureService.close_pending()` follows the two-step fail-operational pattern from `quarantine.py`: read phase (interval check + fetch), SMTP send, then atomic batch-commit of `closed_at` on success only.
- Phase 5 in `tick()` is wrapped in `try/except Exception` for double-layer fail-operational: inner catches `OSError` from SMTP, outer catches any template/DB errors.
- `interval_days=None` bypasses the interval check entirely (used by the MCP on-demand tool).
- Double-blind is lifted at closure: `closure.jinja` correctly reveals `target_statement` to the Asset.
- 25 new tests added (15 unit + 10 integration), all pass. No regressions in the 211 passing tests.

### File List

- `src/apollo/db/alembic/versions/d2e3f4a5b6c7_add_closed_at_to_validation_record.py` (new)
- `src/apollo/db/models.py` (modified — added `closed_at` to `ValidationRecord`)
- `src/apollo/config.py` (modified — added `closure_ceremony_interval_days`)
- `src/apollo/templates/closure.jinja` (new)
- `src/apollo/services/closure.py` (new)
- `src/apollo/services/worker.py` (modified — added Phase 5)
- `src/apollo/mcp/tools.py` (modified — added `trigger_closure_ceremony`)
- `tests/unit/test_closure_service.py` (new)
- `tests/integration/test_worker_closure.py` (new)

## Review Findings

### Decision Needed

- [x] [Review][Decision→Patch] **D1: Concurrent-tick duplicate ceremony → add `pg_try_advisory_lock()`** — Wrap the ceremony in a Postgres advisory lock so concurrent ticks are serialized; second caller bails out gracefully if lock is already held. [closure.py:close_pending]
- [x] [Review][Decision→Patch] **D2: 'offset' records included but unlabelled → add distinct label in `closure.jinja`** — Keep 'offset' records in the fetch; add a visual marker in the template (e.g., "Outcome: OFFSET — late fetch, calibration confidence reduced"). [closure.jinja:7]

### Patch Required

- [x] [Review][Patch] **P1: Post-SMTP DB failure → duplicate ceremony on next tick** — `session_factory.begin()` in `_mark_closed` can raise (DB down) after email is already sent; `closed_at` never written; next tick resends ceremony. [closure.py:90–92]
- [x] [Review][Patch] **P2: `_mark_closed` silent zero-row UPDATE** — `session.execute(sa_update(...))` result is discarded; if all IDs were already closed by a concurrent process, update silently affects zero rows but caller logs success. [closure.py:140–144]
- [x] [Review][Patch] **P3: `IntegrityError` catch too broad, increments `extraction_success` incorrectly** — Any DB constraint violation (FK, NOT NULL, check) is caught and counted as sealing success; a genuine constraint error is hidden. [worker.py: IntegrityError handler]
- [x] [Review][Patch] **P4: `FingerprintService.attach` called outside sealing transaction, exceptions uncaught** — A crash or exception in `FingerprintService.attach` propagates to the outer `except Exception`, counts as `extraction_failed` for a record that was already successfully sealed. [worker.py:~286]
- [x] [Review][Patch] **P5: `trigger_closure_ceremony` no error handling for client construction** — If `SMTPClientImpl(_settings)` or `get_session_factory()` raises, the raw exception propagates to the MCP caller. [mcp/tools.py:trigger_closure_ceremony]
- [x] [Review][Patch] **P6: `_render_email` ValueError propagates unhandled in MCP tool** — `ClosureService.close_pending()` is not wrapped in try/except inside `trigger_closure_ceremony`; a corrupted `closure.jinja` raises `ValueError` directly to the MCP layer. [mcp/tools.py:trigger_closure_ceremony]
- [x] [Review][Patch] **P7: `expiry_at` naive datetime stored silently** — `expiry_at.replace("Z", "+00:00")` is a no-op for strings without a `Z` suffix; resulting naive `datetime` causes `TypeError` on comparison with `datetime.now(UTC)` at validation time. [mcp/tools.py:configure_target]
- [x] [Review][Patch] **P8: `limit=500` truncation not logged** — `_fetch_pending` silently caps at 500 records; excess records wait until the next tick (up to 7 days away) with no warning emitted. [closure.py:_fetch_pending]
- [x] [Review][Patch] **P9: `interval_days=0` fires ceremony on every tick** — Fractional elapsed days is always >= 0; `interval_days=0` does not bypass — it makes the ceremony fire every tick, flooding the Asset. Integration test `test_tick_closes_validated_record_when_interval_zero` validates this boundary defect. [closure.py:70–72, test_worker_closure.py:~846]
- [x] [Review][Patch] **P10: `except OSError` too narrow for SMTP failure** — `SMTPClientImpl` can also raise `smtplib.SMTPException` or `ValueError`; those bypass the fail-operational branch and propagate out of `close_pending`. [closure.py:83]
- [x] [Review][Patch] **P11: `s.predicted_positive is None` renders as 'Negative' in template** — Jinja2 ternary `{{ "Positive" if s.predicted_positive else "Negative" }}` collapses `None` and `False` to the same label; missing data is indistinguishable from a genuine negative reading. [closure.jinja:7]
- [x] [Review][Patch] **P12: `trigger_closure_ceremony` ambiguous return for SMTP failure vs empty queue** — Both "SMTP failed" and "no pending sessions" return the same string, masking infrastructure errors from the operator. [mcp/tools.py:trigger_closure_ceremony]
- [x] [Review][Patch] **P13: Integration test session factory doesn't reset singleton before test** — `_make_closure_service_factory` calls `get_session_factory()` without resetting `_engine`/`_SessionFactory`; if the singleton was initialized before `patched_db_url` ran, factory silently targets production DB. [test_worker_closure.py:610–613]
- [x] [Review][Patch] **P14: `tools.py` missing `from __future__ import annotations`** — All new/modified service files carry the future import; `mcp/tools.py` does not. [mcp/tools.py:1]
- [x] [Review][Patch] **P15: 4 new `configure_target` parameters use `Optional[X]` instead of `X | None`** — `ticker`, `expiry_at`, `threshold_pct`, `threshold_direction` use legacy `Optional[str/float]`; project rules and story dev notes require `X | None` syntax. [mcp/tools.py:25–28]
- [x] [Review][Patch] **P16: `ClosureService` logger calls lack session/record context** — `logger.error` and `logger.info` in `closure.py` include `pending_count`/`closed_count` but no `validation_record_id` list or batch identifier for traceability. [closure.py:83–96]

### Deferred

- [x] [Review][Defer] **W1: Interval proxy uses `max(closed_at)` as ceremony timestamp — no separate audit table** [closure.py:_get_last_ceremony_timestamp] — deferred, design limitation acceptable for V1
- [x] [Review][Defer] **W2: Timezone-naive `last_sent` from a legacy row would crash interval subtraction** [closure.py:70] — deferred, `DateTime(timezone=True)` column prevents naive storage in practice
- [x] [Review][Defer] **W3: Unit tests never exercise real SQLAlchemy session path — internals always patched** [test_closure_service.py] — deferred, pre-existing test design
- [x] [Review][Defer] **W4: `trigger_closure_ceremony` wires SMTP/Jinja/session factory inline — inconsistent with tick() DI pattern** [mcp/tools.py] — deferred, follows quarantine.py MCP tool precedent

## Change Log

- 2026-06-06: Story 3.2 implemented — closure ceremony dispatch. Added `closed_at` column to `validation_record`, `ClosureService` with interval/on-demand modes, Phase 5 in `tick()`, MCP `trigger_closure_ceremony` tool, `closure.jinja` template, and full unit/integration test coverage (25 tests).
- 2026-06-07: Code review complete — 2 decisions needed, 16 patches, 4 deferred, 5 dismissed.
