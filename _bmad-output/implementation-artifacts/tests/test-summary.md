# Test Automation Summary — Epic 1 E2E Tests

## Overview

21 end-to-end tests generated and verified for Epic 1: Target Configuration, Coordinate
Generation, and Email Dispatch. All tests pass against live infrastructure (testcontainers
PostgreSQL + Mailpit SMTP).

**File:** `tests/e2e/test_epic1_e2e.py`

---

## Generated Tests

### Story 1.1 — Target Configuration (`TestEpic1TargetConfiguration`)

| Test | Description |
|------|-------------|
| `test_configure_target_persists_pending_record` | TargetService persists a corpus_record with status=pending, no coordinate, no dispatch columns |
| `test_configure_target_captures_admin_state` | Admin awareness tier and psychological context are stored immutably |
| `test_configure_target_age_in_gate_sets_available_after` | age_in_hours=24 sets available_after to ~now+24h |
| `test_configure_control_target_flag` | is_control_target=True is stored correctly |

### Story 1.2 — Coordinate Generation (`TestEpic1CoordinateGeneration`)

| Test | Description |
|------|-------------|
| `test_tick_assigns_coordinate_after_configure` | tick() assigns a well-formed `XXXX/YYYY` coordinate and advances to dispatched |
| `test_coordinates_are_unique_across_targets` | Three targets receive three distinct coordinates |
| `test_target_not_yet_available_skipped_by_tick` | age_in_hours=24 target stays pending after tick (Age-In gate) |

### Story 1.3 — Email Dispatch with Mailpit (`TestEpic1EmailDispatch`)

| Test | Description |
|------|-------------|
| `test_full_pipeline_delivers_email_to_mailpit` | Full configure→tick pipeline delivers exactly 1 email to Mailpit |
| `test_email_recipient_is_asset_address` | Email To: matches `settings.asset_email_address` |
| `test_email_subject_contains_coordinate` | Subject contains the exact double-blind coordinate |
| `test_email_body_coordinate_matches_db_record` | Body coordinate matches DB `double_blind_coordinate` column |
| `test_email_body_is_double_blind` | Body does NOT contain any fragment of the target statement |
| `test_email_body_contains_all_measurement_fields` | Body contains all 6 measurement fields (PARAM, Time, Location, Sleep quality, Psychological state, Social Field) |
| `test_email_body_contains_parameter_name` | Body includes the parameter name (e.g. `rvd`) |
| `test_db_record_has_dispatch_provenance` | dispatched_at (UTC-aware) and dispatch_agent_version are set on the dispatched record |

### Epic 1 End-to-End Scenarios (`TestEpic1EndToEnd`)

| Test | Description |
|------|-------------|
| `test_multiple_targets_each_deliver_unique_email` | 3 targets → 3 emails, each with a unique coordinate in the subject |
| `test_age_in_gate_prevents_early_dispatch` | age_in_hours=24 produces 0 emails during the current tick |
| `test_second_tick_does_not_redispatch` | Running tick twice does not re-send already-dispatched emails |
| `test_daily_cap_enforced_at_five` | 7 pending targets → ≤5 emails (daily cap enforced) |
| `test_mixed_available_and_gated_targets` | 2 available + 3 gated → 2 emails, 3 records stay pending |
| `test_parameters_preserved_in_dispatched_emails` | VAD and RVD parameters appear in their respective dispatched emails |

---

## Coverage

| Layer | Coverage |
|-------|----------|
| `TargetService.create_target_configuration` | 4/4 ACs covered |
| `QueueService.claim_pending_targets` + `assign_coordinate` | 3/3 ACs covered (coordinate format, uniqueness, Age-In gate) |
| `DispatchService.render_tasking_email` + `mark_dispatched` | 8/8 ACs covered (subject, body, double-blind, fields, provenance) |
| Daily cap enforcement | Covered |
| Idempotency (no re-dispatch) | Covered |
| Mixed available/gated scenarios | Covered |

---

## Infrastructure

- **PostgreSQL:** testcontainers `postgres:16-alpine` (Alembic migrations applied via `db_engine` fixture)
- **SMTP:** Real `SMTPClientImpl` pointed at Mailpit `127.0.0.1:1025`
- **Mailpit verification:** Mailpit HTTP API at `127.0.0.1:8025/api/v1/messages`
- **Skip guard:** Tests are automatically skipped if Mailpit is not reachable (module-level `pytestmark`)
- **Inbox isolation:** `clear_mailpit_inbox` autouse fixture deletes all messages before each test

---

## How to Run

```bash
# Ensure docker-compose services are up:
docker-compose up -d db mailpit

# Run E2E tests:
uv run pytest tests/e2e/test_epic1_e2e.py -v
```

---

## Next Steps

- Add E2E tests for Epic 2 (email ingestion, Pydantic extraction, sealing) once Story 2.1 is implemented
- Integrate `tests/e2e/` into the CI pipeline as a final gate after integration tests
- Consider a dedicated `pytest.ini` marker (`e2e`) to allow selective filtering: `pytest -m e2e`
