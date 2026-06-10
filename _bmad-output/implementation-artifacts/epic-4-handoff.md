# Epic 4 Handoff

**Date:** 2026-06-10
**From:** Session A-C (sprint planning / Correct Course)
**Status:** Epics 1–3 done. Epic 4 (Hardening & Tech Debt) approved, all 5 stories `backlog`, none started.

## Where to start

No Epic 4 story files exist yet in this directory. For each story, run
`bmad-create-story` first to generate the story spec, then `bmad-dev-story`
to implement it. Recommended order (per sprint-change-proposal):

1. **Story 4.1 — Worker Resilience & E2E Repair** (High priority, do first)
   - Fix 4 failing tests in `tests/e2e/test_epic2_e2e.py`
   - Scope `IntegrityError` catches in `worker.py` (Phase 3 sealing) and `validate.py` (`_validate_one`)
   - Stop `extraction_success` inflation from concurrent-seal handling / decorator re-raises
   - Add retry-limit/dead-letter for `b""` empty `raw_email_bytes` in `seal.py`
2. **Story 4.5 — Operator SOP Documentation** (High priority, owner: Tech Writer/Paige) — can run in parallel with 4.1–4.4
3. **Story 4.2 — Operational Hardening** (Medium): `imap_use_ssl` warning, `expiry_at` ISO parsing in `configure_target`, fingerprint-backfill on subsequent tick
4. **Story 4.3 — Domain Vocabulary Formalization** (Medium): `ParameterName`/`AwarenessTier` enums + Alembic check-constraint migration (must prove `upgrade head` → `downgrade base` → `upgrade head`)
5. **Story 4.4 — Test & Code Quality Cleanup** (Low): can be folded into other stories' review cycles

Full acceptance criteria for all 5 stories are in `_bmad-output/planning-artifacts/epics.md` (Epic 4 section).

## Reference docs

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-10.md` — full triage rationale for all 40 prior deferred items
- `_bmad-output/planning-artifacts/architecture.md` — new "Known Limitations / Accepted Risk (V1)" section (9 items, no code changes planned for these)
- `_bmad-output/implementation-artifacts/epic-3-retro-2026-06-09.md` — retro that motivated this epic
- `_bmad-output/implementation-artifacts/deferred-work.md` — now cleared; new findings from future code reviews append here

## Environment notes

- Apollo MCP server is registered in `.mcp.json` (tools: `configure_target`, `get_calibration_stats`, `trigger_closure_ceremony`)
- `.claude/settings.json` `defaultMode` is `default` (was `dontAsk`) — expect permission prompts for new tool/command types

## Loose ends (not blocking, deferred by Vlad on 2026-06-10)

- `data/ollama/id_ed25519` — private SSH key, untracked, not yet gitignored
- Leftover June 6 review scratch files in `implementation-artifacts/`: `diff.patch`, `diff-checkpoint.patch`, `review-diff.patch`, `story-3.2-review.diff`, `prompt-*.md` — candidates for cleanup whenever convenient
