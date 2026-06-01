# Apollo — Session Handoff
**Date:** 2026-05-31
**Status:** Mid-workflow — context limit approaching. Continue from here.

---

## Where We Were

Running `bmad-generate-project-context`. Step 1 (discovery) completed. Step 2 (generation) started — Category 1 (Technology Stack) was drafted and presented to Vlad but **not yet accepted or written to file**. Before accepting, Vlad requested a Party Mode adversarial review of the proposed technology stack. The review revealed the stack was inherited from an earlier, less-advanced iteration and was fundamentally misaligned. Vlad then called for a **complete clean-sheet redesign**.

**The project-context.md file at `_bmad-output/project-context.md` exists but contains only the empty template. Nothing has been written to it yet.**

The next action after this handoff is to: complete the clean-sheet architecture (resolve the three open questions below), then return to `bmad-generate-project-context` step 2 and write the project-context.md based on the new architecture — not the old stack.

---

## The Old Stack (Discarded)

The following services were inherited from the previous project iteration and are **no longer part of the design**:

- Ollama (stays — but role changes)
- apollo-lightrag / LightRAG (REMOVED)
- docling (REMOVED from v1 scope)
- apollo-agent / OpenClaw (REMOVED — absorbed into MCP server)
- browserless + crawl4ai (REMOVED — Second Brain / web archiver is out of v1 scope)
- n8n + n8n_db (REMOVED — replaced by Python workers + Postgres)
- open-webui (REMOVED)
- Redis Streams (REMOVED — never built, not needed)

---

## Adversarial Review — Key Findings

Four agents (Winston/Architect, Amelia/Dev, Murat/QA, Mary/BA) reviewed the old stack independently. Convergent findings:

### Critical (design-breaking)
1. **LLM extraction treats derived output as canonical.** The raw email is the canonical artifact; the LLM extraction is a derived, re-runnable layer. The schema and data model must enforce this lineage — not application discipline.
2. **Double-blind compartment enforcement rested on Redis stream topology** (naming convention). Topology fails open — one misconfigured consumer and the blind is silently breached. Must be enforced via capability/credential boundaries that fail closed.
3. **The calibration engine — the primary success criterion — had no named technology, schema, or owner.** It was the biggest gap in the entire design. It is now a named first-class component.
4. **LightRAG and Redis Streams were over-engineered** for a low-frequency (sessions per week), single-operator, single-asset system. Both removed.

### Mary's unique finding
- Apollo had built a *pipeline* and called it a *measurement instrument*. Nine of ten technology choices were about moving data; none of them computed a Brier score or produced a calibration curve. The center of gravity was in the wrong place.

### Murat's risk scoring
- **R1 (Score 25, MAX silence): Non-deterministic LLM extraction silently corrupts append-only corpus.** Top risk. Addressed by: raw email as canonical, extraction as derived child record, model digest pinning, golden-set regression tests, validation gate before any write.
- **R2 (Score 20, HIGH silence): Double-blind broken by topology.** Addressed by: capability/key boundaries, fail-closed design, negatively-tested compartment guard.
- **R3 (Score 16): Fail-operational claim vs. actual stack.** WSL2 is unreliable as a production substrate. Addressed by: idempotent cron tick, Postgres as sole state store, tested reboot recovery (AC-WSL-1 must pass before pipeline code).

---

## Clean-Sheet Architecture — Agreed Design

### Core Philosophy
Apollo is a **low-frequency, single-operator, single-asset research instrument.** Sessions measured in days and weeks, not milliseconds. Every infrastructure choice must be earned by the cadence, not speculated. Boring technology, fail-closed boundaries, the database as the only shared state.

### Services (V1 — all local on hardware)

**A. Apollo Core (Python 3.12 + Pydantic v2)**
- Single Python application containing all domain logic
- Library plus thin entrypoints — not a long-running daemon for most work
- Pydantic v2 for every domain model (schemas ARE the protocol)

**B. MCP Server (Python, `mcp` SDK)**
- The one long-running listener
- Thin: validates inputs, calls Apollo core services, returns structured results
- Exposes tools: `propose_target`, `dispatch_session`, `ingest_reply`, `run_calibration`, `export_analysis_prompt`, `record_external_analysis`, `reveal_outcome`, etc.
- Claude Code via MCP is the sole operator interface — no web UI

**C. Scheduler / Tick (systemd timer or cron)**
- `apollo tick` — idempotent Python entrypoint, fires every N minutes
- Polls inbox, advances session state, enqueues extractions, retries dispatches
- No in-memory queue; if machine is off for 3 days, next tick picks up where reality left off
- Fail-operational guarantee: pipeline runs unattended during multi-day aviation blackouts

**No additional services.** No Redis, no LightRAG, no n8n, no graph DB, no message broker.

### Data Architecture

**Database: SQLite (V1) → Postgres (V2)**
- Single file, ACID, WAL mode, zero operational surface
- SQLAlchemy (ORM) + Alembic (migrations) from day one so V2 migration is a connection string swap, not a rewrite
- Postgres in V2 enables per-role credential-level compartment enforcement

**Event-sourced corpus (append-only by construction):**
```
corpus_record table:
  record_id        uuid pk
  record_type      text  -- 'raw_email' | 'extraction' | 'outcome'
  parent_id        uuid null  -- extraction MUST reference raw_email parent (CHECK constraint)
  compartment      text  -- enum-constrained
  raw_bytes        bytea null  -- canonical RFC822 email (raw_email only)
  raw_hash         text  -- sha256, unique constraint
  payload          jsonb null  -- derived extraction; null for raw_email
  created_at       timestamptz  -- UTC only. NO updated_at. Ever.
  -- hash chain: each row hashes prev_hash + canonical_payload
```

**Immutability enforcement (DB level, not app trust):**
- `GRANT INSERT, SELECT` only on corpus_record (no UPDATE, no DELETE for app role)
- Belt-and-suspenders: `BEFORE UPDATE OR DELETE` trigger raises exception
- Schema lineage: CHECK constraint forces extraction records to have non-null parent_id

**The raw email is canonical. Extractions are derived child records pointing back to the raw blob's hash. Extractions are re-runnable; the raw record is sealed forever.**

**Job queue (no Redis):**
- `job` table with `SELECT ... FOR UPDATE SKIP LOCKED` claim pattern
- `LISTEN/NOTIFY` on `job_inserted` for instant wakeup; 30s poll as fallback
- States: `queued → running → done | failed | dead`
- Crash recovery: lock TTL expiry → worker reclaims on restart

**Calibration Engine (`apollo.calibration`) — named, owned, first-class:**
- Operates over sealed prediction-outcome pairs only
- Pairs joined after `OUTCOME_REVEALED`; ordering enforced in query (prediction sealed_at < outcome resolved_at)
- Output: calibration curve (reliability diagram), Brier score, ECE (Expected Calibration Error)
- Confidence intervals (Wilson score) on all per-bin rates — never over-read small-n
- Usefulness State Machine (ACTIVE/DEGRADED/DORMANT/REACTIVATED/INVERTED) driven by calibration output, transitions recorded as `LAYER_STATE_CHANGED` events in the append-only log

### LLM Architecture — Three Tiers, No Per-Token Billing

**Tier 1 — Local Ollama (unattended, GPU-bound, in-pipeline)**
- Model: pinned by digest (`OLLAMA_MODEL_DIGEST = "sha256:..."` in config), NOT by tag
- At startup: assert running digest == pinned digest; mismatch = hard fail before any job runs
- Tasks: email extraction (JSON-schema-constrained output), tasking question generation
- Serialized access: single asyncio.Lock, one inference at a time (16GB VRAM ceiling)
- Every `EXTRACTION_PRODUCED` event stamps model digest + prompt version — model identity is part of the experimental record
- Model size: ~7-14B class to fit comfortably within 16GB with embedding model resident

**Tier 2 — Commercial subscriptions, operator-mediated (the paste loop)**
- Claude Pro (via Claude Code), GPT Plus (via chatgpt.com), Google AI Pro (via gemini.google.com)
- NO per-token API billing; subscription access only
- Pattern: `export_analysis_prompt` MCP tool formats corpus slice as self-contained prompt → operator pastes into browser → `record_external_analysis` MCP tool ingests result as attributed `EXTERNAL_ANALYSIS_RECORDED` event (model, date, operator recorded)
- **Nothing on the fail-operational critical path may depend on Tier 2.** Tier 2 = enrichment and decision support, never pipeline automation.

**Tier 3 — Claude Code itself**
- Already a frontier LLM at no marginal cost, in the loop as operator
- Judgment-heavy, attended steps delegated here via MCP tools rather than scripted automation
- The MCP server is the interface; Claude Code is the intelligence driving it when present

**Boundary rule: Ollama does boring, repetitive, unattended, schema-bound work. Subscriptions + Claude Code do rare, judgment-heavy, attended work. Critical path survives on Ollama alone.**

### Compartment Enforcement — Fail-Closed

Two secrets that must never meet:
- Asset must never see target identity
- Admin must never see open-session outcomes before deliberate reveal

**Target identity compartment:**
- Real target identity (instrument, resolution criteria) encrypted at rest under a key when selected
- Dispatch path receives only opaque codename + blinded framing — does not hold the decryption key
- Plaintext unreachable from dispatch code path (capability boundary, not discipline)
- Decryption only in `reveal_outcome()` — writes `OUTCOME_REVEALED` event *before* returning plaintext

**Outcome compartment:**
- Outcomes sealed/encrypted in event log
- No MCP tool returns an open-session outcome in normal operation
- `reveal_outcome(session_id)` is the only path: checks eligibility, key operation, writes event, then returns value
- Cannot peek — can only deliberately reveal — every reveal permanently in the ledger

**Key custody (V1):** Encrypted keyfile with OS-level permissions. Appropriate for V1 threat model (self-deception and accidental leakage, not external attacker). Upgrade to platform secret manager at cloud migration.

**Why not topology:** Capability/key boundaries fail closed (no data rather than leaked data). Topology conventions fail open (one misrouted event = silent breach). For double-blind research, fail-closed is the only acceptable direction.

### Project Structure

```
apollo/
  pyproject.toml            # uv-managed, pinned deps
  alembic.ini
  docker-compose.yml        # V1: Ollama only (or native); V2: add postgres
  .env.example
  migrations/               # alembic versions — DDL is source of truth
  src/apollo/
    config.py               # pydantic-settings, env-loaded, frozen
    db/
      engine.py             # sessionmaker
      models.py             # SQLAlchemy ORM
      repo.py               # append_record(), claim_job() — DB access layer
    domain/
      compartments.py       # Compartment enum, CompartmentGuard, @requires()
      usefulness.py         # UsefulnessStateMachine (pure — no IO)
      calibration.py        # CalibrationEngine (pure functions over corpus slice)
      models.py             # Pydantic domain types: Session, Target, Extraction
    pipeline/
      extract.py            # extraction agent (LLMClient Protocol-injected)
      dispatch.py           # email dispatch
      ingest.py             # raw email → sealed corpus_record
    ollama/
      client.py             # serialized client, digest-pinned, asyncio.Lock
      schemas.py            # Pydantic output contracts per prompt
    mcp/
      server.py             # ~30 lines: register tools, run. No logic.
      tools/
        session.py
        corpus.py
        calibration.py
    services/               # ALL business logic lives here
      session_service.py
      corpus_service.py
      calibration_service.py
    worker/
      daemon.py             # LISTEN/NOTIFY loop + 30s fallback poll
      jobs.py               # dict[kind, callable] handler registry
  tests/
    unit/                   # pure domain, no IO
    integration/            # testcontainers postgres + FakeLLM
    fixtures/
      emails/               # real anonymized session email fixtures
      extractions/          # hand-labeled expected extraction outputs
    conftest.py
```

**Rule: MCP tools and worker jobs contain no business logic. They call services/. Services call db/repo.py and domain/. Transport is a shell.**

### Acceptance Criteria — Must Pass Before Pipeline Code

**AC-WSL-1:** `wsl --shutdown` then Windows restart → worker and Postgres come back, queue intact, no data corruption. Must pass repeatedly before any pipeline work starts.

**AC-OLL-1:** Digest mismatch at Ollama startup raises `ModelPinError` before any job runs.

**AC-CMP-1:** `@requires(TARGET)` called under FEEDBACK context raises `CompartmentViolation` — pure test, no DB.

**AC-CMP-2:** Integration — the `feedback` DB role executing `SELECT target_payload` gets `permission denied`.

**AC-APP-1:** `UPDATE corpus_record SET ...` raises exception under testcontainers Postgres.

**AC-APP-2:** `DELETE FROM corpus_record` likewise aborts.

**AC-EXT-1:** Given `fixtures/emails/session_001.eml`, extraction produces output matching `fixtures/extractions/session_001.json`.

**AC-EXT-2:** Malformed LLM output raises `ExtractionSchemaError`, does NOT write a record.

**AC-WRK-1:** SIGKILL during running job → on restart, job reclaimed and completed, no duplicate corpus record (assert by `raw_hash` count).

### WSL2 Reliability Prerequisites

Before any pipeline code:
- Postgres data volume on WSL2 native filesystem (NOT `/mnt/c` — fsync semantics unsafe)
- `/etc/wsl.conf` and `.wslconfig` pinned (memory, swap, page reporting) — committed to repo
- Windows Task Scheduler autostart: WSL + `docker compose up -d` + worker daemon on boot
- WAL archiving / scheduled `pg_dump` to `/mnt/c` as backup target (off-distro)
- AC-WSL-1 passes repeatedly

### Cloud Migration Path (V2)

| Concern | V1 (local) | V2 (cloud) |
|---|---|---|
| Core + MCP | Python on local box | Same code, containerized, Render / Digital Ocean |
| Scheduler tick | systemd timer | Platform cron job, same `apollo tick` entrypoint |
| Database | SQLite → Postgres migration | Managed Postgres (Render / DO) |
| Secrets/keys | Encrypted keyfile, OS perms | Platform secret manager |
| Raw blobs | Local filesystem, content-addressed | S3-compatible object store, same hash addressing |
| Ollama / GPU | RTX 5070 Ti local | Local box becomes a GPU worker — phones home to cloud DB |

**Git-as-control-plane:** Render/DO connected to GitHub repo, auto-deploy-on-push. Claude Code (operator) edits config, commits, pushes → platform redeploys. No ops console required. Deploy config (`render.yaml` / DO app spec) committed to repo and editable by LLM.

**CI/CD:**
```yaml
ci.yml:  ruff + mypy → unit tests (no IO) → integration (testcontainers + FakeLLM) → alembic migration smoke test
deploy.yml (V2, on main): build → push → deploy hook → alembic upgrade (release step, gated on CI green)
```

**Important:** Cloud migration does NOT eliminate the local box. It demotes it to a GPU worker. Ollama stays local (GPU) and pulls extraction jobs from the cloud Postgres. Fully cloud inference requires paid cloud GPU, which breaks the subscriptions-only economics.

### Explicitly Out of V1 Scope

- Message broker (Redis, Kafka, etc.) — DB-as-queue covers our cadence
- LightRAG / vector DB / graph RAG — SQL covers our queries; export-as-prompt covers analysis
- Web UI or dashboard — MCP + Claude Code is the sole interface
- Multi-asset / multi-operator support — single asset, single operator
- Automated trade execution — Apollo measures; it does not act
- Second Brain / web archiver (browserless, crawl4ai) — separate pillar, separate project phase
- n8n — replaced by Python workers
- Real-time / sub-minute latency — tick interval is the clock, measured in minutes (feature)
- HSM / sophisticated key custody — V1 threat model is self-deception, not external attacker

---

## Three Open Questions (Resolve Before Architecture Is Final)

**Q1: SQLite vs. Postgres from day one**
Winston chose SQLite for V1 simplicity. Amelia's compartment enforcement model (separate DB roles per compartment) requires Postgres features (per-role GRANTs). These are in tension.
- If compartment enforcement via DB credentials is required in V1: use Postgres from day one (single Docker container, simple setup).
- If SQLite trigger-based approach + application-layer guard is sufficient for V1: start SQLite, migrate at cloud time.
- **Decision needed from Vlad.**

**Q2: Where does Ollama live in the V1 stack**
Currently Ollama runs in a Docker container pulling GPU via `nvidia-container-toolkit` over WSL2 (`docker → WSL2 → /dev/dxg`). This is the fragile link Amelia flagged.
- Option A: Ollama in Docker (current) — GPU passthrough chain is a failure point, driver updates can silently fall back to CPU
- Option B: Ollama native on Windows host — Claude Code already talks to it there; skip the Docker/WSL2 GPU chain
- Option B is simpler and more reliable but means Ollama is not containerized alongside other services.
- **Decision needed from Vlad.**

**Q3: Hybrid cloud model — design for it in V1 or defer**
The GPU worker stays local even in V2. Designing for this from V1 (e.g., extraction worker structured to run as a remote job puller against a cloud Postgres) costs a little abstraction now but makes V2 seamless.
- Option A: V1 is purely local, no hybrid awareness — simpler now, refactor required for V2
- Option B: extraction worker built as a portable job-puller from day one (uses DATABASE_URL from config, could point anywhere) — minimal extra cost, clean V2 path
- Option B is cheap (it's just 12-factor config discipline) and worth doing.
- **Decision needed from Vlad (likely B, but confirm).**

---

## What Was Not Captured (Do Before Project-Context)

The following domain-specific rules were discovered in step 1 of `bmad-generate-project-context` and still need to be written into `_bmad-output/project-context.md`. They are fully researched; they just need to be written:

- Session data model rules (VAD/RVD/EBF, measurement timestamp, angular value)
- Compartment event flow rules (what payload is in TaskIssued, what is never included)
- Usefulness State Machine transition rules
- Calibration rules (calibration-before-trading, Brier/ECE, small-n confidence intervals)
- Domain terminology (VAD, RVD, EBF, Receptivity, Social Field, Purity Tier, Admin Awareness Tier, etc.)
- Environmental correlates join rules (asset-reported time, not email receipt time)
- Admin State Snapshot protocol (mandatory prefix to every interaction)
- Deliberate outcome revelation interface rules
- Closure ceremony rules (weekly batched, Saturday morning, 5-15 session ceiling)
- TRNG indeterminacy principle
- Archival-grade corpus requirements (open formats, self-describing, schema-versioned)

All of this comes from the brainstorming corpus and architecture research already read. It does not need to be re-read.

---

## Source Documents (Already Read — Do Not Re-Read Unless Needed)

- `_bmad-output/brainstorming/brainstorming-session-2026-05-29-1841.md` — 124 ideas, Usefulness Framework decisions, HIRA register
- `_bmad-output/planning-artifacts/research/technical-apollo-system-architecture-research-2026-05-31.md` — full service catalogue, phase map, constraint inventory
- `_bmad-output/planning-artifacts/briefs/brief-Apollo-2026-05-31/brief.md` — product brief
- `_bmad-output/planning-artifacts/briefs/brief-Apollo-2026-05-31/addendum.md` — prior art, ARV notes, statistical open questions
- Memory files: `project_apollo_overview.md`, `project_apollo.md` (in `/home/vlad/.claude/projects/-mnt-c-Apollo/memory/`)

---

## Suggested Next Session Start

1. Present this handoff to Vlad and resolve the three open questions (Q1, Q2, Q3)
2. Once resolved, write the clean-sheet architecture to a formal architecture document (or directly into `project-context.md`)
3. Return to `bmad-generate-project-context` step 2 and complete the project-context.md based on the new architecture
4. Consider committing: the brainstorming session, briefs, research doc, and this handoff are all new artifacts worth a commit
