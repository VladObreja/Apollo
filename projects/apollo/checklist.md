# Apollo Checklist

## Phase I Alpha checklist

### A. Workspace and control layer
- [x] Make repo root `C:\Apollo` the active OpenClaw workspace root
- [x] Expose the full repo to the running OpenClaw session
- [x] Preserve the existing running stack as the basis
- [x] Create canonical Apollo control docs under `projects/apollo/`
- [x] Define the Phase I Alpha knowledge contract in `projects/apollo/contract.md`
- [x] Back up core project/runtime files before editing them (`legacy/Backups/`)
- [ ] Add repo root as a safe Git directory inside the container if git operations are needed

### B. Repo hygiene
- [x] Archive the clearly legacy nested workspace content from `Intel/workspace/` into `legacy/`
- [x] Preserve active OpenClaw runtime/config state under `Intel/`
- [x] Move compose-managed secrets out of `docker-compose.yaml` and into `.env`
- [ ] Confirm any remaining legacy leftovers are either archived or intentionally retained
- [ ] Document any directories that must never be ingested

### C. Corpus validation
- [x] Confirm `Vault/raw/` exists and contains meaningful source material
- [x] Confirm `Vault/Clean/` contains project-level clean corpus assets
- [ ] Inspect `Vault/Clean/ingest/ingest_manifest.json`
- [ ] Inspect `Vault/Clean/projects/classification_refined.json`
- [ ] Decide which subset of `Vault/Clean/` is the first retrieval surface
- [ ] Exclude secrets or irrelevant runtime debris from retrieval

### D. Retrieval validation
- [ ] Confirm how LightRAG is currently reading `Vault/Clean`
- [ ] Define the exact indexing / refresh path for the clean corpus
- [ ] Verify project-scoped retrieval assumptions for Apollo vs Aurelius
- [ ] Test the first grounded Apollo query loop

### F. Runtime hardening
- [x] Add restart policies and graceful stop settings to core services in `docker-compose.yaml`
- [x] Add core service healthchecks to `docker-compose.yaml`
- [x] Rewrite `apollo_up.bat` and `apollo_down.bat` around readiness / health checks
- [ ] Validate the hardened compose file against the live Docker runtime
- [ ] Validate the rewritten batch scripts against the live Docker runtime
- [ ] Plan an explicit `n8n` backend migration if Postgres should become authoritative later

### E. Validation pack
- [ ] Create canonical test questions
- [ ] Associate each question with expected evidence sources
- [ ] Record baseline answers for regression testing

## Current top-priority next steps
1. inspect the clean corpus manifests and classification files
2. verify LightRAG input and indexing behavior
3. prove the first source-grounded query loop

## Completion condition for Phase I Alpha
Apollo can answer core questions about Apollo and Aurelius from the curated corpus through the running stack, with clear grounding and recoverable project state.