# Project Hermes Control Folder

This folder is the canonical project cockpit for Hermes.

It exists for two reasons:
1. to keep the Hermes subproject consistent across development sessions
2. to allow Hermes to be recovered or handed off cleanly to another OpenClaw session or another agent after interruption, crash, or reset

## Authority model
- Human-readable Markdown files in this folder are the primary project record
- `status.json` is the machine-readable mirror for automation and future tooling
- Supporting corpora, databases, and later operational datasets remain supporting layers, not the primary control surface

## Current status snapshot
- Project phase: **Phase 0 Foundation**
- Primary objective: stand up a minimal Hermes backbone for blind tasking, session intake, feedback release, and structured analysis
- Architecture stance: **small chunks first, no ambitious-but-rubbish sprawl**
- Development stance: **research backbone first, market automation later**

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
- `contract.md`: first operating contract for Phase 0 Foundation, covering authority hierarchy, MVP workflows, data rules, and anti-drift constraints
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
- Canonical Hermes control docs: `projects/hermes/`
- Apollo control docs: `projects/apollo/`
- Supporting clean corpus: `Vault/Clean/`
- Raw corpus: `Vault/raw/`
- Runtime/state: `Intel/`

## Current operating rule
For now Hermes should be:
- one admin-facing control surface
- one blind tasking workflow
- one structured session intake path
- one controlled feedback-release path
- one database-backed analysis layer

No live trading, no autonomous capital deployment, and no agent theater before the research loop works.

## Recovery note
If the current LLM session is lost, a replacement agent should start from this folder and treat it as the live Hermes record, then inspect the relevant Apollo control docs and current runtime state.
