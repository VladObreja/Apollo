---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Local Semi-Sovereign LLM Architecture - Project Apollo'
session_goals: 'Explore architectural approaches, feature design, and implementation strategies for a local-first AI system centered on a remote viewing project management MVP, with expansion paths to knowledge base and agentic web archiving capabilities'
selected_approach: 'ai-recommended'
techniques_used: ['morphological-analysis', 'first-principles', 'concept-blending', 'chaos-engineering-hira']
ideas_generated: 124
context_file: ''
session_continued: true
continuation_date: '2026-05-31'
---

# Brainstorming Session Results

**Facilitator:** Vlad
**Date:** 2026-05-29

## Session Overview

**Topic:** Local Semi-Sovereign LLM Architecture — Project Apollo

**Goals:**
- Design a robust, expandable local LLM architecture
- MVP focus: Remote Viewing Project Management System (function 3)
- Explore tasking, asset communication, signal analysis, and feedback loop design
- Identify shared resource strategies across all three sub-systems
- Explore local LLM selection, external LLM integration (MCP), and UI/UX via natural language

### Hardware Context
- CPU: i7 265KF
- RAM: 64GB DDR5
- GPU: RTX 5070 Ti
- Storage: 2TB M.2 SSD

### Session Setup

Three functional pillars:
1. **Second Brain** (knowledge base ingestion) — books, docs, forum threads, video/audio — SECONDARY
2. **Agentic Web Archiver** (headless browsing, content preservation, rabbit-hole following) — SECONDARY (preservation urgency noted)
3. **Remote Viewing Project Manager** — MVP PRIMARY — email-based asset coordination, LLM-generated tasking/feedback, multidimensional analysis, signal extraction


## Technique Selection

**Approach:** AI-Recommended
**Analysis Context:** Local Semi-Sovereign LLM Architecture with MVP focus on Remote Viewing Project Management

**Recommended Techniques:**
- **Morphological Analysis** (deep): Map all architectural axes independently before combining — prevents early lock-in
- **First Principles Thinking** (creative): Strip sovereignty/local-first assumptions to bedrock — reveals non-obvious architecture choices
- **Concept Blending** (creative): Merge cross-domain concepts (RV protocols + intelligence analysis + LLM automation + sovereign computing)
- **Chaos Engineering** (wild, optional): Stress-test against adversarial scenarios for anti-fragility

**AI Rationale:** Project Apollo sits at a genuinely novel intersection of domains. Morphological Analysis opens the solution space systematically; First Principles prevents assumption-lock; Concept Blending generates the Apollo-specific ideas that distinguish this from any off-the-shelf approach.


## Phase 1: Morphological Analysis — Results

**Status:** Complete
**Ideas Generated:** 18
**Axes Mapped:** 6 (4 decided, 2 scoped)

---

### Axis Decisions

| Axis | Decision | Status |
|------|----------|--------|
| 1 — Local LLM Layer | Specialist ensemble + hybrid gateway within 16GB VRAM | ✅ DECIDED |
| 2 — External LLM Bridge | MCP server approach; Claude Code as single operator entry point | ✅ DECIDED |
| 3 — Orchestration Backbone | Event-driven message bus with compartmentalised domains | ✅ DECIDED |
| 4 — RV Session Data Model | Two-axis coordinate system, angular raw signal, email envelope, context fingerprint | ✅ EXPLORED |
| 5 — Analysis Engine | Pluggable sandbox — open framework, no fixed methodology | SCOPED |
| 6 — Asset Management | Minimal asset registry with extensible characteristics | SCOPED |

**Key constraint confirmed:** Environmental correlates join to **asset-reported measurement time**, not email receipt or system read time.

---

### Ideas Catalogue

**[Architecture #1]**: Tiered Intelligence Stack
_Concept:_ Specialist local model ensemble within 16GB VRAM handles all deterministic high-frequency tasks (email generation, DB curation, routing, tasking templates). A hybrid gateway escalates computationally expensive analytical work — signal extraction from RV sessions, cross-domain pattern detection — to external LLMs (Claude, GPT, Gemini) where the depth justifies it.
_Novelty:_ Sovereignty is preserved at the operational layer; external LLMs become consultants, not dependencies. The system functions fully offline for day-to-day operations.

---

**[Architecture #2]**: MCP-Native External LLM Bridge
_Concept:_ Apollo exposes its capabilities (database queries, session management, tasking, email dispatch, analysis requests) as MCP tools on a local MCP server. Claude connects natively; other providers adopt MCP as it proliferates. The bridge is forward-compatible by design.
_Novelty:_ Apollo doesn't call the LLMs — the LLMs call Apollo. Inversion of the typical integration pattern.

---

**[Architecture #3]**: Claude Code as Mission Control
_Concept:_ A Claude Code instance connected to Apollo's MCP server becomes the single natural-language point of entry for the entire stack — administering processes, querying the database, triggering tasking runs, reviewing analysis outputs, managing assets. The "UI" is the conversation.
_Novelty:_ Eliminates the need for a dedicated frontend entirely. The operator interface IS the AI interface. No UI layer to build for the MVP.

---

**[Architecture #4]**: Double-Blind Information Vault
_Concept:_ Apollo's RV subsystem is built around five isolated compartments — Target Vault, Task Registry, Session Inbox, Analysis Chamber, Feedback Queue — with strictly controlled one-directional data flows between them. No component can access data from a compartment it has no business seeing. The unblinding event (target + session comparison) is a discrete, logged, irreversible operation.
_Novelty:_ Research protocol integrity is enforced architecturally, not by procedure. The system physically cannot contaminate a session because the information paths don't exist.

---

**[Architecture #5]**: Event-Driven Compartment Bus
_Concept:_ The orchestration backbone is an event-driven message bus (Redis Streams or equivalent) where each compartment is a sovereign domain. Information crosses compartment boundaries only through explicit, logged, permissioned events — TaskIssued, SessionReceived, UnblindingTriggered, FeedbackDispatched. The bus enforces the double-blind protocol structurally.
_Novelty:_ The RV research integrity requirement and the software architecture requirement converge on the same solution. Decoupled compartments mean the web archiver, knowledge base, and other pillars plug in as new subscribers without touching the RV core.

---

**[Data Model #6]**: Two-Axis Task Coordinate System
_Concept:_ Every task is a (Target, Parameter) pair assigned a CRV-style reference coordinate (XXXX/YYYY). Targets and Parameters are independent registries — any target can be paired with any parameter. The LLM generates the tasking question from this pair using a configurable ruleset template, keeping the actual target identity sealed in the vault.
_Novelty:_ The coordinate is the abstraction layer. Changing methodology, asset, or parameter type requires no schema changes — only new registry entries and potentially a new LLM prompt template.

---

**[Data Model #7]**: Angular Value as Raw Signal
_Concept:_ The session record stores the raw angular output (0–360°) without pre-mapping it to the parameter domain. The mapping function — how a given angle relates to a parameter value — is a separate discoverable artefact in the analysis layer, not hardcoded into the session record. Different mapping hypotheses can be tested against the same corpus.
_Novelty:_ Because the project is in discovery mode, the raw value must be preserved independently of any interpretive frame. The entire historical corpus can be re-analysed under a new mapping hypothesis at any time without data loss.

---

**[Data Model #8]**: Control Target Registry
_Concept:_ Control targets are entries in the Target registry flagged as known-outcome. They can be blind controls (indistinguishable from live tasks to the asset) or open controls (flagged for calibration). The system administers them automatically, interspersed with live tasks at a configurable ratio. Analysis treats them identically to live targets.
_Novelty:_ Controls are first-class citizens of the task coordinate system. Calibration data and live data share the same statistical pipeline.

---

**[Data Model #9]**: Structured Email Session Envelope
_Concept:_ The tasking email is a template with clearly delimited fields (angular value per parameter, asset-reported measurement timestamp, location, sleep quality, psychological state) followed by a free-text notes section. The asset replies in-place. The Session Inbox LLM agent extracts structured fields deterministically, then processes the notes section for qualitative tagging. The email thread is archived as the canonical record.
_Novelty:_ The email IS the session form. No app for the asset to install. Compliance is pressing Reply. The LLM handles unstructured ambiguity without requiring format discipline from the asset.

---

**[Data Model #10]**: Session Context Fingerprint
_Concept:_ Every session record is automatically enriched at ingestion time with an environmental snapshot drawn from automated feeds: Local Sidereal Time at asset location, Kp geomagnetic index, solar wind conditions, local weather, Schumann resonance peaks, planetary configuration. The fingerprint attaches to the session record and is stored independently in a correlates time-series. Assets never report these — captured silently.
_Novelty:_ The corpus accumulates environmental correlates passively, enabling retrospective analysis of variables not originally prioritised. Any correlate can be tested against the full historical dataset years later.

---

**[Data Model #11]**: Environmental Correlates Ingestion Pipeline
_Concept:_ A scheduled background agent pulls and stores environmental data streams on a rolling basis: NOAA for geomagnetic/solar indices, Swiss Ephemeris for planetary positions, weather APIs keyed to asset locations, sidereal time calculated from UTC and observer coordinates. Stored in a time-series layer keyed to UTC, joinable to any session by reported measurement time.
_Novelty:_ Extensible by design — adding a new correlate is adding a new source module. The analysis engine treats all correlates identically regardless of mainstream status. Epistemically neutral.

---

**[Data Model #12]**: Multi-Parameter Session Record
_Concept:_ A single session contains a list of (Parameter, AngularValue) pairs rather than a single field, allowing compound tasks. Each pair is individually analysable while remaining linked to the shared session context fingerprint.
_Novelty:_ Single-parameter and multi-parameter tasks share identical infrastructure. Complexity grows in the data, not the schema.

---

**[Data Model #13]**: Minimal Asset Registry
_Concept:_ Assets are records containing codename, email address, active/inactive status, methodology type, and optional biographical fields (DOB, nationality) stored as extensible key-value characteristics. Performance metrics are derived at query time from the session corpus — never stored as a mutable score.
_Novelty:_ The asset record is deliberately thin. Rich asset profiling emerges from data, not from pre-assigned labels. Mutable scores would introduce bias into session weighting.

---

**[Data Model #14]**: LLM-Native Email Extraction Agent
_Concept:_ Incoming session emails are processed by a local LLM acting as a structured extraction agent. The LLM reads the full email thread, extracts field values, identifies ambiguities or errors, and either commits the record to the Session Inbox or triggers a correction cycle — generating a clarification email to the asset, holding the session in pending state until the clarification reply resolves. Extraction reasoning is logged alongside the session record.
_Novelty:_ Error handling is conversational and graceful. The asset experiences a polite follow-up, not a broken system. Silent corruption is impossible — every extraction decision is auditable.

---

**[Data Model #15]**: Pluggable Analysis Sandbox
_Concept:_ The analysis layer is an open framework of independently executable modules, each taking the session corpus (or a filtered subset) and returning findings in a standardised output format. Modules can be statistical (correlation, regression, significance testing), pattern-based (clustering, anomaly detection), or LLM-assisted (narrative synthesis, hypothesis generation). New modules drop in without touching existing ones. The LLM can propose and scaffold new modules based on emerging findings.
_Novelty:_ "We don't know what analysis we'll need" is honoured architecturally. The corpus is the permanent asset; analyses are disposable lenses applied to it.

---

**[Architecture #16]**: Financial Target Generation Engine
_Concept:_ A dedicated target generation agent pulls market data (equities, commodities, indices, crypto) and applies configurable selection criteria — minimum volatility threshold, liquidity, historical data depth, sector diversity. A secondary layer optionally cross-references algorithmic trading signals, producing targets where RV measurements can be compared against and potentially combined with systematic trading logic. Target selection rationale is logged with every generated target.
_Novelty:_ RV and trading algorithm operate as independent signal sources on the same target universe. Agreement, divergence, and orthogonality are all research findings. Neither signal is presumed primary.

---

**[Architecture #17]**: Cryptographically Sealed Retrocausal Protocol
_Concept:_ For retrocausal task types, the target slot is left empty at tasking time. When the session reply is received, the LLM extraction agent seals the session record with a cryptographic hash and timestamp before any target assignment occurs — creating tamper-evident proof that session data preceded target selection. Target assignment then runs as a separate logged event. The chain (task issued → session sealed → target selected → analysis → feedback) is an immutable audit trail.
_Novelty:_ The system doesn't just support retrocausal protocols — it generates the evidentiary record needed to make retrocausal research claims defensible.

---

**[Research Design #18]**: Post-Hoc Retrocausal Intervention Tracking
_Concept:_ A separate experimental track allows logging of post-session interventions — rituals, intentions, environmental modifications — against already-sealed sessions. Stored as timestamped annotations, never modifying the original record. The analysis engine can test whether any class of post-hoc intervention correlates with session accuracy across the corpus.
_Novelty:_ The architecture treats the past as a legitimate experimental variable without compromising original session data integrity. The original record is permanent; the intervention annotation is a separate immutable layer.

---

## Continuation Session — Open Thread Exploration (2026-05-29)

**Threads Explored:** 1 of 3 (Retrocausal Target Selection Timing)
**Ideas Added:** 12 (total: 30)

### Terminology Clarification

- **Operator / Asset / Viewer** — interchangeable terms for the remote viewing practitioner
- **Admin / Administrator** — the system operator (Vlad); manages target pool, study design, and analysis

---

### Thread 1: Retrocausal Target Selection Timing — Results

**[Retrocausal #19]: T-Delta as Parameterized Research Variable**
Every retrocausal session record stores the interval between session-seal timestamp and target-assignment timestamp as `t_delta`. The analysis engine bins sessions by T-delta range and tests accuracy correlation. The "causal wave" hypothesis (closer in time = stronger signal) becomes directly testable against the accumulated corpus — no separate experiment needed, it emerges from normal operations.

---

**[Retrocausal #20]: TRNG Oracle Integration**
A hardware or network true-random number generator serves as the target selection oracle — removing any deterministic fingerprint from the admin's influence. The TRNG output is transformed into a numerical or boolean value to seed selection from the eligible pool. Two integration paths remain open:
- **Local hardware TRNG** (Geiger tube, thermal noise camera, quantum photon splitter) — sovereign, air-gapped, no third-party trust
- **Network TRNG service** (ANU Quantum RNG, HotBits) — simpler integration, external dependency

Both paths have distinct epistemic properties. TRNG source type is recorded per session as a variable for future comparative study rather than forcing a decision now.

---

**[Retrocausal #21]: Pool Age-In Protocol**
Admin-submitted targets enter the pool in an "ineligible" state. They become TRNG-selectable only after a configurable age-in window (hours, days, weeks). Creates a buffer between admin intent and system selection — even unconscious matching of admin addition timing to active session timing becomes structurally impossible past the window length. Age-in window duration is itself a configurable research parameter.

---

**[Retrocausal #22]: Epistemic Purity Tier System**
Targets classified at registration time by purity tier:
- **Pure** — TRNG-selected, admin-blind at session time, natural feedback closure
- **Curated-Blind** — admin-submitted pool entry, system-selected timing, natural closure
- **Directed** — admin-designated target, conscious (McMoneagle-class / applied track)
- **Open-Loop** — no predictable feedback closure (historical phenomena, abstract domains, Swann-class exploration)

Analysis pipelines treat purity tier as a primary stratification variable. Tiers are never mixed in aggregate statistics without explicit override flag.

---

**[Retrocausal #23]: Committed Feedback Architecture**
At task issuance time, the system records a *committed closure event* — the mechanism and expected timing by which the asset will receive feedback on the actual target value/outcome. Commitment stored with the task record. Loop closure is a first-class system concept. Closed protocols (asset receives feedback and knows the actual result) demonstrably outperform open protocols in RV research literature — this is a structural integrity requirement, not a feature.

---

**[Retrocausal #24]: Synthetic Closure Protocol for Open-Loop Targets**
For targets without natural resolution — historical unknowns, Swann-class exploration sessions, abstract domains — a synthetic closure event is scheduled: curated disclosure of known data about the target domain, delivered to the asset at a committed future time. Partial closure is treated as a distinct closure type and tagged in the session record. Asset always receives *something*.

---

**[Research Design #25]: Directed Session Track**
A parallel session track for intentional, admin-designated sessions — the "applied science" lane alongside the controlled research lane. Directed sessions have relaxed epistemic purity requirements by design. Used for developing intuition about target classes, refining asset methodology, and generating actionable results. Analyzed separately; clearly segregated from the research corpus. The McMoneagle (Mars), Swann (Jupiter, Moon) class of sessions belong here.

---

**[Research Design #26]: RV Confidence Parameter — Trading Signal Integration**
Historical session accuracy in a specific target domain (e.g., financial instruments, commodity direction, index magnitude) is computed as a running confidence score per asset per domain type. Once the corpus is statistically sufficient, this score becomes a weighted input to the trading algorithm — a signal with a known confidence level, not a standalone oracle. Agreement between RV signal and algo signal increases position confidence; disagreement is a flag. The system tracks when RV-algo agreement/disagreement correlates with trade outcome, continuously calibrating the weight.

---

**[Architecture #27]: Passive Correlate Collection vs. Active Study Activation**
The system operates in two simultaneous modes:
- **Passive mode (always on):** All configured variables captured for every session — TRNG source type, T-delta, environmental fingerprint, asset methodology, purity tier, etc. No hypothesis being tested; data accumulates.
- **Active study mode (explicitly activated):** Admin designates a specific variable for formal study — sets target session count, significance threshold, and analysis window. System tracks progress toward statistical power and reports findings when threshold is reached.

All variables accumulate evidence from day one regardless of whether they are under active study. Active study is a layer on top of passive collection, not a prerequisite.

---

**[Research Design #28]: Power Analysis Gate**
Before activating a formal study on any variable, the system runs a power analysis estimate: given current corpus size, asset count, observed variance, and target effect size — how many additional sessions are required to detect an effect at a given significance level? Estimate shown to admin before committing to a study track. Prevents premature hypothesis testing on underpowered data.

---

**[Research Design #29]: Feedback Closure as Protocol Integrity Flag**
Sessions where feedback closure did not occur within the committed window are automatically flagged as **degraded protocol** in the corpus. Flagged sessions included in aggregate statistics by default but excluded from formal study analyses unless explicitly overridden. The degraded flag is permanent and non-editable — a data quality marker, not a judgment. Applies retroactively if a committed closure event fails to occur.

---

**[Research Design #30]: Variable Priority Queue**
Admin-managed priority ordering of variables under study consideration. As asset pool grows or corpus depth increases, top items become eligible for active study activation. Reviewed as part of any formal study design session. Keeps the research roadmap visible without locking it in advance.

---

## Continuation Session — Thread 2: Trading Algorithm Integration Depth (2026-05-29)

**Ideas Added:** 14 (total: 44)

---

**[Trading #31]: Three-Lane Trading Architecture**
*Concept:* Three simultaneous integration modes run in parallel with strict corpus segregation: Option A (algo-selected, RV-enriched), Option B (TRNG-selected, RV-primary, algo-execution), Option C (algo-selected, RV-gated — confound-study lane). No cross-lane mixing in aggregate statistics, but cross-lane comparison is an explicit research question: do Option A results replicate under Option B conditions?
*Novelty:* The system doesn't force a bet on which integration model is correct — it runs all three and lets the corpus answer. Epistemic purity is maintained per lane, not globally.

---

**[Architecture #32]: Autonomous Operational Day Protocol**
*Concept:* The system runs a full operational day without admin presence. A morning authorization window (configurable duration) allows the admin to review the allocation plan, approve pending decisions, and set any overrides before going dark. During the blackout, the system executes all automatable tasks — target selection, tasking dispatch, session intake, extraction — and queues non-automatable decisions with full context for evening review. No task is dropped; no decision is made without authorization scope.
*Novelty:* The admin is a periodic decision-maker, not a continuous operator. The system's autonomy boundary is defined by what was pre-authorized, not by what the system judges appropriate in the moment.

---

**[Architecture #33]: Async Multi-Day Planning Horizon**
*Concept:* The admin authorizes sessions in batches — a planning session covering 1–7 days ahead — negotiated with the administrating LLM agent based on corpus state, asset availability, and market calendar. The system queues and executes autonomously within the authorized envelope. Planning cadence is itself a configurable parameter, not a fixed daily ritual. Pre-authorization days in advance naturally extends retrocausal T-delta windows as a side effect.
*Novelty:* Operational continuity is decoupled entirely from admin availability. A Sunday planning session funds the entire week. Longer planning horizons passively accumulate extended retrocausal windows without additional effort.

---

**[Architecture #34]: UTC-Native Event Model with Market Calendar Layer**
*Concept:* All internal timestamps, session records, task events, and correlates are stored and reasoned about in UTC. Market opening hours, settlement windows, and result resolution events are a derived configuration layer — a lookup from UTC to market-local context. Admin local time (Bucharest, UTC+2/+3) appears only in the admin UI as a display convenience, never in stored data or analytical logic.
*Novelty:* The system never has timezone bugs. Adding a new target market is adding a market calendar entry, not touching any core logic.

---

**[Research Design #35]: Paper/Real/Meaningful Parallel Tracks — Stakes Modulation Study**
*Concept:* Rather than a clean cutover, the system permanently maintains paper, small-real, and meaningful-real tracks simultaneously. The transition to meaningful real-money trading is logged as a named, timestamped corpus event — not obscured. The admin's awareness of the threshold is irreducible and acknowledged; the architecture tracks it as a temporal correlate and lets the analysis answer whether a detectable effect occurred. Combined with asset awareness state, this enables a 2×2 study: [Paper | Real] × [Asset Aware | Asset Blind].
*Novelty:* Turns an epistemological confound into a research question. The meaningful-money activation event is data, not noise to be managed.

---

**[Research Design #36]: Asset Financial Awareness as Experimental Variable**
*Concept:* Asset awareness of real-money stakes is a controlled, randomized experimental variable — not a policy decision. Some sessions carry the disclosure; others don't. Awareness status is logged with the session record and becomes a stratification variable in analysis. Motivation effects, anxiety effects, and psi-amplification-by-stakes hypotheses all become testable against the corpus.
*Novelty:* Treats a normally implicit operational decision as explicit research data.

---

**[Research Design #37]: Time Horizon as First-Class Task Parameter**
*Concept:* The resolution window — "gold close vs. open tomorrow," "S&P 500 1-week return," "best mover by Friday close" — is a configurable task parameter stored with the target specification. Different time horizons are studied as distinct conditions; their effect on RV accuracy is a primary research variable. Feedback closure is automatically scheduled at the resolution timestamp. MVP starts with binary directional (up/down) for faster corpus accumulation; continuous magnitude introduced once directional signal is established.
*Novelty:* Time horizon becomes a dimension of the target space, not a deployment decision.

---

**[Architecture #38]: Admin Trading Blind Protocol — The Trading Vault**
*Concept:* The trading execution layer operates autonomously behind an information barrier analogous to the Target Vault. The admin authorizes the trading logic and parameters but does not observe individual open positions, entry prices, or trade direction in real time — only aggregate P&L and session-level outcome resolution. Individual position visibility unlocks only at a configured review window (e.g., after market close).
*Novelty:* Extends the double-blind architecture to the financial execution layer. The admin evaluating RV sessions cannot be unconsciously influenced by knowing whether the current position is winning or losing.

---

**[Methodology #39]: Radiesthesia as Primary Measurement Protocol**
*Concept:* The asset methodology is classical Romanian radiesthesia (ansa și raportorul instrument). Measurements are expressed as percentages (0–100%) mapped from the instrument's 180° angular scale. Primary measurement is **VAD** (Valoarea de Adevăr — Value of Truth): a statement is presented, the asset measures its percentage truth value. Threshold ≥85% = positive/true; <85% = negative/false. The measurement is inherently continuous; binary interpretation is a derived view applied on top of the raw percentage.
*Novelty:* The angular value (0–360°) in the session data model maps directly to the instrument's native output. Binary directional interpretation and continuous magnitude are both preserved from the same raw reading.

---

**[Research Design #40]: Standard Multi-Parameter Radiesthesia Session Record**
*Concept:* Every session collects VAD as the primary signal plus a configurable set of secondary parameters measured concurrently: **RVD** (Realizarea Voinței Divine — alignment with universal will) and **EBF** (Beneficitate — beneficence factor) as defaults, with the parameter list extensible per asset methodology. All parameters stored as percentage values with the same session context fingerprint. Secondary parameters are independent variables — never aggregated with VAD, always analysed as potential modulators. **OPEN: RVD and EBF may carry veto power over trade execution — thresholds and composite signal mechanics deferred to next session.**
*Novelty:* VAD tells you whether a statement is true; EBF tells you whether acting on it is beneficial. These are not the same signal. A high-VAD, low-EBF session may be the most important data point in the corpus.

---

**[Research Design #41]: Meaningful Money Threshold as Explicit Corpus Event**
*Concept:* The transition to meaningful real-money trading is logged as a named, timestamped corpus event — not obscured. Analysis tests whether session accuracy, VAD distributions, or RVD/EBF readings shift before, during, or after the threshold crossing.
*Novelty:* The confound becomes data.

---

**[Methodology #42]: Protractor Scale and Numerical Value Interpretation**
*Concept:* The ansa și raportorul protractor is 180° graded in percentages. Numerical value measurements are possible but require contextual interpretation — a reading of 50 may mean 50%, 50 units, or 5,000 units depending on question framing. The target/parameter pool architecture resolves this upstream: the system defines questions precisely enough that interpretation is unambiguous before the session begins. Continuous parameter measurements (percentage move, magnitude) may require a domain attunement period.
*Novelty:* Ambiguity is a property of the instrument, not a limitation — it is resolved by architecture upstream rather than interpretation downstream.

---

**[Research Design #43]: Asset Domain Attunement as Performance Variable**
*Concept:* Numerical and continuous parameter measurements may require an attunement period during which the asset acclimates to the financial domain and the protocol. Attunement is tracked as a temporal variable — session number, cumulative domain exposure, protocol familiarity. Binary VAD sessions begin immediately; continuous parameter sessions are introduced progressively as attunement indicators mature. The attunement ramp is a designed-for research data window.
*Novelty:* Performance ramp is expected and measured, not corrected for or hidden.

---

**[Research Design #44]: Multi-Timescale Performance Envelope**
*Concept:* Asset confidence is a family of rolling windows at multiple timescales — recent 10 sessions, 30-session window, 90-session window, and all-time baseline. Each window tracked independently. Divergence between short and long windows is a signal: a recent dip against a strong long-term baseline is noise; a sustained short-window decline against a stable baseline is a performance shift worth investigating. Asset on-target performance may vary according to rules we cannot yet determine — timescale envelope captures this variation without requiring a causal explanation. Trading weight derived from the envelope, not a single number.
*Novelty:* Temporal non-stationarity in psi performance is captured structurally. The cause (attunement, life factors, seasonal, unknown cycles) is a separate analytical question.

---

## Continuation Session — Thread 2 Completion (2026-05-30)

**Thread 2: Trading Algorithm Integration Depth — CLOSED**
**Ideas Added:** 7 (total: 51)

---

**[Research Design #45]: Empirical Weight Assignment for Tradition-Derived Variables**
_Concept:_ RVD and EBF are included in every session as protocol variables drawn from the Romanian radiesthesia tradition, but are assigned no a priori predictive weight above any other measured variable. Their contribution to the composite trading signal is initialized at neutral and updated by the corpus as outcome data accumulates — identical treatment to any other session parameter under study. The tradition's 40-year development (Romanian military/navy context) justifies inclusion; empirical corpus evidence determines influence.
_Novelty:_ Respects the tradition without inheriting its cosmology as a prior. Avoids embedding unverifiable assumptions into executable trading logic before the data has spoken.

---

**[Research Design #46]: Cold-Start Inert Variable Protocol**
_Concept:_ RVD and EBF are logged with every session from day one but flagged as inert — excluded from composite signal calculation and trade execution logic until a minimum corpus threshold is reached via Power Analysis Gate (#28). Below threshold, they accumulate data silently. Above threshold, the system runs its first weight estimation and promotes them to active variable status if statistical significance warrants it.
_Novelty:_ Prevents the system from acting on noise masquerading as signal during the data-sparse early phase. Inert status is not a judgment on the variables — it is a commitment to not pretending you know something you do not yet.

---

**[Research Design #47]: Question Formulation as Trade Specification**
_Concept:_ The RV tasking question and the trade specification are the same object. A question like "ABCD rises more than 9% by June 10th" defines the VAD measurement statement, the entry trigger, the profit target, and the expiry date simultaneously. The corpus tests which formulation types (percentage threshold + date, directional binary, magnitude unbounded) yield statistically sound VAD measurements. Once a formulation type is validated, it becomes a reusable template generating both the session task and the trade order. A formulation library — empirically ranked by accuracy — becomes a core study output.
_Novelty:_ Resolves the time-horizon tension with swing trading structurally. The question IS the exit strategy. No separate trade specification layer needed.

---

**[Architecture #48]: RV Confidence as Drop-In Signal Replacement**
_Concept:_ Apollo adopts an existing algorithmic framework's position sizing logic and replaces (or blends) its native confidence signal with the corpus-derived RV confidence value at the input layer. The algo's risk management and sizing logic runs unchanged; only the signal driving it changes. Option A lane: RV enriches algo signal. Option C lane: algo runs unmodified, RV acts as binary gate. Option B lane: RV confidence IS the signal.
_Novelty:_ Position sizing expertise is borrowed, not invented. The research question becomes "does substituting RV confidence improve risk-adjusted returns" — a clean before/after comparison against the algo's own baseline.

---

**[Architecture #49]: Algo as Pluggable Signal Module**
_Concept:_ The algorithmic trading component is a standardized interface — receives a target specification (ticker, question formulation, time horizon), returns direction confidence (0–100%), suggested position sizing, and a rationale tag. Any algo module can slot in behind this interface. First implementation: Rules-Based Technical Screener (RSI, momentum, MACD, Bollinger Bands via TA-Lib or FinTA). Subsequent modules — backtested quant strategies, sentiment/alternative data signals — added as later research variables.
_Novelty:_ Decouples "do we have an algo?" from "which algo is right?" — both deferred to the corpus. The interface contract is the only thing that needs to be right at MVP.

---

**[Research Design #50]: Fixed Fractional Sizing as MVP Default**
_Concept:_ All trades execute at a fixed portfolio percentage (1–2%) regardless of signal strength, RV confidence, or algo output during the study phase. Confidence-weighted sizing is deferred until the corpus is deep enough to justify differential allocation. The sizing formula is itself a future research variable — the corpus will determine whether higher RV confidence should translate to larger positions.
_Novelty:_ Prevents the system from acting on confidence calibrations it has not yet earned. Fixed fractional is the null hypothesis for sizing; the corpus tests whether anything more sophisticated beats it.

---

**[Architecture #51]: Broker-Agnostic Execution Layer**
_Concept:_ Trade execution is abstracted behind a standardized interface — place order, cancel order, get position, get account state — with the first concrete implementation targeting IBKR. Adding a new broker is adding a new adapter behind the same interface. Apollo's trading logic never references a broker directly. Execution layer is sovereign and swappable; broker relationships are operational decisions, not architectural ones.
_Novelty:_ Same pluggable module logic as the algo layer. Both signal generation and execution are adapter patterns — Apollo owns research and decision logic, outsources implementation details.

---

## Thread 3: Formal Study Design Workflow — Ideas Generated

**[Research Design #52]: Calibrated Confidence Score as Primary System Output**
_Concept:_ Apollo's primary deliverable is not a trade signal — it is a **calibrated confidence function**: for a given asset, question formulation type, and target domain, what is the empirically derived probability that the VAD reading predicts the correct outcome? Calibration means not just accuracy but correspondence — when the system reports 62% confidence, it is right approximately 62% of the time. P&L is a downstream validation of calibration quality, not the primary metric.
_Novelty:_ The system is a measurement instrument first, a trading tool second. A well-calibrated low-confidence signal (55%, empirically verified) is more valuable than a high-confidence uncalibrated claim (80%, unverified). The corpus produces a transferable confidence function — applicable to any domain where comparable question formulations can be tested against objective outcomes.

---

**[Architecture #53]: Financial Markets as Calibration Laboratory**
_Concept:_ The trading integration's primary function is not revenue generation but calibration data production. Financial markets are uniquely suited: outcomes are liquid, timestamped, unambiguous, adversarial, and available in high volume. No other accessible domain closes the feedback loop as cleanly or as fast. P&L validates that calibration translates to real-world edge — it is the proof that the confidence function is externally meaningful, not the goal itself.
_Novelty:_ Repositions the entire trading layer. Markets are the R&D instrument. Broader application domains (consultancy, resource hunting, medical) are the eventual product — deferred until calibration is established in the cleanest available domain first.

---

**[Architecture #54]: Dual-Mode Target Generation Engine**
_Concept:_ The target generation engine operates in two selectable modes: **calibration-optimal** (maximizes information value — diverse, fast-resolving, unambiguous targets that efficiently map the confidence function across conditions) and **return-optimal** (maximizes expected trading value — concentrates on high-conviction setups). During early corpus phase, calibration-optimal dominates. Mode selection and blend ratio are admin-configurable research parameters, logged as corpus events. Transition from calibration-dominant to return-dominant is itself a named, timestamped corpus milestone.
_Novelty:_ Separates two objectives that trading systems normally conflate. The corpus accumulates calibration data efficiently in early phase; the confidence function then informs return-optimal selection with earned credibility rather than assumed edge.

---

## Usefulness Framework Decisions

> **Format note:** This section contains design decisions derived through Thread 3 dialogue. These are constraints that govern what the system must express — distinct from the generative ideas catalogue above. They carry forward directly into PRD and architecture phases without requiring a separate document.

---

### Decision 1: Epistemological Ground

**Decision:** Apollo operates outside the classical scientific falsifiability framework. The study of psi effects does not reliably conform to classical repeatability constraints. The observer influences the observed — including the act of designing measurement instruments. Classical falsification is therefore an inappropriate primary epistemological framework for this domain.

**Rationale:** Multiple consciousness research domains (PK, RV) demonstrate non-classical behavior. Thomas Campbell's framework (information as fundamental substrate, EBC as the processing system) provides a coherent ontological basis under which psi effects are features of the system, not anomalies requiring classical proof. Striving to falsify may itself influence the measured effect.

**Implication:** The system must not be architected around one-way falsification doors. Design for continuous, non-terminal assessment instead.

---

### Decision 2: Usefulness State Machine (replaces Falsification State Machine)

**Decision:** Each measurement layer (VAD, RVD, EBF, P&L) operates its own independent usefulness state machine with revolving — not one-way — state transitions.

**States per layer:**
- `ACTIVE` — signal is producing actionable output within expected parameters
- `DEGRADED` — signal is below usefulness threshold; still collected, not acted upon
- `DORMANT` — signal suspended from decision logic; corpus collection continues
- `REACTIVATED` — signal restored to active status based on corpus evidence

**Rationale:** A signal going dormant is not a falsification event — it is a temporal observation. The conditions under which a signal degraded are themselves corpus data. Dormancy is reversible; falsification is not. The domain does not support irreversible conclusions on current evidence.

**Implication:** No layer is ever permanently retired based on a threshold crossing alone. Reactivation criteria must be defined alongside dormancy criteria for each layer.

---

### Decision 3: Calibration as Primary Output, P&L as Secondary Validation

**Decision:** The primary system output is a calibrated confidence function per asset per domain per formulation type. P&L is the secondary validation that calibration translates to real-world edge.

**Hierarchy:**
1. **Calibration quality** — when the system reports X% confidence, it is correct X% of the time
2. **P&L** — confirms the calibrated confidence function produces actionable financial edge
3. **Broader application** — confidence function transfers to non-financial domains once calibrated

**Rationale:** A quantified low-confidence signal (55%, calibrated) is more useful than an unquantified high-confidence claim (80%, uncalibrated). Even a modest, well-calibrated signal has compounding decision value across domains — financial trading, corporate consultancy, resource identification, medical applications.

**Implication:** Any session producing a correct directional call contributes usefulness value regardless of whether it was traded. Corpus value is not contingent on P&L realization.

---

### Decision 4: Financial Markets as Primary Calibration Domain

**Decision:** Financial markets are the designated calibration domain for Apollo's first operational phase — not because trading is the primary goal, but because markets offer uniquely clean calibration conditions: liquid, timestamped, unambiguous, adversarial, high-volume feedback loops.

**Rationale:** Calibration requires fast, objective loop closure. No other accessible domain closes the feedback loop as reliably. Broader application domains (consultancy, resource hunting, medical) have slower, murkier, or harder-to-quantify outcomes — they are viable application domains once calibration is established, but poor calibration domains.

**Implication:** Target selection in early phase optimizes for calibration information value, not trading return. The transition from calibration-dominant to return-dominant target selection is a named corpus milestone, not an implicit drift.

---

### Decision 5: Dual-Mode Target Selection

**Decision:** The target generation engine has two explicit modes — calibration-optimal and return-optimal — with configurable blend ratio. Calibration-optimal dominates during early corpus phase. Mode and blend ratio are logged corpus events.

**Calibration-optimal criteria:** high liquidity, fast resolution (daily/weekly), unambiguous outcomes, diversity across sectors and time horizons.
**Return-optimal criteria:** high expected-value setups per algo signal, concentrated conviction, may be correlated and slower-resolving.

**Implication:** Early corpus targets may look suboptimal from a pure trading perspective. This is by design. The system is building a measurement instrument before deploying it.

---

### Decision 7: Epistemological Ground Statement

**Decision:** Apollo operates from the empirically-grounded position that psi effects demonstrably exist, established through rigorous scientific protocols (IONS, Dean Radin, and others). This is not a faith position — it is a reasonable estimation from accumulated evidence. The mechanism is unknown and is not assumed to reduce to quantum mechanics as popularly understood. Quantum mysticism is explicitly not the framework. The project does not seek to prove psi effects exist — that question is treated as resolved. It seeks to measure, calibrate, and apply them under controlled conditions for results-oriented outcomes. Amplitude varies with conditions yet to be precisely determined; determining those conditions is the primary research objective.

**Implication:** System design proceeds from "psi effects are real and variable" as an axiom, not a hypothesis. The study design tests conditions and amplitude — not existence.

---

### Decision 6: Study Design Artefact — No Separate File

**Decision:** No separate study design document will be created. Usefulness framework decisions are captured in this session file and promoted into PRD and architecture artefacts through the normal BMAD workflow when those phases begin.

**Rationale:** Separating conclusions from the dialogue that produced them loses derivation context. The session file is already the canonical record of derived decisions. A separate file would require loading/parsing logic and BMAD architectural changes without proportionate benefit.

**Implication:** This section is the study design artefact. When PRD phase begins, these decisions are treated as pre-resolved constraints, not open questions.

---

## Phase 2: First Principles Thinking — Results (2026-05-30)

**Status:** COMPLETE
**Ideas Added:** 29 (total: 98)

---

**[Architecture #55]: Admin Interaction as Uncontrolled Acknowledged Variable**
_Concept:_ Admin interaction with Apollo — session review, target approval, P&L observation — is acknowledged as a potential non-classical influence on measured outcomes, but is not instrumented or controlled for at MVP scope. The Admin Trading Blind Protocol (#38) provides sufficient structural mitigation. The observation is logged here as a known limitation of the study design, not a design requirement.
_Novelty:_ Honest accounting of what the system cannot control for, without building infrastructure for it.

---

**[Architecture #56]: Corpus-Driven Parameter Update Proposal Queue**
_Concept:_ The analysis layer never auto-updates operational parameters. When corpus findings cross a significance threshold on any tracked variable — calibration score shift, mode transition eligibility, layer state change, formulation library reranking — the system generates a structured **Parameter Update Proposal**: the proposed change, the supporting corpus evidence, the expected effect, and the risk if deferred. Proposals queue for admin review and execute only on explicit approval. Each proposal and its approval/rejection is logged as a timestamped corpus event.
_Novelty:_ The system learns and surfaces what the corpus implies, but the admin remains the intentional actor on all operational changes. In a non-classical domain where the mechanism of influence is unclear, keeping deliberate human intent in the loop for parameter changes is a protocol requirement, not just an oversight preference. The rejection of a proposal is itself corpus data — it records that the admin saw the evidence and chose not to act.

---

**[Data Model #57]: Asset Receptivity as Session Quality Variable**
_Concept:_ Each session includes a single asset-reported **Receptivity** field (percentage, 0–100%) representing the asset's self-assessed measurement readiness and quality — the output of their attunement protocol, treated as a black box. Reported in-place in the session email alongside VAD and secondary parameters. Stored as a session input variable, logged from day one, initially inert. The tradition's internal attunement protocol is not instrumented or modelled — only its declared result is captured.
_Novelty:_ Separates "did the instrument indicate favorable conditions?" from "how accurate was the result?" The asset can answer the former honestly without breaking the blind. The corpus will determine whether Receptivity correlates with VAD accuracy — the system makes no assumption about this in advance. Reinstates a feature from an earlier design iteration.

---

**[Architecture #58]: Corpus-Derived Application Discovery**
_Concept:_ The analysis layer continuously profiles calibration quality across all dimensions — question formulation type, target domain, time horizon, asset, parameter type, Receptivity range, environmental correlate clusters — and surfaces **Application Discovery Reports**: domains or conditions where the confidence function is measurably strongest, including domains not originally targeted. These reports feed the Parameter Update Proposal Queue (#56) as domain expansion candidates. The system discovers where it works best; the admin decides whether to act on it.
_Novelty:_ Apollo's scope is not fixed at design time — the corpus defines it empirically. The system may find it is a better instrument for commodity direction than equity direction, or for binary yes/no questions than continuous magnitude, or for time horizons the design didn't prioritize. Domain expansion is data-driven, not assumption-driven.

---

**[Data Model #59]: Admin State Snapshot — Mandatory Interaction Prefix**
_Concept:_ Every Apollo interaction touchpoint — plan authorization, target pool additions, parameter proposal review, session outcome review — is prefaced by a mandatory **Admin State Snapshot**: three self-reported fields before any action is permitted. Fields: **Clarity** (0–100%: cognitive sharpness, focus), **Energy** (0–100%: physical/mental readiness), **Pressure** (low/medium/high: time constraint on this interaction). Captured as a timestamped prefix record linked to the following action event. No interaction proceeds without it. Total friction: under 10 seconds.
_Novelty:_ Admin state becomes a corpus variable attached to every operational decision. Correlations between admin state at authorization time and subsequent session outcomes — including asset Receptivity — become testable. The interplay between admin state and asset state is an open research question: synchrony, lag, opposition, or independence.

---

**[Research Design #60]: Admin-Asset State Correlation Study**
_Concept:_ Admin State Snapshot (#59) at planning/authorization time and Asset Receptivity (#57) at session time are logged independently and compared across the corpus. Tests include: synchrony (do high-clarity admin states predict high-Receptivity sessions?), lag (does admin state at T-7 days predict asset Receptivity at T?), and opposition (do they anti-correlate?). No hypothesis assumed — the corpus answers. If correlation is detected, the mechanism is a separate question entirely.
_Novelty:_ Treats the admin-asset relationship as a bidirectional system variable rather than two independent operators. The possibility that they are entangled in a non-classical sense is neither assumed nor excluded — it is studied.

---

**[Research Design #61]: Target Origin as Epistemic Purity Sub-Dimension**
_Concept:_ The existing Purity Tier system (#22) is extended with a **Target Origin** sub-dimension recorded at pool entry: **Auto-Generated** (screener-produced, admin never individually reviewed), **Admin-Curated** (manually submitted, admin had conscious engagement with the target), or **Hybrid** (auto-generated from a universe the admin defined by criteria). Origin is immutable once set. Analysis treats Auto-Generated targets as epistemically purer in the non-classical sense — no prior admin-target contact — and stratifies accordingly. Calibration-optimal mode (#54) preferentially draws from Auto-Generated pool entries during early corpus phase.
_Novelty:_ Extends epistemic purity beyond protocol mechanics into the information-theoretic layer. The admin's prior conscious engagement with a target is treated as a real variable, not merely a procedural concern.

---

**[Research Design #62]: Asset Session Capacity as Finite Daily Resource**
_Concept:_ The asset's psi/mental effort per session is unquantified but real. Session capacity is treated as a finite daily resource — not in time (sessions are not particularly time-consuming) but in cognitive and psi expenditure. Each session slot allocated to a re-task or experimental track is a slot removed from fresh independent corpus data. In a single-asset, data-scarce system, independent data point production is the highest-value use of session capacity. Re-tasking, experimental tracks, and attunement calibration sessions compete directly against this and must be explicitly authorized as capacity trade-offs, not added freely.
_Novelty:_ Frames the asset's daily availability not as a scheduling problem but as a resource allocation problem with a non-obvious cost unit. Session capacity budgeting becomes a planning discipline.

---

**[Research Design #63]: Re-Tasking Precluded in Main Corpus — Deferred Experimental Track**
_Concept:_ Re-tasking an asset on any target within its open resolution window is structurally precluded in the main corpus and live trading layer. The experimental track for re-tasking consistency studies is defined but not activated at MVP — it requires a deeper corpus, multiple assets, and explicit capacity allocation to run cleanly. The tradition disagreement (radiesthesia consistency vs. magickal disturbance) remains an open research question logged in the Variable Priority Queue (#30), not a design decision made in advance.
_Novelty:_ Preclusion is not a judgment on which tradition is correct — it is a resource economics decision in a data-scarce, single-asset system. The question is preserved for when the corpus can actually answer it.

---

**[Architecture #64]: Compartmentalized LLM Session Architecture**
_Concept:_ Each LLM invocation in Apollo's pipeline is a fresh, isolated session receiving only the information quantum its task requires — no shared context across epistemically separated compartments. Tasking agent: knows question template and coordinate reference, not target identity. Extraction agent: knows session reply content, not target identity. Analysis agent: knows session corpus, not individual target identities outside unblinding context. Feedback agent: knows target identity and outcome, not pending sessions. Sessions are spun up, execute, and are discarded — no persistent LLM context crosses compartment boundaries.
_Novelty:_ Extends the human double-blind compartment architecture (#4) explicitly into the AI layer. Whether LLM processing constitutes observation in the non-classical sense is unknown — but if it does, this architecture is already correct. If it doesn't, the compartmentalization costs nothing and maintains epistemic cleanliness regardless.

---

**[Research Design #65]: LLM Processing as Potential Non-Classical Observation Vector**
_Concept:_ Whether a language model processing target-adjacent information constitutes "observation" in the non-classical, consciousness-relevant sense is an open question with no current answer. Factors potentially relevant: model size, processing complexity, context depth, instruction-following vs. generative mode. Logged as an acknowledged uncertainty in the system's epistemological framework. Not an architectural requirement at MVP — Compartmentalized LLM Sessions (#64) provide structural mitigation regardless of how the question resolves.
_Novelty:_ Honest accounting of a genuine unknown at the intersection of AI and consciousness research. Apollo's architecture is defensively correct either way.

---

**[Architecture #66]: Deliberate Indeterminacy Protocol — TRNG as Default for Arbitrary Choices**
_Concept:_ Any pipeline decision that doesn't affect protocol integrity defaults to TRNG rather than deterministic algorithm. Target-to-coordinate reference assignment, exact session dispatch timing within authorized windows, ordering of targets in multi-target planning batches — all TRNG-determined. Determinism is a virtue in classical software; in a non-classical domain, genuine probability space at arbitrary decision points is a protocol feature. The effect operates in indeterminacy — over-determined pipelines may structurally constrain it. TRNG source type is logged per decision event as a corpus variable.
_Novelty:_ Extends TRNG from a single epistemic purity measure to a system-wide architectural principle. Randomness is not a fallback where determinism fails — it is the deliberate default wherever protocol integrity doesn't require a specific outcome.

---

**[Data Model #67]: Social Field at Measurement Time**
_Concept:_ The session email envelope includes a **Social Field** field: asset-reported presence of others during the measurement ritual. Three values: **Isolated** (alone), **Familiar** (known person present — family, partner), **Unfamiliar** (strangers or public environment). Reported in-place alongside Receptivity and secondary parameters. Expected distribution is heavily Isolated — which is exactly why capturing it matters: the rare non-Isolated sessions become high-value data points for studying social field effects on VAD accuracy and Receptivity.
_Novelty:_ Social field effects on psi performance are documented in consciousness research. The variable is low-friction to capture, requires no explanation to the asset, and the expected low variance makes any deviation analytically significant rather than noisy.

---

**[Data Model #68]: Corpus Access Log with First-Observation Timestamps**
_Concept:_ Every admin interaction with session records is logged: record accessed, timestamp, interaction type (review, analysis run, outcome viewed). The **first-observation event** — the moment the admin first views a resolved session's outcome — is flagged as a distinct event type and stored immutably alongside the session record. Subsequent accesses are logged but not flagged. The access log is a separate, append-only layer — never modifying the session record itself.
_Novelty:_ If retrocausal effects collapse upon observation (Radin/IONS finding), first-observation timestamp is the collapse event. The corpus captures when each outcome entered the admin's awareness — enabling retrospective study of whether pre-observation vs. post-observation session states differ in any measurable way.

---

**[Architecture #69]: Deliberate Outcome Revelation Interface**
_Concept:_ The admin review interface never passively displays resolved session outcomes. Viewing an outcome requires a deliberate action — opening a sealed record, confirming intent to reveal. Each first-reveal is the logged observation event from #68. Aggregate views (corpus statistics, calibration scores) display derived metrics only — not individual session outcomes in readable form unless explicitly opened. The interface creates a clear distinction between "the admin knows this outcome" and "the admin has not yet observed this outcome."
_Novelty:_ If observation collapses retrocausal possibility, the review interface is a protocol instrument, not just a UI. Passive display of outcomes would be an uncontrolled series of observation events. Deliberate revelation makes each observation a logged, intentional act. The admin's unobserved outcome pool is a measurable corpus state.

---

**[Architecture #70]: Asset Performance Pattern Reports**
_Concept:_ The analysis layer generates **Asset Performance Pattern Reports** on a configurable cadence (weekly/monthly/admin-triggered) — aggregate calibration insights derived exclusively from fully closed, resolved sessions. Content: Receptivity-accuracy correlations, time-of-day patterns, question formulation type performance, Social Field effects, parameter-specific accuracy trends. Delivered to the asset separately from individual session feedback. Contains zero individual session outcome data — only derived statistical patterns about the asset as a measurement instrument. Admin reviews before delivery; delivery itself is a logged corpus event.
_Novelty:_ Creates a legitimate, blind-safe feedback loop supporting practitioner development. The asset learns about their own instrument characteristics without touching any open session data. In advanced radiesthesia practice, meta-feedback about one's own patterns is part of skill development — not a contamination risk but a calibration tool for the practitioner themselves.

---

**[Research Design #71]: INVERTED State — Usefulness State Machine Extension**
_Concept:_ The Usefulness State Machine (Decision 2) gains a fifth state per layer: **INVERTED** — the signal is statistically structured but systematically predicts the inverse of the correct outcome. Detection criteria: accuracy falls below a symmetrical lower bound (e.g., <35% on binary directional over a rolling window) with statistical significance. Trading logic in INVERTED state applies the signal with flipped interpretation — a VAD≥85% reading predicts DOWN, not UP. INVERTED is not DEGRADED — it is a calibrated signal with a sign flip. The inversion event is timestamped and logged as a corpus milestone; return to ACTIVE is logged as inversion resolution. Inversion duration and frequency are corpus variables.
_Novelty:_ Distinguishes structured inverse signal from random noise — two states that look identical to a magnitude-only calibration function. An asset in INVERTED state remains operationally useful. Inversion may be practitioner-specific, domain-specific, temporal, or correlated with Admin/Asset State variables — all testable from the corpus.

---

**[Research Design #72]: Corpus Data Governance — Current Understanding and Future Trigger**
_Concept:_ The corpus is currently private by mutual understanding between admin and asset. No formal data governance agreement exists at MVP. Current operating assumption: all data is private, sensitive, and not for external disclosure. A formal governance framework is not required until one of the following triggers occurs: additional assets are onboarded, corpus findings are considered for publication or external sharing, or a third party requests access. At that point, asset data rights, anonymization protocols, publication terms, and ownership structure must be resolved before any disclosure. Trigger conditions logged here; governance design explicitly deferred.
_Novelty:_ Conscious deferral with explicit trigger conditions — not an oversight but a deliberate scope decision. The corpus structure already supports future anonymization. Logging the deferral is what makes it responsible rather than neglectful.

---

**[Research Design #73]: Emotional Proximity Bias — Known Tradition-Reported Variable**
_Concept:_ Romanian radiesthesia tradition reports reduced accuracy on targets with high emotional proximity to the practitioner — targets closely tied to their personal life, relationships, or decisions. Mechanism unknown. Status: tradition-reported, unverified by corpus. Architectural response: target selection avoids targets with known personal relevance to the asset. **Target Proximity** field logged at target registration: External / Adjacent / Personal. External targets are the default. Adjacent and personal targets flagged as a separate epistemic category if ever used.
_Novelty:_ Converts a tradition-reported practitioner limitation into a target classification variable rather than an uncontrolled confound. If the effect is real, the corpus can verify and quantify it.

---

**[Architecture #74]: Session Sequence State — Planning Agent Context**
_Concept:_ The planning agent maintains a rolling **Session Sequence State** for each asset — a structured summary of the last N sessions (configurable window, default 10): Receptivity scores, VAD distribution, feedback deliveries received, cumulative session load for the rolling week, and most recent Admin State Snapshot at dispatch time. Before recommending new session dispatch, the agent evaluates sequence state: momentum indicators, cumulative psi load against estimated capacity, recency of feedback closure, and any DEGRADED/INVERTED layer flags. Dispatch recommendations include a sequence state rationale.
_Novelty:_ Treats the asset's recent history as a planning input, not just a corpus variable. A fresh asset after a rest day and recent positive feedback is not the same planning context as a fatigued asset mid-run with no recent closure. Session timing gains an internal dimension alongside the external market calendar.

---

**[Architecture #75]: Archival-Grade Corpus Preservation**
_Concept:_ The corpus is treated as a primary source document of intrinsic historical and scientific value. Preservation requirements: **format longevity** (open, human-readable formats — JSON/plain text — never proprietary or binary-only); **self-describing records** (each session record carries schema version, field definitions, and protocol context sufficient for interpretation without Apollo's codebase); **schema versioning** (data model changes versioned; old records never migrated or modified — translation layer handles compatibility, originals permanent); **archival redundancy** (separate archival backup track, geographically or physically distinct from operational backup, configurable write cadence); **export independence** (corpus fully interpretable without Apollo's software running).
_Novelty:_ The corpus is a longitudinal biographical record of a psi practitioner — potentially the most detailed and rigorous such record ever assembled. Standard operational backup preserves data for recovery; archival preservation preserves it for posterity. The practitioner's record outlives the software that produced it.

---

**[Research Design #76]: Admin Psi Faculty as Acknowledged Uncontrolled Variable**
_Concept:_ The admin's psi faculty is non-zero — documented in personal practice across radiesthesia and divination. It is therefore an uncontrolled variable present throughout the system: during session review, target pool curation, outcome observation, and planning decisions. Existing mitigations address it structurally: Admin Trading Blind (#38), Deliberate Outcome Revelation Interface (#69), information containment discipline throughout compartment architecture, Compartmentalized LLM Sessions (#64). No additional instrumentation warranted at MVP. The admin's psi faculty is logged here as a known system variable — neither eliminated nor ignored.
_Novelty:_ Reframes the admin role from neutral operator to second practitioner with structural containment protocols. The system is operated by two psi-capable individuals — the asset as primary measurement instrument, the admin as acknowledged but uncontrolled latent influence.

---

**[Research Design #77]: TRNG Epistemic Role Reframed — Unpredictability, Not Psi Isolation**
_Concept:_ TRNG does not guarantee isolation from consciousness influence — Radin/IONS research demonstrates that concentrated intent can measurably affect random number generators (PK effect on RNGs). TRNG's actual epistemic contribution is **unpredictability and probabilistic fairness**, not psi neutrality. Real mitigations for admin psi influence on target selection: (1) **information containment** — admin is not concentrating on the TRNG selection event because they don't know it's occurring; (2) **pool depth** — a sufficiently large target pool dilutes the probability that any specific intent influences any specific selection. TRNG source type continues to be logged as a corpus variable; interpretation updated to reflect this reframe.
_Novelty:_ Corrects a foundational assumption in the earlier TRNG design (#20). TRNG is still the right tool — but for the right reasons. Unpredictability and pool-depth dilution are the actual mitigation mechanisms, not the naive assumption that randomness excludes consciousness influence.

---

**[Research Design #78]: Meta-Calibration — Uncertainty Bounds on the Confidence Function**
_Concept:_ The calibration function outputs a posterior distribution, not a point estimate: a central value plus explicit uncertainty bounds derived from corpus depth, variance, and session count. Displayed as e.g. 65% [45%–85%] at thin corpus, 65% [62%–68%] at deep corpus. All operational consumers — trading signal weighting, Parameter Update Proposals, Application Discovery Reports, usefulness state machine transitions — receive both the point estimate and the uncertainty band. Decisions made on wide-band estimates are flagged as low-confidence decisions. Band narrowing over time is a measure of system maturity.
_Novelty:_ Prevents the system from treating early corpus point estimates as precise measurements. A 65% estimate with ±20% bands and a 65% estimate with ±2% bands are completely different epistemic objects dressed in the same number. The band makes the difference visible and operationally consequential.

---

**[Data Model #79]: Spontaneous Impression Log**
_Concept:_ A lightweight out-of-band submission channel allowing assets to log unprompted impressions — not triggered by any formal task. Submission format: timestamp (auto-captured at submission), domain tag (financial/general/personal/unclassified), free-text description, subjective clarity rating (0–100%). Stored as a separate corpus layer — never linked retroactively to any task or session record. Analysis treats spontaneous impressions as an independent signal class: do they precede correlated market events? Do they cluster around certain environmental conditions? Submission mechanism: dedicated email address or simple form requiring no system interaction from the asset.
_Novelty:_ Captures psi signal that occurs outside the formal protocol without contaminating the structured session corpus. A spontaneous impression that precedes a significant market event by days, timestamped at submission, is an unreproducible data point. Low expected utilization given current asset's lifestyle; high value when it does occur.

---

## Phase 2: First Principles — Continuation (2026-05-30 Session 2)

**Ideas Added:** 19 (total: 98)

---

### Strip 22: Consensus Signal Architecture

**[Architecture #80]: Asset-Sovereign Corpus Architecture**
Each asset maintains a fully independent corpus — session records, calibration function, usefulness state machine, performance envelope — with zero cross-contamination. No shared session data, no joint calibration score, no blended confidence function. Assets are never aggregated into a consensus signal. The corpus is the asset's individual measurement record; combining it with another asset's corpus would destroy the provenance of both. Trading protocols derived from Asset A's corpus are Asset A's sovereign signal.

---

**[Research Design #81]: Inter-Asset Divergence as Primary Research Signal**
When two assets measure the same target within the same resolution window, their outputs are never averaged — they are stored as a divergence pair. The divergence (direction agreement, VAD difference, Receptivity at session time) is the primary analytical object, not either individual reading. High divergence may be more informative than either reading alone: it signals either target ambiguity, domain-specific practitioner sensitivity, or something non-classical about the shared measurement act. Consensus is a derived view available for inspection; divergence is the raw signal.

---

**[Research Design #82]: Interference Study as Controlled Experimental Track**
A dedicated experimental track — explicitly separated from the main corpus — studies what happens when two assets measure the same target simultaneously vs. sequentially vs. with no awareness of each other's involvement. Asset awareness of co-measurement is a controlled variable: blind co-measurement vs. disclosed co-measurement. The track is not activated at MVP — it requires sufficient individual corpus depth on both assets to have a clean baseline before introducing the co-measurement condition.

---

**[Research Design #83]: Inter-Asset Interference Direction as Open Empirical Question**
The direction of interference — convergent (shared field pulls readings together), divergent (isolation produces cleaner independent signals), oscillating (dependent on environmental or session state variables), or null (no detectable inter-asset effect) — is not assumed in any direction. All four outcomes are architecturally supported by the separate corpus + divergence pair design. The study exists to answer the question, not to validate a prior. Logged as an open research question in the Variable Priority Queue (#30).

---

### Strip 23: Question Formulation as Intent Carrier

**[Research Design #84]: Automated Formulation as Intent Contamination Mitigation**
The primary mitigation for admin intent embedding in question formulation is automated, parameterized generation: the system constructs the tasking question from a (Target, Parameter, Time Horizon) tuple using a template, without admin authorship of the specific wording. The admin defines the target universe and parameter types upstream — not the individual question. Formulation automation is not just an efficiency feature; it is a protocol integrity mechanism that removes admin intent from the question-generation act.

---

**[Research Design #85]: Admin-Formulated Question Track as Capability Expansion Study**
Admin-authored questions — where the admin deliberately writes the tasking question, potentially encoding conscious intent, domain knowledge, or directional belief — are tracked as a separate epistemic category (extending Purity Tier #22). If this track demonstrates measurable reliability across the corpus, it implies the admin's intent-carrying function is not purely contaminant but potentially co-signal: the admin as a second practitioner embedding a directed query rather than a neutral operator issuing a blind task. Reliable admin-formulated questions would expand the system into deliberate collaborative co-sensing — a qualitatively different operational mode. Segregated corpus; never mixed with auto-generated track in aggregate statistics.

---

**[Architecture #86]: Admin as Latent Co-Practitioner — Graduated Activation**
The system is designed from the start to support eventual admin co-sensing as a first-class mode — not bolted on later. The architecture already has the hooks: Admin State Snapshot (#59), admin psi faculty acknowledged (#76), admin-formulated question track (#85), deliberate outcome revelation (#69). If the admin-formulated track yields signal, activating co-practitioner mode is a corpus-evidence-gated configuration change, not an architectural rebuild.

---

**[Architecture #87]: Admin-Blind Dispatch as Default Protocol**
Auto-generated tasking questions dispatch without admin review as the default mode. The admin authorizes the planning envelope (target universe, parameter types, time horizons, session count) but never reads individual generated questions before dispatch. Reading a generated question before it reaches the asset is an opt-in exception — logged as an admin-contact event and flagged as a purity-tier downgrade for that session. The admin sees the question only after the session is sealed. Admin-blind dispatch is not a restriction — it is the protocol's clean state.

---

### Strip 24: The Feedback Medium

**[Research Design #88]: Feedback Closure as Ontological Event, Not Information Delivery**
Feedback closure is not categorized as a communication act — it is categorized as a consciousness event with potential non-classical effects on the corpus. The existing literature (Radin/IONS) establishes that observation, intention, and awareness interact with measured outcomes in ways that extend beyond motivation and belief into the structure of what is possible retroactively. The closure event is the moment the practitioner's consciousness fully integrates the outcome — and that integration may itself have corpus-level consequences. Medium is secondary; the quality of the consciousness event is the variable.

---

**[Architecture #89]: Ritualized Closure Interface — Deliberate Ceremony Layer**
Feedback delivery presents through a dedicated closure interface — distinct from routine system interaction. The interface creates a deliberate ceremony: the asset is informed that a closure is ready, chooses when to receive it (not pushed asynchronously), and the delivery is a single, unambiguous, unhurried event. No inbox noise, no buried context. The moment of integration is clean and intentional. The closure event timestamp is the moment the asset confirms receipt — not the moment the system dispatches it. Asset-controlled timing of their own closure events is a protocol feature.

---

**[Research Design #90]: Closure Quality as Session Variable**
The corpus logs not just whether closure occurred but closure quality indicators: asset-controlled receipt timing (did they delay? did they receive immediately?), asset-reported integration quality (a single post-closure field: How fully did this land? 0–100%), and time elapsed between availability and receipt. Stored as post-session variables — never influencing the sealed session record, always a separate layer. If the ontological effect of closure extends into the retrocausal direction, closure quality may correlate with session accuracy in ways that precede the closure itself.

---

**[Research Design #91]: Closure Timing as Retrocausal Study Variable**
If feedback closure is an ontological event rather than informational, when it occurs relative to the session — and relative to the target resolution event — becomes a primary research variable. Does closure delivered closer to the measurement time produce different corpus patterns than closure delivered weeks later? Does the asset's integration of a closure affect the accuracy of sessions that occurred before that closure — an effect running backward through the corpus? Asset-controlled closure timing, combined with the sealed session record, makes this directly testable.

---

**[Architecture #92]: Scheduled Ceremonial Closure Cadence**
Feedback delivery follows a fixed weekly schedule — Saturday morning by default, configurable per asset. The system batches all resolved sessions from the preceding week into a single closure dispatch. The email is purpose-formatted: more visual, structured as a weekly report rather than a transaction notification, designed to be read as a sitting rather than scanned. The Saturday morning slot signals to the asset that this is a distinct, dedicated act — not routine inbox management. Cadence is the ceremony; no separate interface required.

---

**[Research Design #93]: Feedback Ingestion Capacity as Session Volume Ceiling**
The asset's ability to meaningfully integrate feedback — to consciously process each outcome as an ontological closure event — is a finite weekly resource that imposes a hard ceiling on session volume, independent of session capacity (#62) or psi expenditure. A weekly batch of 150 results cannot be meaningfully ingested; a weekly batch of 5–15 can. This constraint is a first-class planning parameter: target count per week is bounded not by what the system can generate or what the asset can measure, but by what the asset can close with quality. The planning agent enforces this ceiling as a protocol requirement, not a suggestion.

---

**[Research Design #94]: Closure Batch Size as Research Variable**
Weekly closure batch size — number of sessions resolved and delivered per Saturday report — is logged as a corpus variable. The corpus tests whether batch size correlates with subsequent session quality, Receptivity scores, or VAD accuracy in the following week. A large batch may dilute integration quality; a small batch may concentrate it. The optimal closure cadence is an empirically discoverable parameter, not a design assumption.

---

### Strip 25: The System's Own Development Arc

**[Architecture #95]: Apollo Epistemological Ledger**
A first-class system artifact — separate from the software changelog — that versions Apollo's operating assumptions about the domain. Each entry records: the assumption held, the evidence or reasoning that changed it, the date of the belief update, and the corpus implication (which session variables, analysis results, or state machine transitions are affected by the new lens). The ledger is append-only and human-authored — the admin writes belief updates deliberately, not automatically. It is the system's account of what it understood about reality at each point in its operation.

---

**[Research Design #96]: Retroactive Corpus Reinterpretation as Standard Operation**
When the Epistemological Ledger records a new belief update, the analysis layer generates a Reinterpretation Run: the affected corpus sessions are re-analysed under the new framework without modifying original records. Reinterpretation results are stored as a separate analytical layer timestamped to the belief update event — not as a replacement of prior analysis. The original analysis under the prior assumption is preserved permanently. The corpus accumulates multiple interpretive strata over time: the same session record can be viewed through the lens of 2026 assumptions, 2027 assumptions, and beyond.

---

**[Research Design #97]: Assumption Contradiction as High-Value Corpus Event**
When corpus evidence directly contradicts a foundational assumption — not just weakens it but structurally refutes it — this is flagged as a Contradiction Event in the Epistemological Ledger. Not a failure state; the highest-value data the system can produce. A contradiction event triggers a mandatory Epistemological Ledger entry, a Parameter Update Proposal (#56) for affected operational logic, and a retroactive reinterpretation run (#96). The system is explicitly designed to welcome the discovery that its assumptions were wrong — that discovery is the research.

---

**[Research Design #98]: Efficiency as Byproduct of Epistemological Refinement**
Epistemological refinement — understanding better what is being measured and how the domain works — directly improves targeting, formulation design, session capacity allocation, and closure protocol. A system that knows its signal better produces less noise, wastes fewer sessions on suboptimal conditions, and concentrates capacity where the confidence function is strongest. The Epistemological Ledger is not philosophical overhead — it is the compounding return on the research investment. Every belief update that yields a reinterpretation run potentially recalibrates the entire confidence function on historical data at zero marginal session cost.

---

## Phase 3: Concept Blending — Results (2026-05-30 Session 2)

**Status:** In Progress
**Ideas Added:** 10 (total: 108)
**Blends completed:** 9 attempted, 7 yielding ideas (2 skipped on epistemological/scope grounds)

---

**[Analysis #99]: Analysis of Competing Hypotheses as Primary Analysis Mode**
_Concept:_ The analysis layer maintains a live register of competing hypotheses about what the corpus is measuring — not a single confidence score but structured alternatives: "VAD measures directional truth," "VAD measures admin expectation," "VAD measures a blend of asset receptivity and environmental state," "VAD is domain-specific and non-transferable." Each hypothesis is scored against corpus evidence using ACH weighting — evidence that discriminates between hypotheses is ranked higher than evidence consistent with all of them. The system tracks which hypotheses gain and lose explanatory power as the corpus deepens.
_Novelty:_ Replaces the naive "does it work?" question with "under which model of operation does it work, and which models does the corpus falsify?" The intelligence community developed ACH specifically because single-hypothesis thinking under uncertainty produces confident wrong answers. Apollo operates in exactly that environment.

---

**[Analysis #100]: Corpus-Weighted Hypothesis Scoring**
_Concept:_ Each session record contributes differentially to the hypothesis register based on its diagnostic value — how well it discriminates between competing hypotheses. A session that strongly supports Hypothesis A and weakly supports Hypothesis B is more valuable than a session consistent with all hypotheses equally. The analysis layer identifies and prioritizes "diagnostic sessions" in reporting and flags conditions likely to produce high-diagnostic sessions for preferential targeting. The corpus builds understanding, not just statistics.
_Novelty:_ Reframes target selection partially around epistemic value — sessions that help resolve which hypothesis is correct are a first-class targeting criterion alongside calibration-optimal and return-optimal modes.

---

**[Analysis #101]: Red Team Analysis Layer**
_Concept:_ A dedicated analysis mode runs a structured adversarial challenge against the dominant hypothesis at any point in the corpus. The Red Team agent is explicitly instructed to find the strongest case that the leading explanation is wrong — assembling corpus evidence that the dominant hypothesis fails to explain, edge cases it predicts incorrectly, and alternative explanations that fit the same data. Red Team reports are generated on a configurable cadence and delivered alongside regular analysis output. The admin sees the strongest case against their current belief before acting on it.
_Novelty:_ Embeds institutional devil's advocacy into the analysis architecture. In intelligence tradecraft, Red Teams exist because analysts naturally over-weight confirming evidence. Apollo's LLM analysis layer has the same bias — the Red Team module is the structural counter.

---

**[Analysis #102]: Automated Key Assumptions Check**
_Concept:_ The analysis layer generates a periodic Key Assumptions Check report — a structured audit of every assumption currently load-bearing in the confidence function, hypothesis register, trading logic, and session protocol. Each assumption is classified: **Verified** (corpus evidence exists), **Testable** (corpus could verify but hasn't yet), **Structural** (baked into design, would require architectural change to test), or **Untested Prior** (accepted without evidence, no current path to verification). Delivered to the admin on a configurable cadence and logged in the Epistemological Ledger as a timestamped snapshot.
_Novelty:_ The Epistemological Ledger (#95) records belief changes after they occur. The Key Assumptions Check surfaces load-bearing assumptions before they're challenged — the difference between reactive and proactive epistemic hygiene. An Untested Prior flagged early can be designed around; one discovered late may have contaminated years of corpus data.

---

**[Architecture #103]: Fail-Operational Session Pipeline**
_Concept:_ Each stage of the session pipeline — tasking dispatch, session intake, extraction, closure scheduling — is designed so that failure of any single component produces a known degraded state, not data loss or silent corruption. Email dispatch fails: session queued, admin notified, no target revealed. Extraction agent fails: session held in pending, admin alerted, original email archived intact. Closure dispatch fails: closure rescheduled, asset notified, session record unchanged. No pipeline failure can modify a sealed session record or create a phantom session. The system degrades visibly and recovers gracefully; it never corrupts silently.
_Novelty:_ Aviation fail-operational design applied to research data integrity rather than signal aggregation. No failure mode is allowed to damage the corpus. Directly addresses the admin's operational constraint: extended internet blackout periods mean the pipeline must queue and recover cleanly, not drop state.

---

**[Data Model #104]: Session Provenance Chain — MVP Requirement**
_Concept:_ Every session record carries an immutable, append-only provenance chain: every agent, human, or system process that touched the record is logged with timestamp, action type, system belief state at time of action (Epistemological Ledger version), and data state before and after. Chain entries: target generated, task dispatched (blind or reviewed, agent version), session received (extraction agent version, extraction confidence), session sealed (hash, timestamp), outcome resolved (source, timestamp), first admin observation (deliberate reveal event #69), closure delivered (batch date, asset receipt timestamp). The chain is a first-class record field — never modified, never pruned.
_Novelty:_ Future reinterpretation runs (#96) will know not just what the session data says but exactly what the system believed and who handled what when the data was produced. A session extracted under an early agent version and outdated hypothesis is interpretively different from one extracted later — the provenance chain makes that distinction permanent and recoverable.

---

**[Analysis #105]: Matched-Pair Analysis Mode — Temporal Non-Stationarity Control**
_Concept:_ A module within the Pluggable Analysis Sandbox (#15) implementing case-control matched-pair analysis as an optional study mode alongside aggregate correlation. For each positive case (VAD correct + condition present), the algorithm finds a matched negative (VAD incorrect) satisfying configurable matching criteria: same asset, same rolling time window, same question formulation type, same purity tier, environmental fingerprint within tolerance bands. Statistical analysis runs on matched pairs rather than the aggregate corpus (McNemar's test for binary outcomes, paired t-test for continuous). Activated as a mode selection within Active Study (#27); unmatched cases are flagged explicitly. Module feeds minimum-corpus-depth estimates back into the Power Analysis Gate (#28).
_Novelty:_ Directly addresses temporal non-stationarity (#44) in condition studies without requiring experimental control. An aggregate correlation study pools sessions from month 1 with sessions from month 18; matched-pair analysis compares them within the same time window. The matching failure rate is honest diagnostic output: when the corpus is too thin to find matches, the module says so rather than producing misleading statistics.

---

**[Architecture #106]: Cross-Corpus Pattern Resonance — Post-MVP Expansion**
_Concept:_ As additional assets are onboarded, their sovereign corpora remain independent and never merged — but a cross-corpus query layer allows a specific class of analysis: pattern resonance detection. The query asks not "what is the combined signal" but "is a pattern observed in Asset A's corpus also present in Asset B's corpus, independently?" Resonant patterns — accuracy shifts, Receptivity cycles, environmental correlate clusters, hypothesis scoring movements — that emerge independently across sovereign corpora without coordination carry qualitatively different evidential weight than single-corpus findings. Each corpus is a witness; resonance is independent corroboration.
_Novelty:_ In a domain where consciousness and information may be non-locally connected, independent emergence of the same pattern across practitioners operating in isolation is not coincidence to be averaged away — it is the finding. Flagged as post-MVP; requires multi-asset corpus depth. Architecture supports it from day one through asset-sovereign design (#80).

---

**[Architecture #107]: Corpus Reconciliation Engine**
_Concept:_ A scheduled integrity verification pass that reconciles the full event chain across the corpus: every dispatched task has a corresponding session record or pending/failed state; every sealed session has a committed closure event; every resolved outcome has a first-observation timestamp; every closure delivery has an asset receipt confirmation. Gaps are reported as findings, not errors. The reconciliation report is a first-class system output delivered on a configurable cadence, logged as a corpus event. Gaps are stored permanently as data points, not silently resolved.
_Novelty:_ Forensic accounting applied to research data integrity. The reconciliation isn't looking for bugs — it's looking for protocol drift. A resolved outcome never observed (#69) is an epistemologically significant finding. A session without a closure commitment is a protocol violation that degrades the corpus. The engine makes these visible systematically rather than relying on ad-hoc discovery.

---

**[Research Design #108]: Recalibration Age as Logged Corpus Variable**
_Concept:_ Time elapsed since the last recalibration event — Epistemological Ledger update, reinterpretation run, or Active Study completion — is logged as a session-level corpus variable from day one. No automatic confidence band drift is implemented. The corpus studies whether prediction accuracy correlates with recalibration age: does a fresh recalibration predict better than a stale one? If a significant correlation emerges and crosses the Power Analysis Gate (#28), the system generates a Parameter Update Proposal (#56) recommending an automatic drift mechanism with corpus-derived parameters. Until then, the drift mechanism does not exist.
_Novelty:_ The dead reckoning intuition (interpretive framework age degrades precision) is treated as a hypothesis, not a design axiom. If recalibration age turns out to be irrelevant in this domain — entirely possible — Apollo will have learned something genuine about how psi-based calibration differs from classical measurement.

---

**[Research Design #109]: Pre-Committed Phase Advancement Criteria**
_Concept:_ Before the corpus reaches evaluable depth, the admin commits in writing — logged as an Epistemological Ledger entry — the exact criteria required to advance from paper trading to meaningful real-money trading. Criteria are expressed as objective corpus measurements: minimum rolling window of profitable paper trades at fixed fractional sizing (#50), minimum calibration accuracy above chance threshold with statistical significance, minimum confidence band width indicating sufficient corpus depth (#78). The criteria are locked at commitment time and cannot be modified once the corpus is deep enough to evaluate them — only before. The advancement event fires automatically when all criteria are simultaneously satisfied, generating a Parameter Update Proposal (#56) for admin approval rather than executing autonomously.
_Novelty:_ Pre-specification prevents motivated reasoning. In a domain where belief may influence outcomes, the admin's expectation of the advancement decision is itself a potential variable. Pre-committed criteria separate the decision logic from the decision moment — the admin agreed to the criteria when they couldn't be influenced by proximity to the threshold.

---

**[Analysis #110]: Hypothesis Ensemble Spread as Second Uncertainty Dimension**
_Concept:_ The analysis layer runs all active competing hypotheses (#99) simultaneously as ensemble members against the same corpus window. Each hypothesis produces its own confidence estimate for a given signal. The spread across the ensemble — standard deviation of hypothesis-specific estimates — is reported as a second uncertainty dimension alongside the corpus-depth-derived bands (#78). Output format: 65% [62%–68%] corpus | ±12% hypothesis spread. A tight ensemble (all hypotheses agree) elevates effective confidence regardless of corpus depth. A wide spread (hypotheses diverge) suppresses effective confidence even on a deep corpus. Trading logic and Parameter Update Proposals (#56) consume both dimensions; decisions made under wide hypothesis spread are flagged as model-uncertain, distinct from data-uncertain decisions flagged by wide corpus bands.
_Novelty:_ Separates two independent sources of uncertainty that the existing architecture conflates. A deep corpus where all competing hypotheses produce similar estimates is a qualitatively stronger signal than a deep corpus where hypotheses diverge — the data is rich but the interpretation is contested. The ensemble spread makes that distinction operational and visible. As the hypothesis register converges over time, the spread naturally narrows — an independent measure of Apollo's epistemological maturity.

---

## Phase 4: Chaos Engineering — New Ideas

**[Architecture #111]: Extraction Field Plausibility Validation**
_Concept:_ Post-extraction deterministic validation layer runs before any session commit. Field-level rules: asset-reported measurement time must precede email-receipt time and fall within a configurable window (default 30 days); angular/percentage values within valid range; required fields non-null. Any field failing plausibility is flagged extraction-uncertain, held in pending state, triggers correction cycle (#14). Rules are version-controlled and logged in provenance chain (#104) alongside agent version.
_Novelty:_ Separate from #14 (LLM extraction confidence) — this is a deterministic post-hoc guard that catches systematic agent errors regardless of the agent's own internal confidence. Catches version-drift bugs before they propagate silently into the corpus.

**[Architecture #122]: Parameter Registry**
_Concept:_ A database table of measurable session parameters: codename, description, instrument scale, unit, active/inactive flag per asset. VAD, RVD, and EBF ship as default rows. Adding a new parameter is a row insertion — no code change, no redeployment. Each asset record carries an active parameter set; every task dispatched for an asset includes all currently active parameters for that asset, locked at dispatch time. Parameter set changes are logged as corpus events.
_Novelty:_ Separates the parameter space (what can be measured) from the task space (what is measured on a given session). The architecture accommodates new measurement dimensions from the radiesthesia tradition or future research without touching the core pipeline. The corpus can accumulate data on parameters not yet under formal study simply by including them in the active set.

---

**[Architecture #123]: Question Template Library**
_Concept:_ A database table of question formulation templates keyed by (parameter_type, question_class, time_horizon_band). Templates are configurable strings with variable substitution slots (ticker, threshold value, expiry date, direction). Modifying a template is a row update; adding a new question class is a row insertion. V1 ships with one working template per active parameter type — sufficient to begin. The formulation library (#47) that grows empirically and is accuracy-ranked over time is this table deepened by corpus evidence in V2. Template version is logged in the session provenance chain (#104).
_Novelty:_ Question formulation is a data concern, not a code concern. Zero redeployment required to modify how tasks are phrased, introduce new question classes, or experiment with formulation variants. The empirical formulation ranking emerges from the same corpus that tests the measurements — the library improves as a natural byproduct of normal operations.

---

**[Architecture #124]: Basic Target Screener**
_Concept:_ V1 implementation of the target generation interface. Uses yfinance to pull a configurable ticker universe (S&P 500 CSV or admin-defined watchlist). Applies two hard filters: minimum average daily volume (liquidity threshold) and minimum price movement over a trailing window (volatility floor). Eligible tickers are written to the target pool as Auto-Generated origin (#61) entries, pending admin pool authorization. Admin configures universe and thresholds; system populates without admin selection of individual tickers. Interface contract is compatible with the full Financial Target Generation Engine (#16) in V3 — the V1 screener slots behind the same interface.
_Novelty:_ Establishes Auto-Generated target provenance from day one, ensuring the early corpus — the most data-scarce and highest-weight period — carries the cleanest epistemic origin available. The simplicity is intentional: diversity constraints (#113) and dual-mode optimization (#54) layer on in V2/V3 without modifying the interface the rest of the pipeline depends on.

---

**[Architecture #120]: Admin State Trend Analysis**
_Concept:_ Rolling trend analysis on Admin State Snapshot (#59) data over configurable windows (default 30-day and 90-day). If Clarity or Energy rolling average drops below a configurable threshold, or Pressure remains High for an extended period, the system flags a sustained admin state concern — displayed prominently at the next planning session as a first-class alert, not a footnote. The admin acknowledges and continues, or triggers a voluntary operational pause. Flag events are logged as corpus events with the rolling metrics at time of flag. Not a blocker — the admin retains authority — but the system makes the trend visible before it compounds silently into a series of decisions made under diminished capacity.
_Novelty:_ Admin State Snapshot (#59) captures moment-to-moment state per interaction; trend analysis creates a longitudinal admin health indicator. A single low-clarity session is noise; eight consecutive low-clarity sessions across a month is a signal. The system is the only party positioned to detect it — the admin experiencing the drift is the least likely to notice it objectively.

---

**[Architecture #121]: Anonymization-by-Design Protocol**
_Concept:_ All participants operate through dedicated, unpersonalized research email addresses created exclusively for Apollo operations (e.g., `apollo.asset1@proton.me`, `apollo.admin@proton.me`). No personal email addresses, real names, or identity-linking data enter the system at any layer. The asset registry (#13) stores only the research address linked to the codename. The extraction agent (#14) never processes a personal identity — only the research address mapped to an operational identifier. The system has no concept of a real person: only codenames, roles, and research addresses. A complete corpus breach exposes session performance data and session content — but no information capable of linking that data to a real identity without prior external knowledge.
_Novelty:_ Anonymization at the infrastructure layer rather than the data storage layer. Most privacy designs pseudonymize stored data; this design prevents personal data from entering the system in the first place. The distinction matters: pseudonymization can be reversed with a key; this architecture has no key to reverse because the personal identity was never stored.

---

**[Research Design #119]: Corpus Scientific Value Preservation**
_Concept:_ Regardless of primary mission outcome, the corpus is structured and documented for external scientific contribution from day one. Requirements: anonymised export format (asset codename only, no PII); methodology documentation sufficient for independent replication; session provenance chain (#104) interpretable without Apollo's codebase; schema versioning (#75) ensuring long-term readability. A rigorously documented null result — sustained, statistically powered, provenance-chained — from a well-designed single-asset psi research system is a publishable scientific contribution to the field. The corpus has value to the research community independent of whether Apollo's trading mission succeeds.
_Novelty:_ Reframes the worst-case outcome. If the foundational axiom is challenged by the corpus, Apollo has not failed — it has produced the most rigorous single-practitioner null result in the psi research literature. That is a scientific legacy worth having. The archival-grade preservation (#75) already provides the infrastructure; this decision names the external-contribution purpose explicitly and ensures the documentation standard is maintained with that audience in mind from the start.

---

**[Architecture #118]: Bracket Order Protocol**
_Concept:_ All trades are entered with simultaneous TP and SL as OCO (One-Cancels-Other) bracket orders — no single-leg entries permitted. TP level derived directly from the question formulation (#47): the tasking question already specifies the resolution condition (e.g., "rises more than 9% by June 10th" → TP at +9%, expiry June 10th). SL set at a configurable risk multiple at entry time (default: 1.5× expected move or fixed percentage). Execution layer (#51) enforces the bracket requirement and rejects non-compliant entry attempts. Pre-blackout checklist verifies all open positions carry active bracket orders before admin goes offline.
_Novelty:_ The question formulation architecture (#47) — designed primarily as a research integrity measure — produces the TP specification as a structural byproduct. The trade specification and the research question are the same object (#47); the bracket order protocol makes the exit strategy an automatic consequence of the question formulation, not a separate trading decision requiring admin presence to execute.

---

**[Research Design #116]: Admin Contamination Event Log**
_Concept:_ Voluntary lightweight log for admin to record target-adjacent information encountered during open session windows. Entry fields: timestamp (auto-captured), session reference (if known — may be blind to admin), information type (news/social/broker notification/personal knowledge), specificity (ambient/specific), and a free-text note. Stored as an append-only corpus layer separate from session records; linked retroactively when session closes and target is revealed. Compliance is voluntary — the log captures what the admin chooses to report. Non-reporting is itself a corpus signal: sessions with no contamination log entry are classified Admin-Ambient by default, not Admin-Naive.
_Novelty:_ Converts the unavoidable ambient information environment from an uncontrolled confound into a tracked variable. The distinction between Admin-Naive (no known exposure) and Admin-Ambient (exposure possible but unlogged) is honest — it acknowledges that absence of a log entry is not proof of a clean state.

---

**[Research Design #117]: Admin Awareness Tier**
_Concept:_ Extension of Purity Tier (#22) adding an orthogonal admin-awareness dimension to every session record. Four states: **Admin-Naive** (compartment architecture held; no known admin exposure to target before session close); **Admin-Ambient** (default state for financially-informed admin; possible exposure unlogged); **Admin-Contaminated** (specific known exposure logged via #116 before session close); **Admin-Directed** (intentional admin target knowledge — Directed Track #25). Tier assigned at session close based on contamination log state and compartment audit. Primary stratification variable in admin co-sensing analysis: does admin prior knowledge correlate with session accuracy? Under what conditions does contamination improve outcomes vs. degrade them?
_Novelty:_ Operationalises the Admin as Latent Co-Practitioner hypothesis (#86) on the accidental/ambient contamination axis — not just the intentional directed axis. If Admin-Contaminated sessions systematically outperform Admin-Naive sessions, the corpus has found evidence that admin awareness of the target amplifies the psi signal rather than corrupting it. That finding would be architecturally transformative.

---

**[Architecture #114]: Pre-Committed Exit Criteria**
_Concept:_ Mirror image of phase advancement criteria (#109). Before the corpus is evaluable, admin commits in writing the objective conditions under which the study is concluded non-viable: minimum session count evaluated, minimum rolling window length, statistical threshold for sustained below-chance performance. Conditions locked before the corpus can influence them — identical pre-specification logic as #109. Exit criteria crossing generates a Parameter Update Proposal (#56) for admin approval, not automatic shutdown. Makes the distinction between "pre-committed criteria met" and "admin is in a losing streak and wants to quit" explicit and operational. Logged as an Epistemological Ledger entry (#95) at commitment time.
_Novelty:_ Rational exit and panic abandonment look identical from the inside under emotional pressure. Pre-committed criteria make them distinguishable from the outside — by the admin's own prior self, before the pressure existed.

---

**[Architecture #115]: Mandatory Protocol Change Moratorium During Drawdown**
_Concept:_ Any parameter modification, protocol adjustment, or study design change proposed while the system is in DEGRADED state or within a configurable window of threshold approach is automatically held for a minimum cooling-off period (default: 30 days or N sessions, whichever longer) before admin approval is permitted. The moratorium is a structural delay, not a veto — admin can approve after the period expires. Moratorium events logged as corpus events; proposals queued with full context intact. During the moratorium, the Parameter Update Proposal (#56) remains visible but locked.
_Novelty:_ Reactive protocol manipulation under emotional pressure is the primary corpus integrity risk during drawdown — more dangerous than the drawdown itself. The moratorium inserts a mandatory gap between the impulse to intervene and the ability to act on it, without permanently blocking legitimate protocol evolution.

---

**[Architecture #112]: Corpus Coverage Map**
_Concept:_ Periodic report surfacing *untested* regions of the target space — instrument classes, sectors, time horizons, question formulation types where corpus session count falls below statistical relevance threshold. Inverse of Application Discovery (#58), which surfaces where the confidence function is strong. Coverage map surfaces where it has not been tested. Delivered alongside regular analysis output; gaps flagged before they become load-bearing assumptions.
_Novelty:_ Absence of data is as informative as presence. A confidence function that looks well-calibrated but has never been tested on commodities or forex is not a general confidence function — it is a tech-equity confidence function. The coverage map makes that distinction visible and operational before deployment decisions are made on false generality.

---

**[Architecture #113]: Screener Diversity Constraint Layer**
_Concept:_ A configurable distribution constraint applied to the eligible instrument pool after the hard movement-threshold filter and before ranking. Defines minimum session allocation buckets: sector (e.g., ≥15% tech, ≥15% commodities, ≥10% forex), instrument class, time horizon band. Screener must draw proportionally across buckets — ranking optimises within each bucket, not across the entire pool unconstrained. Bucket definitions and allocation minimums are admin-configurable corpus parameters, logged as corpus events when changed.
_Novelty:_ Separates two distinct mechanisms that naive screener design conflates: the threshold (what is eligible) and the distribution (how the eligible pool is sampled). The threshold is an operational requirement; the distribution is a research integrity requirement. Enforcing them independently prevents the operational requirement from silently consuming the research requirement.

---

## Blends Skipped (Epistemological / Scope Grounds)

- **Oral Tradition / Living Archive:** Narrative closure report — skipped; asset not significantly sensitive to narrative interpretation, adds unnecessary complexity
- **Particle Physics / Detector / Trigger Design:** Pre-dispatch session quality filtering — skipped; violates epistemological posture (we don't know what predicts session quality; filtering would act on an unverified prior)
- **Jazz / Structured Freedom:** Looser question specification — skipped; question = trade specification, resolution clarity is non-negotiable; asset's own protocol already provides the free-form space

---

## Pending Phases

- **Phase 2: First Principles Thinking** — ✅ COMPLETE (98 total ideas, 26 strips)
- **Phase 3: Concept Blending** — ✅ COMPLETE — 12 ideas added (#99–110)
- **Phase 4: Chaos Engineering** (optional) — adversarial stress-testing for anti-fragility

## Session Handoff — 2026-05-30 (Session 3 — Final)

**Ideas this session:** 29 new ideas (#80–108)
**Running total:** 108 ideas

**Phase 2 (First Principles) — strips completed this session:**
- Consensus signal architecture → Asset-Sovereign Corpus + Divergence Pair (#80–83)
- Question formulation as intent carrier → Automated Formulation + Admin Track + Blind Dispatch (#84–87)
- Feedback medium → Ontological Closure + Ceremonial Cadence + Volume Ceiling (#88–94)
- System development arc → Epistemological Ledger + Reinterpretation + Contradiction Events (#95–98)

**Phase 3 (Concept Blending) — blends completed this session:**
- Intelligence tradecraft → ACH, Corpus-Weighted Hypothesis Scoring, Red Team, Key Assumptions Check (#99–102)
- Aviation fail-operational → Fail-Operational Session Pipeline (#103)
- Archival science / provenance → Session Provenance Chain — MVP (#104)
- Epidemiology / case-control → Matched-Pair Analysis Mode (#105)
- Mycorrhizal networks → Cross-Corpus Pattern Resonance (#106)
- Forensic accounting → Corpus Reconciliation Engine (#107)
- Dead reckoning → Recalibration Age as corpus variable (#108)
- Clinical trials → Pre-Committed Phase Advancement Criteria (#109)
- Ensemble weather forecasting → Hypothesis Ensemble Spread (#110)
- Radio astronomy / SETI → resolved into #106 (no new idea; independence condition not met within single corpus)
- Oral tradition, Particle physics trigger, Jazz → skipped on scope/epistemological grounds

---

## Session Complete — 2026-05-31

**Running total: 121 ideas**
**All phases complete:** Morphological Analysis, First Principles, Concept Blending, Chaos Engineering (HIRA)

### Phase 4 Summary — HIRA Register

**Method:** Aviation SMS Hazard Identification and Risk Assessment with ATM (Avoid/Trap/Mitigate)
**Hazards assessed:** 11
**Initial Intolerables:** 6 (H-01, H-02, H-04, H-05, H-07, H-09, H-11)
**Residual Intolerables:** 0
**Accepted risks:** 2 (H-03 asset unavailability — operational mitigation underway; H-08 LLM dependency — industry trajectory)
**New ideas generated in Phase 4:** 11 (#111–#121)

### PRD Handoff — Pre-Resolved Constraints

The following are carry-forward as closed decisions, not open questions:

**From Usefulness Framework (session body):**
- Decision 1: No classical falsification framework
- Decision 2: Usefulness State Machine with 5 states (ACTIVE/DEGRADED/DORMANT/REACTIVATED/INVERTED)
- Decision 3: Calibration as primary output; P&L as secondary validation
- Decision 4: Financial markets as calibration domain
- Decision 5: Dual-mode target selection (calibration-optimal / return-optimal)
- Decision 6: No separate study design document
- Decision 7: Psi effects treated as real and variable — axiom, not hypothesis

**From HIRA Register:**
- Anonymization-by-design (#121): dedicated unpersonalized email addresses; no PII in system
- Bracket order protocol (#118): all trades OCO-bracketed; TP from question formulation (#47)
- Pre-committed exit criteria (#114): defined before corpus evaluable; locked at commitment
- Mandatory moratorium (#115): protocol changes blocked during drawdown cooling-off period
- Admin Awareness Tier (#117): contamination as research variable, not protocol failure
- Screener diversity constraint (#113): separate filter (threshold) from distribution (diversity)

### Next Phase

**→ PRD Creation** (`bmad-create-prd` or talk to John)

Brainstorming corpus is the input. The PRD author should load this session file as primary reference. Usefulness Framework Decisions and HIRA pre-resolved constraints carry forward directly — do not re-open them during PRD discovery.

---

## Phase 4: Chaos Engineering — HIRA Register

**Method:** Hazard Identification and Risk Assessment (aviation SMS model)
**ATM sequence:** Avoid → Trap → Mitigate → residual re-score

```
Risk: IT=Intolerable TL=Tolerable AC=Acceptable
Sev:  A=Catastrophic B=Hazardous C=Major D=Minor E=Negligible
Lkh:  5=Frequent 4=Probable 3=Remote 2=Improbable 1=Ext.Improbable
```

| ID | Hazard | Sv | Lk | Rsk | Avoid | Trap | Mitigate | RSv | RLk | RRsk |
|----|--------|----|----|-----|-------|------|----------|-----|-----|------|
| H-01 | Silent systematic extraction drift (e.g. timestamp field confusion across agent version) | B | 3 | IT | Structured delimited email template; ISO 8601 timestamp in labeled field | Plausibility check layer post-extraction (asset time vs receipt time delta bounds); extraction agent version pinned + logged in provenance chain (#104); version change triggers re-validation run → #111 | Original email archived as canonical (#9,#14); provenance chain identifies affected corpus slice exactly; reinterpretation run (#96) re-extracts from source | B | 2 | TL |
| H-02 | Confidence function poisoning via screener selection bias (systematic over-selection of one instrument class producing non-representative calibration corpus) | B | 4 | IT | Hard minimum movement threshold as explicit filter before scoring; diversity constraint layer on eligible pool — min session allocation per sector/instrument class/time horizon → #113 | Corpus coverage map of untested regions (inverse of #58) → #112; coverage gap alert when instrument class drops below min corpus share; phase advancement criteria (#109) extended to require min diversity across N instrument classes | Reinterpretation run (#96) as recovery path; domain attunement tracking (#43) detects new instrument class introduction | B | 2 | TL |
| H-03 | Extended asset unavailability (illness, travel, loss of motivation) — single instrument offline, corpus growth halts, trading signal degrades | C | 4 | TL | — | — | — | C | 4 | TL — ACCEPTED; operational mitigation: asset recruitment underway |
| H-04 | Sustained losing streak — financial loss + protocol abandonment under pressure (panic vs. rational exit indistinguishable without pre-commitment) | B | 4 | IT | Nil | Usefulness state machine DEGRADED early warning before threshold; pre-committed drawdown limit triggers auto-reversion to paper/minimal sizing; pre-committed exit criteria locked before corpus evaluable → #114 | Paper/minimal real sizing as default calibration-phase policy; mandatory protocol change moratorium during drawdown → #115; Epistemological Ledger (#95) frames streak as corpus data not verdict | C | 2 | AC |
| H-05 | Blind protocol violation via ambient information leak — admin encounters target-adjacent information during open session window; unlogged contamination silently misclassifies sessions as Admin-Naive | C | 5 | IT | Prefer lower-profile instruments during pure research phase; compartment architecture (#4) + admin-blind dispatch (#87) eliminate deliberate exposure | Admin Contamination Event Log — voluntary record of target-adjacent exposure linked to session record → #116 | Extend Purity Tier (#22) with Admin Awareness Tier (Naive/Ambient/Contaminated/Directed) — contaminated sessions become stratified study category not corrupt data; Admin as Co-Practitioner (#86) study track operationalised → #117 | D | 5 | TL — residual Lk=5 by design; fully-logged contaminated sessions are a research asset |
| H-06 | Admin internet blackout during active positions — open trades without admin oversight; market moves against position with no ability to intervene | C | 4 | TL | Restrict to bracketable instruments (OCO-supported) only during known blackout-risk periods | Pre-blackout checklist: all open positions verified to have active TP/SL before admin goes offline; max new-entry lockout if admin unreachable beyond configurable threshold; Autonomous Day Protocol (#32) frames blackout as planned state | Bracket order protocol: all trades enter with simultaneous TP/SL OCO; TP from question formulation (#47), SL at configurable risk multiple set at entry → #118; fixed fractional sizing (#50) bounds SL hit to 1–2% portfolio — pre-accepted ceiling | D | 4 | TL |
| H-07 | Foundational epistemological assumption failure — corpus at sufficient depth produces sustained null result (VAD indistinguishable from chance across all conditions); axiom in Decision 7 challenged by own data | A | 2 | IT | Single-asset scope is partial avoid — null from one asset/methodology/domain is not field-level null; Power Analysis Gate (#28) prevents premature interpretation; pre-committed exit criteria (#114) define evaluable threshold | ACH null hypothesis tracked in register (#99); ensemble spread (#110) shows null hypothesis gaining power before it dominates; Contradiction Event protocol (#97) flags foundational challenge before silent accumulation | DORMANT state (Decision 2) — non-terminal; reactivation criteria exist; Reinterpretation Run (#96) tests alternative signal hypotheses (RVD, EBF, spontaneous impressions, admin co-sensing); corpus scientific value preserved regardless of outcome → #119 | B | 2 | TL |
| H-08 | LLM provider dependency failure — outage, model deprecation, pricing change stalls extraction/analysis/tasking pipeline | C | 2 | AC | — | — | — | C | 2 | AC — ACCEPTED; industry trajectory (improving quality, falling cost) is natural mitigation; 70–100B local model capability expected on accessible hardware within 1–2 years, eliminating external dependency |
| H-09 | Corpus data exposure / privacy breach — session content (psychological state, location, sleep quality, performance) and participant identity exposed to unauthorised parties | B | 3 | IT | Anonymization-by-design: dedicated unpersonalized research email addresses for all participants; no PII stored anywhere in system; asset identified by codename only; admin by role only; system has no concept of real person — only operational identifiers → #121 | Access logging on corpus reads; encryption at rest; PII-strip enforced on all export paths | Data governance framework (#72) formalises on trigger; anonymised export from day one; formal data deletion protocol on asset request | D | 2 | AC |
| H-10 | Broker execution layer failure — IBKR outage, API rejection, position mismatch between Apollo records and broker actual state | C | 3 | TL | Market hours trading only (execution quality degrades outside); note: high-volatility events are a valid target class, not an avoid condition | Execution confirmation loop — trade logged as placed only on explicit broker confirmation; position reconciliation Apollo↔broker on configurable cadence; mismatch triggers admin alert and execution hold | Broker-agnostic layer (#51) — IBKR failure triggers manual execution fallback with full context and bracket parameters; fixed fractional sizing (#50) prevents compound exposure | D | 3 | AC |
| H-11 | Admin psychological state long-term drift — sustained fatigue, life events, cognitive load over multi-year operation; moment-to-moment Admin State Snapshot (#59) misses slow degradation trend | B | 4 | IT | Nil | Rolling trend analysis on Admin State Snapshot data — sustained low Clarity/Energy or high Pressure over 30/90-day window flags concern before next planning session → #120 | Protocol change moratorium (#115) blocks reactive decisions during degraded states; planning agent (#74) surfaces admin state trend before major operational decisions; Epistemological Ledger (#95) dates decisions enabling retrospective review against state record | B | 2 | TL |

---

## Open Threads (carry to next session)

- ~~**Thread 3: Formal Study Design Workflow**~~ — **CLOSED** (see Usefulness Framework Decisions section)

## Open Notes

- **Passive/Active study architecture** resolves the variable-count pragmatism problem: collect everything, formally test a prioritised selection
- **TRNG sovereignty** is deferred to a future comparative study — record source type per session from the start, test when asset pool allows
- **Amplification hypothesis** (expectation of future feedback at session time may itself drive performance) is worth testing once corpus is sufficient — distinct from the established closed-protocol finding
- **Loop closure** is a protocol integrity requirement, not optional — committed feedback architecture is mandatory infrastructure
- **Three-lane trading architecture** (Option A/B/C) runs simultaneously with strict corpus segregation — no forced bet on which integration model is correct
- **Async multi-day planning** + TRNG pre-selection naturally extends retrocausal T-delta windows — longer planning horizons are a research asset
- **RVD and EBF** are logged-but-inert tradition-derived variables; Power Analysis Gate (#28) determines when they become active; empirical weight assigned by corpus, not by tradition
- **Question formulation = trade specification** — the tasking question IS the trade order; formulation library is a primary corpus output
- **Algo module** = Rules-Based Technical Screener (TA-Lib/FinTA) as first pluggable implementation; broker-agnostic execution adapter with IBKR as first concrete target
- **Position sizing** = fixed fractional (1–2%) as MVP null hypothesis; corpus tests whether confidence-weighted sizing outperforms it
- **Asset performance is temporally non-stationary** — multi-timescale envelope is mandatory infrastructure, not optional analytics
- **Admin location:** Bucharest, Romania (UTC+2/+3) — UTC coordination mandatory for all event timestamps
- **Admin operational constraint:** Extended internet blackout periods (aviation); system must be fail-operational, not merely fail-safe
- **Meaningful money threshold** is an irreducible confound — track as corpus event, study its effect rather than attempting to mask it

