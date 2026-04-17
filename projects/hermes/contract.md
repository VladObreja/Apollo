# Hermes Phase 0 Foundation Contract

## Purpose
This contract defines what Hermes must be able to do, preserve, and avoid during its first phase.

It exists to prevent drift between:
- the idea of Hermes and the first useful implementation
- research support and premature market automation
- human workflow discipline and improvised process
- one session and the next

In Phase 0, Hermes is not being asked to prove every claim about psi functioning.
It is being asked to become a disciplined operational backbone for tasking, capture, feedback, storage, and analysis.

## Core Phase 0 proof
Hermes succeeds in Phase 0 when it can support a full end-to-end controlled session loop for at least one administrator and one viewer with recoverable continuity.

That loop is:
1. define a target or task
2. assign or release tasking in a controlled way
3. collect a remote session submission
4. store the session and related metadata in structured form
5. release feedback at the intended stage
6. preserve the resulting record for later review and analysis

## Contract scope
This contract applies to:
- project continuity
- role definition
- core workflows
- authority hierarchy
- first data model rules
- remote access assumptions
- anti-drift constraints

This contract does **not** define later live trading automation, broker integration, real-money execution, or broad speculative theory frameworks.

## Operating actors
Hermes should currently assume the following actors.

### 1. Project administrator
The administrator:
- defines protocol scope
- creates and approves tasks
- controls viewer access and role assignment
- controls feedback release timing
- reviews outputs and analysis
- decides whether and when to expand scope

### 2. Psionic asset / viewer
The viewer:
- receives tasking through the approved interface
- submits session material
- may later receive feedback
- does not control the target database, scoring rules, or protocol changes

### 3. Hermes system
The Hermes system:
- stores structured task and session records
- enforces workflow stages where possible
- preserves timestamps and metadata
- supports analysis and review
- does not independently escalate to consequential real-world action

## Authority hierarchy
Hermes should treat the following sources in this order of authority.

### Tier 1: Canonical control truth
Primary authority:
- `projects/hermes/README.md`
- `projects/hermes/charter.md`
- `projects/hermes/contract.md`
- `projects/hermes/status.md`
- `projects/hermes/decisions.md`
- `projects/hermes/checklist.md`
- `projects/hermes/handoff.md`
- `projects/hermes/status.json`

Use these to answer:
- what Hermes is
- what phase it is in
- what workflows exist
- what is allowed now
- what is deferred

### Tier 2: Structured Hermes records
Secondary authority:
- Hermes database records
- exported session records
- target records
- scoring and feedback records
- analysis outputs derived from stored Hermes data

Use these to support operations and analysis.
Do not let them silently override Tier 1 control docs without an explicit documented update.

### Tier 3: Supporting Apollo context and broader evidence
Tertiary authority:
- `projects/apollo/`
- selected supporting material under `Vault/Clean/`
- archived transcripts or recovery notes when continuity checks are needed

Use these for:
- infrastructure context
- governance context
- recovery support
- provenance checks

Do not treat broader Apollo or archive material as a substitute for explicit Hermes control docs.

## First required workflows
Hermes Phase 0 only needs a very small workflow set.

### Workflow 1: Task creation
Hermes must support creation of a task record that includes at minimum:
- task identifier
- task category
- administrator
- intended viewer or viewer group
- target reference or target payload location
- blinding mode
- creation timestamp
- status

### Workflow 2: Task release
Hermes must support controlled release of tasking to a viewer.

The release process must preserve the intended protocol.
For example, if a target should remain blind, the viewer-facing interface must only expose the permitted tasking reference and instructions, not the hidden target details.

### Workflow 3: Session submission
Hermes must support remote session submission including at minimum:
- task identifier
- viewer identifier
- submission timestamp
- raw session content or attached session artifact
- optional self-report fields such as confidence, modality, notes, and conditions

### Workflow 4: Feedback release
Hermes must support administrator-controlled feedback release.

Feedback must not be treated as automatically visible from the start.
The system should preserve feedback state, including:
- withheld
- released
- release timestamp
- released by whom

### Workflow 5: Analysis and review
Hermes must support basic review and analysis over stored data.
At minimum the system should be able to inspect:
- session counts
- sessions by viewer
- sessions by task category
- basic outcome and scoring fields when present
- historical comparisons over time

## Data rules for Phase 0
Hermes should preserve structured records from the start.

### Minimum record families
Hermes should eventually maintain at least these logical record types:
- viewers
- tasks
- targets
- sessions
- feedback events
- scoring or outcome events
- analysis summaries

### Minimum data principles
1. every task should have a stable identifier
2. every session should point to a task and viewer
3. timestamps should be recorded consistently
4. raw submitted content should be preserved separately from interpreted summaries
5. feedback state should be explicit
6. scoring or outcome fields should not overwrite raw session data
7. administrator edits should be auditable where practical

## Remote access contract
Hermes is expected to be remotely accessible because both the administrator and viewers need to interact with it off-machine.

For Phase 0, remote access should mean:
- a controlled admin-facing interface
- a controlled viewer-facing interface or submission path
- role-appropriate visibility
- no assumption that every user sees the same data

Remote access does **not** require a polished public product in Phase 0.
It only requires a reliable path for real use.

## Market-facing rule for Phase 0
Hermes may be designed with future market-facing workflows in mind, but it must not confuse future intent with current implementation.

### Allowed in Phase 0
- defining how market-oriented tasks might later be represented
- capturing outcome fields that would support later analysis
- planning paper-trading style evaluation

### Not allowed in Phase 0
- automated real-money trading
- autonomous broker execution
- treating unvalidated session output as sufficient grounds for live capital deployment
- pretending a market edge exists before evidence review

## Answer contract
When Hermes answers questions about its own project or workflow state, it should:
- prefer Tier 1 control docs first
- distinguish current capability from planned capability
- distinguish recorded data from interpretation
- say when an answer depends on stored operational records rather than project docs
- preserve the difference between research support and market application

## Grounding rules
A valid Hermes Phase 0 answer or action should be:
- consistent with the control docs
- aligned to the current phase
- aware of workflow boundaries
- explicit about missing data or uncertainty
- careful not to leak hidden target information into blind workflows

A weak answer or action is one that:
- improvises protocol rules that are not documented
- exposes target details too early
- blurs raw session data with later interpretation
- assumes market readiness before evidence exists
- expands the system surface faster than the workflow discipline

## Anti-drift rules
Hermes must not, during Phase 0:
- expand into live trading before the research loop works
- let viewers access hidden target data prematurely
- rely on chat memory alone for operational continuity
- replace structured records with loose narrative summaries
- build complicated multi-agent ceremony before the basic loop is proven
- treat speculation as evidence

## Recovery and handoff rule
If continuity is lost, a replacement session or agent should reconstruct Hermes in this order:
1. `projects/hermes/README.md`
2. `projects/hermes/charter.md`
3. `projects/hermes/contract.md`
4. `projects/hermes/status.md`
5. `projects/hermes/decisions.md`
6. `projects/hermes/checklist.md`
7. `projects/hermes/handoff.md`
8. Hermes operational records and database exports as needed
9. Apollo control docs for shared infrastructure context

## Exit condition for this contract
This contract remains primary until Hermes has:
- a working task creation flow
- a working viewer submission flow
- controlled feedback release
- stable structured storage for the core records
- basic analysis outputs
- enough reliability to begin paper-trading style evaluation planning

Once that is true, Hermes can revise this contract for the next phase.

## Practical interpretation
In Phase 0, Hermes is not proving that psi operations can run an empire.
It is proving that the project can run one disciplined session loop cleanly, repeatedly, and in a form that survives interruption.
