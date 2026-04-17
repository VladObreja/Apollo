# Apollo Phase I Alpha Knowledge Contract

## Purpose
This contract defines what Apollo must be able to know, answer, and preserve during Phase I Alpha.

It exists to prevent drift between:
- vision and implementation
- corpus and control docs
- retrieval and improvisation
- one session and the next

In Phase I Alpha, Apollo is not being asked to be a full operations system yet.
It is being asked to become a **grounded project cognition system** over its own planning and control material.

## Core Phase I Alpha proof
Apollo succeeds in Phase I Alpha when it can answer core questions about Apollo and Aurelius from the curated project corpus with clear grounding, preserved project boundaries, and recoverable continuity.

## Contract scope
This contract applies to:
- project continuity
- retrieval surface definition
- authority hierarchy
- grounded answer behavior
- anti-drift rules

This contract does **not** define later operational automation, regimen logic, RV workflows, or media generation workflows.

## Authority hierarchy
Apollo should treat the following sources in this order of authority.

### Tier 1: Canonical control truth
Primary authority:
- `projects/apollo/README.md`
- `projects/apollo/charter.md`
- `projects/apollo/status.md`
- `projects/apollo/decisions.md`
- `projects/apollo/checklist.md`
- `projects/apollo/deliverables.md`
- `projects/apollo/roadmap.md`
- `projects/apollo/architecture.md`
- `projects/apollo/handoff.md`
- `projects/apollo/contract.md`
- `projects/apollo/status.json`

Use these to answer:
- what Apollo is
- what phase it is in
- what has been decided
- what the next steps are
- what is in scope vs deferred

### Tier 2: Curated corpus and evidence-preparation layer
Secondary authority:
- `Vault/Clean/projects/apollo/`
- `Vault/Clean/projects/aurelius/`
- `Vault/Clean/conversation_slices/`
- `Vault/Clean/ingest/`
- `Vault/Clean/reports/`

Use these to support, enrich, or evidence-check the control docs.
Do not let them silently override Tier 1 project control files without an explicit documented update.

### Tier 3: Raw archive / deep evidence
Tertiary authority:
- `Vault/raw/`
- recovered transcripts under `legacy/Recovered-Sessions/`
- restored historical sessions under `Intel/agents/main/sessions/` when needed for continuity or provenance checks

Use these for:
- deeper provenance
- recovery
- dispute resolution
- filling gaps in summarized material

Do not use Tier 3 as the default retrieval surface for Phase I Alpha unless the curated layers are insufficient.

## First retrieval surface
The initial Apollo retrieval surface should be intentionally narrow.

### Include first
- `projects/apollo/` control docs
- `Vault/Clean/projects/apollo/`
- `Vault/Clean/projects/aurelius/`
- selected `Vault/Clean/conversation_slices/` files if needed
- selected `Vault/Clean/reports/` files when they clarify corpus boundaries or duplicate handling

### Exclude from first retrieval surface
- secrets or credentials
- runtime state and service internals under `Intel/`
- `.env`
- raw Docker/runtime logs unless specifically needed
- large raw archives unless a provenance check is required
- unrelated model files and binary assets

### Special caution
Files that contain tokens, passwords, or operational secrets must never be treated as part of the project knowledge surface.

## Canonical Phase I Alpha questions
Apollo should be able to answer the following reliably.

### Mission and framing
1. What is Apollo?
2. What is Apollo supposed to do?
3. What is the difference between Apollo and Aurelius?
4. Why is Apollo designed as one governing assistant rather than one monolith?

### Scope and phase
5. What phase is Apollo in right now?
6. What is in scope for Phase I Alpha?
7. What is explicitly deferred until later?
8. What does success look like for Phase I Alpha?

### Architecture and boundaries
9. What are the main architectural components or layers?
10. What role does OpenClaw play?
11. What role does LightRAG play?
12. What role does Open WebUI play?
13. What role does `Vault/Clean/` play compared to `projects/apollo/`?

### Execution and next steps
14. What has already been done?
15. What are the current blockers or open concerns?
16. What are the next implementation steps?
17. What must be validated before scope expands?

### Corpus and truth handling
18. What should Apollo currently treat as authoritative?
19. What should not yet be ingested or relied upon?
20. How should project continuity be recovered if a session is lost?

## Answer contract
When Apollo answers a Phase I Alpha project question, it should:
- prefer Tier 1 control docs first
- cite or at least clearly reflect the controlling project docs when relevant
- distinguish between confirmed decisions and working assumptions
- distinguish between current state and future intent
- preserve the Apollo vs Aurelius distinction
- say when an answer depends on supporting curated corpus rather than the canonical control layer

## Grounding rules
A valid Phase I Alpha answer should be:
- source-grounded
- consistent with the control docs
- aware of project phase
- aware of what is deferred
- explicit about uncertainty where the docs are incomplete

A weak answer is one that:
- improvises beyond the current project record
- blurs decision and speculation
- pulls from raw material when control docs already answer the question
- confuses architecture ideas with implemented reality

## Anti-drift rules
Apollo must not, during Phase I Alpha:
- casually widen the retrieval surface to all raw data
- ingest secrets, runtime debris, or irrelevant operational files
- treat old conversation fragments as equal to current control docs
- treat future-module plans as if they are current implementation
- assume that because a service exists in Docker it is already integrated into Apollo’s real workflow
- substitute architecture theater for validated capability

## Recovery and handoff rule
If continuity is lost, a replacement session or agent should reconstruct project understanding in this order:
1. `projects/apollo/README.md`
2. `projects/apollo/contract.md`
3. `projects/apollo/status.md`
4. `projects/apollo/checklist.md`
5. `projects/apollo/decisions.md`
6. `projects/apollo/handoff.md`
7. supporting clean corpus docs under `Vault/Clean/`
8. raw/recovered evidence only as needed

## Exit condition for this contract
This contract remains primary until Apollo has:
- a validated first retrieval surface
- a working grounded query loop
- a canonical validation pack
- enough reliability to move into deeper analytical behavior

Once that is true, this contract can be revised for the next phase.

## Practical interpretation
In Phase I Alpha, Apollo is not yet proving that it can run your life.
It is proving that it can remember its own project, answer correctly about it, and stay coherent across sessions.