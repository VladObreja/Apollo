"""
Apollo MCP server instance.

All MCP tools register themselves against this `mcp` object via the
`@mcp.tool()` decorator in `tools.py`. The server is started by `main.py`.
"""

from mcp.server.fastmcp import FastMCP

mcp: FastMCP = FastMCP("apollo")
