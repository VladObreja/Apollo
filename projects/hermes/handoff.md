# Hermes Handoff Notes

## Purpose of this file
This file is for session recovery and handoff to another OpenClaw session or another agent.

## If you are a new session or new agent
Start here:
1. read `projects/hermes/README.md`
2. read `projects/hermes/charter.md`
3. read `projects/hermes/contract.md`
4. read `projects/hermes/status.md`
5. read `projects/hermes/decisions.md`
6. read `projects/hermes/checklist.md`
7. inspect relevant Apollo control docs under `projects/apollo/`
8. inspect current runtime state if implementation work has already begun

## Current project situation
Hermes is a newly formalized Apollo subproject.
The project is still in Phase 0 Foundation.
The immediate aim is not broad psi-platform sprawl and not market automation.
The immediate aim is to establish a disciplined first operational loop for tasking, session intake, feedback release, structured storage, and basic analysis.

## High-value facts
- Hermes is focused on remote viewing and broader psi-functioning workflows
- Hermes has two long-range aims:
  - support psi-functioning research operations
  - later explore market-facing remote-viewing use cases
- Apollo remains the governing platform and shared infrastructure layer
- This OpenClaw instance is intended to be the central coordination surface
- Remote access is required because the administrator and viewers must be able to interact with Hermes off-machine
- The user is the initial project administrator
- Hermes should support at least one viewer first, with possible expansion later
- Blindness and protocol discipline matter and must not be casually broken by the interface
- Live trading and autonomous real-money execution are explicitly out of scope for Phase 0

## Next best actions
- finish the remaining core continuity file `status.json`
- define the minimum Hermes record schemas for viewers, tasks, targets, sessions, feedback, and scoring/outcomes
- choose the first real remote workflow surface
- decide the first persistence pattern, database-first, file-first, or hybrid
- prove one end-to-end session loop cleanly

## Warning notes
- Do not let viewer-facing flows expose hidden target information too early
- Do not treat chat memory as the project record
- Do not expand into complex multi-agent systems before the first workflow works
- Do not drift into live market execution based on ambition alone
- Preserve raw session submissions separately from later scoring or interpretation

## Handoff standard
Any major new decision or milestone should update at least:
- `status.md`
- `decisions.md`
- `checklist.md`
- `status.json`

If the project structure changes materially, also update:
- `charter.md`
- `contract.md`
- `README.md`
- `handoff.md`
