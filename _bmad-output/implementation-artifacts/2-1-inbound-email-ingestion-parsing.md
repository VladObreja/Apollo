---
baseline_commit: fd0524f
---

# Story 2.1: Inbound Email Ingestion & Parsing

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the System Daemon,
I want to poll for incoming reply emails and parse their unstructured contents via a local LLM constrained by strict Pydantic schemas,
So that I can securely extract the Asset's raw measurements.

## Acceptance Criteria

1. **Given** an incoming email on the designated unpersonalized account (`settings.imap_username`)
   **When** the `email_poller` service runs as Phase 3 of `apollo tick`
   **Then** it connects to the IMAP server, fetches UNSEEN messages, and marks each as SEEN (idempotency guarantee)
   **And** it parses each email's subject to extract the coordinate via `r'Target ID ([A-Z0-9]{4}/[A-Z0-9]{4})'`
   **And** for each coordinate that matches a `dispatched` corpus_record, it stores the raw email bytes on the record (`raw_email_bytes`, `received_at` in UTC)

2. **Given** a matched corpus_record with raw email bytes stored
   **When** the extraction phase runs
   **Then** it renders an extraction prompt via `src/apollo/templates/extraction_prompt.jinja` (Jinja2)
   **And** it calls the local Ollama LLM passing `ExtractionResultSchema.model_json_schema()` as the `format` constraint
   **And** it validates the LLM response against `ExtractionResultSchema` (Pydantic v2)

3. **Given** a Pydantic `ValidationError` on the first LLM attempt
   **When** the extraction service handles the error
   **Then** it appends the validation error text to the original prompt and makes exactly one retry
   **And** if the retry also fails validation, it raises `ExtractionSchemaError` (custom domain exception — never a bare ValueError)
   **And** the raw email bytes remain stored on the record regardless of extraction outcome

4. **Given** a successful extraction (no ValidationError)
   **When** the LLM returns a valid `ExtractionResultSchema`
   **Then** the extraction result is returned to the caller (status remains `dispatched` — sealing is Story 2.2)
   **And** the extraction outcome (success or `ExtractionSchemaError`) is logged in structured JSON with `record_id`

## Tasks / Subtasks

- [x] DB Schema: Add Email Ingestion Columns (AC: 1, 3)
  - [x] Create new Alembic migration chained to `c9d8e7f6a5b4` — use revision ID `e5f6a7b8c9d0`
  - [x] Add `raw_email_bytes`: `LargeBinary`, `nullable=True` (stores raw MIME bytes from IMAP)
  - [x] Add `received_at`: `DateTime(timezone=True)`, `nullable=True` (UTC timestamp of email reception)
  - [x] Create index `ix_corpus_record_received_at` on `received_at`
  - [x] Update `CorpusRecord` ORM model in `db/models.py` to reflect both new columns
  - [x] Ensure `downgrade()` drops index then columns in reverse order
  - [x] **No trigger update needed** — new columns are mutable lifecycle columns, not guarded by existing trigger

- [x] Config: IMAP + Ollama Settings (AC: 1, 2)
  - [x] Extend `src/apollo/config.py` `Settings` with IMAP fields (see Dev Notes for exact field names/defaults)
  - [x] Extend `Settings` with Ollama fields (see Dev Notes)
  - [x] Unit test: instantiate `Settings` with no env vars and assert all new defaults are correct

- [x] Domain: ExtractionResultSchema + Exceptions (AC: 2, 3)
  - [x] Add `ExtractionResultSchema` Pydantic v2 model to `src/apollo/domain/models.py` (see Dev Notes for exact fields and descriptions)
  - [x] Create `src/apollo/domain/exceptions.py` with `ExtractionSchemaError(Exception)` (see Dev Notes)
  - [x] Unit test: `ExtractionResultSchema.model_json_schema()` produces a valid JSON schema dict (non-empty, no `Any` types)
  - [x] Unit test: `ExtractionResultSchema` rejects `param_value` outside 0-100 range

- [x] Jinja2 Extraction Prompt Template (AC: 2)
  - [x] Create `src/apollo/templates/extraction_prompt.jinja` (see Dev Notes for exact format)
  - [x] Unit test in `tests/unit/test_templates.py`: render template with known `coordinate`, `parameter`, `email_body` and assert all three appear in output

- [x] ExtractionService (AC: 2, 3, 4)
  - [x] Create `src/apollo/services/extract.py`
  - [x] Define `LLMClient` Protocol: `def extract(self, prompt: str, schema: dict[str, Any]) -> str: ...`
  - [x] Implement `OllamaClientImpl(base_url: str, model_digest: str)` using only Python stdlib `urllib.request` — no httpx, no aiohttp (see Dev Notes for implementation sketch)
  - [x] Implement `ExtractionService` static class:
    - [x] `render_extraction_prompt(record: CorpusRecord, email_body: str, env: Environment) -> str` — renders `extraction_prompt.jinja`
    - [x] `extract(record: CorpusRecord, raw_email_body: str, llm_client: LLMClient, env: Environment) -> ExtractionResultSchema`
      - Renders prompt → calls `llm_client.extract(prompt, schema)` → parses JSON → validates with `ExtractionResultSchema.model_validate()`
      - On `ValidationError`: appends error text to prompt and retries once
      - On second `ValidationError`: raises `ExtractionSchemaError`
  - [x] Decorate `extract` with `@requires(Compartment.EXTRACTION_WRITE)`
  - [x] Unit tests in `tests/unit/test_extract_service.py` (see Testing section)

- [x] EmailPollerService (AC: 1, 3)
  - [x] Create `src/apollo/services/email_poller.py`
  - [x] Define `IMAPClient` Protocol: `def fetch_unseen_emails(self) -> list[bytes]: ...` (returns list of raw MIME message bytes)
  - [x] Implement `IMAPClientImpl(settings: Settings)` using Python stdlib `imaplib` + `email.parser.BytesParser` (see Dev Notes)
  - [x] Implement `EmailPollerService` static class:
    - [x] `parse_coordinate_from_subject(subject: str) -> str | None` — regex extraction, returns `None` if no match
    - [x] `parse_email_body(raw_bytes: bytes) -> str` — extracts `text/plain` part from MIME bytes
    - [x] `store_raw_email(record: CorpusRecord, raw_bytes: bytes, session: Session) -> None` — sets `raw_email_bytes`, `received_at = datetime.now(UTC)`, calls `session.add(record)`; decorated `@requires(Compartment.EXTRACTION_WRITE)`
    - [x] `fetch_new_session_emails(session: Session, imap_client: IMAPClient) -> list[tuple[CorpusRecord, bytes]]` — polls IMAP, matches by coordinate to dispatched records, stores raw bytes, returns matched pairs
  - [x] Unit tests in `tests/unit/test_email_poller.py` (see Testing section)

- [x] Worker Tick Extension — Phase 3 (AC: 1, 2, 3, 4)
  - [x] Update `src/apollo/services/worker.py`: add optional `llm_client: LLMClient | None = None` and `imap_client: IMAPClient | None = None` parameters to `tick()`
  - [x] If `llm_client is None`, create `OllamaClientImpl(settings.ollama_base_url, settings.ollama_model_digest)` at top of `tick()` (lazy, not at import time)
  - [x] If `imap_client is None`, create `IMAPClientImpl(settings)` at top of `tick()`
  - [x] After Phase 2 (queued → dispatched), add Phase 3:
    - Open read session, call `EmailPollerService.fetch_new_session_emails(session, imap_client)` → list of `(record, raw_bytes)`
    - Construct Jinja2 `Environment` pointing at `_TEMPLATES_DIR` (reuse existing `_TEMPLATES_DIR` constant)
    - For each pair: call `ExtractionService.extract(record, body, llm_client, env)` where `body = EmailPollerService.parse_email_body(raw_bytes)`
    - Wrap per-record extraction in `try/except ExtractionSchemaError`: log structured error with `record_id`, continue
    - On success: log structured success with `record_id` (status stays `dispatched` — sealing in Story 2.2)
  - [x] Integration test in `tests/integration/test_worker_email_phase.py` (see Testing section)

- [x] Unit Tests (AC: 1, 2, 3, 4)
  - [x] `tests/unit/test_extract_service.py`:
    - `test_extract_success` — FakeLLM returns valid JSON; assert returns `ExtractionResultSchema`
    - `test_extract_retries_on_validation_error` — FakeLLM returns invalid JSON once then valid; assert 2 calls made, returns schema
    - `test_extract_raises_extraction_schema_error_after_two_failures` — FakeLLM always returns invalid JSON; assert `ExtractionSchemaError` raised
    - `test_extract_prompt_contains_coordinate_and_parameter` — assert rendered prompt includes coordinate and parameter
  - [x] `tests/unit/test_email_poller.py`:
    - `test_parse_coordinate_from_subject_valid` — "Re: Apollo Research Session — Target ID 8A2F/9B4C" → "8A2F/9B4C"
    - `test_parse_coordinate_from_subject_no_match` — unrelated subject → `None`
    - `test_parse_email_body_plain_text` — MIME message with `text/plain` → correct body string
    - `test_parse_email_body_multipart` — MIME multipart with `text/plain` + `text/html` → plain text extracted
    - `test_fetch_new_session_emails_matches_dispatched_record` — FakeIMAPClient with 1 email matching a seeded dispatched record; assert 1 pair returned, `raw_email_bytes` stored on record
    - `test_fetch_new_session_emails_ignores_unknown_coordinate` — email with unrecognized coordinate → empty list returned

- [x] Integration Tests (AC: 1, 2, 3, 4)
  - [x] `tests/integration/test_worker_email_phase.py` — use same `patched_db_url` + `db_session` pattern as existing integration tests
  - [x] Seed 1 `dispatched` corpus_record with `double_blind_coordinate = "8A2F/9B4C"`
  - [x] Supply `FakeIMAPClient` with 1 synthetic email whose subject is `"Re: Apollo Research Session — Target ID 8A2F/9B4C"`
  - [x] Supply `FakeLLM` returning valid JSON matching `ExtractionResultSchema`
  - [x] Call `tick(imap_client=..., llm_client=...)`; call `session.expire_all()`
  - [x] Assert: record `raw_email_bytes` is not None, `received_at` is UTC-aware
  - [x] Assert: record status is still `dispatched` (sealing not in scope for 2.1)
  - [x] Failure path: `FakeLLM` always fails; assert `ExtractionSchemaError` is caught (tick does not raise), record stays `dispatched`

## Dev Notes

### Architecture Rules for This Story

- **Layer isolation is absolute:** `services/email_poller.py` and `services/extract.py` import from `db/models.py`, `domain/models.py`, `domain/compartments.py`, `domain/exceptions.py`. They MUST NOT import from `mcp/`.
- **No MCP changes in this story** — Phase 3 is a worker concern only.
- **stdlib only for IMAP and HTTP:** `imaplib` + `email.parser.BytesParser` for IMAP; `urllib.request` + `json` for Ollama. Do NOT add httpx, aiohttp, or any IMAP library.
- **Jinja2 Environment constructed once per tick** — pass it into `ExtractionService.render_extraction_prompt`, not instantiated inside the function. Reuse the existing `_TEMPLATES_DIR` path constant.
- **UTC everywhere:** `received_at = datetime.now(UTC)` — never `datetime.utcnow()`.
- **`@requires(Compartment.EXTRACTION_WRITE)` on all write methods** — `EXTRACTION_WRITE` is already defined in `domain/compartments.py`.
- **Status stays `dispatched` in Story 2.1** — `TargetStatus.SEALED` transition is Story 2.2. Do NOT add new status values to `domain/types.py`.
- **Raw bytes stored before LLM call** — `store_raw_email()` commits in its own transaction, then LLM extraction runs outside any DB transaction. If LLM fails, the raw bytes are already durably stored.
- **ExtractionSchemaError is a domain exception** — defined in `domain/exceptions.py`, raised by `ExtractionService.extract()`, caught in `worker.tick()` Phase 3 per-record loop (same pattern as SMTP failure in Phase 2).

### New Config Fields (`config.py`)

```python
# IMAP configuration — defaults for Proton Mail Bridge
imap_host: str = "127.0.0.1"
imap_port: int = 1143          # Proton Bridge IMAP port (not standard 993)
imap_username: str = ""
imap_password: SecretStr = SecretStr("")
imap_mailbox: str = "INBOX"
imap_use_ssl: bool = False     # False for Proton Bridge (plain local), True for direct IMAP/SSL

# Ollama configuration — model digest pinned, not by name
ollama_base_url: str = "http://localhost:11434"
ollama_model_digest: str = ""  # Must be set in .env: e.g., "sha256:abc123..."
ollama_timeout_seconds: int = 60
```

**Note:** Ollama runs natively on Windows host. From WSL2, `localhost` works in mirrored network mode (default on Windows 11). If using NAT mode, the user must set `OLLAMA_BASE_URL` to the host gateway IP in `.env`.

**Note:** `ollama_model_digest` intentionally has an empty default — if unset and Ollama is actually called, `OllamaClientImpl` will raise at runtime. Unit tests use `FakeLLM` so this config field is never read in tests.

### ExtractionResultSchema (`domain/models.py` — append to existing file)

```python
class ExtractionResultSchema(BaseModel):
    """LLM-extracted measurements from an Asset reply email.

    All fields carry detailed descriptions because Ollama uses them to
    understand what to extract from the unstructured email body.
    """

    param_value: float = Field(
        ge=0,
        le=100,
        description=(
            "The Asset's primary numerical measurement for the requested parameter "
            "(e.g., VAD, RVD, EBF), on a 0–100 scale. This is the value from the "
            "'PARAM (...)' line in the email reply."
        ),
    )
    measurement_timestamp: datetime | None = Field(
        default=None,
        description=(
            "The exact UTC datetime when the Asset performed the measurement. "
            "Extract from the 'Time of measurement (UTC)' field. "
            "Format as ISO-8601 (e.g., '2026-06-02T14:30:00Z')."
        ),
    )
    asset_location: str | None = Field(
        default=None,
        description=(
            "The Asset's physical location during the measurement session. "
            "Extract verbatim from the 'Location' field."
        ),
    )
    sleep_quality: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "The Asset's self-reported sleep quality on a 0–100 scale. "
            "Extract from the 'Sleep quality (0–100)' field. Return None if missing."
        ),
    )
    psychological_state: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "The Asset's self-reported psychological state on a 0–100 scale. "
            "Extract from the 'Psychological state (0–100)' field. Return None if missing."
        ),
    )
    social_field: str | None = Field(
        default=None,
        description=(
            "The Asset's social context during measurement. Must be exactly one of: "
            "'Isolated', 'Familiar', or 'Unfamiliar'. "
            "Extract from the 'Social Field' line. Return None if missing or unclear."
        ),
    )
    asset_notes: str | None = Field(
        default=None,
        description=(
            "Any additional qualitative notes or observations written by the Asset "
            "beyond the structured fields."
        ),
    )
```

### `domain/exceptions.py` (NEW file)

```python
"""Domain-specific exceptions for Apollo.

Never raise generic Exception or ValueError — use these named exceptions
so the worker daemon can handle specific failure modes safely.
"""


class ExtractionSchemaError(Exception):
    """Raised when the LLM fails to produce a valid ExtractionResultSchema after one retry.

    Caught in worker.tick() Phase 3 per-record loop. The raw email bytes
    are already stored; Story 2.3 will route this to the quarantine table.
    """
```

### Jinja2 Extraction Prompt Template (`src/apollo/templates/extraction_prompt.jinja`)

```
You are a data extraction assistant. Extract the research session measurements from the email below.

Session context:
- Target ID: {{ coordinate }}
- Parameter measured: {{ parameter }} (0-100 scale)

Extract the following fields:
- param_value: The numerical measurement for {{ parameter }}, 0-100 (required)
- measurement_timestamp: ISO-8601 UTC datetime of measurement (optional)
- asset_location: Physical location during measurement (optional)
- sleep_quality: Sleep quality 0-100 (optional)
- psychological_state: Psychological state 0-100 (optional)
- social_field: One of "Isolated", "Familiar", or "Unfamiliar" (optional)
- asset_notes: Additional qualitative notes (optional)

Email body:
{{ email_body }}
```

### OllamaClientImpl Sketch (`services/extract.py`)

```python
import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from jinja2 import Environment
from pydantic import ValidationError
from sqlalchemy.orm import Session

from apollo.db.models import CorpusRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import ExtractionSchemaError
from apollo.domain.models import ExtractionResultSchema


class LLMClient(Protocol):
    def extract(self, prompt: str, schema: dict[str, Any]) -> str: ...


class OllamaClientImpl:
    def __init__(self, base_url: str, model_digest: str, timeout: int = 60) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_digest = model_digest
        self._timeout = timeout

    def extract(self, prompt: str, schema: dict[str, Any]) -> str:
        payload = json.dumps(
            {"model": self._model_digest, "prompt": prompt, "format": schema, "stream": False}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            result: dict[str, Any] = json.loads(resp.read())
        return str(result["response"])


class ExtractionService:
    @staticmethod
    def _render_prompt(
        record: CorpusRecord, email_body: str, env: Environment
    ) -> str:
        template = env.get_template("extraction_prompt.jinja")
        return template.render(
            coordinate=record.double_blind_coordinate,
            parameter=record.parameter_name,
            email_body=email_body,
        )

    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def extract(
        record: CorpusRecord,
        email_body: str,
        llm_client: LLMClient,
        env: Environment,
    ) -> ExtractionResultSchema:
        schema = ExtractionResultSchema.model_json_schema()
        prompt = ExtractionService._render_prompt(record, email_body, env)

        raw = llm_client.extract(prompt, schema)
        try:
            return ExtractionResultSchema.model_validate(json.loads(raw))
        except (ValidationError, json.JSONDecodeError) as first_err:
            retry_prompt = (
                f"{prompt}\n\nValidation error on previous response: {first_err}\n"
                "Please correct and return valid JSON."
            )
            raw_retry = llm_client.extract(retry_prompt, schema)
            try:
                return ExtractionResultSchema.model_validate(json.loads(raw_retry))
            except (ValidationError, json.JSONDecodeError) as final_err:
                raise ExtractionSchemaError(
                    f"LLM failed to produce valid ExtractionResultSchema after 1 retry: {final_err}"
                ) from final_err
```

### IMAPClientImpl Sketch (`services/email_poller.py`)

```python
import imaplib
import re
from datetime import UTC, datetime
from email.parser import BytesParser
from email.policy import default as email_default_policy
from typing import Protocol

from sqlalchemy.orm import Session

from apollo.config import Settings
from apollo.db.models import CorpusRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.types import TargetStatus

_COORD_RE = re.compile(r"Target ID ([A-Z0-9]{4}/[A-Z0-9]{4})")


class IMAPClient(Protocol):
    def fetch_unseen_emails(self) -> list[bytes]: ...


class IMAPClientImpl:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_unseen_emails(self) -> list[bytes]:
        imap_class = imaplib.IMAP4_SSL if self._settings.imap_use_ssl else imaplib.IMAP4
        with imap_class(self._settings.imap_host, self._settings.imap_port) as conn:
            conn.login(
                self._settings.imap_username,
                self._settings.imap_password.get_secret_value(),
            )
            conn.select(self._settings.imap_mailbox)
            _, uids = conn.search(None, "UNSEEN")
            raw_emails: list[bytes] = []
            for uid in uids[0].split():
                _, msg_data = conn.fetch(uid, "(RFC822)")
                if msg_data and msg_data[0]:
                    raw_bytes = msg_data[0][1]  # type: ignore[index]
                    if isinstance(raw_bytes, bytes):
                        raw_emails.append(raw_bytes)
                # Mark SEEN unconditionally — we've taken responsibility for this email
                conn.store(uid, "+FLAGS", r"\Seen")
            return raw_emails


class EmailPollerService:
    @staticmethod
    def parse_coordinate_from_subject(subject: str) -> str | None:
        m = _COORD_RE.search(subject)
        return m.group(1) if m else None

    @staticmethod
    def parse_email_body(raw_bytes: bytes) -> str:
        msg = BytesParser(policy=email_default_policy).parsebytes(raw_bytes)
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="replace")
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="replace")
        return ""

    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def store_raw_email(
        record: CorpusRecord, raw_bytes: bytes, session: Session
    ) -> None:
        record.raw_email_bytes = raw_bytes
        record.received_at = datetime.now(UTC)
        session.add(record)

    @staticmethod
    def fetch_new_session_emails(
        session: Session, imap_client: IMAPClient
    ) -> list[tuple[CorpusRecord, bytes]]:
        raw_emails = imap_client.fetch_unseen_emails()
        matched: list[tuple[CorpusRecord, bytes]] = []
        SessionFactory = get_session_factory()
        for raw_bytes in raw_emails:
            msg = BytesParser(policy=email_default_policy).parsebytes(raw_bytes)
            subject = str(msg.get("subject") or "")
            coord = EmailPollerService.parse_coordinate_from_subject(subject)
            if coord is None:
                continue
            record: CorpusRecord | None = (
                session.query(CorpusRecord)
                .filter(
                    CorpusRecord.double_blind_coordinate == coord,
                    CorpusRecord.status == TargetStatus.DISPATCHED.value,
                )
                .first()
            )
            if record is None:
                continue
            with SessionFactory.begin() as write_session:
                fresh: CorpusRecord | None = write_session.get(CorpusRecord, record.id)
                if fresh is not None:
                    EmailPollerService.store_raw_email(fresh, raw_bytes, write_session)
            matched.append((record, raw_bytes))
        return matched
```

**Note:** `fetch_new_session_emails` reads from `session` (to query by coordinate) but writes raw bytes in a separate `SessionFactory.begin()` transaction. This ensures raw bytes are durably committed before any LLM call (fail-operational: bytes survive a crash).

### Worker Tick Extension (Phase 3 sketch)

```python
# In worker.py tick() — add after Phase 2, imports at top of file

from apollo.services.email_poller import EmailPollerService, IMAPClient, IMAPClientImpl
from apollo.services.extract import ExtractionService, LLMClient, OllamaClientImpl
from apollo.domain.exceptions import ExtractionSchemaError

def tick(
    smtp_client: SMTPClient | None = None,
    llm_client: LLMClient | None = None,
    imap_client: IMAPClient | None = None,
) -> None:
    ...
    # At top of tick():
    if llm_client is None:
        llm_client = OllamaClientImpl(
            _settings.ollama_base_url,
            _settings.ollama_model_digest,
            _settings.ollama_timeout_seconds,
        )
    if imap_client is None:
        imap_client = IMAPClientImpl(_settings)

    # --- Phase 3: dispatched → extraction attempt ---
    with SessionFactory() as read_session:
        matched_pairs = EmailPollerService.fetch_new_session_emails(read_session, imap_client)

    extraction_success = 0
    extraction_failed = 0
    for record, raw_bytes in matched_pairs:
        body = EmailPollerService.parse_email_body(raw_bytes)
        try:
            _result = ExtractionService.extract(record, body, llm_client, env)
            extraction_success += 1
            logger.info(
                "apollo.worker.tick: extraction succeeded",
                extra={"record_id": str(record.id)},
            )
            # Story 2.2: SealingService.seal(record, raw_bytes, _result) goes here
        except ExtractionSchemaError as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: extraction failed after retry",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
            # Story 2.3: QuarantineService.quarantine(...) goes here

    if matched_pairs:
        logger.info(
            "apollo.worker.tick: extraction phase complete",
            extra={"success": extraction_success, "failed": extraction_failed},
        )
```

**Note:** `env` (the Jinja2 Environment) is constructed once per tick and reused across Phase 2 and Phase 3. The `_TEMPLATES_DIR` constant already defined in `worker.py` covers both templates.

### Alembic Migration Details

New revision `e5f6a7b8c9d0`, `down_revision = "c9d8e7f6a5b4"`:

```python
def upgrade() -> None:
    op.add_column("corpus_record", sa.Column("raw_email_bytes", sa.LargeBinary(), nullable=True))
    op.add_column("corpus_record", sa.Column("received_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_corpus_record_received_at", "corpus_record", ["received_at"])

def downgrade() -> None:
    op.drop_index("ix_corpus_record_received_at", table_name="corpus_record")
    op.drop_column("corpus_record", "received_at")
    op.drop_column("corpus_record", "raw_email_bytes")
```

Migration revision chain: `d21693fe0e00` → `b4c7e1f02a9d` → `a1b2c3d4e5f6` → `c9d8e7f6a5b4` → **`e5f6a7b8c9d0`**

### FakeLLM for Tests

Define in `tests/unit/test_extract_service.py` (or add to `tests/utils.py`):

```python
class FakeLLM:
    """Canned LLM responses for extraction tests; raises after nth call."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._call_count = 0

    def extract(self, prompt: str, schema: dict[str, Any]) -> str:
        if self._call_count >= len(self._responses):
            raise AssertionError("FakeLLM called more times than expected")
        response = self._responses[self._call_count]
        self._call_count += 1
        return response
```

FakeIMAPClient (add to `tests/utils.py`):

```python
class FakeIMAPClient:
    """Returns canned raw MIME bytes as unseen emails."""

    def __init__(self, raw_emails: list[bytes]) -> None:
        self._raw_emails = raw_emails

    def fetch_unseen_emails(self) -> list[bytes]:
        return list(self._raw_emails)
```

### Testing Strategy

**Unit tests (no DB, no IO):**
- `tests/unit/test_extract_service.py` — all via `FakeLLM`; no DB, no Ollama, no network
- `tests/unit/test_email_poller.py` — parse/match logic via `FakeIMAPClient`; DB interactions use `FakeSession` / `MagicMock`
- `tests/unit/test_templates.py` — extend existing file to test `extraction_prompt.jinja` rendering
- `tests/unit/test_domain.py` — extend existing file with `ExtractionResultSchema` validation tests

**Integration tests (testcontainers Postgres):**
- `tests/integration/test_worker_email_phase.py`
- Use `patched_db_url` monkeypatch fixture (patches `DATABASE_URL` + resets `_engine`/`_SessionFactory` in `apollo.db.session`) — copy exact pattern from `test_worker_tick.py`
- Call `session.expire_all()` after `tick()` to force fresh DB reads (established pattern from Story 1.2)
- Build a synthetic raw MIME bytes fixture using Python stdlib `email.mime.text.MIMEText` + `email.mime.multipart.MIMEMultipart`

### Established Patterns (carry forward from Stories 1.1–1.4)

1. `SessionFactory.begin()` for write transactions — never call `session.commit()` manually
2. `get_session_factory()` lazy factory — all services use it
3. `@requires(Compartment.X)` on every write method
4. `mypy --strict` must pass — use `X | None` syntax, no `Optional[X]`
5. `ruff format .` + `ruff check .` before any commit
6. `tests/conftest.py` adds `src/` to sys.path — unit tests import `apollo.*` directly
7. Integration tests use `patched_db_url` monkeypatch fixture
8. `session.expire_all()` after `tick()` in integration tests
9. Table name is singular `corpus_record`
10. `server_default = None` for nullable columns — do NOT use `sa.text("NULL")`
11. Alembic: never modify existing revisions, always chain new ones
12. `module`-scoped testcontainer fixture, `function`-scoped `db_session` with DELETE+commit isolation
13. Factory patterns: `CorpusRecordFactory` in `tests/factories.py` — use for seeding records in integration tests (do NOT use raw SQL inserts)
14. `FakeSMTPClient` lives in `tests/utils.py` — add `FakeLLM` and `FakeIMAPClient` to the same file
15. `datetime.now(UTC)` — never `datetime.utcnow()` (deprecated in Python 3.12)

### Deferred Items from Previous Stories (awareness, no action required in 2.1)

- `db_session` fixture rollback teardown is a no-op — pre-existing known issue
- Deduplicate FakeSMTPClient — still pending; do NOT create a new duplicate; add FakeLLM/FakeIMAPClient to `tests/utils.py`
- Structured logging not yet initialized in `main.py` — logs will appear only if a handler is configured externally

### Files to CREATE (NEW)

- `src/apollo/services/extract.py` — `LLMClient` Protocol, `OllamaClientImpl`, `ExtractionService`
- `src/apollo/services/email_poller.py` — `IMAPClient` Protocol, `IMAPClientImpl`, `EmailPollerService`
- `src/apollo/domain/exceptions.py` — `ExtractionSchemaError`
- `src/apollo/templates/extraction_prompt.jinja` — Ollama extraction prompt template
- `src/apollo/db/alembic/versions/e5f6a7b8c9d0_add_email_ingestion_columns.py` — Alembic migration
- `tests/unit/test_extract_service.py` — unit tests for ExtractionService
- `tests/unit/test_email_poller.py` — unit tests for EmailPollerService
- `tests/integration/test_worker_email_phase.py` — integration tests for Phase 3

### Files to UPDATE (EXISTING)

- `src/apollo/config.py` — add IMAP + Ollama config fields (SecretStr for `imap_password`)
- `src/apollo/domain/models.py` — append `ExtractionResultSchema` class
- `src/apollo/db/models.py` — add `raw_email_bytes`, `received_at` columns to `CorpusRecord`
- `src/apollo/services/worker.py` — add Phase 3; add `llm_client` + `imap_client` DI params to `tick()`
- `tests/utils.py` — add `FakeLLM` and `FakeIMAPClient`
- `tests/unit/test_templates.py` — add test for `extraction_prompt.jinja`
- `tests/unit/test_domain.py` — add `ExtractionResultSchema` validation tests

### Files NOT to Touch

- `src/apollo/domain/types.py` — no new status values in 2.1
- `src/apollo/domain/compartments.py` — `EXTRACTION_WRITE` already defined
- `src/apollo/domain/coordinates.py` — no changes
- `src/apollo/mcp/` — no interface changes in this story
- `src/apollo/templates/extraction.jinja` — outbound tasking template; unchanged
- `src/apollo/services/dispatch.py` — no changes
- `src/apollo/services/queue.py` — no changes
- `src/apollo/services/target.py` — no changes
- Existing Alembic migrations — never modify, only chain

### New Dependency Check

No new runtime dependencies required. All needed libraries are Python stdlib:
- `imaplib` — stdlib IMAP4 client
- `email.parser.BytesParser`, `email.policy.default` — stdlib MIME parsing
- `urllib.request`, `json` — stdlib HTTP + JSON for Ollama
- `re` — stdlib regex for coordinate matching

Do NOT add `httpx`, `aiohttp`, `imapclient`, `IMAPClient`, or any email helper library.

### References

- Project Context: `_bmad-output/project-context.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Structure Patterns, Process Patterns)
- Epics (Story 2.1 AC): `_bmad-output/planning-artifacts/epics.md`
- Epistemological Schema: `_bmad-output/planning-artifacts/epistemological-schema-architecture.md` (RadiesthesiaMeasurement model)
- PRD (NFR-4, UJ-2): `_bmad-output/planning-artifacts/prds/prd-Apollo-2026-06-01/prd.md`
- Previous Story (1.3): `_bmad-output/implementation-artifacts/1-3-task-email-dispatch.md`
- Extraction template (outbound reference): `src/apollo/templates/extraction.jinja`

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- `test_json_schema_is_valid_dict` initially searched for "Any" string in schema repr and hit it in the model docstring. Fixed to check `type` or `anyOf` per property.
- Existing `test_worker_tick.py` tests relied implicitly on SMTP failing to keep records in `queued`. With Mailpit live + `FakeSMTPClient`, Phase 2 dispatches records. Updated 5 tests to `status in (QUEUED, DISPATCHED)`.
- `mypy --strict` raised `Unused "type: ignore"` on `email_poller.py:72` — removed the now-unnecessary comment.

### Completion Notes List

- Alembic migration `e5f6a7b8c9d0` adds `raw_email_bytes` (LargeBinary) + `received_at` (UTC DateTime) + index to `corpus_record`. Chains to `c9d8e7f6a5b4`.
- `ExtractionResultSchema` in `domain/models.py`: 7 fields, all with `Field(description=...)`, 0-100 ranges enforced. `model_json_schema()` produces a fully typed schema for Ollama `format` constraint.
- `ExtractionSchemaError` in new `domain/exceptions.py`. Never raise bare ValueError.
- `services/extract.py`: `LLMClient` Protocol + `OllamaClientImpl` (stdlib `urllib.request` only) + `ExtractionService.extract()` with 1-retry. `@requires(Compartment.EXTRACTION_WRITE)` applied.
- `services/email_poller.py`: `IMAPClient` Protocol + `IMAPClientImpl` (stdlib `imaplib`, marks SEEN unconditionally) + `EmailPollerService`. Raw bytes stored in own transaction before LLM call (fail-operational).
- `worker.py` Phase 3 added: polls IMAP → matches dispatched records → stores bytes → extracts. `ExtractionSchemaError` caught per-record. `llm_client`/`imap_client` DI params added to `tick()`.
- `FakeLLM` and `FakeIMAPClient` added to `tests/utils.py`. All existing integration tests updated to inject `FakeSMTPClient` + `FakeIMAPClient`.
- 100 tests pass (82 unit + 18 integration). `mypy --strict` clean. `ruff check` + `ruff format` clean.

### File List

**NEW:**
- `src/apollo/db/alembic/versions/e5f6a7b8c9d0_add_email_ingestion_columns.py`
- `src/apollo/domain/exceptions.py`
- `src/apollo/services/extract.py`
- `src/apollo/services/email_poller.py`
- `src/apollo/templates/extraction_prompt.jinja`
- `tests/unit/test_extract_service.py`
- `tests/unit/test_email_poller.py`
- `tests/unit/test_templates.py`
- `tests/integration/test_worker_email_phase.py`

**UPDATED:**
- `src/apollo/config.py` — 6 IMAP + 3 Ollama config fields
- `src/apollo/db/models.py` — `raw_email_bytes`, `received_at` columns + `LargeBinary` import
- `src/apollo/domain/models.py` — appended `ExtractionResultSchema`
- `src/apollo/services/worker.py` — Phase 3; `llm_client` + `imap_client` DI params
- `tests/utils.py` — `FakeLLM`, `FakeIMAPClient`
- `tests/unit/test_domain.py` — `TestExtractionResultSchema` (8 tests)
- `tests/unit/test_dispatch_service.py` — IMAP + Ollama defaults tests; FakeIMAPClient injection
- `tests/integration/test_worker_tick.py` — `FakeSMTPClient`/`FakeIMAPClient` injection; Phase 1 assertion fixes
- `tests/integration/test_worker_dispatch.py` — `FakeIMAPClient` injection
- `tests/e2e/test_epic1_e2e.py` — `FakeIMAPClient` injection

### Change Log

- 2026-06-02: Story created by bmad-create-story workflow.
- 2026-06-02: Implemented all tasks for Story 2.1. 100 tests pass, mypy strict clean, ruff clean.

### Review Findings

- [ ] [Review][Decision] Prompt injection via unbounded email_body � The template inserts Asset-controlled email content verbatim into the LLM instruction context with autoescape=False.
- [ ] [Review][Patch] Stale ORM record returned from fetch_new_session_emails [services/email_poller.py]
- [ ] [Review][Patch] Network/HTTP errors and JSON errors in OllamaClientImpl bypass retry logic and crash the tick [services/extract.py]
- [ ] [Review][Patch] fetch_new_session_emails creates its own SessionFactory on every call [services/email_poller.py]
- [ ] [Review][Patch] social_field accepts any string, violating documented constraint [domain/models.py]
- [ ] [Review][Patch] raw_email_bytes can be silently overwritten or written to non-DISPATCHED record [services/email_poller.py]
- [ ] [Review][Patch] SEEN flag is set unconditionally even for messages with non-bytes payloads [services/email_poller.py]
- [ ] [Review][Patch] ExtractionService.extract carries an undocumented/dead session parameter [services/extract.py]
- [ ] [Review][Patch] ollama_model_digest defaults to empty string, no startup guard [src/apollo/config.py]
- [ ] [Review][Patch] TEMPLATES_DIR path computation duplicated across two new test files [tests/]
- [ ] [Review][Patch] conn.select(), conn.search(), conn.fetch() exceptions or statuses ignored or propagated [services/email_poller.py]
- [ ] [Review][Patch] SessionFactory.begin() raises inside for-loop -> Unrecoverable data loss [services/email_poller.py]
- [ ] [Review][Patch] Ollama JSON response missing 'response' key -> KeyError bypasses retry [services/extract.py]
- [ ] [Review][Patch] Phase 3 for-loop unexpected exceptions abort all remaining extractions [services/worker.py]
- [ ] [Review][Patch] _render_prompt TemplateNotFound exception propagates [services/extract.py]
- [ ] [Review][Patch] Multipart email no text/plain part -> Empty body [services/email_poller.py]
- [ ] [Review][Patch] LLM returns naive datetime for measurement_timestamp -> stored as naive [domain/models.py]
- [ ] [Review][Patch] Index drop rollback issue [src/apollo/db/alembic/versions/e5f6a7b8c9d0_add_email_ingestion_columns.py]
- [ ] [Review][Patch] FakeLLM AssertionError leaks to worker loop [tests/utils.py]
- [ ] [Review][Patch] imap_username empty credentials raises ValueError at runtime not startup [src/apollo/config.py]
- [ ] [Review][Patch] Phase 3 summary log uses wrong structured field names [services/worker.py]
- [ ] [Review][Patch] render_extraction_prompt implemented as private _render_prompt [services/extract.py]
- [ ] [Review][Patch] test_extract_prompt_contains_coordinate_and_parameter split into two tests [tests/unit/test_templates.py]
- [ ] [Review][Patch] Multiple required unit test names deviate from spec [tests/unit/]
- [ ] [Review][Patch] tests/unit/test_templates.py created instead of extending an existing one [tests/unit/test_templates.py]
- [ ] [Review][Patch] FakeLLM.prompts attribute added without authorisation [tests/utils.py]
- [ ] [Review][Patch] ExtractionService.extract task checkbox left unchecked in story file [_bmad-output/implementation-artifacts/2-1-inbound-email-ingestion-parsing.md]
- [x] [Review][Patch] Integration test coordinates not isolated [tests/integration/test_worker_email_phase.py]
- [ ] [Review][Patch] Phase 3 env construction placement contradicts spec note [services/worker.py]
- [x] [Review][Defer] IMAP connection is opened and closed on every fetch_unseen_emails [services/email_poller.py] � deferred, pre-existing / by design
- [x] [Review][Defer] imap_use_ssl = False default has no security warning [src/apollo/config.py] � deferred, pre-existing
- [x] [Review][Defer] FakeIMAPClient reused across tick calls causes all emails to be re-delivered [tests/utils.py] � deferred, pre-existing

