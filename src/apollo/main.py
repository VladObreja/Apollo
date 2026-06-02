"""
Apollo application entrypoint.

Dispatches sub-commands based on sys.argv:
    apollo tick     — run worker tick (claim targets, assign coordinates)
    apollo mcp      — start the FastMCP server (Claude Code interface)
    apollo          — defaults to MCP server (backwards-compatible)
"""

import sys


def main() -> None:
    """CLI entrypoint declared in pyproject.toml as ``apollo``."""
    args = sys.argv[1:]
    sub = args[0] if args else "mcp"

    if sub == "tick":
        from apollo.services.worker import tick

        tick()
    elif sub == "mcp":
        from apollo.mcp import tools as _tools  # noqa: F401 — registers MCP tools
        from apollo.mcp.server import mcp

        mcp.run()
    else:
        print(f"Unknown sub-command: {sub!r}", file=sys.stderr)
        print("Usage: apollo [tick|mcp]", file=sys.stderr)
        sys.exit(1)
