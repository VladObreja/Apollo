---
baseline_commit: aa909c8cc9df66a652143b93ea4be47e8857e3ee
---

# Story 3.3: Statistical Calibration Scoring

Status: done

## Story

As the Admin,
I want the system to continuously compute Brier scores, ECE, and empirical hit rates with Wilson score intervals over the closed sessions,
so that I can discover the Asset's actual optimal conviction threshold and establish our statistical confidence.

## Acceptance Criteria

1. **Given** a corpus of sealed, ground-truth-validated, epistemologically closed sessions
   **When** the `get_calibration_stats` MCP tool is invoked
   **Then** it returns the **Brier score** — `BS = (1/N) * Σ (predicted_prob_i − actual_i)²` — where `predicted_prob_i = param_value / 100.0` and `actual_i ∈ {0, 1}`

2. **Given** the same corpus of closed sessions
   **When** `get_calibration_stats` is invoked
   **Then** it computes the **Expected Calibration Error (ECE)** — using 10 equal-width bins over [0.0, 1.0]; ECE = Σ `(|bin|/N) × |avg_confidence − fraction_positive|` — and returns it in the readout

3. **Given** the same corpus
   **When** `get_calibration_stats` is invoked
   **Then** it computes the overall **empirical hit rate** and its **Wilson score 95% confidence interval** (lower, upper) and returns all three values

4. **Given** sessions flagged as `validation_status = 'offset'` (fetch delay > 2h, i.e., temporal drift)
   **When** `get_calibration_stats` is invoked
   **Then** the tool reports the count of offset sessions separately and **excludes** them from Brier/ECE/hit-rate calculations (they represent temporally drifted observations whose reliability is uncertain)

5. **Given** no closed sessions in the corpus (`closed_at IS NOT NULL` returns nothing)
   **When** `get_calibration_stats` is invoked
   **Then** the tool returns a readout indicating zero sessions scored with null metric values (no crash)

6. **Given** the computation runs
   **When** `get_calibration_stats` executes
   **Then** the service method is decorated with `@requires(Compartment.CALIBRATION_READ)` and accesses ONLY `validation_record` rows — it never joins to or reads `extraction_payload`, `raw_email_bytes`, or any field that reveals the original target identity (double-blind integrity is provable from the query)

7. **Given** the calibration output
   **When** the readout is returned
   **Then** it includes a **conviction-bucket breakdown** — 10 equal-width buckets of `param_value` (0–10, 10–20, … 90–100) — each reporting: count, hit rate, and Wilson 95% CI (lower, upper)

## Tasks / Subtasks

- [x] **Task 1: Domain models for calibration output**
  - [x] 1.1 Add `ConvictionBucket` Pydantic model to `src/apollo/domain/models.py`
  - [x] 1.2 Add `CalibrationStats` Pydantic model to `src/apollo/domain/models.py`

- [x] **Task 2: CalibrationService implementation**
  - [x] 2.1 Create `src/apollo/services/calibration.py`
  - [x] 2.2 Implement `CalibrationService.get_stats(session_factory)` decorated with `@requires(Compartment.CALIBRATION_READ)` — queries only `validation_record` rows where `closed_at IS NOT NULL`
  - [x] 2.3 Implement `_compute_brier_score(rows)` — pure function, no DB access
  - [x] 2.4 Implement `_compute_ece(rows, n_bins=10)` — 10-bin equal-width ECE, pure function
  - [x] 2.5 Implement `_wilson_ci(k, n, z=1.96)` — Wilson score CI, pure function; returns `(lower, upper)` or `(None, None)` if `n == 0`
  - [x] 2.6 Implement `_compute_hit_rate_with_ci(rows)` — overall empirical hit rate + Wilson CI
  - [x] 2.7 Implement `_compute_conviction_buckets(rows)` — 10 equal-width buckets by param_value (0–10, …, 90–100), each with hit rate + Wilson CI
  - [x] 2.8 Separate offset rows first (`validation_status == 'offset'`) and exclude from all metric computations

- [x] **Task 3: `get_calibration_stats` MCP tool**
  - [x] 3.1 Add `get_calibration_stats()` MCP tool to `src/apollo/mcp/tools.py`
  - [x] 3.2 Format and return a structured plaintext readout (no JSON blob — readable by Admin)

- [x] **Task 4: Unit tests**
  - [x] 4.1 Create `tests/unit/test_calibration_service.py`
  - [x] 4.2 Frozen corpus fixture: N=10 sessions with known param_values and outcomes for hand-verified math
  - [x] 4.3 Test `_compute_brier_score` against hand-computed value
  - [x] 4.4 Test `_compute_ece` against hand-computed value
  - [x] 4.5 Test `_wilson_ci` boundary cases: `n=0`, `k=0`, `k=n`
  - [x] 4.6 Test offset exclusion — offset rows must not appear in scored N
  - [x] 4.7 Test empty corpus returns `CalibrationStats` with null metrics (no crash)
  - [x] 4.8 Test conviction bucket count and structure

- [x] **Task 5: Integration test**
  - [x] 5.1 Create `tests/integration/test_worker_calibration.py`
  - [x] 5.2 Seed N closed validation records (mix of hit/miss/offset) via factories
  - [x] 5.3 Invoke `CalibrationService.get_stats()` against the real Postgres container
  - [x] 5.4 Assert returned `CalibrationStats` fields match expected values

## Dev Notes

### Architecture Context

This story completes Epic 3. The calibration engine must be strictly isolated from the extraction compartment — this is the core double-blind integrity guarantee of the whole system.

**Key isolation rule**: `CalibrationService` must query ONLY `validation_record`. It must NEVER join to `corpus_record` for `target_statement`, `extraction_payload`, or `raw_email_bytes`. The only safe column to access from `corpus_record` is `id` (for joining), and even that join is unnecessary — `validation_record` is self-contained for calibration math.

**Data available in `validation_record`** (from Story 3.1):
- `param_value: float` — Asset's raw conviction score (0–100). `predicted_prob = param_value / 100.0`
- `predicted_positive: bool | None` — True if param_value ≥ 50.0
- `actual_positive: bool | None` — True if market moved in predicted direction
- `validation_status: str` — 'hit' | 'miss' | 'offset'
- `closed_at: datetime | None` — set by ClosureService (Story 3.2); NULL means not yet closed

**Temporal drift rule**: `offset` status means the market data was fetched more than 2 hours after expiry. These sessions are epistemologically uncertain — their ground truth may not correspond to the actual moment the Asset was predicting. Exclude them from all metric computations but report their count.

### Statistical Math Reference

**Brier Score**:
```
BS = (1/N) * Σ (p_i - o_i)²
```
- `p_i = param_value / 100.0` (predicted probability, 0.0–1.0)
- `o_i = 1.0 if actual_positive else 0.0`
- N = scored rows (offset excluded)
- Range: [0, 1]. Lower is better. Skill score = 0 → random (0.25 for 50/50 base rate).

**ECE (Expected Calibration Error)** — 10-bin:
```
ECE = Σ_{b=1}^{B} (|B_b| / N) * |avg_confidence(B_b) - fraction_positive(B_b)|
```
- Bin edges: 0.0, 0.1, 0.2, ..., 1.0 (10 bins, left-inclusive)
- `avg_confidence(B_b)` = mean of `p_i` for rows in bin `b`
- `fraction_positive(B_b)` = fraction of `actual_positive == True` in bin `b`
- Empty bins contribute 0.0

**Wilson Score CI** (95%):
```
z = 1.96
p_hat = k / n
center = p_hat + z² / (2n)
margin = z * sqrt(p_hat * (1 - p_hat) / n + z² / (4n²))
denom = 1 + z² / n
lower = (center - margin) / denom
upper = (center + margin) / denom
```
- Returns `(None, None)` when `n == 0`

**Conviction Buckets**:
- 10 equal-width buckets based on `param_value` (not predicted_prob): [0,10), [10,20), ..., [90,100]
- The 100.0 edge case: `param_value == 100.0` goes into bucket 9 (90–100]
- Each bucket: `n`, `hit_rate`, `ci_lower`, `ci_upper`, `avg_conviction`

### Previous Story Learnings

- From Story 3.2: The `ClosureService` sets `closed_at` atomically on a batch of `validation_record` rows. The calibration engine must filter `closed_at IS NOT NULL` to only process epistemologically closed sessions.
- From Story 3.1: `validation_status` is one of 'hit', 'miss', 'offset'. Only 'hit' and 'miss' are scored; 'offset' is excluded.
- From Story 2.2: `@requires(Compartment.CALIBRATION_READ)` is the correct compartment decorator. It is currently a stub (no RLS) but documents the intent.
- Pattern: service files use `from __future__ import annotations` at the top.
- Pattern: services use `sessionmaker[Session]` type for `session_factory`.
- Pattern: MCP tool imports are deferred inside the function body (see `trigger_closure_ceremony` pattern).

### Integration Test Pattern

Follow the pattern from `test_worker_validation.py` and `test_worker_closure.py`:
- Use `db_session` and `patched_db_url` fixtures from conftest
- Use `CorpusRecordFactory` + `ValidationRecordFactory` to seed data
- `ValidationRecordFactory` defaults: `validation_status='hit'`, `param_value=75.0`, `corpus_record_id=uuid4()` (dangling FK — OK for calibration since it never joins back to corpus_record)
- For closed sessions, set `closed_at=datetime.now(UTC)` on the factory call

### MCP Tool Output Format

Return a human-readable plaintext block, not JSON. Example format:
```
=== Apollo Calibration Statistics ===
Corpus: 42 closed sessions (3 offset excluded, 39 scored)
Computed: 2026-06-07T14:32:00Z

--- Overall Metrics ---
Brier Score:   0.1823  (lower → better; random = 0.25)
ECE:           0.0941
Hit Rate:      0.7179  [Wilson 95% CI: 0.5617 – 0.8385]

--- Conviction Buckets ---
Bucket    N   Hit Rate   95% CI
 0–10     2    0.00%    [0.00% –  84.19%]
10–20     0      —           —
20–30     1   100.00%  [20.65% – 100.00%]
...
90–100    8    87.50%  [52.91% –  97.76%]
```

## Dev Agent Record

### Debug Log

- Wilson CI produced tiny floating-point negative (~-2e-17) at k=0 boundary. Fixed by clamping output to [0.0, 1.0] in `_wilson_ci`. This is mathematically correct (probabilities are bounded).
- Integration tests failed with `UniqueViolation` on `ix_corpus_record_raw_hash` when multiple test helpers used the same static `"a"*64` hash. Fixed with `_unique_hash()` using `uuid4().hex * 2`.

### Completion Notes

All 5 tasks complete. 28 unit tests + 8 integration tests = 36 new tests, all passing. Zero regressions in 219-test suite.

**What was implemented:**
- `ConvictionBucket` + `CalibrationStats` Pydantic domain models
- `CalibrationService.get_stats()` under `@requires(Compartment.CALIBRATION_READ)` — queries only `validation_record WHERE closed_at IS NOT NULL`, separates offset rows, computes Brier score, ECE (10-bin, integer-binned), Wilson CI, and 10 conviction buckets
- `get_calibration_stats` MCP tool — returns formatted human-readable readout
- Integer-based binning (`_prob_bin`, `_param_bucket`) avoids all floating-point boundary edge cases
- Double-blind integrity preserved: `CalibrationService` never joins to `corpus_record`

### Review Findings

- [x] [Review][Patch] Missing lower-bound clamp in `_param_bucket` — `param_value < -10.0` returns bucket index `-1`, causing `KeyError` in `bucket_rows` dict [src/apollo/services/calibration.py:39] — fix: `return max(0, min(int(param_value / (100.0 / _N_BUCKETS)), _N_BUCKETS - 1))`
- [x] [Review][Patch] `scored_rows` uses denylist (`!= "offset"`) — unknown `validation_status` values (e.g. `"pending"`, `"error"`) would inflate `n_scored`; use allowlist `in ("hit", "miss")` [src/apollo/services/calibration.py:136]
- [x] [Review][Patch] MCP tool exception path has no logging — add `logger.exception(...)` before returning the error string so failures surface in server logs [src/apollo/mcp/tools.py:108]
- [x] [Review][Patch] AC5 violation: zero-corpus early return omits null metric display — AC requires a readout indicating zero sessions scored with null metric values, not a bare "No closed sessions" message [src/apollo/mcp/tools.py:105]
- [x] [Review][Defer] `NaN` `param_value` causes `ValueError` in `int()` conversion [src/apollo/services/calibration.py:34] — deferred, `param_value` validated ≥0 by extraction Pydantic schema upstream
- [x] [Review][Defer] Bucket label ambiguity at decade boundaries — `param_value=10.0` maps to bucket 1 ("10–20") but label "0–10" implies inclusion of 10; implementation is correct, label is cosmetic [src/apollo/services/calibration.py:93]
- [x] [Review][Defer] `computed_at` stamped after DB session closes — tiny time gap between query completion and timestamp; negligible for this use case [src/apollo/services/calibration.py:162]
- [x] [Review][Defer] Integration test seeds `extraction_payload` with calibration `param_value` — doesn't prove double-blind isolation; deferred, service query is provably isolated by code inspection; test improvement only [tests/integration/test_worker_calibration.py]
- [x] [Review][Defer] No `lazy="raise"` guard on `corpus_record` FK in `ValidationRecord` — future developer could silently break double-blind by accessing the relationship; deferred, architectural hardening [src/apollo/db/models.py]
- [x] [Review][Defer] `test_offset_rows_excluded_from_brier` only asserts score CHANGES when offset row is included, not the correct excluded value — exclusion is correctly tested in `test_get_stats_excludes_offset`; test improvement only [tests/unit/test_calibration_service.py]

## File List

- `src/apollo/domain/models.py` — added `ConvictionBucket`, `CalibrationStats`
- `src/apollo/services/calibration.py` — new file, full calibration engine
- `src/apollo/mcp/tools.py` — added `get_calibration_stats` MCP tool
- `tests/unit/test_calibration_service.py` — new file, 28 unit tests
- `tests/integration/test_worker_calibration.py` — new file, 8 integration tests
- `_bmad-output/implementation-artifacts/3-3-statistical-calibration-scoring.md` — this story file

## Change Log

| Date | Change |
|------|--------|
| 2026-06-07 | Story file created from epic definition; baseline_commit set |
| 2026-06-07 | Implementation complete — CalibrationService, MCP tool, 36 tests, 219/219 pass |
