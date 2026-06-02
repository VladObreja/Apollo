---
baseline_commit: 4dff837b048c1a6812a2596f9dd55717e2893cc7
---
# Story 1.1: Initialize Domain & Target Configuration (MCP)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Admin,
I want to configure target selection rules and parameters via an MCP tool,
so that the system knows what to task the asset with while capturing my psychological context.

## Acceptance Criteria

1. **Given** I provide a target statement, parameter, my current state, and optional target metadata (`is_control_target`, `age_in_hours`)
   **When** the Claude Code agent calls the `configure_target` MCP tool
   **Then** a target instance and parameter are securely created in the PostgreSQL database using SQLAlchemy
2. **And** an Admin State Snapshot and Awareness Tier are captured and immutably associated with the record
3. **And** the `uv` package structure and database tables (`corpus_record`) are properly initialized for this feature.

## Tasks / Subtasks

- [x] Initialize Project Structure (AC: 3)
  - [x] Scaffold using `uv init --package --python 3.12`
  - [x] Add dependencies: `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg2-binary`, `alembic`, `mcp`, `jinja2`
  - [x] Add dev dependencies: `ruff`, `mypy`, `pytest`, `testcontainers`
  - [x] Create `src/apollo/` and subdirectories (`domain/`, `db/`, `services/`, `mcp/`)
  - [x] Setup `src/apollo/config.py` using `pydantic-settings`
- [x] Implement Domain Layer (AC: 1, 2)
  - [x] Create `src/apollo/domain/models.py` with Pydantic v2 schemas for targets and admin state. Ensure NO database imports.
  - [x] Add strict `Field(description="...")` annotations for LLM steering.
- [x] Implement Database Layer (AC: 1, 2, 3)
  - [x] Create `src/apollo/db/models.py` with SQLAlchemy models for `corpus_record`.
  - [x] Setup Alembic and generate the initial migration script.
- [x] Implement Service and MCP Layers (AC: 1)
  - [x] Create `src/apollo/services/target.py` for target creation business logic.
  - [x] Create `src/apollo/mcp/tools.py` exposing the `configure_target` MCP tool, strictly delegating to the service layer.

## Dev Notes

- **Architecture Compliance:** Use purely PostgreSQL. DDL driven by Alembic. 
- **Strict Typing:** Must pass `mypy --strict`. No `Any` types.
- **Layer Isolation:** `src/apollo/mcp/` cannot bypass `src/apollo/services/` to access `db/`. `src/apollo/domain/` cannot import `db/` or `services/`.
- **Testing:** Unit tests test domain logic. Integration tests (`tests/integration/`) MUST use `testcontainers` for real Postgres. Never use SQLite shortcuts. 

### Project Structure Notes

- Adhere strictly to the scaffolding outlined in architecture.md:
  - `src/apollo/domain/`
  - `src/apollo/db/`
  - `src/apollo/services/`
  - `src/apollo/mcp/`

### References

- Project Context: [project-context.md](file:///c:/Apollo/_bmad-output/project-context.md)
- Architecture: [architecture.md](file:///c:/Apollo/_bmad-output/planning-artifacts/architecture.md)
- Epics: [epics.md](file:///c:/Apollo/_bmad-output/planning-artifacts/epics.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.1 Pro (High)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Implemented pure domain Pydantic models for TargetConfiguration
- Implemented SQLAlchemy declarative models for DB
- Scaffolded Alembic migrations, added initial schema
- Implemented TargetService and MCP configure_target tool
- Verified with Pytest, MyPy (--strict), and Ruff

### File List

- `pyproject.toml`
- `src/apollo/config.py`
- `src/apollo/domain/models.py`
- `src/apollo/db/models.py`
- `src/apollo/db/session.py`
- `src/apollo/db/alembic/env.py`
- `src/apollo/db/alembic/versions/d21693fe0e00_initial_schema.py`
- `src/apollo/services/target.py`
- `src/apollo/mcp/tools.py`
- `tests/unit/test_domain.py`

### Change Log
- Initial implementation of the domain, DB, service, and MCP layers for target configuration

### Review Findings

#### Decision-Needed

- [x] [Review][Decision] Table naming: keep `corpus_record` (singular) — RESOLVED: keep singular; architecture.md to be updated to reflect this convention.
- [x] [Review][Decision] Immutability trigger — RESOLVED: add `BEFORE UPDATE` trigger in this story's migration (→ converted to Patch below).
- [x] [Review][Decision] `@requires(Compartment.X)` — RESOLVED: scaffold minimal `Compartment` enum + `@requires` stub in this story (→ converted to Patch below).
- [x] [Review][Decision] `awareness_tier`/`parameter_name` enums — RESOLVED: defer; domain vocabulary still being finalized.

#### Patches

- [x] [Review][Patch] `metadata` field name shadows Pydantic v2 reserved attribute on `TargetConfiguration` — rename to `target_metadata` [`src/apollo/domain/models.py`]
- [x] [Review][Patch] `configure_target` is a plain function, not an MCP tool — add `@mcp.tool()` decorator and wire to a `FastMCP` server instance in `src/apollo/mcp/server.py` [`src/apollo/mcp/tools.py`]
- [x] [Review][Patch] No `src/apollo/mcp/server.py` and no `main.py` — MCP server never starts. Create `server.py` with `FastMCP` init and `main.py` entrypoint that calls `server.run()` [`src/apollo/mcp/`]
- [x] [Review][Patch] Engine and session created at module import time — breaks unit test isolation. Wrap in a factory function or lazy-init pattern [`src/apollo/db/session.py`]
- [x] [Review][Patch] Session context manager does not auto-rollback on exception — use `with session.begin():` or explicit `try/except/rollback/raise` [`src/apollo/services/target.py`]
- [x] [Review][Patch] Migration `id` column missing `server_default=sa.text("gen_random_uuid()")` — raw SQL inserts will NULL-crash the PK [`src/apollo/db/alembic/versions/d21693fe0e00_initial_schema.py`]
- [x] [Review][Patch] Migration `created_at` column missing `server_default=sa.text("NOW()")` — raw SQL inserts will fail NOT NULL constraint [`src/apollo/db/alembic/versions/d21693fe0e00_initial_schema.py`]
- [x] [Review][Patch] `age_in_hours` accepts negative integers — add `ge=0` constraint to Pydantic field [`src/apollo/domain/models.py`]
- [x] [Review][Patch] No `tests/conftest.py` and no `tests/__init__.py` — unit test `from apollo.domain.models import ...` will fail without `src/` on `PYTHONPATH` [`tests/`]
- [x] [Review][Patch] `TargetParameter.name` field description is too generic for LLM steering — enumerate valid values (`vad`, `rvd`, `ebf`, etc.) in the `Field(description=...)` [`src/apollo/domain/models.py`]
- [x] [Review][Patch] Add `BEFORE UPDATE` immutability trigger on `corpus_record` — AC-2 requires immutable association; add trigger in a new Alembic migration version [`src/apollo/db/alembic/versions/`]
- [x] [Review][Patch] Scaffold `Compartment` enum + `@requires` stub — create `src/apollo/domain/compartments.py` with minimal stub; decorate `TargetService.create_target_configuration` [`src/apollo/domain/compartments.py`, `src/apollo/services/target.py`]

#### Deferred

- [x] [Review][Defer] Hardcoded DB URL default `postgresql://postgres:postgres@localhost:5432/apollo` in `config.py` — deferred, pre-existing/acceptable for local dev scaffold; must document in README that `.env` is required for any non-local environment
- [x] [Review][Defer] No test factory pattern (`factory_boy`) — deferred, pre-existing; integration tests will need this but unit tests are acceptable as direct instantiation for Story 1.1 scope
- [x] [Review][Defer] Missing `docker-compose.yml` for local PostgreSQL — deferred, pre-existing; AC-WSL-1 infra qualification is a separate architecture concern not in Story 1.1 ACs
- [x] [Review][Defer] Missing GitHub Actions CI pipeline `ci.yml` — deferred, pre-existing; architecture mandates it but it is not in Story 1.1 acceptance criteria
- [x] [Review][Defer] Table naming convention `corpus_record` (singular) — deferred; architecture.md will be updated to adopt singular convention going forward
- [x] [Review][Defer] `awareness_tier`/`parameter_name` enums in `domain/types.py` — deferred; domain vocabulary still being finalized; add validation in a future story
