"""Tests for visualization tools (tools/visualization.py)."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Image

from .helpers import BELL_CIRCUIT

from stim_mcp_server.tools.circuit_management import create_circuit
from stim_mcp_server.tools.visualization import get_circuit_diagram


class TestGetCircuitDiagram:
    def test_text_diagram(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(get_circuit_diagram(cid, diagram_type="text"))
        assert result["success"] is True
        assert isinstance(result["diagram"], str)
        assert len(result["diagram"]) > 0

    def test_timeline_alias(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(get_circuit_diagram(cid, diagram_type="timeline"))
        assert result["success"] is True

    def test_svg_diagram_returns_image(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = get_circuit_diagram(cid, diagram_type="svg")
        assert isinstance(result, Image)
        assert result._mime_type == "image/png"
        assert len(result.data) > 0

    def test_crumble_url(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(get_circuit_diagram(cid, diagram_type="crumble"))
        assert result["success"] is True
        assert "url" in result
        assert "algassert.com/crumble" in result["url"]

    def test_crumble_is_default(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(get_circuit_diagram(cid))
        assert result["success"] is True
        assert result["format"] == "crumble"
        assert "url" in result

    def test_missing_circuit(self):
        result = json.loads(get_circuit_diagram("ghost", diagram_type="text"))
        assert result["success"] is False
