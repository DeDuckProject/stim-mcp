"""Health check tool."""

from __future__ import annotations

import json

import stim

from stim_mcp_server.analytics import log_tool_call

_store = None


def hello_quantum() -> str:
    """Health check. Returns Stim version and the number of active circuit sessions."""
    return json.dumps(
        {
            "status": "ok",
            "stim_version": stim.__version__,
            "active_sessions": len(_store.list_ids()),
            "privacy_notice": (
                "This is a shared server. Circuit IDs are 128-bit random tokens "
                "and are not guessable, but there is no user authentication or "
                "access control. Do not use this server for sensitive circuits. "
                "For private use, run the MCP server locally. "
                "Tool invocations are logged anonymously (tool name only) for usage analytics."
            ),
        }
    )


def register(mcp, store) -> None:
    global _store
    _store = store
    mcp.tool()(log_tool_call(hello_quantum))
