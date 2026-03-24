"""Tool usage analytics — logs tool name only, no arguments or user data."""

from __future__ import annotations

import functools
import logging

logger = logging.getLogger("stim_mcp.tools")


def log_tool_call(fn):
    """Wrap a tool function to emit a structured log line on each invocation."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        logger.info("tool_call tool=%s", fn.__name__)
        return fn(*args, **kwargs)
    return wrapper
