# Deferred Work

## Deferred from: code review of 1-1-initialize-domain-target-configuration-mcp (2026-06-02)

- Hardcoded DB URL default `postgresql://postgres:postgres@localhost:5432/apollo` in `config.py` — acceptable for local dev scaffold; must document in README that `.env` is required before any non-local deployment.
- No test factory pattern (`factory_boy`) — unit tests currently use direct model instantiation which is acceptable for Story 1.1 scope; integration tests will require factory patterns to protect against schema evolution breakage.
- Missing `docker-compose.yml` for local PostgreSQL — AC-WSL-1 infra qualification is a separate architecture concern; create as part of infrastructure setup story.
- Missing GitHub Actions CI pipeline `.github/workflows/ci.yml` — architecture mandates sequential gating (ruff → mypy → unit → integration → alembic reversibility); not in Story 1.1 acceptance criteria, create as a dedicated DevOps story.
- Table naming convention: `corpus_record` (singular) adopted going forward — architecture.md naming conventions section must be updated from "plural" to "singular" to align with the implemented convention.
- `awareness_tier` and `parameter_name` enums in `domain/types.py` — domain vocabulary (`vad`, `rvd`, `ebf`, tier levels) still being finalized; add `ParameterName` and `AwarenessTier` enums and update service/migration check constraints in a future story.
