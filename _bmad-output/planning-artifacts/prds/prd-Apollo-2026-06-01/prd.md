---
title: Apollo PRD
status: final
created: 2026-06-01
updated: 2026-06-01
---

# Apollo Product Requirements Document

## User Journeys

The following journeys define the primary interaction loops between the Administrator (Vlad), the System, and the Asset (Jane).

### UJ-1: Target Planning & Dispatch
**Protagonists:** Vlad (Admin), Claude Code Agent, Apollo Worker Daemon
1. **Vlad** interacts with the Claude Code agent (the single administrative entry point) to provide general protocol guidelines and target criteria for the next operational period.
2. The **Claude Code Agent** translates these into database configurations (Target Selection rules). It does *not* fetch the targets directly, preserving compartment isolation.
3. The **Apollo Worker Daemon** autonomously fetches the targets (e.g., "Gold price will increase by >9% from open to close tomorrow") based on the configured rules. It strictly enforces a **cap of 5 targets per day** to prevent cognitive and closure overload on the asset.
4. Concurrently, the system captures an **Admin State Snapshot** (Vlad's psychological context) and logs the **Admin Awareness Tier** to monitor potential upstream telepathic contamination.
5. The system pairs the target statement with a parameter (e.g., VAD) and generates a double-blind coordinate (e.g., `XXXX/YYYY`).
6. A local LLM agent drafts and dispatches the tasking email to **Jane** using only the coordinate and requested parameters. **Anonymization-by-Design** is strictly enforced: dispatch occurs exclusively between unpersonalized research emails (e.g., `apollo.admin@proton.me` to `apollo.asset1@proton.me`).

### UJ-2: Asset Session & Extraction
**Protagonists:** Jane (Asset), Local Extraction Agent
1. **Jane** receives a templated email: *"Target ID XXXX/YYYY: Please measure the parameter of interest... PARAM: [ ], time of measurement (UTC): [ ], location: [ ], sleep quality: [ ], psychological state: [ ], Social Field (Isolated/Familiar/Unfamiliar): [ ]"*.
2. Jane performs her radiesthesia measurement against the double-blind coordinate.
3. She hits "Reply", fills in the numerical values and the exact time the measurement was taken (decoupling it from the email transmission timestamp for accurate environmental correlation). She optionally adds natural language notes, and sends the email.
4. The **Local Extraction Agent** intercepts the email, parses the unstructured text, and maps it to a strict Pydantic schema.
5. If valid, the system cryptographically seals the session and commits the extracted data to the database.

### UJ-3: Clarification Loop (Exception Path)
**Protagonists:** Jane (Asset), Local Extraction Agent
1. If the Local Extraction Agent detects missing or corrupted values, it halts the database insertion.
2. Operating strictly within its Compartment Guard (with zero access to the true target identity), the agent generates a polite clarification email and sends it to Jane.
3. Jane replies with the corrected values.
4. The agent re-validates and successfully commits the data.

### UJ-4: Ground-Truth Validation
**Protagonists:** System Daemon
1. At the precise expiry time specified in the target formulation (e.g., market close), a background system process awakens.
2. The system checks the actual market outcome (the ground truth price).
3. The system validates Jane's sealed prediction against the outcome and records the result.

### UJ-5: Weekly Closure Ceremony
**Protagonists:** System Daemon, Jane (Asset)
1. At the scheduled weekly interval, the system aggregates all validated sessions for that week.
2. The system drafts a "Closure Ceremony" email containing the definitive list of actual target outcomes.
3. Jane receives the email, permanently closing the feedback loop for those sessions. This fulfills the epistemological requirement that the asset must eventually perceive the true outcome to complete the retrocausal loop.

## System & Epistemological Constraints (NFRs)

Because Apollo treats psi-functioning as axiomatic and highly sensitive to observer effects and procedural contamination, the system architecture must physically enforce research integrity. 

**NFR-1: Strict Compartment Isolation (Double-Blind Purity)**
The system must enforce strict informational boundaries (`CompartmentGuards` in code). The entity (or Local LLM process) drafting the clarification emails or extracting the session data must be completely blind to the true identity of the target. Information crosses compartment boundaries only through explicit, logged, and permissioned events on the Event-Driven Compartment Bus.

**NFR-2: Immutable Event-Sourced Ledger**
The `corpus_record` is an event-sourced, append-only ledger. The raw incoming email bytes from the Asset are strictly immutable. Any downstream interpretations of those bytes (e.g., Pydantic extractions of `VAD`, `RVD`) are treated as derived, mutable records that can be versioned via "Epistemological Epochs" allowing the corpus to be re-analyzed later without corrupting the historical ground truth.

**NFR-3: The 2x2 Stakes Matrix (Psi Interference Tracking)**
To study the potential confounding effects of capital-weight vs. performance-anxiety, the system must independently track two boolean states for every session:
1. `real_money_at_stake`: Was actual capital objectively risked?
2. `asset_financial_awareness`: Was the asset subjectively aware that capital was risked?

**NFR-4: Strict Schema-Driven Extraction (Pydantic Protocol)**
Pydantic v2 schemas are the absolute protocol of the system. The Local LLM (Ollama) is constrained by these explicitly typed schemas to extract the required variables (`VAD`, `sleep_quality`, etc.). The system must never write unvalidated or partial data to the database; it must either pass validation or trigger the Clarification Loop (UJ-3).

**NFR-5: Fail-Operational and No Silent Discards**
Missing sessions or systemic outages (e.g., failure to fetch a market price at the exact closure time) MUST NOT result in the session being automatically discarded. They must remain pending for human review. If closure is artificially delayed, it must be flagged (e.g., `Offset`) so the Calibration Engine can correctly account for temporal drift in its calculations.

**NFR-6: UTC-Native Time Architecture**
All system events, market closure deadlines, and environmental correlative timestamps must be recorded natively in UTC to prevent temporal synchronization errors and preserve chronological integrity.

**NFR-7: Session Provenance Chain**
Every session record must carry an immutable, append-only provenance chain. Every system process that touches the record (task dispatched, extraction LLM agent version, extraction confidence, cryptographic seal hash) must be logged with a timestamp and the system's Epistemological Ledger belief state at the time of action.

**NFR-8: Data Registry Architecture**
The database format must isolate concerns into specific registries:
- **Minimal Asset Registry:** Stores only operational identifiers and active/inactive status. Asset performance metrics are ALWAYS derived dynamically at query time from the corpus, never stored as mutable scores.
- **Parameter Registry:** A table defining VAD, RVD, EBF, etc., separating what can be measured from the task itself.
- **Question Template Library:** A table of variable-substitution strings mapping parameter types and time horizons, resolving question formulation upstream.

## Target & Parameter Mechanics

**1. The Two-Axis Coordinate System**
Every session operates by dynamically pairing a `TargetInstance` with a specific `Parameter`. This pairing generates the unique, double-blind coordinate (e.g., `XXXX/YYYY`) that is delivered to the Asset. The Target and the Parameter remain independent in the database.

**2. Question Formulation as Trade Specification**
The system resolves ambiguity upstream. A target formulation must precisely define the entity, the condition, and the exact time horizon (e.g., *"Gold price will increase by >9% from open to close tomorrow, 2026-06-02"*). Because the question formulation explicitly contains the time horizon and threshold, the question itself serves as the exit strategy and validation criteria.

**3. Continuous Parameter Measurement (Radiesthesia Scale)**
The Asset measures parameters using a standard radiesthesia scale (0–180° mapped to 0–100%). The system treats these measurements as continuous percentage values, not binary inputs. 
- **VAD (Valoarea de Adevăr - Value of Truth):** The primary signal. It measures the truth value of the target affirmation. Traditionally, a VAD ≥ 85% is interpreted as "True".
- **RVD (Realizarea Voinței Divine) & EBF (Beneficitate):** Secondary parameters recorded concurrently to evaluate the beneficence and alignment of the target.

**4. Cold-Start Inert Variable Protocol**
While VAD is evaluated as the primary directional signal, RVD and EBF are treated as **inert variables** during the V1 data-gathering phase. They are logged with every session from day one, but they carry no a priori predictive weight and do not alter the system's decisions until the corpus achieves enough statistical power (via a Power Analysis Gate) to assign them an empirically proven weight.

**5. Session Context Fingerprint (Environmental Correlates)**
Every session record is automatically enriched at ingestion time with an environmental snapshot. A background agent pulls and stores data streams on a rolling basis (e.g., Local Sidereal Time at asset location, Kp geomagnetic index, solar wind conditions, Schumann resonance peaks). This fingerprint attaches to the session record permanently, enabling retrospective analysis of environmental correlates without requiring the Asset to consciously report them.

## Success Metrics & Calibration Goals

**1. V1 Success Criteria (Calibration over P&L)**
- **Hit Rate > Chance:** Establish a hit rate above random chance at a statistically significant confidence level. The precise threshold will be empirically determined by the corpus.
- **Empirical Threshold Discovery (The >85% Rule):** Traditionally, radiesthesia treats a reading of ≥85% as a "Positive/True" indication. Apollo treats this strictly as a *starting guideline hypothesis*. The system's primary analytical goal is to empirically discover what the *actual* optimal threshold is for Jane (e.g., perhaps the true conviction threshold is 78%, or 92%).
- **Calibrated Confidence Function:** The primary output of V1 is a reliable, calibrated confidence score—proving that when the system reports X% confidence, it is correct X% of the time.
- **Operational Signal:** The full pipeline runs autonomously (zero manual intervention during the extraction, validation, and weekly closure phases).

**2. Null Result Handling**
- Apollo treats psi functioning as axiomatic. If the analysis yields a null result, the conclusion is that the *current protocol configuration* or *target formulation* is insufficient—not that the underlying phenomenon is absent. Protocol revision follows immediately.

**3. Counter-Metrics**
- **Asset Cognitive Overload:** If Hit Rate is high but the Asset reports consistently degraded sleep quality or psychological state in the session metadata, the operational protocol is failing.
- **Protocol Degradation Rate:** Tracking the number of sessions flagged as "Degraded Protocol" due to failed or artificially delayed feedback closure events.
