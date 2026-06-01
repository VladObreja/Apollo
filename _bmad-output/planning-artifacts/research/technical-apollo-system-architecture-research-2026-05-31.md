---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-05-29-1841.md'
  - 'memory/project_apollo_overview.md'
  - 'memory/project_apollo.md'
workflowType: 'research'
lastStep: 4
research_type: 'technical'
research_topic: 'Apollo Conceptual System Architecture'
research_goals: 'Synthesize v1 stack + v2/v3 brainstorming ideas into a coherent module and service map, phase-mapped to implementation order, without fixing exact technology choices.'
user_name: 'Vlad'
date: '2026-05-31'
web_research_enabled: false
source_verification: false
---

# Apollo — Conceptual System Architecture

**Date:** 2026-05-31
**Author:** Vlad
**Input:** v1 stack (7 services, running) + brainstorming corpus (121 ideas, 4 phases, HIRA register)

---

## Research Overview

This document synthesizes the current v1 Docker stack with the full v2/v3 brainstorming corpus into
a module and service map for the Apollo system. Exact technology choices are intentionally deferred;
this document names what each module *does* and *why it exists*, not how it is implemented.
Phase annotations (v1 / v2 / v3) indicate first-appearance of each module.

Source: internal synthesis only — no external web sources.

---

## Technical Research Scope Confirmation

**Research Topic:** Apollo Conceptual System Architecture
**Research Goals:** Module and service map, phase-mapped, no fixed tech choices

**Scope:**
- Architecture Analysis — domain decomposition, compartment model, information flow
- Service Catalogue — responsibilities, boundaries, phase mapping
- Integration Patterns — event bus topology, inter-domain communication
- Constraint Inventory — HIRA residuals, VRAM budget, fail-operational requirements

**Scope Confirmed:** 2026-05-31

---

## 1. V1 Stack — Baseline Assessment

The current stack comprises eight Docker services across three functional areas.

| Service | Port | Role | Status |
|---------|------|------|--------|
| ollama | 11434 | Local LLM inference (GPU) | **Core — keep** |
| apollo-lightrag | 9621 | Graph RAG, knowledge corpus | **Core — keep** |
| docling | 5001 | Document conversion (PDF/docx/html → text) | **Core — keep** |
| apollo-agent / OpenClaw | 18789 | Natural language knowledge query agent | **Core — keep** |
| browserless | 3003 | Headless browser (web archiver) | **Core — keep** |
| apollo-scout / crawl4ai | 11235 | Web scraping and content extraction | **Core — keep** |
| n8n + n8n_db | 5678 | Workflow automation + Postgres backend | **Promote** — n8n_db becomes shared relational store |
| open-webui | 3000 | Chat UI | **Demote** — Claude Code MCP becomes primary interface |

**Gap analysis:** The v1 stack covers Pillar 2 (Second Brain) and provides the inference substrate.
It has no RV operations layer, no event bus, no compartment enforcement, no corpus store,
no trading layer, and no control plane beyond n8n workflows. All of that is the build.

---

## 2. Service Catalogue

Services are organized into six layers. Layer 0 is horizontal infrastructure; all other
layers depend on it. Layers 1–4 are functional domains. Layer 5 is the external boundary.

---

### Layer 0 — Foundation (Infrastructure)

These services have no domain logic. They are shared horizontal resources.

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Local LLM Runtime** | GPU-bound inference for all local model invocations. Hosts specialist ensemble within 16 GB VRAM budget. | v1 |
| **Embedding Engine** | Produces dense vector representations for semantic search across all domains. | v1 |
| **Document Conversion Service** | Converts raw documents (PDF, EPUB, DOCX, HTML) to clean text for downstream ingestion. | v1 |
| **Event Message Bus** | Async pub/sub backbone routing all inter-domain events. Enforces compartment boundaries structurally — a service only receives events on topics it is subscribed to. The RV double-blind protocol is enforced here, not by procedure. | v1 |
| **Relational Database** | Structured persistent state: asset registry, target registry, task records, parameter definitions, study configurations, proposal queue. Promoted from n8n's Postgres instance. | v1 |
| **Time-Series Store** | Environmental correlates (Kp index, solar wind, LST, weather, Schumann peaks) keyed to UTC. Joinable to any session by asset-reported measurement time. | v1 |
| **Append-Only Audit Log** | Immutable event ledger for session provenance chains, corpus events, first-observation timestamps, and admin interaction records. Never updated — only appended. | v1 |
| **TRNG Service** | True random number source for target selection, coordinate assignment, and any pipeline decision not requiring a specific outcome. Source type logged per invocation. | v1 |

---

### Layer 1 — Knowledge Domain (Pillar 2 — Second Brain)

Handles all non-RV knowledge: books, documents, web archives, conversation slices.

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Knowledge Ingestion Pipeline** | Orchestrates document → conversion → chunking → embedding → graph insertion. Manages batch sizing to respect VRAM budget during insertion runs. | v1 |
| **Graph RAG Engine** | Stores and queries the knowledge graph (entity relationships + vector similarity). Current instance: apollo-lightrag:9621 (Apollo/Aurelius corpus). Hermes gets a separate instance. | v1 |
| **Knowledge Query Agent** | Receives natural language queries; orchestrates retrieval from Graph RAG and returns grounded answers. Invoked by the control plane on demand; goes dark under GPU load. | v1 |
| **Web Archiver** | Headless browser + scraper pair. Follows links, captures full page content to disk before any processing. Preservation-first: content written to cold storage unconditionally, then queued for optional ingestion. | v1 |

---

### Layer 2 — RV Operations Domain (Pillar 1 — MVP)

The core of the new build. Structured around five isolated compartments enforced by the event bus.
No compartment has access to data from a compartment it has no business seeing.

---

#### Compartment A — Target Management

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Target Registry** | Persistent store for all targets. Fields: codename, domain class, origin type (Auto-Generated / Admin-Curated / Hybrid), proximity tag (External / Adjacent / Personal), purity tier (Pure / Curated-Blind / Directed / Open-Loop), age-in status, eligibility timestamp. | v1 |
| **Target Screener** | Pulls eligible instruments from a configurable universe; applies liquidity and volatility hard filters; enforces diversity constraint (minimum allocation per sector / instrument class / time horizon). Writes Auto-Generated entries to Target Registry without admin review of individual tickers. | v1 (basic) → v2 (dual-mode) |
| **Target Vault** | Sealed sub-compartment within Target Management. Maps coordinate references (XXXX/YYYY) to actual target identities. Only the Unblinding Service reads from the Vault — and only at the unblinding event. No other service or agent has read access. | v1 |

---

#### Compartment B — Task Lifecycle

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Parameter Registry** | Defines all measurable session parameters: VAD, RVD, EBF as defaults; extensible by row insertion. Each asset carries an active parameter set. Parameter set locked at task dispatch time. | v1 |
| **Question Template Engine** | Constructs tasking questions from (Target class, Parameter type, Time Horizon) tuple using versioned templates. No admin authorship of individual questions in default mode. Admin-blind dispatch is the clean state; admin-contact is an opt-in exception logged as a purity-tier downgrade. | v1 |
| **Task Registry** | Assigns XXXX/YYYY coordinate to each (Target × Parameter) pair. Stores: coordinate, question text, dispatch timestamp, committed closure event specification, purity tier, admin awareness tier at dispatch. | v1 |

---

#### Compartment C — Session Operations

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Email Gateway** | Dispatches formatted tasking emails from the anonymized admin research address to asset research addresses. Receives inbound replies; routes to Session Inbox Agent. Queues outbound on failure; never drops. | v1 |
| **Session Inbox Agent** | LLM extraction: reads full email thread, extracts structured fields (VAD, RVD, EBF, Receptivity, Social Field, measurement timestamp, free-text notes), runs plausibility validation (timestamp bounds, value ranges). On success: commits to Session Store. On failure or ambiguity: triggers correction cycle (generates clarification email, holds session in pending). Extraction reasoning logged. | v1 |
| **Session Store** | Canonical session records. Each record carries: coordinate, extracted fields, asset-reported measurement timestamp, session context fingerprint (auto-enriched from Time-Series Store at ingestion), provenance chain. Records are sealed immediately after extraction commit. | v1 |
| **Cryptographic Seal Service** | For retrocausal protocol tasks: seals session record (hash + timestamp) before target assignment. The seal proves session data preceded target selection. Irreversible. | v1 |
| **Unblinding Service** | Discrete, logged, irreversible operation: reads from Target Vault, joins target identity to the sealed session record, writes the unblinding event to the Audit Log. The only service that crosses the Vault boundary. Triggered explicitly by admin; never automatic. | v1 |

---

#### Compartment D — Analysis

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Analysis Sandbox** | Open framework of independently executable modules. Each module receives a session corpus subset, returns findings in a standardized format. Modules: statistical (correlation, regression), pattern (clustering, anomaly), LLM-assisted (narrative synthesis, hypothesis generation). New modules added without touching existing ones. | v2 |
| **Calibration Engine** | Computes the empirical confidence function per asset per domain per formulation type. Outputs: point estimate + uncertainty band derived from corpus depth. All consumers receive both. Band narrowing is a measure of system maturity. | v2 |
| **Hypothesis Register & ACH Engine** | Maintains competing hypotheses about what the corpus is measuring. Each hypothesis scored against corpus evidence. Ensemble spread (hypothesis divergence) reported as second uncertainty dimension alongside corpus-depth bands. Red Team module generates adversarial challenges against the dominant hypothesis on cadence. | v2 |
| **Study Manager** | Manages active studies: tracks session count against power analysis estimates, reports findings when significance threshold reached. Distinguishes passive collection (always on) from active study (explicitly activated). Power Analysis Gate prevents premature hypothesis testing on underpowered data. | v2 |
| **Epistemological Ledger** | Human-authored, append-only belief version history. Each entry: assumption held, evidence/reasoning, date, corpus implication. Triggers Reinterpretation Runs when a belief update affects prior analysis. Original analyses preserved permanently; reinterpretations are additional layers. | v2 |
| **Corpus Reconciliation Engine** | Scheduled integrity audit: verifies every dispatched task has a corresponding session or known pending/failed state; every sealed session has a committed closure; every resolved outcome has a first-observation timestamp. Reports gaps as findings; never silently resolves them. | v1 (basic) → v2 (full) |

---

#### Compartment E — Feedback Loop

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Feedback Queue** | Batches resolved sessions by asset and week. Respects feedback ingestion capacity ceiling (5–15 sessions per batch). Enforces Saturday morning delivery cadence by default. Closure dispatch failure triggers rescheduling, never loss. | v1 |
| **Closure Interface** | Delivers the weekly closure report as a deliberate, single-event ceremony. Asset controls when they open it; receipt timestamp is the first-observation event logged in Audit Log. Never pushed asynchronously. | v1 |
| **Asset Performance Reporter** | Generates blind-safe aggregate pattern reports for assets: Receptivity-accuracy correlations, time-of-day patterns, formulation type performance, Social Field effects. Contains zero individual outcome data. Admin reviews before delivery; delivery is a corpus event. | v2 |

---

#### Shared RV Services

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Environmental Correlates Ingestion Pipeline** | Scheduled background agent pulling NOAA geomagnetic/solar indices, Swiss Ephemeris planetary positions, weather APIs keyed to asset locations, sidereal time calculations. Stored in Time-Series Store, joinable to sessions by measurement timestamp. | v1 (NOAA + LST) → v2 (full suite) |
| **Asset Registry** | Thin records: codename, research email address, active/inactive, methodology type, active parameter set. No mutable performance scores — those are derived at query time. | v1 |
| **Spontaneous Impression Log** | Lightweight out-of-band channel for unprompted asset impressions: submission timestamp, domain tag, free-text, clarity rating. Separate corpus layer; never linked retroactively to task records. | v2 |
| **Admin Contamination Event Log** | Voluntary append-only log of target-adjacent information encountered by admin during open session windows. Linked to sessions at close. Sessions with no entry classified Admin-Ambient by default. | v1 |

---

### Layer 3 — Trading Domain (v2/v3)

Operates behind an information barrier analogous to the Target Vault.
Admin authorizes logic and parameters; does not observe individual open positions in real time.

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Trading Vault** | Information barrier for execution layer. Admin sees only aggregate P&L and session-level outcome resolution during open positions. Individual position visibility unlocks at configured review window. Extends the double-blind architecture to the financial execution layer. | v2 |
| **Algo Signal Module** | Pluggable interface: receives (ticker, question formulation, time horizon), returns direction confidence, suggested sizing, rationale tag. First implementation: rules-based technical screener (RSI, momentum, MACD, Bollinger Bands). Subsequent modules slot behind the same interface. | v2 |
| **Position Manager** | Enforces bracket order protocol: all trades enter with simultaneous TP and SL as OCO. TP derived directly from question formulation. SL at configurable risk multiple set at entry. Rejects non-compliant entries. Pre-blackout checklist verifies all open positions have active bracket orders. | v2 |
| **Broker Execution Adapter** | Broker-agnostic interface: place order, cancel order, get position, get account state. First concrete implementation: IBKR. Additional brokers added as new adapter implementations; core trading logic never references a broker directly. Executes confirmation loop; position reconciliation against broker on cadence. | v2 |
| **Market Data Feed** | Price, volume, calendar data for target generation, trade resolution, and outcome auto-detection. Separate from Environmental Correlates — financial data, not psi correlates. | v2 |

---

### Layer 4 — Control Plane

The operational nerve center. Interfaces with all other layers.
Claude Code (via MCP) is the primary human-facing entry point into the entire control plane.

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Planning Agent** | Maintains rolling Session Sequence State per asset (last N sessions: Receptivity scores, VAD distribution, feedback deliveries, cumulative load, admin state at dispatch). Evaluates sequence state before recommending dispatch. Supports multi-day batch authorization. | v1 |
| **Admin State Monitor** | Captures Admin State Snapshot (Clarity, Energy, Pressure) as mandatory prefix to every system interaction. Runs rolling trend analysis over 30- and 90-day windows. Flags sustained degradation before next planning session. | v1 |
| **Parameter Update Proposal Queue** | Any corpus finding crossing a significance threshold generates a structured proposal: change, evidence, expected effect, risk of deferral. Proposals queue for admin approval. Moratorium enforcement: proposals during drawdown cooling-off period are held, not surfaced. Each approval/rejection logged as a corpus event. | v2 |
| **Protocol Integrity Service** | Enforces pre-committed phase advancement and exit criteria. Monitors drawdown state; triggers moratorium timer on threshold crossing. Pre-committed criteria gating: advancement event fires as a Proposal, not an autonomous action. | v2 |
| **MCP Server** | Apollo exposes capabilities as MCP tools: corpus queries, session management, planning authorization, analysis requests, admin actions, vault management. External LLMs (Claude Code primary; GPT, Gemini as analysis escalation) call Apollo — Apollo does not call them. Inversion of the typical integration pattern. | v1 (partial — apollo_admin.py exists) → v1.5 (full RV tools) |
| **Audit Service** | Governs access to corpus records. Enforces deliberate outcome revelation (sealed until admin explicitly opens). Logs all corpus read events with timestamps. Append-only. No passive display of resolved outcomes. | v1 |

---

### Layer 5 — External Boundary

| Interface | Direction | Responsibility | Phase |
|-----------|-----------|---------------|-------|
| **Email Service** | Bidirectional | Outbound: tasking dispatch from anonymized research address. Inbound: session reply receipt, routing to Session Inbox. All addresses unpersonalized research-only addresses. | v1 |
| **External LLM Bridge** (MCP) | Inbound | Claude Code as primary operator. GPT/Gemini as on-demand analysis escalation. LLMs call Apollo tools — not the reverse. Forward-compatible as MCP adoption grows. | v1 |
| **Market Data Feeds** | Inbound | Equity/index/forex/commodity price and volume data. Used by Target Screener, Algo Signal Module, and outcome resolution. | v2 |
| **Environmental Data Feeds** | Inbound | NOAA (Kp/solar wind), Swiss Ephemeris (planetary positions), weather APIs (asset locations), Schumann resonance. Feeds Environmental Correlates Pipeline. | v1 (partial) → v2 (full) |
| **TRNG Sources** | Inbound | Hardware TRNG (Geiger tube, thermal noise) or network quantum RNG (ANU). Source type logged per invocation. Both paths architecturally supported; selection is a per-event operational decision, not a fixed choice. | v1 |

---

## 3. Inter-Domain Event Flow

Key event types flowing across the event bus, organized by protocol phase:

```
TASKING PHASE
─────────────
TargetPoolUpdated      Target Management → Task Registry
TaskIssued             Task Registry → Email Gateway
                       (payload: coordinate + question; target identity NEVER included)

SESSION PHASE
─────────────
SessionReceived        Email Gateway → Session Inbox Agent
ExtractionComplete     Session Inbox Agent → Session Store
ExtractionAmbiguous    Session Inbox Agent → Email Gateway (correction cycle)
SessionSealed          Session Store → TRNG Service (triggers target selection for retrocausal tasks)
TargetAssigned         Target Vault → Analysis (via Unblinding Service — irreversible, logged)

ANALYSIS PHASE
──────────────
OutcomeResolved        Market Data Feed → Analysis Sandbox
AnalysisFinding        Analysis Sandbox → Parameter Update Proposal Queue
CalibrationUpdated     Calibration Engine → all consumers
HypothesisShift        Hypothesis Register → Epistemological Ledger

FEEDBACK PHASE
──────────────
ClosureReady           Feedback Queue → Closure Interface (batched weekly)
ClosureDelivered       Closure Interface → Audit Log (asset receipt timestamp)
ClosureQualityLogged   Asset-reported post-closure field → Session Store (separate layer)

TRADING PHASE (v2)
──────────────────
TradeSignalReady       Analysis → Trading Vault
TradeAuthorized        Admin → Trading Vault (within pre-authorized envelope)
TradeExecuted          Broker Adapter → Audit Log + Corpus
PositionReconciled     Broker Adapter → Position Manager (cadence check)

CONTROL PLANE
─────────────
AdminStateSnapshot     Admin → Planning Agent (every interaction, mandatory prefix)
ParameterUpdateProposed  Protocol Integrity → Proposal Queue
ParameterUpdateApproved  Admin → Proposal Queue → Operational Change
MoratoriumStarted      Protocol Integrity → Proposal Queue (blocks approvals)
```

---

## 4. Phase Map

### V1 — Foundation + RV Operations MVP

**Objective:** Running system capable of conducting a complete RV session cycle from target
selection through to feedback delivery, with environmental correlates and basic corpus integrity.

**Reused from current stack:**
- Local LLM Runtime, Embedding Engine, Document Conversion, Graph RAG Engine, Knowledge Query Agent
- Web Archiver (browserless + crawl4ai)
- Relational Database (promoted from n8n_db)
- MCP Server (apollo_admin.py — extend with RV tools)

**New in v1:**
- Event Message Bus
- Time-Series Store
- Append-Only Audit Log
- TRNG Service (network TRNG sufficient for v1)
- Target Registry + Target Vault
- Parameter Registry + Question Template Engine + Task Registry
- Email Gateway
- Session Inbox Agent (LLM extraction + plausibility check)
- Session Store + Cryptographic Seal Service + Unblinding Service
- Asset Registry
- Environmental Correlates Pipeline (NOAA + LST basics)
- Feedback Queue + Closure Interface
- Planning Agent (basic dispatch authorization)
- Admin State Monitor (snapshot capture, no trend analysis yet)
- Audit Service (deliberate revelation enforcement)
- Corpus Reconciliation Engine (basic gap detection)
- Admin Contamination Event Log

**Exit criteria for v1:** Complete session cycle executed end-to-end. At least one session per week
sustainable over a 4-week run without data loss, silent corruption, or protocol breach.

---

### V2 — Analysis, Calibration, Trading Integration

**Objective:** Calibration function producing empirical confidence bands.
Basic trading lane operational (paper trading with bracket orders).

**New in v2:**
- Analysis Sandbox (first statistical modules)
- Calibration Engine (confidence function + uncertainty bands)
- Hypothesis Register & ACH Engine
- Study Manager + Power Analysis Gate
- Epistemological Ledger
- Corpus Reconciliation Engine (full audit pass)
- Asset Performance Reporter
- Spontaneous Impression Log
- Environmental Correlates Pipeline (full suite: ephemeris, Schumann, weather)
- Target Screener (basic yfinance-based, diversity constraints)
- Trading Vault + Algo Signal Module (rules-based screener)
- Position Manager (bracket order enforcement)
- Broker Execution Adapter (IBKR)
- Market Data Feed
- Parameter Update Proposal Queue
- Protocol Integrity Service (drawdown detection + moratorium)
- Admin State Trend Analysis (rolling 30/90-day windows)

**Exit criteria for v2:** Calibration function outputs confidence bands with corpus-depth
uncertainty. Paper trading lane running with all bracket orders enforced. Power Analysis Gate
returns meaningful estimates for the first candidate variables.

---

### V3 — Multi-Asset, Advanced Analysis, Full Trading

**Objective:** Multi-asset corpus support. Advanced analysis modes. Return-optimal trading lane.
Admin co-practitioner mode experimentally activated if corpus warrants.

**New in v3:**
- Cross-Corpus Query Layer (pattern resonance detection across sovereign asset corpora)
- Red Team Analysis Module
- Matched-Pair Analysis Mode
- Hypothesis Ensemble Spread (second uncertainty dimension)
- Corpus Coverage Map (untested region detection)
- Corpus Scientific Value Export (anonymized, publication-ready format)
- Target Screener v2 (dual-mode: calibration-optimal / return-optimal)
- Algo Signal Module v2 (quant strategies behind same interface)
- Admin Co-Practitioner Mode (corpus-evidence-gated configuration, not rebuild)
- Admin-Formulated Question Track (separate epistemic category)
- Formal Data Governance Framework (triggered by multi-asset onboarding)

---

## 5. Architectural Constraints Inventory

These are non-negotiable constraints carried forward from the HIRA register and Usefulness
Framework decisions. They constrain technology choices in the next phase.

| Constraint | Source | Architectural Implication |
|-----------|--------|--------------------------|
| 16 GB VRAM ceiling | Hardware | Specialist ensemble only; LLM sessions cannot run concurrently with large model inference. External LLM escalation for heavy analysis. Pre-warming discipline for ingestion runs. |
| Fail-operational pipeline | Aviation blackout (admin) | Every pipeline stage must degrade to a known visible state. No silent data loss. Email dispatch failures queue; extraction failures hold in pending; closure failures reschedule. State always recoverable. |
| UTC-native event model | H-34 decision | All timestamps stored and reasoned in UTC. Bucharest local time (UTC+2/+3) is display-only. Market calendars are a lookup layer. No timezone logic in core pipeline. |
| Append-only corpus | H-01, H-02, archival-grade | Original session records never modified. Reinterpretations are separate, timestamped layers. Schema versioning ensures old records interpretable without running software. |
| Admin as periodic decision-maker | Architecture #32/#33 | System executes autonomously within a pre-authorized envelope. No admin availability required for day-to-day operation. Planning agent manages the authorization boundary. |
| No PII anywhere in system | H-09, #121 | Anonymization at infrastructure layer. Research email addresses only. Asset registry stores codename + research address. No real-person concept in any data model. |
| Compartmentalized LLM sessions | #64 | Each LLM invocation receives only the information quantum its task requires. No shared context across compartment boundaries. Sessions spun up, execute, discarded. |
| Bracket orders mandatory | H-06, #118 | TP from question formulation. SL at configurable risk multiple set at entry. No single-leg entries permitted. Broker adapter rejects non-compliant orders. |
| Parameter changes gated by Proposal Queue | #56 | Analysis layer never auto-updates operational parameters. Every change surfaces as a proposal for admin approval. Moratorium blocks approvals during drawdown cooling-off period. |
| TRNG for arbitrary pipeline decisions | #66 | Randomness is the deliberate default wherever protocol integrity doesn't require a specific outcome. Determinism is reserved for where it is strictly necessary. |

---

## 6. V1 Service Topology — Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — EXTERNAL BOUNDARY                                    │
│  Email Service │ Market Data │ Env Data Feeds │ TRNG │ Ext LLMs │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 4 — CONTROL PLANE                                        │
│  Planning Agent │ Admin State Monitor │ MCP Server             │
│  Audit Service │ Protocol Integrity │ Proposal Queue           │
└────────────────────────┬────────────────────────────────────────┘
                         │  EVENT MESSAGE BUS
          ┌──────────────┼──────────────────────┐
          │              │                      │
┌─────────▼────┐  ┌──────▼──────────┐  ┌───────▼──────┐
│  LAYER 1     │  │  LAYER 2        │  │  LAYER 3     │
│  KNOWLEDGE   │  │  RV OPERATIONS  │  │  TRADING     │
│              │  │                 │  │  (v2)        │
│ Ingestion    │  │ [A] Target Mgmt │  │ Trading Vault│
│ Pipeline     │  │ [B] Task Life.  │  │ Algo Module  │
│ Graph RAG    │  │ [C] Session Ops │  │ Position Mgr │
│ Query Agent  │  │ [D] Analysis    │  │ Broker Adptr │
│ Web Archiver │  │ [E] Feedback    │  │ Market Feed  │
└──────────────┘  │ Env Correlates  │  └──────────────┘
                  │ Asset Registry  │
                  └─────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 0 — FOUNDATION                                           │
│  LLM Runtime │ Embedding Engine │ Doc Conversion               │
│  Relational DB │ Time-Series Store │ Append-Only Log           │
│  TRNG Service (local)                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Open Questions for PRD Phase

The following are not closed decisions — they are design choices that the PRD author should
resolve with Vlad before architecture finalization.

1. **Event bus topology:** Single bus for all domains, or separate buses per domain (Knowledge,
   RV, Trading, Control)? Single bus is simpler; separate buses enforce compartment isolation
   more structurally.

2. **Analysis sandbox execution model:** Scheduled batch (cadence-driven) or event-triggered
   (runs when new session data arrives)? Both have correctness; batch is simpler to reason about
   for the corpus integrity requirements.

3. **v1 n8n retention:** Does n8n stay as the workflow automation engine for the new pipeline
   (Email Gateway, Environmental Correlates scheduling), or does it get replaced by the Event
   Message Bus + custom agents? n8n is operational but adds dependency complexity.

4. **Hermes isolation:** Does Hermes (psi research system, port 9622) share the Layer 0
   foundation services with Apollo (same Relational DB, same Event Bus) or run fully
   isolated? Sharing reduces resource footprint; isolation is architecturally cleaner.

5. **Claude Code as sole operator UI:** Is open-webui fully retired in v1, or kept alongside
   Claude Code for specific non-admin use cases (e.g., knowledge base browsing)?

---

*Document generated from brainstorming corpus synthesis. No external sources consulted.*
*Next phase: PRD Creation (`bmad-create-prd` or talk to John).*
