# Project Apollo Control Folder

This folder is the canonical project cockpit for Apollo.

It exists for two reasons:
1. to keep the project consistent across development sessions
2. to allow Apollo to be recovered or handed off cleanly to another OpenClaw session or another agent

## Authority model
- Human-readable Markdown files in this folder are the primary project record
- `status.json` is the machine-readable mirror for automation and future tooling
- `Vault/Clean/` remains a supporting corpus and evidence layer, not the primary control surface

## Current status snapshot
- Project phase: **Phase I Alpha**
- Primary objective: stand up a usable local-first Apollo backbone that can answer grounded questions about the Apollo and Aurelius planning corpus
- Architecture stance: **one governing assistant, not one monolith**
- Development stance: **thin backbone first, defer heavy orchestration**

## Read this first in a new session
1. `README.md`
2. `charter.md`
3. `contract.md`
4. `status.md`
5. `checklist.md`
6. `decisions.md`
7. `roadmap.md`
8. `architecture.md`
9. `handoff.md`
10. `sources.md`
11. `status.json`

## Key project files
- `charter.md`: mission, scope, principles
- `contract.md`: Phase I Alpha authority hierarchy, retrieval surface, canonical questions, and anti-drift rules
- `status.md`: current state and next actions
- `decisions.md`: confirmed and open decisions
- `deliverables.md`: expected outputs and acceptance criteria
- `checklist.md`: concrete implementation checklist
- `roadmap.md`: phased build sequence
- `architecture.md`: text-form component diagram and system boundaries
- `handoff.md`: session recovery / agent handoff notes
- `sources.md`: where this project record was derived from
- `status.json`: structured project state

## Important paths
- Repo root: `C:\Apollo` / `/home/node/.openclaw/workspace`
- Canonical project control docs: `projects/apollo/`
- Supporting clean corpus: `Vault/Clean/`
- Raw corpus: `Vault/raw/`
- Retrieval DB area: `Vault/Database/`
- Runtime/state: `Intel/`
- Archived legacy nested workspace: `legacy/Intel/workspace/`

## Current operating rule
For now Apollo should be:
- one admin interface
- one ingestion path
- one storage layout
- one retrieval layer
- one query loop

No elaborate councils or agent hierarchies until the backbone is proven.

## Recovery note
If the current LLM session is lost, a replacement agent should start from this folder and treat it as the live project record, then inspect the `Vault/Clean/` corpus and current stack state.