"""
Apollo application entrypoint.

Starts the FastMCP server over stdio transport (Claude Code default).
Importing `tools` registers all @mcp.tool() decorators against the server.
"""
from apollo.mcp import tools as _tools  # noqa: F401 — registers MCP tools
from apollo.mcp.server import mcp


def main() -> None:
    """CLI entrypoint: `apollo` (declared in pyproject.toml)."""
    mcp.run()
