"""Tests for health tools (tools/health.py)."""

from __future__ import annotations

import json

from stim_mcp_server.tools.health import hello_quantum


class TestHelloQuantum:
    def test_returns_ok(self):
        result = json.loads(hello_quantum())
        assert result["status"] == "ok"
        assert "stim_version" in result
        assert isinstance(result["active_sessions"], int)
