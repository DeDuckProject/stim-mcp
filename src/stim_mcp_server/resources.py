"""MCP resource handlers."""

from __future__ import annotations

import json

_store = None


def register(mcp, store) -> None:
    global _store
    _store = store

    @mcp.resource("stim://circuit/{circuit_id}")
    def resource_circuit(circuit_id: str) -> str:
        """Raw Stim source code for the circuit session."""
        try:
            session = _store.get(circuit_id)
            return str(session.circuit)
        except KeyError:
            return f"Error: no circuit with id '{circuit_id}'"

    @mcp.resource("stim://dem/{circuit_id}")
    def resource_dem(circuit_id: str) -> str:
        """Detector Error Model for the circuit session (if applicable)."""
        try:
            session = _store.get(circuit_id)
            dem = session.circuit.detector_error_model(decompose_errors=True)
            return str(dem)
        except KeyError:
            return f"Error: no circuit with id '{circuit_id}'"
        except Exception as exc:
            return f"Error building DEM: {exc}"

    @mcp.resource("stim://stats/{circuit_id}")
    def resource_stats(circuit_id: str) -> str:
        """Most recent simulation statistics for the circuit session (JSON)."""
        try:
            session = _store.get(circuit_id)
            if not session.stats:
                return json.dumps({"note": "No simulation has been run yet for this circuit."})
            return json.dumps(session.stats, indent=2)
        except KeyError:
            return f"Error: no circuit with id '{circuit_id}'"
