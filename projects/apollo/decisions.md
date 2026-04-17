# Apollo Decisions

## Confirmed decisions

### Architecture and operating model
- Apollo will be designed as **one governing assistant, not one giant monolith**
- Apollo is a **local-first governing knowledge-and-operations system**
- Apollo must keep **knowledge**, **interpretation**, and **action** conceptually separate
- Apollo should evolve from a tool stack into a coherent system through explicit responsibility boundaries

### Development strategy
- For now, avoid heavy orchestration and build a **thin usable backbone first**
- Use the existing running stack as the basis rather than restarting architecture selection from scratch
- Follow an **OTS-first** bias: adopt, wrap, or lightly extend before building custom
- Use agentic development only later and only for clearly bounded tasks

### Current Phase I stance
- Phase I Alpha is about ingestion, normalization, retrieval, and grounded querying
- Phase I Alpha is **not** about councils, autonomous agents, regimen automation, RV workflows, or media generation
- The first real proof should be: Apollo can answer grounded questions about the existing Apollo and Aurelius planning corpus
- The Phase I Alpha knowledge contract is now defined in `projects/apollo/contract.md` and should govern authority hierarchy, initial retrieval surface, canonical question coverage, and anti-drift behavior

### Project control and continuity
- `projects/apollo/` is the canonical control folder for purpose, status, decisions, deliverables, roadmap, and handoff
- Markdown files are the primary source of truth
- `status.json` is the structured machine-readable mirror
- A database may be added later as a derived layer, not the primary project record

### Corpus and knowledge handling
- Use `Vault/Clean/` as the clean corpus layer for downstream retrieval and ingestion work
- Do not ingest the raw corpus blindly when cleaned/projected material exists
- Preserve project boundaries explicitly: Apollo, Aurelius, Shared, Other
- Treat Gemini export material as a source to be sliced and summarized, not ingested raw without cleanup
- Keep project-level docs such as `master_context.md`, `decisions.md`, `tasks.md`, and `deliverables.md` because they improve retrieval quality

### Workspace / repo hygiene
- The repo root `C:\Apollo` is now the active OpenClaw workspace root
- The legacy nested workspace under `Intel/workspace/` should be archived rather than deleted
- Runtime/config/state under `Intel/` should be handled conservatively to avoid breaking the live system
- Before modifying core runtime/project files such as `docker-compose.yaml`, `apollo_up.bat`, `apollo_down.bat`, and `.env`, create a dated/versioned backup under `legacy/Backups/`

### Runtime hardening stance
- Remote access is required, so current port exposure remains intentionally unchanged in this hardening pass
- `docker-compose.yaml` should be hardened with restart policies, graceful stop periods, and healthchecks across core services
- Compose-managed secrets should live in `.env`, not inline in `docker-compose.yaml`
- `n8n` should remain on its current SQLite-backed runtime for now, rather than being silently migrated to Postgres during a hardening pass
- `apollo_up.bat` and `apollo_down.bat` should act as readiness-aware lifecycle scripts, not blind wrappers around fixed sleeps or optimistic shutdown messaging

## Working assumptions
- The current Docker compose stack is the active target architecture
- The cleaned corpus under `Vault/Clean/` is useful and worth keeping
- The first valuable Apollo seed corpus is mostly text-first and planning-first, not full universal ingestion
- Canonical project control docs should live outside `Vault/Clean/` so control and corpus remain distinct

## Open decisions
- Exactly how LightRAG should index the clean corpus in its current container configuration
- Whether large timeline-style docs should remain retrieval-primary or be supplemented by smaller thematic notes
- Whether to create a dedicated script layer for corpus registration/normalization immediately or only after validating the existing clean corpus
- When to begin formalizing Aurelius as the first operational module on top of Apollo
- When to introduce structured task/state syncing into n8n/Postgres

## Decision rule going forward
When new work is proposed, evaluate it in this order:
1. does it serve the Phase I Alpha proof?
2. is there already an off-the-shelf answer?
3. does it preserve project clarity and provenance?
4. does it reduce complexity or add it?