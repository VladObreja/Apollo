# Apollo Deliverables

## Deliverable model
This file tracks what Apollo is expected to produce, first in Phase I Alpha and later in broader phases.

## Phase I Alpha deliverables

### 1. Core runtime baseline
**Target:** OpenClaw, Ollama, Open WebUI, and LightRAG are all functioning as the living Apollo backbone.

**Current state:** largely present

**Done when:**
- operator can use the admin interface
- local model responds
- retrieval service is reachable
- the stack is stable enough for corpus testing

### 2. Canonical project control folder
**Target:** `projects/apollo/` contains the durable project record.

**Current state:** created in this session

**Done when:**
- purpose, status, decisions, deliverables, checklist, roadmap, architecture, and handoff are documented
- another session can recover the project from these docs alone

### 3. Clean seed corpus for Apollo
**Target:** Apollo and Aurelius planning materials exist in a controlled, retrieval-friendly form.

**Current state:** substantially present under `Vault/Clean/`

**Done when:**
- the clean corpus is validated as the initial retrieval surface
- sensitive or irrelevant material is excluded from the retrieval path

### 4. Retrieval-ready indexing path
**Target:** the chosen clean corpus can be indexed and queried through LightRAG.

**Current state:** not yet verified end-to-end

**Done when:**
- the LightRAG input path is confirmed
- indexing or refresh procedure is defined
- Apollo and Aurelius queries can be scoped and tested

### 5. First grounded query loop
**Target:** Apollo answers core project questions with source awareness.

**Current state:** planned, not yet proven

**Done when:**
- Apollo can answer questions like:
  - What is Apollo supposed to do?
  - What is the Phase I focus?
  - How does Aurelius relate to Apollo?
- answers are grounded in the clean corpus and project control docs

### 6. Validation pack
**Target:** a small reusable test set exists to verify Apollo remains useful and grounded.

**Current state:** not yet created

**Done when:**
- canonical project questions are written down
- expected evidence sources are known
- the results can be checked after changes

## Later-phase deliverables
### Phase II
- claim/entity/relationship-aware analysis
- contradiction and timeline workflows
- better retrieval packaging and uncertainty reporting

### Phase III
- Aurelius operational module baseline
- regimen objects, schedules, reminders, outcome logging

### Phase IV
- RV workflows
- subliminal/pathworking generation workflows
- reusable module contract

### Phase V
- mature orchestration layer
- specialist subagents where genuinely useful
- better auditability and observability

## Acceptance standard
Apollo is advancing correctly when the deliverables reduce ambiguity, improve continuity, and make the system more recoverable by humans and agents alike.