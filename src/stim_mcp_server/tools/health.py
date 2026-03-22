"""Health check tool."""

from __future__ import annotations

import json

import stim

_store = None


def hello_quantum() -> str:
    """Health check. Returns Stim version and the number of active circuit sessions."""
    return json.dumps(
        {
            "status": "ok",
            "stim_version": stim.__version__,
            "active_sessions": len(_store.list_ids()),
        }
    )


def register(mcp, store) -> None:
    global _store
    _store = store
    mcp.tool()(hello_quantum)
