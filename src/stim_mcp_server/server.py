"""Stim MCP Server - main entry point."""

from __future__ import annotations

import json
from typing import Literal

import stim
from mcp.server.fastmcp import FastMCP

from .circuit_store import CircuitStore

mcp = FastMCP(
    "stim-mcp-server",
    instructions=(
        "This server exposes Google's Stim quantum stabilizer circuit simulator as MCP tools. "
        "Use create_circuit to start a session, then sample_circuit, analyze_errors, "
        "get_circuit_diagram, inject_noise, and append_operation to explore and refine circuits."
    ),
)

_store = CircuitStore()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@mcp.tool()
def hello_quantum() -> str:
    """Health check. Returns Stim version and the number of active circuit sessions."""
    return json.dumps(
        {
            "status": "ok",
            "stim_version": stim.__version__,
            "active_sessions": len(_store.list_ids()),
        }
    )


# ---------------------------------------------------------------------------
# Phase 1: Circuit management
# ---------------------------------------------------------------------------


@mcp.tool()
def create_circuit(circuit_text: str) -> str:
    """Validate a Stim circuit string and open a persistent session.

    Args:
        circuit_text: A Stim-format circuit (e.g. 'H 0\\nCNOT 0 1\\nM 0 1').

    Returns:
        JSON with 'success' (bool) and 'circuit_id' (str) on success,
        or 'success': false and 'error' on invalid syntax.
    """
    try:
        circuit = stim.Circuit(circuit_text)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})

    circuit_id = _store.create(circuit)
    return json.dumps(
        {
            "success": True,
            "circuit_id": circuit_id,
            "num_qubits": circuit.num_qubits,
            "num_measurements": circuit.num_measurements,
        }
    )


@mcp.tool()
def append_operation(circuit_id: str, operation_text: str) -> str:
    """Append one or more Stim instructions to an existing circuit session.

    This allows iterative circuit construction without resending the whole circuit.

    Args:
        circuit_id: An active circuit session ID.
        operation_text: One or more Stim instruction lines to append
                        (e.g. 'DEPOLARIZE1(0.01) 0 1\\nM 0 1').

    Returns:
        JSON with updated circuit metadata, or an error message.
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    try:
        extension = stim.Circuit(operation_text)
        session.circuit += extension
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})

    return json.dumps(
        {
            "success": True,
            "circuit_id": circuit_id,
            "num_qubits": session.circuit.num_qubits,
            "num_measurements": session.circuit.num_measurements,
        }
    )


# ---------------------------------------------------------------------------
# Phase 2: Simulation
# ---------------------------------------------------------------------------


@mcp.tool()
def sample_circuit(circuit_id: str, shots: int = 1000) -> str:
    """Compile and simulate a circuit, returning measurement statistics.

    Args:
        circuit_id: An active circuit session ID.
        shots: Number of simulation shots (default 1000, max 1_000_000).

    Returns:
        JSON summary: shot count, per-measurement-bit flip rates, and
        (if the circuit has detectors) logical error rate per shot.
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    shots = min(max(1, shots), 1_000_000)
    circuit = session.circuit

    result: dict = {"success": True, "circuit_id": circuit_id, "shots": shots}

    # --- Measurement samples ---
    if circuit.num_measurements > 0:
        sampler = circuit.compile_sampler()
        samples = sampler.sample(shots=shots)  # shape: (shots, num_measurements)
        flip_rates = samples.mean(axis=0).tolist()
        result["measurement_flip_rates"] = flip_rates
        result["num_measurements"] = circuit.num_measurements
    else:
        result["measurement_flip_rates"] = []
        result["num_measurements"] = 0

    # --- Logical error rate (requires detectors + observables) ---
    if circuit.num_detectors > 0 and circuit.num_observables > 0:
        try:
            det_sampler = circuit.compile_detector_sampler()
            _, obs_data = det_sampler.sample(shots=shots, separate_observables=True)
            # obs_data shape: (shots, num_observables)
            logical_error_per_obs = obs_data.mean(axis=0).tolist()
            result["logical_error_rates"] = logical_error_per_obs
            result["num_observables"] = circuit.num_observables
        except Exception as exc:
            result["logical_error_rates"] = None
            result["logical_error_note"] = str(exc)

    _store.update_stats(circuit_id, result)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Phase 3: Error analysis
# ---------------------------------------------------------------------------


@mcp.tool()
def analyze_errors(circuit_id: str) -> str:
    """Build the Detector Error Model and find the shortest logical error paths.

    Args:
        circuit_id: An active circuit session ID.

    Returns:
        JSON with the DEM (as text) and the shortest graphlike error path
        (i.e. the minimum number of physical errors needed to cause an
        undetected logical failure — this gives the effective code distance).
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    circuit = session.circuit

    try:
        dem = circuit.detector_error_model(decompose_errors=True)
    except Exception as exc:
        return json.dumps(
            {
                "success": False,
                "error": (
                    f"Could not build Detector Error Model: {exc}. "
                    "Ensure the circuit has DETECTOR and OBSERVABLE_INCLUDE instructions."
                ),
            }
        )

    result: dict = {
        "success": True,
        "circuit_id": circuit_id,
        "dem": str(dem),
        "num_errors": dem.num_errors,
        "num_detectors": dem.num_detectors,
        "num_observables": dem.num_observables,
    }

    try:
        shortest = dem.shortest_graphlike_error()
        result["shortest_error_path"] = str(shortest)
        result["code_distance_lower_bound"] = len(shortest)
    except Exception as exc:
        result["shortest_error_path"] = None
        result["shortest_error_note"] = str(exc)

    return json.dumps(result)


# ---------------------------------------------------------------------------
# Phase 4: Visualization
# ---------------------------------------------------------------------------


@mcp.tool()
def get_circuit_diagram(
    circuit_id: str,
    diagram_type: Literal["text", "svg", "timeline"] = "text",
) -> str:
    """Generate a visual or textual representation of the circuit.

    Args:
        circuit_id: An active circuit session ID.
        diagram_type: One of:
            - 'text'     → ASCII timeline diagram
            - 'timeline' → alias for 'text'
            - 'svg'      → SVG timeline image (returns SVG markup)

    Returns:
        JSON with 'diagram' (string content) and 'format' fields, or an error.
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    circuit = session.circuit
    stim_type_map = {
        "text": "timeline-text",
        "timeline": "timeline-text",
        "svg": "timeline-svg",
    }
    stim_diagram_type = stim_type_map.get(diagram_type, "timeline-text")

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


# ---------------------------------------------------------------------------
# Noise injection
# ---------------------------------------------------------------------------


@mcp.tool()
def inject_noise(
    circuit_id: str,
    noise_type: Literal["DEPOLARIZE1", "X_ERROR"] = "DEPOLARIZE1",
    probability: float = 0.001,
) -> str:
    """Insert noise gates after every gate in the circuit to model a noisy device.

    A new circuit session is created with the noisy version; the original is unchanged.

    Args:
        circuit_id: An active circuit session ID (source circuit).
        noise_type: 'DEPOLARIZE1' (depolarizing noise) or 'X_ERROR' (bit-flip noise).
        probability: Error probability per gate (0 < p <= 0.5).

    Returns:
        JSON with a new 'circuit_id' for the noisy circuit, or an error.
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    if not (0 < probability <= 0.5):
        return json.dumps(
            {"success": False, "error": "probability must be in (0, 0.5]"}
        )

    if noise_type not in ("DEPOLARIZE1", "X_ERROR"):
        return json.dumps(
            {"success": False, "error": "noise_type must be 'DEPOLARIZE1' or 'X_ERROR'"}
        )

    circuit = session.circuit

    # Build a noisy version by inserting after-clifford errors
    try:
        if noise_type == "DEPOLARIZE1":
            noisy = circuit.with_noise(after_clifford_depolarization=probability)
        else:
            # X_ERROR: rebuild manually by appending X_ERROR after measurements
            # Use with_noise for a best-effort approach via before_measure_flip
            noisy = circuit.with_noise(before_measure_flip_probability=probability)
    except AttributeError:
        # Older stim versions may not have with_noise; fall back to manual append
        noisy_text = str(circuit)
        n = circuit.num_qubits
        targets = " ".join(str(i) for i in range(n))
        noisy_text += f"\n{noise_type}({probability}) {targets}"
        try:
            noisy = stim.Circuit(noisy_text)
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    new_id = _store.create(noisy)
    return json.dumps(
        {
            "success": True,
            "source_circuit_id": circuit_id,
            "noisy_circuit_id": new_id,
            "noise_type": noise_type,
            "probability": probability,
        }
    )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
