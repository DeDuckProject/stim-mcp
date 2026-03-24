"""Visualization tool: get_circuit_diagram."""

from __future__ import annotations

import json
from typing import Any, Literal

import cairosvg
from mcp.server.fastmcp import Image

from stim_mcp_server.analytics import log_tool_call

_store = None


def get_circuit_diagram(
    circuit_id: str,
    diagram_type: Literal["text", "svg", "timeline", "crumble"] = "crumble",
) -> Any:
    """Generate a visual or textual representation of the circuit.

    Args:
        circuit_id: An active circuit session ID.
        diagram_type: One of:
            - 'crumble'  → URL to interactive Crumble visualizer (default, most token-efficient)
            - 'text'     → ASCII timeline diagram
            - 'timeline' → alias for 'text'
            - 'svg'      → SVG timeline image (returned as an image, not markup)

    Returns:
        For 'crumble': JSON with a 'url' field linking to the Crumble editor.
        For 'text'/'timeline': JSON with 'diagram' (ASCII string).
        For 'svg': An image rendered by the client.
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    circuit = session.circuit

    if diagram_type == "crumble":
        try:
            url = circuit.to_crumble_url()
            return json.dumps(
                {
                    "success": True,
                    "circuit_id": circuit_id,
                    "format": "crumble",
                    "url": url,
                }
            )
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    if diagram_type == "svg":
        try:
            svg_str = str(circuit.diagram(type="timeline-svg"))
            png_bytes = cairosvg.svg2png(bytestring=svg_str.encode("utf-8"))
            return Image(data=png_bytes, format="png")
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    # text / timeline
    stim_diagram_type = "timeline-text"
    try:
        diagram = circuit.diagram(type=stim_diagram_type)
        return json.dumps(
            {
                "success": True,
                "circuit_id": circuit_id,
                "format": diagram_type,
                "diagram": str(diagram),
            }
        )
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def register(mcp, store) -> None:
    global _store
    _store = store
    mcp.tool()(log_tool_call(get_circuit_diagram))
