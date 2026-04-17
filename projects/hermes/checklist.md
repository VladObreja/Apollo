# Hermes Checklist

## Phase 0 Foundation checklist

### A. Control layer
- [x] Create `projects/hermes/README.md`
- [x] Create `projects/hermes/charter.md`
- [x] Create `projects/hermes/contract.md`
- [x] Create `projects/hermes/status.md`
- [x] Create `projects/hermes/decisions.md`
- [ ] Create `projects/hermes/checklist.md`
- [ ] Create `projects/hermes/handoff.md`
- [ ] Create `projects/hermes/status.json`

### B. MVP workflow definition
- [ ] Define the first task object schema
- [ ] Define the first viewer object schema
- [ ] Define the first target object schema
- [ ] Define the first session submission schema
- [ ] Define the first feedback event schema
- [ ] Define the first scoring/outcome schema
- [ ] Define the first end-to-end administrator workflow
- [ ] Define the first end-to-end viewer workflow

### C. Access and interface decisions
- [ ] Decide the first admin interface path
- [ ] Decide the first viewer submission path
- [ ] Decide the first authentication approach
- [ ] Decide how role-based visibility will be enforced
- [ ] Confirm the first remote access pattern is usable for real sessions

### D. Persistence and analysis
- [ ] Decide whether Phase 0 storage is database-first, file-first, or hybrid
- [ ] Create the first durable storage layout for Hermes records
- [ ] Ensure raw session material is preserved separately from interpretation
- [ ] Ensure feedback state is explicitly recorded
- [ ] Define the first basic review/analysis outputs

### E. Protocol discipline
- [ ] Define the minimum blind or partially blind tasking protocol
- [ ] Define what information is visible to the viewer at each stage
- [ ] Define the feedback-release rule
- [ ] Define what administrator actions require explicit review
- [ ] Define the first scoring or outcome-assessment procedure

### F. Validation
- [ ] Run one complete simulated Hermes session loop
- [ ] Run one complete real Hermes session loop
- [ ] Confirm that a replacement session/agent can recover Hermes state from the project docs
- [ ] Confirm that records remain usable for later analysis after the first completed sessions

## Current top-priority next steps
1. finish the remaining core continuity files
2. define the minimum Hermes record schema set
3. choose the first actual remote workflow surface
4. prove one end-to-end session loop cleanly

## Completion condition for Phase 0 Foundation
Hermes Phase 0 is complete when the project can run at least one disciplined end-to-end session loop with recoverable continuity, structured storage, controlled feedback, and basic analysis support.
