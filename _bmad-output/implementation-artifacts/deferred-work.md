# Deferred Work

## Deferred from: code review of 1-1-initialize-domain-target-configuration-mcp (2026-06-02)

- Hardcoded DB URL default `postgresql://postgres:postgres@localhost:5432/apollo` in `config.py` — acceptable for local dev scaffold; must document in README that `.env` is required before any non-local deployment.
- No test factory pattern (`factory_boy`) — unit tests currently use direct model instantiation which is acceptable for Story 1.1 scope; integration tests will require factory patterns to protect against schema evolution breakage.
- Missing `docker-compose.yml` for local PostgreSQL — AC-WSL-1 infra qualification is a separate architecture concern; create as part of infrastructure setup story.
- Missing GitHub Actions CI pipeline `.github/workflows/ci.yml` — architecture mandates sequential gating (ruff → mypy → unit → integration → alembic reversibility); not in Story 1.1 acceptance criteria, create as a dedicated DevOps story.
- Table naming convention: `corpus_record` (singular) adopted going forward — architecture.md naming conventions section must be updated from "plural" to "singular" to align with the implemented convention.
- `awareness_tier` and `parameter_name` enums in `domain/types.py` — domain vocabulary (`vad`, `rvd`, `ebf`, tier levels) still being finalized; add `ParameterName` and `AwarenessTier` enums and update service/migration check constraints in a future story.

## Deferred from: code review of 1-2-event-driven-queue-coordinate-generation (2026-06-02)

- No structured logging initialization in the CLI entrypoint (`main.py`), so worker log messages are not printed or formatted as structured JSON. [main.py](file:///c:/Apollo/src/apollo/main.py#L13)

## Deferred from: code review of 1-3-task-email-dispatch (2026-06-02)

- Deduplicate FakeSMTPClient across test files [tests/integration/test_worker_dispatch.py] — deferred, pre-existing
- db_session fixture rollback teardown is a no-op [tests/integration/test_worker_dispatch.py] — deferred, pre-existing

## Deferred from: code review of 2-1-inbound-email-ingestion-parsing (2026-06-02)

- IMAP connection is opened and closed on every fetch_unseen_emails [services/email_poller.py]
- imap_use_ssl = False default has no security warning [src/apollo/config.py]
- FakeIMAPClient reused across tick calls causes all emails to be re-delivered [tests/utils.py]

- Prompt injection via unbounded email_body � The template inserts Asset-controlled email content verbatim into the LLM instruction context with autoescape=False. � deferred, We accept the risk of prompt injection from Assets for now. [_bmad-output/implementation-artifacts/2-1-inbound-email-ingestion-parsing.md]
