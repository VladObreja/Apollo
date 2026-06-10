---
stepsCompleted: [1, 2, 3]
inputDocuments: ["c:\\Apollo\\_bmad-output\\planning-artifacts\\prds\\prd-Apollo-2026-06-01\\prd.md", "c:\\Apollo\\_bmad-output\\planning-artifacts\\architecture.md"]
---

# Apollo - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Apollo, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Admin (Vlad) configures protocol guidelines and target criteria via Claude Code agent to establish Target Selection rules in the database.
FR2: Apollo Worker Daemon autonomously fetches targets while enforcing a strict cap of 5 targets per day.
FR3: System captures an Admin State Snapshot and logs the Admin Awareness Tier upon target creation.
FR4: System dynamically pairs a Target statement with a Parameter (e.g., VAD) to generate a Double-Blind Coordinate (e.g., XXXX/YYYY).
FR5: Local LLM agent drafts and dispatches the tasking email to the Asset (Jane) using isolated/unpersonalized research emails.
FR6: Local Extraction Agent intercepts the Asset's reply email, parses the unstructured text, and maps it strictly to a Pydantic schema.
FR7: Upon valid extraction, system cryptographically seals the session and commits the data to the event-sourced database.
FR8: Clarification Loop: If extraction is invalid, the Extraction Agent generates a polite clarification email to the Asset without leaking the true target identity, receives the reply, and re-validates.
FR9: Ground-Truth Validation: A background system daemon checks the actual market outcome at the precise expiry time and validates the Asset's sealed prediction against it.
FR10: Weekly Closure Ceremony: System aggregates all validated sessions for the week and drafts/sends a closure email containing definitive outcomes to the Asset.

### NonFunctional Requirements

NFR1: Strict Compartment Isolation (Double-Blind Purity): Must enforce boundaries via `CompartmentGuards`.
NFR2: Immutable Event-Sourced Ledger: `corpus_record` is append-only. Raw email bytes are strictly immutable. Extractions are mutable to support Epistemological Epochs.
NFR3: The 2x2 Stakes Matrix: System must independently track `real_money_at_stake` and `asset_financial_awareness` for every session.
NFR4: Strict Schema-Driven Extraction: Pydantic v2 schemas restrict LLM extraction outputs. Never write unvalidated or partial data.
NFR5: Fail-Operational and No Silent Discards: Missed sessions remain pending for review. Rescheduled closures must be flagged for temporal drift tracking.
NFR6: UTC-Native Time Architecture: All events, closure deadlines, and correlative timestamps recorded natively in UTC.
NFR7: Session Provenance Chain: Every session record must carry an immutable provenance chain capturing agent version, Epistemological Ledger state, confidence, and crypto seal hash.
NFR8: Data Registry Architecture: Database strictly isolates Asset Registry, Parameter Registry, and Question Template Library. Asset performance metrics must be dynamically derived, never stored.

### Additional Requirements

- **Starter Template:** Greenfield initialization using `uv init --package --python 3.12` with strictly pinned dependencies (No heavy web frameworks like FastAPI).
- **Project Organization:** Strict compartmentalization: `src/apollo/domain/` (Pure logic, no DB imports), `src/apollo/db/` (SQLAlchemy, Alembic), `src/apollo/services/` (Business logic, Worker daemon), `src/apollo/mcp/` (Interface).
- **Database & State:** PostgreSQL is the single source of truth using SQLAlchemy ORM and Alembic migrations. Uses Row-Level Security (RLS) for isolation.
- **Queueing:** PostgreSQL `LISTEN/NOTIFY` with `SELECT ... FOR UPDATE SKIP LOCKED` for task worker queue (No Redis).
- **Quarantine:** Dedicated `quarantine_record` table physically separates failed/corrupted extractions from the primary `corpus_record`.
- **LLM Templating:** Jinja2 (v3.1.6) exclusively used for LLM Agent Templating to ensure deterministic prompt construction.
- **Configuration:** 12-factor application design utilizing `pydantic-settings`.
- **Testing:** `pytest` + `testcontainers` for real PostgreSQL containerization in integration testing. No SQLite shortcuts.
- **CI/CD:** GitHub Actions with sequential gating (ruff -> mypy -> unit -> integration -> alembic reversibility).

### UX Design Requirements

None

### FR Coverage Map

### FR Coverage Map

FR1: Epic 1 - Admin target configuration
FR2: Epic 1 - Target fetching daemon
FR3: Epic 1 - Admin State Snapshot capture
FR4: Epic 1 - Double-Blind Coordinate pairing
FR5: Epic 1 - Tasking email dispatch
FR6: Epic 2 - Email interception & Pydantic mapping
FR7: Epic 2 - Cryptographic sealing & DB commit
FR8: Epic 2 - Clarification Loop (quarantine and retry)
FR9: Epic 3 - Ground-Truth Validation at expiry
FR10: Epic 3 - Weekly Closure Ceremony

## Epic List

### Epic 1: Target Definition & Dispatch

Establish the front half of the pipeline. The Admin can safely configure targets, and the system autonomously constructs double-blind assignments and dispatches them to the Asset.

### Story 1.1: Initialize Domain & Target Configuration (MCP)

As an Admin,
I want to configure target selection rules and parameters via an MCP tool,
So that the system knows what to task the asset with while capturing my psychological context.

**Acceptance Criteria:**

**Given** I provide a target statement, parameter, my current state, and optional target metadata (`is_control_target`, `age_in_hours`)
**When** the Claude Code agent calls the `configure_target` MCP tool
**Then** a target instance and parameter are securely created in the PostgreSQL database using SQLAlchemy
**And** an Admin State Snapshot and Awareness Tier are captured and immutably associated with the record
**And** the `uv` package structure and database tables (`corpus_record`) are properly initialized for this feature.

### Story 1.2: Event-Driven Queue & Coordinate Generation

As the System Daemon,
I want to fetch pending targets up to a strict daily cap and generate blinded coordinates,
So that tasks are ready for dispatch without exposing the true target identity.

**Acceptance Criteria:**

**Given** there are pending targets in the database
**When** the worker daemon executes an `apollo tick`
**Then** it fetches a maximum of 5 targets per day using a `SELECT ... WHERE available_after <= NOW() FOR UPDATE SKIP LOCKED` query (enforcing the Age-In protocol)
**And** it pairs each target with a parameter and generates a cryptographically randomized, unique double-blind coordinate (e.g., `8A2F/9B4C`)
**And** it ensures the coordinate cannot be reverse-engineered or correlated to previous sessions (even if the underlying target is identical)
**And** the generated coordinate is securely saved to the record.

### Story 1.3: Task Email Dispatch

As the System Daemon,
I want to format an email template and dispatch it to the Asset,
So that the asset receives blinded tasking instructions natively in UTC.

**Acceptance Criteria:**

**Given** a generated coordinate and parameter
**When** the dispatch component is triggered
**Then** it renders the tasking email strictly using the Jinja2 (`extraction.jinja`) templates
**And** it dispatches the email to the Asset's designated unpersonalized email address (e.g., `apollo.asset1@proton.me`) via SMTP
**And** it logs the dispatch event's provenance, agent version, and timestamp securely in UTC.

### Story 1.4: Epic 1 Tech Debt & Infrastructure Setup

As a Developer,
I want to establish CI/CD pipelines, containerize the database, and refactor test fixtures,
So that the codebase is robust, maintainable, and protected against regressions as we scale.

**Acceptance Criteria:**

**Given** the current state of the Apollo codebase at the end of Epic 1
**When** the tech debt and infrastructure setup is complete
**Then** a `docker-compose.yml` file is created to spin up a local PostgreSQL instance
**And** a GitHub Actions workflow (`.github/workflows/ci.yml`) is implemented with sequential gating (ruff -> mypy -> unit -> integration -> alembic reversibility)
**And** structured logging is initialized in the CLI entrypoint (`main.py`)
**And** test fixtures are refactored to use `factory_boy` for model instantiation
**And** `FakeSMTPClient` is deduplicated into a shared testing utility module
**And** test isolation issues (like the `db_session` fixture rollback no-op) are resolved
**And** documentation (`architecture.md`, `README.md`) is updated to reflect database URL requirements and the singular `corpus_record` naming convention.

### Epic 2: Asset Data Extraction & Sealing

Close the immediate operational loop. The system receives the Asset's response, rigorously validates it into structured data, seals it immutably, and recovers from errors gracefully.

### Story 2.1: Inbound Email Ingestion & Parsing

As the System Daemon,
I want to poll for incoming reply emails and parse their unstructured contents via a local LLM constrained by strict Pydantic schemas,
So that I can securely extract the Asset's raw measurements.

**Acceptance Criteria:**

**Given** an incoming email on the designated unpersonalized account
**When** the `email_poller` service runs
**Then** it extracts the raw email body and metadata
**And** passes it to the local Ollama LLM strictly enforcing the Pydantic JSON schema (VAD, timestamp, etc.)
**And** catches any Pydantic `ValidationError` if the LLM output is malformed.

### Story 2.2: Epistemological Sealing & Ledger Commit (Happy Path)

As the System,
I want to cryptographically seal successfully extracted sessions into the ledger,
So that the raw data is permanently immutable and ready for calibration.

**Acceptance Criteria:**

**Given** a successfully extracted Pydantic schema (Happy Path)
**When** the pipeline commits the record
**Then** the raw email bytes and extraction are cryptographically hashed (`raw_hash`)
**And** the record is inserted into `corpus_record` as an immutable event
**And** the session's provenance chain (LLM version, confidence) is logged
**And** the 2x2 Stakes Matrix states are properly recorded.

### Story 2.3: Quarantine & Clarification Loop (Exception Path)

As the System,
I want to isolate malformed extractions and autonomously request clarification from the Asset,
So that the pipeline doesn't crash and compartment isolation is preserved.

**Acceptance Criteria:**

**Given** a `ValidationError` during extraction
**When** the pipeline handles the error
**Then** the raw email is inserted into the `quarantine_record` table (bypassing the main ledger)
**And** a polite clarification email is rendered via Jinja2 (`clarification.jinja`) without exposing the true target
**And** the email is dispatched to the Asset requesting correction.

### Story 2.4: Environmental Context Fingerprinting

As the System,
I want to automatically enrich the extracted session record with an environmental snapshot (e.g., Kp index, Local Sidereal Time, solar wind conditions),
So that we can retrospectively analyze environmental correlates without requiring the Asset to manually report them.

**Acceptance Criteria:**

**Given** a successfully validated session ready for sealing
**When** the pipeline finalizes the record
**Then** a background agent fetches the current environmental metrics for the exact time of the Asset's measurement
**And** the data (Local Sidereal Time, Kp index, etc.) is immutably attached to the session's fingerprint
**And** if external data sources are temporarily unavailable, the session sealing does not fail (it gracefully tags the metadata as pending retrieval).

### Epic 3: Calibration & Closure

Complete the epistemological retrocausal loop. The system autonomously scores predictions against market reality and provides periodic closure feedback to the Asset.

### Story 3.1: Ground-Truth Market Validation

As the Calibration Engine,
I want to autonomously check the actual market outcome at the precise expiry time,
So that I can validate the Asset's sealed prediction against ground truth.

**Acceptance Criteria:**

**Given** a sealed session with a pending expiry time
**When** the precise UTC expiry time is reached
**Then** a background process awakens and fetches the ground truth market outcome
**And** validates the Asset's sealed prediction against the actual outcome
**And** securely records the result in the database (creating a new derived record, never altering the original immutable event)
**And** if market data is artificially delayed or an outage occurs, it flags the session (`Offset` / `Replay`) to account for temporal drift without discarding it.

### Story 3.2: Flexible Closure Ceremony Dispatch

As the System,
I want to aggregate validated sessions and send a definitive closure email based on a flexible schedule or an on-demand trigger,
So that the epistemological loop can be closed precisely when the Admin or Asset requires it (e.g., weekly, end-of-day, or immediately for testing).

**Acceptance Criteria:**

**Given** validated sessions waiting for closure
**When** the configured interval is reached (e.g., weekly or daily) **OR** when an on-demand generation is triggered manually
**Then** it aggregates all ground-truth validated sessions pending closure
**And** drafts a "Closure Ceremony" email containing the definitive list of actual target outcomes
**And** dispatches the email to the Asset
**And** updates the ledger to mark those sessions as epistemologically closed
**And** the Admin can trigger this on-demand at any time via an MCP tool (since Claude Code is the sole interface).

### Story 3.3: Statistical Calibration Scoring

As the Admin,
I want the system to continuously compute Brier scores, ECE, and empirical hit rates with Wilson score intervals over the closed sessions,
So that I can discover the Asset's actual optimal conviction threshold and establish our statistical confidence.

**Acceptance Criteria:**

**Given** a corpus of sealed, ground-truth-validated sessions
**When** the calibration engine is queried via the `get_calibration_stats` MCP tool
**Then** it computes the Brier score, Expected Calibration Error (ECE), and hit rates with Wilson score intervals
**And** the math engine properly accounts for temporal drift flags in its confidence calculations
**And** the logic executes entirely isolated from the extraction compartment (proving double-blind integrity)
**And** it returns the statistical readout back to the Claude Code agent.

### Epic 4: Hardening & Tech Debt

Added 2026-06-10 via Correct Course (sprint-change-proposal-2026-06-10.md). With FR1–FR10 shipped across Epics 1–3, this epic addresses the remaining unscheduled deferred-work items — including the `IntegrityError` scoping flagged in 3 independent code reviews — before V2 planning begins.

### Story 4.1: Worker Resilience & E2E Repair

As a Developer,
I want the worker's error-handling paths to be precise and the E2E suite to be trustworthy,
So that failure modes are correctly counted and CI red actually means something.

**Acceptance Criteria:**

**Given** the current worker, validation, and sealing services
**When** the resilience hardening is complete
**Then** the 4 failing tests in `tests/e2e/test_epic2_e2e.py` are fixed to match Story 2.2/2.3 sealing + quarantine behavior and pass in CI
**And** the `IntegrityError` catch in worker Phase 3 sealing is scoped to the specific concurrent-seal unique constraint, with other violations propagating or logged distinctly
**And** the `IntegrityError` catch in `_validate_one` is scoped to the `corpus_record_id` UNIQUE constraint
**And** `extraction_success` is no longer inflated by concurrent-seal `IntegrityError` handling or decorator-chain re-raises after a successful seal
**And** `b""` empty `raw_email_bytes` no longer causes a permanent DISPATCHED retry loop — a per-record retry limit or dead-letter mechanism is added.

### Story 4.2: Operational Hardening

As the Admin,
I want config and parsing edge cases handled,
So that the system degrades safely under real-world conditions.

**Acceptance Criteria:**

**Given** the current IMAP, MCP, and worker configuration
**When** the operational hardening is complete
**Then** a startup warning is logged when `imap_use_ssl=False`
**And** `expiry_at` ISO parsing in `configure_target` correctly handles non-Z-suffix offsets and date-only strings, producing UTC-aware datetimes
**And** sealed records permanently missing their environmental fingerprint row (due to a crash between seal-commit and fingerprint-write) are detected and backfilled on a subsequent tick.

### Story 4.3: Domain Vocabulary Formalization

As a Developer,
I want `parameter_name` and `admin_awareness_tier` to be type-safe enums,
So that the domain vocabulary that has stabilized across 3 epics is enforced in code and the database.

**Acceptance Criteria:**

**Given** the finalized domain vocabulary (`vad`, `rvd`, `ebf`, tier levels per architecture.md)
**When** the formalization is complete
**Then** `ParameterName` and `AwarenessTier` enums exist in `domain/types.py`
**And** Pydantic extraction/validation schemas use these enums
**And** an Alembic migration adds DB check constraints on `parameter_name` and `admin_awareness_tier`, proven reversible (`upgrade head` → `downgrade base` → `upgrade head`).

### Story 4.4: Test & Code Quality Cleanup

As a Developer,
I want test fixtures and minor code inconsistencies cleaned up,
So that the suite stays maintainable as the project grows.

**Acceptance Criteria:**

**Given** the accumulated test-suite debt across Epics 2 and 3
**When** the cleanup is complete
**Then** `_unique_hash()` is extracted into `tests/utils.py` and used by Story 3.2/3.3 test files
**And** `FakeIMAPClient` no longer re-delivers previously-fetched emails on subsequent `tick()` calls
**And** `QuarantineRecordFactory` produces a valid parent `CorpusRecord` (or is documented as requiring one)
**And** `FakeSMTPClient(raise_on_nth=1)` usage in `test_worker_quarantine.py` is robust to additional Phase 2 SMTP calls
**And** `_make_reply_email` and `_seed_dispatched` test helpers are consolidated into `tests/utils.py`
**And** an integration test proves `CalibrationService` double-blind isolation
**And** `test_offset_rows_excluded_from_brier` asserts the correct excluded Brier value
**And** a unit test exercises the real SQLAlchemy session path for `_get_last_ceremony_timestamp`/`_fetch_pending` in `ClosureService`
**And** `trigger_closure_ceremony` MCP tool wiring follows the `tick()` DI pattern for consistency.

### Story 4.5: Operator SOP Documentation

As the Admin (Vlad),
I want a written SOP for operating Apollo day-to-day,
So that configuring targets, monitoring tick cadence, and interpreting calibration output doesn't require holding the entire system in my head.

**Acceptance Criteria:**

**Given** the fully operational Apollo system at the end of Epic 3
**When** the SOP is complete
**Then** it documents how to configure a target via `configure_target`
**And** the expected `apollo tick` cadence and how to verify it's running
**And** how to interpret `get_calibration_stats` output (Brier score, ECE, Wilson CI)
**And** how to manually trigger a closure ceremony via `trigger_closure_ceremony`
**And** it references the "Known Limitations / Accepted Risk (V1)" section of `architecture.md`.


