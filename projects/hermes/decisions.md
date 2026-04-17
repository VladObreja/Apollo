# Hermes Decisions

## Confirmed decisions

### Project identity and role
- Hermes is a distinct Apollo subproject focused on remote viewing and broader psi-functioning workflows
- Apollo remains the governing platform and shared infrastructure layer
- Hermes should have its own canonical control folder under `projects/hermes/`
- Markdown control docs are the primary continuity layer, with structured/machine-readable mirrors added as supporting artifacts

### Development strategy
- Hermes will be built in small, useful chunks rather than as a large speculative system
- The first goal is a disciplined research backbone, not a grand unified psi platform
- The first real proof is an end-to-end session loop, not theoretical completeness
- Research support comes before market automation
- Human-readable continuity and recoverability matter from the start

### Human operating model
- The user is the initial project administrator
- Hermes should support at least one psionic asset / viewer in the first implementation
- Hermes should later allow multiple viewers, but that is not a Phase 0 requirement
- Consequential actions remain under human authority

### Core Phase 0 workflow
- Hermes Phase 0 is centered on: task creation, controlled task release, remote session submission, controlled feedback release, structured storage, and basic analysis
- Blind or partially blind workflows are important and must be supported carefully
- Raw session submissions should be preserved separately from later interpretation or scoring
- Feedback release should be controlled rather than assumed to be automatically visible

### Technical stance
- This OpenClaw instance is intended to be the central coordination surface for Hermes
- Hermes may use local models/agents on the RTX 5070 Ti where practical
- Hermes may use cloud/API models where justified
- Remote access is required because both administrator and viewers need off-machine interaction
- A database-backed analysis layer is part of the intended system direction

### Market-facing stance
- Hermes has a second long-range objective related to market-oriented remote-viewing support
- Phase 0 must not include live automated trading
- Real-money automation is explicitly deferred until after strong evidence and controlled intermediate phases
- Paper-style evaluation and analytical preparation are acceptable future intermediate steps

## Working assumptions
- The first useful Hermes implementation should be small enough to build and test quickly
- Structured persistence is mandatory even if the exact first storage pattern is still undecided
- Viewer-facing interfaces must expose only the information appropriate to the protocol state
- Basic analysis should start with simple counts, categorization, and outcome tracking before more elaborate scoring frameworks
- Hermes continuity should not depend on this chat thread remaining available

## Open decisions
- What the first real remote submission interface should be, web form, chat workflow, database UI, or hybrid
- Whether the first storage layer should be database-first, file-first, or hybrid
- How authentication and role separation should be handled in the first remote-access version
- What the minimum scoring schema should be for early Hermes sessions
- How market-oriented tasks should be represented later without distorting the research-first backbone
- Which local vs cloud model responsibilities should be assigned first
- How much protocol variation should be supported in the initial implementation

## Decision rule going forward
When new Hermes work is proposed, evaluate it in this order:
1. does it strengthen the first disciplined session loop?
2. does it preserve blindness, protocol control, and structured records?
3. does it improve recoverability across sessions and interruptions?
4. is it needed now, or is it later-phase ambition trying to sneak in early?
