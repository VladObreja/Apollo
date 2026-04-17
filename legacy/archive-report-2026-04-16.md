# Legacy Workspace Sanitization Report (2026-04-16)

## Archived from old nested workspace
Source root: `Intel/workspace/`
Archive root: `legacy/Intel/workspace/`

### Moved successfully
- `AGENTS.md`
- `BOOTSTRAP.md`
- `HEARTBEAT.md`
- `IDENTITY.md`
- `SOUL.md`
- `TOOLS.md`
- `USER.md`
- `memory/2026-04-16-lightrag-ingestion.md`
- `state/`

### Not moved yet (permissions / ownership friction from running container context)
- `.git/`
- `.openclaw/`
- `vault/` (empty directory)

## Left active intentionally under `Intel/`
These appear to be current OpenClaw runtime/config/state and were not archived:
- `openclaw.json*`
- `memory/`
- `memory.md`
- `tasks/`
- `flows/`
- `logs/`
- `devices/`
- `identity/`
- `subagents/`
- `exec-approvals.json`
- `PROJECT_LOG.md`
- related runtime folders

## Rationale
The goal was to sanitize the clearly obsolete nested workspace while avoiding any risk to the active OpenClaw runtime mounted from `Intel/`.
