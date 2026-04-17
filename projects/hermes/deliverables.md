# Hermes Deliverables

## Deliverable model
This file tracks what Hermes is expected to produce in Phase 0 Foundation.

The immediate priority is not a polished product.
It is a working research backbone that can run real Hermes operations with disciplined storage, blinding separation, and recoverable continuity.

## Current implementation stance
For the current build cycle, Hermes is taking a **database-first backbone** approach so the project can become operational quickly.

The initial technical focus is:
- a dedicated Hermes PostgreSQL service
- a minimal Phase 0 schema
- clean separation between hidden target truth and operational task release
- structured session capture for later analysis

This should be treated as the first practical implementation path, not the final form of Hermes forever.

## Phase 0 Foundation deliverables

### 1. Dedicated Hermes database service
**Target:** Hermes has its own PostgreSQL 16 service, isolated from the main Apollo automation state.

**Current state:** planned

**Done when:**
- a dedicated `hermes_db` service exists in `docker-compose.yaml`
- the service uses its own credentials and database name
- the data persists in a dedicated Hermes data path
- the service has a healthcheck
- Hermes research data is not mixed into unrelated Apollo operational tables

**Why it matters:**
Hermes needs clean research isolation, structured persistence, and room for later analytical growth.

### 2. Phase 0 schema baseline
**Target:** Hermes has a minimum viable database schema for targets, tasks, and sessions.

**Current state:** planned

**Done when:**
- the schema includes a `targets` table
- the schema includes a `tasks` table
- the schema includes a `sessions` table
- UUID-based primary keys are in place
- timestamps are recorded consistently
- the schema supports structured JSON payloads where needed

**Why it matters:**
Hermes cannot be a disciplined research system if its operational records remain vague, ad hoc, or trapped in chat history.

### 3. Hidden target vs released task separation
**Target:** Hermes preserves the difference between canonical target truth and viewer-facing operational tasking.

**Current state:** planned

**Done when:**
- hidden target data lives in `targets`
- released operational task records live in `tasks`
- a task points to a target without exposing hidden target details by default
- the structure supports blind, double-blind, or partially front-loaded protocols
- future viewer-facing interfaces can be built so they query task-safe data only

**Why it matters:**
Protocol discipline depends on not leaking hidden target truth into the operational viewing flow.

### 4. Structured session capture
**Target:** Hermes stores session results in a form that supports both immediate operations and later analysis.

**Current state:** planned

**Done when:**
- each session record points to a specific `task_id`
- each session record points to a specific `viewer_id`
- the primary 0-100 radiesthesia-style measurement is supported
- auxiliary traditional or messy protocol parameters can be stored without schema collapse
- subjective notes can be preserved
- confidence can be recorded
- timing is captured consistently

**Why it matters:**
Hermes needs to support real-world operational messiness without giving up structured analysis.

### 5. Environmental context capture
**Target:** Hermes can store optional environmental/physical context alongside sessions.

**Current state:** planned

**Done when:**
- local sidereal time can be recorded
- solar-weather-related context can be recorded
- moon phase can be recorded
- these values can remain optional where appropriate
- later analysis can compare environmental variables against outcomes

**Why it matters:**
If Hermes is going to test environmental correlations seriously, those factors need to be captured from the start.

### 6. Viewer registry support
**Target:** Hermes can support identifiable human operators as durable research participants.

**Current state:** partially specified, not yet implemented

**Done when:**
- a viewer registry exists
- viewers have stable identifiers
- viewer records can support later background/training metadata
- sessions can be reliably attributed to a specific viewer

**Why it matters:**
Hermes cannot analyze consistency, drift, or operator-specific patterns without stable viewer identity.

### 7. First research-ready operating backbone
**Target:** Hermes can support one real research loop using the database backbone.

**Current state:** planned

**Done when:**
- an administrator can create or register a target
- an administrator can create a task linked to that target
- a viewer can be associated with a session
- a session can be stored against the task cleanly
- feedback can later be derived from the target/task relationship
- the stored records remain usable for later review and analysis

**Why it matters:**
The point of the schema is not decorative neatness. It is to make Hermes runnable.

## Phase 0 schema notes
The current implementation direction assumes:
- `targets.payload_data` can hold the canonical target payload in JSON form
- `tasks.coordinate` provides the operational reference used for viewer tasking
- `sessions.primary_measurement` captures the main 0-100 value
- `sessions.auxiliary_parameters` captures additional protocol-specific values without overconstraining Phase 0

This is intentionally permissive enough to support real work while still preserving structure.

## Future-expansion deliverables, not Phase 0 blockers
These are important, but they are not required to declare the first backbone operational.

### Later, but not required now
- pgvector or other semantic-analysis extensions
- richer scoring and outcome tables
- automated environmental enrichment
- market-data ingestion
- automated feedback release based on market timestamps
- paper-trading evaluation workflows
- real-money execution controls

## Acceptance standard
Hermes is advancing correctly when the deliverables:
- make the project runnable sooner, not later
- preserve blindness and data integrity
- isolate Hermes research state cleanly
- keep raw or canonical truth separate from released operational tasking
- produce records that survive crashes, resets, and session loss

## Immediate recommendation
The next implementation move after this file is:
1. add the dedicated `hermes_db` service definition
2. define the exact Phase 0 SQL initialization script
3. add the missing viewer registry table so `viewer_id` is a real foreign-key path rather than a loose placeholder
4. run the first database-backed Hermes task/session test loop
