# Apollo Sources

## Purpose
This file records where the canonical Apollo control docs were derived from, so future sessions can trace the origin of the current project record.

## Primary source groups

### 1. Current planning conversation
The current OpenClaw session established:
- the formal tasking map
- the capability matrix
- the phased roadmap
- the Phase I Alpha implementation blueprint
- the decision to keep the stack thin for now
- the decision to create `projects/apollo/` as the canonical control folder

### 2. Existing distilled Apollo docs
Source path:
- `Vault/Clean/projects/apollo/`

Files consulted:
- `master_context.md`
- `timeline.md`
- `decisions.md`
- `tasks.md`
- `deliverables.md`

### 3. Existing clean corpus support material
Relevant supporting paths:
- `Vault/Clean/conversation_slices/`
- `Vault/Clean/ingest/`
- `Vault/Clean/reports/`
- `Vault/Clean/projects/`

### 4. Existing raw corpus
Source path:
- `Vault/raw/`

This contains Apollo and Aurelius source material and remains the deeper evidence/archive layer.

### 5. Existing repo/runtime structure
Observed paths:
- `docker-compose.yaml`
- `Intel/`
- `Vault/`
- `data/`
- `legacy/`

## Source usage rule
When updating Apollo control docs:
- prefer canonical control docs first
- then supporting clean corpus docs
- then raw source material when a deeper check is needed

## Important distinction
- `projects/apollo/` = canonical control and continuity layer
- `Vault/Clean/` = curated knowledge/corpus layer
- `Vault/raw/` = raw evidence/archive layer