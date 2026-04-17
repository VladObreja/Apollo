# Apollo Handoff Notes

## Purpose of this file
This file is for session recovery and handoff to another OpenClaw session or another agent.

## If you are a new session or new agent
Start here:
1. read `projects/apollo/README.md`
2. read `charter.md`
3. read `status.md`
4. read `checklist.md`
5. read `decisions.md`
6. inspect `Vault/Clean/projects/apollo/` and `Vault/Clean/projects/aurelius/`
7. inspect `Vault/Clean/ingest/` and `Vault/Clean/reports/`
8. confirm the running stack still includes OpenClaw, Ollama, Open WebUI, and LightRAG

## Current project situation
Apollo is in a planning-to-technical-transition stage.
The stack is already running.
The repo root is now the workspace root.
The project already has a useful clean corpus under `Vault/Clean/`.
The immediate aim is not advanced orchestration but proving a grounded retrieval/query loop for Apollo and Aurelius planning material.

## High-value facts
- The user wants one governing assistant, not one monolith
- The system should be local-first and modular
- `Vault/Clean/` contains prior ingestion/digestion work and should be reused
- `projects/apollo/` is now the canonical project control surface
- Legacy nested workspace clutter from `Intel/workspace/` has been archived under `legacy/`

## Next best actions
- inspect the clean corpus manifests and classification files
- verify LightRAG input/index behavior against the clean corpus
- define or verify the first retrieval surface
- prove the first grounded query loop

## Warning notes
- Do not casually ingest secrets or irrelevant runtime files
- Do not reintroduce heavy orchestration before the thin backbone works
- Keep Apollo control docs and corpus docs conceptually separate

## Handoff standard
Any major new decision or milestone should update at least:
- `status.md`
- `decisions.md`
- `checklist.md`
- `status.json`

If a larger shift occurs, also update:
- `charter.md`
- `roadmap.md`
- `deliverables.md`