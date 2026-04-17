# Hermes Status

## Current state
- Date: 2026-04-17
- Overall status: **in progress**
- Active phase: **Phase 0 Foundation**
- Focus: establishing the minimum viable Hermes backbone for remote-viewing / psi-functioning operations with disciplined tasking, remote session intake, controlled feedback release, structured storage, and basic analysis

## What is already true
### Project framing
- Hermes has been defined as a focused Apollo subproject
- Hermes has two long-range aims:
  - support psi-functioning research in multiple operational modes
  - explore whether structured remote-viewing workflows can later support market-facing prediction work
- Hermes is explicitly being built in smaller chunks rather than as a sprawling all-at-once system

### Governance and architecture stance
- Apollo remains the governing platform and shared infrastructure layer
- This OpenClaw instance is intended to be the central coordination surface for Hermes
- Hermes should use local agents/models where practical and cloud/API models where justified
- Remote access is considered necessary because both the administrator and viewers must be able to interact with the system off-machine

### Human roles
- The user is the project administrator
- Hermes is expected to support at least one psionic asset / viewer initially
- The design should allow later expansion to multiple viewers without requiring that complexity at the start

### Project control layer
- `projects/hermes/README.md` has been created as the canonical control-folder introduction
- `projects/hermes/charter.md` has been created and defines mission, scope, principles, and first-phase boundaries
- `projects/hermes/contract.md` has been created and defines the first operating contract for roles, workflows, authority, and anti-drift rules

## Current objective
Prove the first real Hermes loop:
1. create a task
2. release tasking in a controlled way
3. receive a remote session submission
4. store the session and related metadata in structured form
5. release feedback at the intended stage
6. preserve the record for later review and analysis

## Immediate next actions
1. complete the remaining Hermes core control files (`decisions.md`, `checklist.md`, `handoff.md`, `status.json`)
2. define the minimum logical data model for viewers, tasks, targets, sessions, feedback, and scoring/outcomes
3. define the first practical remote workflow for one administrator and one viewer
4. decide what the first real submission interface should be
5. decide where Hermes structured records should live first, database-first, file-first, or hybrid
6. define the minimum analysis/reporting outputs for Phase 0

## Known constraints and open concerns
- The exact first implementation surface is not yet chosen, web form, chat-driven workflow, database UI, or hybrid
- The exact storage implementation is not yet chosen, though structured persistence is mandatory
- Blindness and protocol discipline must be preserved, which means viewer-facing flows cannot casually expose target details
- Market-facing ambitions exist, but Phase 0 must not drift into live trading or premature automation
- The project still needs explicit operational decisions for authentication, role separation, and remote access boundaries

## Current recommendation
Keep Hermes narrow.
Do not expand into live market automation, complex multi-agent orchestration, or speculative feature breadth until the first disciplined session loop works cleanly and repeatedly.
