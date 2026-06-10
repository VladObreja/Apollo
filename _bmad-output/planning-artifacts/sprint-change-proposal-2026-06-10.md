# Sprint Change Proposal — Deferred Work Triage

**Date:** 2026-06-10
**Facilitated via:** Correct Course workflow (bmad-correct-course)
**Trigger:** Backlog hygiene review of `_bmad-output/implementation-artifacts/deferred-work.md` (40 items across Stories 1.1–3.3), informed by the Epic 3 Retrospective (2026-06-09).

---

## 1. Issue Summary

`deferred-work.md` had accumulated 40 individual deferred items from code reviews of Stories 1.1 through 3.3. With all three epics now marked `done`, several of these items:

- Were already resolved by Story 1.4 (Epic 1 Tech Debt & Infrastructure) but never struck from the register
- Were already formally accepted as V1 debt in the Epic 3 retrospective register
- Include the `IntegrityError` scoping issue, independently flagged in 3 separate code reviews (2.3, 3.1, 3.2) — per the retro: "deferred items with 3+ flags are no longer truly deferred, they are unscheduled stories"
- Remain genuinely unscheduled and need a home before V2 planning begins

This proposal triages all 40 items to a final disposition and proposes a new Epic 4 to schedule the remaining work.

---

## 2. Impact Analysis

### Epic Impact
- Epics 1–3: No changes to scope or acceptance criteria — all already `done` and verified.
- **New Epic 4 (Hardening & Tech Debt)** proposed, containing 5 stories.

### Story Impact
- No existing stories are reopened or modified.
- 5 new stories added (4.1–4.5).

### Artifact Conflicts
- `architecture.md`: new "Known Limitations / Accepted Risk (V1)" section to be added (no conflicting content, additive only).
- `epics.md`: new Epic 4 section appended.
- `sprint-status.yaml`: new epic-4 and story entries added as `backlog`.
- PRD: **no conflicts** — all FR1–FR10 already shipped; Epic 4 is hardening only, does not expand MVP scope.

### Technical Impact
- Story 4.1 touches `worker.py`, `validate.py`, `seal.py`, and `tests/e2e/test_epic2_e2e.py`.
- Story 4.2 touches `config.py`, `mcp/tools.py`, `worker.py`.
- Story 4.3 requires a new Alembic migration (check constraints on `parameter_name`, `admin_awareness_tier`).
- Story 4.4 is test-only / MCP-tool wiring consistency, no schema impact.
- Story 4.5 is documentation only.

---

## 3. Disposition of All 40 Deferred Items

| Disposition | Count | Detail |
|---|---|---|
| Resolved by Story 1.4 (verified in code) | 8 | All 1.1/1.2/1.3 items — docker-compose, CI, factory_boy, structured logging, FakeSMTPClient dedup, db_session fixture, README/.env, naming convention |
| Already accepted in Epic 3 retro register | 6 | IMAP per-fetch connection (2.1), clock injection (2.2), asset_latitude (2.4), detached ORM pattern (3.1), validated_at shared timestamp (3.1), lazy="raise" FK guard (3.3) |
| → Story 4.1 (Worker Resilience & E2E Repair) | 5 + retro A1 | b"" empty-bytes retry loop (2.2), IntegrityError Phase 3 (2.3), IntegrityError _validate_one (3.1), worker IntegrityError extraction_success inflation (3.1), extraction_success double-fire (2.4), + 4 failing E2E tests (retro A1) |
| → Story 4.2 (Operational Hardening) | 3 | imap_use_ssl warning (2.1), expiry_at ISO parsing (3.1), fingerprint backfill after crash (2.4) |
| → Story 4.3 (Domain Vocabulary Formalization) | 1 | ParameterName/AwarenessTier enums (1.1) |
| → Story 4.4 (Test & Code Quality Cleanup) | 8 + retro A2 | FakeIMAPClient redelivery (2.1), QuarantineRecordFactory dangling FK (2.3), SMTP counter fragility (2.3), test helper dedup (2.2), calibration double-blind integration test (3.3), test_offset_rows_excluded_from_brier (3.3), closure service real-session unit test (3.2 W3), trigger_closure_ceremony DI consistency (3.2 W4), + _unique_hash() dedup (retro A2) |
| → Documented as accepted risk in architecture.md | 9 | prompt injection via email_body (2.1), unbounded quarantine retry (2.3), clarification_sent_at NULL ambiguity (2.3), ceremony_log absence (3.2 W1), naive last_sent (3.2 W2), NaN param_value (3.3), bucket label cosmetic (3.3), computed_at drift (3.3), model_dump wrapping (2.2) |
| → Story 4.5 (Operator SOP, retro A4) | retro A4 | Not from deferred-work.md; folded in per retro action item |

**Total: 8 + 6 + 6 + 3 + 1 + 9 + 9 = 40 +A1/A2/A4** ✓ all items dispositioned.

---

## 4. Recommended Approach

**Option 1: Direct Adjustment** — Add Epic 4 with 5 new stories within the existing project structure. No PRD changes, no rollback, no MVP scope change.

- **Effort:** Low–Medium (Stories 4.1–4.2 are bug-fix scale; 4.3 is a small migration; 4.4 is test cleanup; 4.5 is documentation)
- **Risk:** Low — all changes are additive or scoped fixes to existing, well-tested code paths
- **Rationale:** All FRs are shipped; this is pure hardening before V2 planning, which the retro already recommended ("Tech debt cleanup — A1 and A3 above before new feature scope"). Sequencing 4.1 (High priority, includes A1/A3) first directly follows that recommendation.

Options 2 (Rollback) and 3 (MVP Review) are not applicable — no failed approach or scope conflict exists.

---

## 4. New Epic 4: Hardening & Tech Debt

### Story 4.1: Worker Resilience & E2E Repair (Priority: High)

As a Developer, I want the worker's error-handling paths to be precise and the E2E suite to be trustworthy, so that failure modes are correctly counted and CI red actually means something.

**Acceptance Criteria:**
- The 4 failing tests in `tests/e2e/test_epic2_e2e.py` are fixed to match Story 2.2/2.3 sealing + quarantine behavior and pass in CI.
- The `IntegrityError` catch in worker Phase 3 sealing (`worker.py`) is scoped to the specific concurrent-seal unique constraint; any other `IntegrityError` propagates or is logged distinctly.
- The `IntegrityError` catch in `_validate_one` (`validate.py`) is scoped to the `corpus_record_id` UNIQUE constraint; other constraint violations are not silently logged as "already validated".
- `extraction_success` is no longer inflated by concurrent-seal `IntegrityError` handling or by decorator-chain re-raises after a successful seal.
- `b""` empty `raw_email_bytes` no longer causes a permanent DISPATCHED retry loop — a per-record retry limit or dead-letter mechanism is added (`seal.py`).

### Story 4.2: Operational Hardening (Priority: Medium)

As the Admin, I want config and parsing edge cases handled so the system degrades safely under real-world conditions.

**Acceptance Criteria:**
- A startup warning is logged when `imap_use_ssl=False` (`config.py`).
- `expiry_at` ISO parsing in `configure_target` (`mcp/tools.py`) correctly handles non-Z-suffix offsets and date-only strings, producing UTC-aware datetimes.
- Sealed records that are permanently missing their environmental fingerprint row (due to crash between seal-commit and fingerprint-write) are detected and backfilled on a subsequent tick (`worker.py`).

### Story 4.3: Domain Vocabulary Formalization (Priority: Medium)

As a Developer, I want `parameter_name` and `admin_awareness_tier` to be type-safe enums now that the domain vocabulary has stabilized across 3 epics.

**Acceptance Criteria:**
- `ParameterName` and `AwarenessTier` enums are added to `domain/types.py` with the finalized values (`vad`, `rvd`, `ebf`, tier levels per `architecture.md`).
- Pydantic extraction/validation schemas use these enums.
- An Alembic migration adds DB check constraints on `parameter_name` and `admin_awareness_tier` columns, proven reversible (`upgrade head` → `downgrade base` → `upgrade head`).

### Story 4.4: Test & Code Quality Cleanup (Priority: Low)

As a Developer, I want test fixtures and minor code inconsistencies cleaned up so the suite stays maintainable.

**Acceptance Criteria:**
- `_unique_hash()` is extracted into `tests/utils.py` as a shared utility and used by Stories 3.2/3.3 test files.
- `FakeIMAPClient` does not re-deliver previously-fetched emails on subsequent `tick()` calls.
- `QuarantineRecordFactory` produces a valid parent `CorpusRecord` (or is documented as requiring one) so it can be used standalone.
- `FakeSMTPClient(raise_on_nth=1)` usage in `test_worker_quarantine.py` is made robust to additional Phase 2 SMTP calls.
- `_make_reply_email` and `_seed_dispatched` test helpers are consolidated into `tests/utils.py`.
- An integration test proves `CalibrationService` double-blind isolation (currently only proven by code inspection).
- `test_offset_rows_excluded_from_brier` asserts the correct excluded Brier value, not just that the score changes.
- A unit test exercises the real SQLAlchemy session path for `_get_last_ceremony_timestamp`/`_fetch_pending` in `ClosureService`.
- `trigger_closure_ceremony` MCP tool wiring follows the `tick()` DI pattern for consistency with other MCP tools.

### Story 4.5: Operator SOP Documentation (Priority: High, owner: Tech Writer)

As the Admin (Vlad), I want a written SOP for operating Apollo day-to-day, so that configuring targets, monitoring tick cadence, and interpreting calibration output doesn't require holding the entire system in my head.

**Acceptance Criteria:**
- SOP document covers: configuring a target via `configure_target`, expected `apollo tick` cadence and how to verify it's running, interpreting `get_calibration_stats` output (Brier score, ECE, Wilson CI), and manually triggering a closure ceremony via `trigger_closure_ceremony`.
- SOP references the new "Known Limitations / Accepted Risk (V1)" section of `architecture.md`.

---

## 5. Architecture.md Addition: "Known Limitations / Accepted Risk (V1)"

A new section will be added documenting these 9 items as deliberately accepted for V1 (no code changes planned):

1. Prompt injection via unbounded `email_body` in extraction prompts — single trusted Asset, risk accepted.
2. Unbounded quarantine retry loop — single trusted Asset, low volume.
3. `clarification_sent_at=NULL` ambiguity after SIGKILL between T1 commit and SMTP send — no resend mechanism; low volume, Admin monitors.
4. Closure ceremony has no dedicated `ceremony_log` audit table — `max(closed_at)` proxy used instead.
5. Closure ceremony: timezone-naive `last_sent` would crash interval subtraction — theoretical only, `DateTime(timezone=True)` prevents naive storage in practice.
6. `NaN` `param_value` would raise `ValueError` in calibration bucketing — validated ≥0 upstream by Pydantic extraction schema.
7. Calibration bucket label cosmetic ambiguity at decade boundaries (e.g., `param_value=10.0` → bucket "0–10").
8. `computed_at` timestamp stamped after DB session close — negligible time drift.
9. `model_dump` `PydanticSerializationError` not wrapped in `SealingError` — caught by outer handler and counted correctly, just under a generic log category.

---

## 6. Implementation Handoff

**Change scope classification: Moderate** — backlog reorganization (new epic + stories added to `epics.md` and `sprint-status.yaml`), no PRD/architecture redesign.

| Story | Owner | Notes |
|---|---|---|
| 4.1 | Developer (Amelia) | High priority — do first, includes retro A1 + A3 |
| 4.2 | Developer (Amelia) | Medium priority |
| 4.3 | Developer (Amelia) | Medium priority — includes Alembic migration |
| 4.4 | Developer (Amelia) | Low priority — can be folded into other stories' review cycles |
| 4.5 | Tech Writer (Paige) | High priority per retro — can run in parallel with 4.1–4.4 |
| Architecture.md update | Developer (Amelia) or Architect (Winston) | Additive doc change, can be done alongside Story 4.1 |

**Success criteria:** `deferred-work.md` can be archived/cleared once Stories 4.1–4.5 reach `done`, with the 9 accepted-risk items permanently living in `architecture.md` instead.

---

## Approval

- [x] Approved by Vlad (Admin/Project Lead) on 2026-06-10
