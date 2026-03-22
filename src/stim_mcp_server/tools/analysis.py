"""Analysis tools: analyze_errors, inject_noise."""

from __future__ import annotations

import json
from typing import Literal

import stim

_store = None


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

    try:
        if noise_type == "DEPOLARIZE1":
            noisy = circuit.with_noise(after_clifford_depolarization=probability)
        else:
            noisy = circuit.with_noise(before_measure_flip_probability=probability)
    except AttributeError:
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


def register(mcp, store) -> None:
    global _store
    _store = store
    mcp.tool()(analyze_errors)
    mcp.tool()(inject_noise)
