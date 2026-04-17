# MEMORY.md

## Current long-term context
- The user is developing **Project Apollo** with me inside OpenClaw.
- Apollo is the main active project. Aurelius is the first serious module/program intended to live on top of Apollo's shared infrastructure.
- The user wants a system that feels like **one governing assistant, not one monolith**.

## Apollo, core framing
- Apollo is a **local-first governing knowledge-and-operations system**.
- Its purpose is to acquire knowledge, organize meaning, and support action.
- Preferred design stance: local-first, OTS-first where possible, clear responsibility boundaries, provenance preserved, backbone before theatrics.
- Knowledge, interpretation, and action should stay conceptually distinct.

## Apollo, current phase
- Apollo is in **Phase I Alpha**.
- Current objective: prove a thin but real backbone that can answer grounded questions about the Apollo and Aurelius planning corpus.
- Current scope is ingestion, normalization, retrieval, and source-grounded querying.
- Heavy orchestration, agent councils, regimen automation, RV workflows, and media-generation workflows are explicitly deferred until the backbone works.

## Canonical project continuity
- `projects/apollo/` is the canonical control surface for Apollo.
- `Vault/Clean/` is the curated corpus / evidence layer.
- `Vault/raw/` is the raw archive layer.
- Apollo continuity should not rely on chat history alone. The project control files must stay current.

## Apollo, recovered project progress
- The running stack already includes OpenClaw, Ollama, Open WebUI, LightRAG, Docling, Browserless, Crawl4AI, and n8n + Postgres.
- The repo root is the active OpenClaw workspace root.
- The old nested workspace under `Intel/workspace/` was archived under `legacy/Intel/workspace/`, while active runtime/config under `Intel/` was preserved.
- The raw corpus was inventoried and deduped into reports under `Vault/Clean/reports/`.
- Project buckets and project docs were created under `Vault/Clean/projects/`, including Apollo and Aurelius timelines plus scaffold docs.
- A lost standby-interrupted chat thread was recovered from saved session transcripts and written to `legacy/Recovered-Sessions/2026-04-17-lost-session-recovery.md`.
- The immediate next technical work is still to verify the clean retrieval surface and LightRAG indexing/query behavior.

## Working preferences and constraints
- Prefer staged, practical progress over architecture sprawl.
- Reuse existing stack and cleaned corpus before building more automation.
- Do not ingest secrets or irrelevant runtime debris casually.
- Preserve explicit project boundaries: Apollo, Aurelius, Shared, Other.
- Before modifying core project/runtime files such as `docker-compose.yaml`, `apollo_up.bat`, `apollo_down.bat`, `.env`, and similar core files, create a dated/versioned backup in `legacy/Backups/`.

## Memory durability rule
- `MEMORY.md` matters and should not silently disappear.
- If `MEMORY.md` is ever missing in a main session, restore it from `memory/backups/MEMORY.latest.md` if available, otherwise reconstruct it from recent daily notes and canonical project files, then tell the user.
- After meaningful edits to `MEMORY.md`, keep a mirrored backup in `memory/backups/`.
