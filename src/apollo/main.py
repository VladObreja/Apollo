"""
Apollo application entrypoint.

Dispatches sub-commands based on sys.argv:
    apollo tick     — run worker tick (claim targets, assign coordinates)
    apollo mcp      — start the FastMCP server (Claude Code interface)
    apollo          — defaults to MCP server (backwards-compatible)
"""

import json
import logging
import logging.config
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": "INFO",
            },
        }
    )


def main() -> None:
    """CLI entrypoint declared in pyproject.toml as ``apollo``."""
    setup_logging()
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
