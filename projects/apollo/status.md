# Apollo Status

## Current state
- Date: 2026-04-17
- Overall status: **in progress**
- Active phase: **Phase I Alpha**
- Focus: establishing the minimum viable Apollo backbone using the stack that is already running, with the Phase I Alpha knowledge contract now defined

## What is already true
### Runtime / platform
- The Docker stack is live and already includes the main Apollo building blocks:
  - OpenClaw
  - Ollama
  - Open WebUI
  - LightRAG
  - Docling
  - Browserless
  - Crawl4AI
  - n8n + Postgres
- The repo root `C:\Apollo` is now mounted as the OpenClaw workspace root
- The conversation is happening against the live running stack
- A first hardening pass has now been applied to `docker-compose.yaml` and `.env`:
  - restart policies added across services
  - graceful stop timings added
  - healthchecks added for core services
  - compose-managed secrets moved into `.env`
  - remote-exposed ports intentionally left unchanged
  - `n8n` was **not** switched to Postgres in this pass, to avoid an implicit state migration away from the existing SQLite-backed runtime
- `apollo_up.bat` and `apollo_down.bat` have now been rewritten around Docker availability checks, compose detection, health-based waits, ordered shutdown, and stop verification instead of fixed sleeps and optimistic status messages

### Repository / workspace
- The full repo is now visible inside OpenClaw
- The old nested workspace under `Intel/workspace/` has been substantially sanitized and archived to `legacy/Intel/workspace/`
- Current runtime/config data under `Intel/` was intentionally left active

### Corpus / knowledge assets
- `Vault/raw/` contains a meaningful seed corpus, including Apollo and Aurelius material
- `Vault/Clean/` already contains valuable preprocessed assets:
  - project classification
  - duplicate reports
  - conversation slices
  - project-level distilled docs
  - ingest manifests / ingest directories
- This means Apollo is not starting from zero and should reuse this work

## What has been decided in the current planning cycle
- Use the existing `docker-compose.yaml` as the basis rather than replacing the stack
- Keep advanced orchestration deferred for now
- Build a thin usable backbone first
- Use `projects/apollo/` as the canonical project control location
- Treat `Vault/Clean/` as a supporting knowledge corpus rather than the sole project control surface
- Use `projects/apollo/contract.md` as the Phase I Alpha knowledge contract for authority hierarchy, retrieval surface, canonical questions, and anti-drift rules

## Current objective
Prove the first live Apollo loop:
1. use the existing clean Apollo/Aurelius corpus
2. ensure it is retrieval-ready
3. establish source-grounded querying through the running system
4. validate that the resulting answers satisfy the knowledge contract in `projects/apollo/contract.md`

## Immediate next actions
1. validate the hardened compose file and rewritten batch scripts against the live Docker runtime
2. inspect and validate `Vault/Clean` as the initial retrieval corpus
3. verify what LightRAG is actually reading from `Vault/Clean`
4. define and/or verify the indexing path for the clean corpus
5. prove the admin query loop with canonical Apollo questions
6. keep secrets and irrelevant runtime debris out of the retrieval surface

## Known issues / open operational concerns
- Git inside the container currently reports a safe-directory ownership issue
- Path naming conventions should be kept consistent (`Vault/...` rather than mixed variants in project docs/scripts)
- Sensitive files inside the repo tree must never be ingested casually
- The root workspace identity/memory files are still somewhat fresh and minimal after migration
- The hardened compose file still needs validation against the real Docker runtime, because Docker CLI access is not available from the current session
- `n8n_db` exists and is restart-safe, but `n8n` is intentionally still left on the existing SQLite-backed runtime until a deliberate migration is planned

## Current recommendation
Do not expand scope yet.
Use the existing cleaned corpus and the existing running stack to prove the first real Apollo capability before adding more automation.