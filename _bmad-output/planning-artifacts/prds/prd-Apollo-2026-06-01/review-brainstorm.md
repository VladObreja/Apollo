# Review against Brainstorm & Feature Staging (V1)

**Verdict:** Mostly Complete, but missing several explicit V1 variables.

## Critical Findings
1. **Admin State & Purity Tier (Brainstorm #59, #117, #22):** The PRD currently focuses heavily on the Asset's metadata (sleep quality, social context) and the 2x2 Stakes Matrix, but V1 explicitly requires logging the *Admin's* state at dispatch (Admin State Snapshot, Admin Awareness Tier) and the Epistemic Purity Tier of the target itself.
2. **UTC-Native Architecture (Brainstorm #34):** The V1 feature staging explicitly mandates a UTC-Native event model. This should be explicitly added to the NFRs to prevent any timezone bugs in the pipeline.
3. **Angular Value as Raw Signal (Brainstorm #7):** While the PRD mentions the 0-180° scale mapped to 0-100%, it should explicitly state that the *raw angular output* must be preserved in the database independently of the percentage mapping, so that the mapping hypothesis can be changed later.

## Medium Findings
- **Archival-Grade Corpus Preservation & Epistemological Ledger (#75, #95):** We have the "Immutable Ledger" NFR, which covers the data persistence, but we should make sure the "Epistemological Ledger" (versioning the analysis frameworks) is explicitly stated.

---

## Audit Pass 2: Maximum Effort Reconciliation (Database & Email)

**Verdict:** The Brainstorming document prescribed highly specific field formats that the original PRD generalized. These have now been explicitly reconciled into the PRD.

### Reconciled Email Format
- **Anonymization-by-Design (#121):** Email dispatch must occur strictly between unpersonalized research emails (e.g., `apollo.asset1@...`).
- **Structured Envelope Fields (#9, #67):** The PRD originally summarized these as "sleep quality, social status." This has been corrected to the exact Brainstorm schema: `time of measurement (UTC)`, `location`, `sleep quality`, `psychological state`, and `Social Field (Isolated/Familiar/Unfamiliar)`.

### Reconciled Database Format
- **Session Provenance Chain (#104):** Appended as NFR-7. The database must permanently log every touch (task dispatch, extraction agent version, seal hash) alongside the Epistemological Ledger state.
- **Data Registry Architecture (#122, #123, #13):** Appended as NFR-8. Explicitly defines the Parameter Registry, Question Template Library, and Minimal Asset Registry, enforcing the rule that Asset performance is derived at query time, not stored mutably.
