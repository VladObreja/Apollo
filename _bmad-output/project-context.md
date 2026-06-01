---
project_name: 'Apollo'
user_name: 'Vlad'
date: '2026-05-31'
sections_completed: ['technology_stack']
existing_patterns_found: 0
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Core Language:** Python 3.12
- **Data Validation & Models:** Pydantic v2 (Schemas act as the protocol)
- **Database & ORM:** PostgreSQL + SQLAlchemy + Alembic (DDL is the source of truth, Postgres used for strict role-level compartment enforcement)
- **LLM Tier 1 (Unattended pipeline):** Local Ollama (Running natively on Windows Host. Model strictly pinned by digest `OLLAMA_MODEL_DIGEST = "sha256:..."`)
- **LLM Tier 2/3 (Attended tasks):** Commercial subscriptions (OpenAI GPT Plus, Google AI Pro, Claude Pro) and Claude Code. No per-token API billing.
- **Agent Interface:** Official `mcp` Python SDK
- **Task Scheduling:** Idempotent `apollo tick` via systemd timer / cron (Strictly no Redis, Celery, or message brokers)
- **Environment Management:** `uv` managed, single package, pinned dependencies
- **V2 Portability:** Extraction worker uses strict 12-factor config (`DATABASE_URL`) to pull jobs from a cloud Postgres instance in V2.

## Critical Implementation Rules

### Language-Specific Rules

- **Domain Logic & Compartments:** MCP tools and worker jobs contain ZERO business logic. They are typed adapters that delegate to `services/`. Service methods MUST be decorated with `@requires(Compartment.X)` to enforce capability boundaries purely in code.
- **Pydantic v2 JSON Schema Constraint:** Pydantic models define the absolute protocol. They must be strictly typed (no `Any`) because they are exported via `model_json_schema()` directly to Ollama to constrain generation.
- **Dependency Inversion (Protocols):** External integrations (especially the LLM) must be defined using `typing.Protocol` (e.g., `LLMClient`). Concrete implementations are injected at runtime to allow `FakeLLM` injection during tests.
- **LLM Error Handling & Retries:** When parsing Ollama structured output, catch Pydantic `ValidationError`. Allow exactly *one* bounded retry by appending the validation error to the prompt. If it fails again, raise `ExtractionSchemaError` and abort. NEVER write unvalidated/partial data to the database.
- **Database Access:** All database queries must use SQLAlchemy ORM. Schema changes must be driven entirely by Alembic (DDL is the single source of truth). Use `SELECT ... FOR UPDATE SKIP LOCKED` for idempotent job claiming.
- **Strict Typing:** All Python code must be thoroughly typed and capable of passing `mypy` strict type checks in CI.

### Framework-Specific Rules (MCP, Worker, Calibration & Epistemological Updates)

- **MCP is the Exclusive Interface:** All operator interaction happens exclusively through MCP tools exposed to Claude Code. No Web UI or hidden REST APIs.
- **Strictly Typed MCP Tools:** MCP tool signatures must use Pydantic models. Tools resolve the `CompartmentGuard` context and delegate to `services/`.
- **Stateless Worker Daemon:** The worker maintains ZERO in-memory queue state, running a `LISTEN/NOTIFY` loop directly against the Postgres `job` table.
- **Crash Recovery & Idempotency:** Survive `SIGKILL` using **Lock TTL Expiry**. Every worker handler must be perfectly idempotent.
- **First-Class Calibration Engine:** Operates exclusively over sealed prediction-outcome pairs. Outputs Brier scores, ECE, and empirical hit rates with Wilson score confidence intervals. 
- **Epistemological Schema Evolution:** The database schema MUST remain mutable to support "epistemological updates" (when the research dictates our data capture models were wrong). Alembic drives schema evolution, and `payload` models must be allowed to evolve.
- **Selective Immutability:** The `raw_email` bytes are the only strictly immutable artifact (reality cannot be altered). However, the derived `extraction` payloads are explicitly mutable to allow the system to re-analyze historical data when the project's protocol or vision is updated.

### Testing Rules

- **Strict Unit/Integration Boundaries:** Unit tests (`tests/unit/`) must test pure domain logic only—absolutely NO database calls, NO file IO, and NO LLM calls. Integration tests (`tests/integration/`) must use `testcontainers` for real Postgres execution.
- **LLM Faking (No Network in Tests):** Never call the real Ollama SDK in tests. Use the `LLMClient` Protocol to inject a `FakeLLM` that returns canned, structured JSON.
- **Data-Driven Fixtures over Mocking:** Use real, anonymized email files (`fixtures/emails/session_001.eml`) and assert the extraction against hand-labeled outputs (`fixtures/extractions/session_001.json`). Avoid heavy use of `unittest.mock` patching; use real data fixtures instead.
- **Hard Constraint Testing:** Database immutability triggers (AC-APP-1/2) and Compartment Guard decorators (AC-CMP-1/2) must be explicitly tested. A test must attempt an `UPDATE` on `corpus_record` and assert that Postgres rejects it.
- **Calibration Assertions:** Use a frozen `corpus()` fixture that produces *N* sealed sessions with known outcomes. The Calibration Engine's Brier score, ECE, and Wilson intervals must be tested against hand-computed mathematical equivalents.

### Code Quality & Style Rules

- **Linting & Formatting:** Use `ruff` as the single unified tool for all linting and code formatting.
- **Type Checking:** Enforce strict typing with `mypy --strict`. All function signatures and complex variables must be fully type-hinted.
- **Strict Code Organization:** The `src/apollo/` directory structure must be strictly respected: `domain/` for pure logic (no IO), `db/` for ORM/repository, `services/` for business logic, and adapters (`pipeline/`, `ollama/`, `mcp/`, `worker/`) on the edges.
- **Twelve-Factor Configuration:** All configuration must be environment-driven using `pydantic-settings` in `config.py`. Code must never read `os.environ` directly. The `Settings` object must be frozen and globally accessible.
- **No "Magic" or Metaprogramming:** Code must be explicit, boring, and statically traceable. Avoid dynamic imports, complex `**kwargs` proxying, or excessive metaprogramming. If it confuses `mypy`, don't do it.
- **Strict Domain Vocabulary:** Code must use the exact scientific terminology of the instrument. Variables and columns must literally be named `vad`, `rvd`, `ebf`, `receptivity`, `social_field`, `purity_tier`, and `admin_awareness_tier`.
- **LLM-Steering Schemas:** Every field in a Pydantic extraction schema MUST include a detailed `Field(description="...")`. Ollama relies heavily on these descriptions in the generated JSON schema to understand what to extract.
- **Domain-Specific Exceptions:** Never raise generic `Exception` or `ValueError`. Define and raise explicit domain exceptions (e.g., `CompartmentViolation`, `ExtractionSchemaError`) so the worker daemon can handle specific failure modes safely.
- **Structured Logging:** Use structured JSON logging. Every log line emitted within the context of a session MUST include the `session_id` to allow deterministic tracing through the asynchronous worker logs.

### Development Workflow Rules

- **Git as the Control Plane:** All infrastructure and deployment configuration (e.g., `docker-compose.yml`, `.wslconfig`, `render.yaml`) must be committed to the repository. The LLM operator manages deployments exclusively by editing configs and pushing.
- **Human-in-the-Loop PR Review:** AI agents (like Claude Code) must commit code to feature branches. The human operator MUST review the PR diff before merging to `main`. Automatic direct pushes to the deployment branch are forbidden.
- **Strict CI/CD Pipeline Gating:** The CI workflow must enforce sequential gating: `ruff` + `mypy` → Unit Tests → Integration Tests → Alembic smoke test. 
- **Reversible Migrations Only:** The Alembic CI smoke test must prove migrations are fully reversible (`upgrade head` → `downgrade base` → `upgrade head`). 
- **Dev/Prod Parity (No Local SQLite):** All local development and integration testing MUST run against a local Postgres container. Using SQLite as a testing shortcut is strictly forbidden.
- **Infrastructure Qualification First (AC-WSL-1):** Before writing any Python pipeline code, the WSL2 infrastructure must be qualified. A hard Windows reboot must automatically revive the Postgres container and worker daemon. 
- **Trigger via Scheduler Only:** Do not write utility scripts to bypass the pipeline. To test a flow locally, insert the required state into the database and run the `apollo tick` entrypoint. The dev workflow must mirror the production unattended workflow.
- **Respect the Temporal Cadence:** The system operates on a delayed-reveal cadence (the Weekly Closure Ceremony). Development workflows and tests must never assume that a session's outcome is instantly available after a prediction.

### Critical Don't-Miss Rules

- **Temporal Precision & Scheduling:** Sessions (both Admin and Asset) MUST be explicitly configurable to specific moments in time, rather than defaulting to "now", to cater to rigid schedules and recover from internet outages.
- **Financial Market Constraints:** The `domain/` layer must explicitly integrate market calendar dependencies. The system must algorithmically calculate trading days, hours, and holidays to enforce valid session windows, rather than relying on static cron configurations.
- **No Automatic Discarding & Temporal Drift Flags:** Missed sessions (due to outages or failures) MUST NOT be automatically discarded. They remain pending for human consultancy. If rescheduled, they must be flagged (e.g., `Offset` or `Replay`) so the Calibration Engine can account for temporal drift in its confidence intervals.
- **Double-Blind Integrity:** At no point can the entity making a prediction (Ollama) have access to the outcome. The extraction components and the calibration components must run in entirely isolated, mathematically proven compartments.
- **Epistemological Schema Review:** Before writing the implementation code, the team MUST execute a formal review of the proposed database schema and extraction validation mechanisms to ensure they align perfectly with the axiomatic requirements of the project. This review will commence immediately upon finalization of this context document.
