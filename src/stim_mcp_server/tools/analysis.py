"""Analysis tools: analyze_errors, inject_noise."""

from __future__ import annotations

import json
from typing import Literal

import stim

from stim_mcp_server.analytics import log_tool_call

_store = None

_SINGLE_QUBIT_NOISE = {"DEPOLARIZE1", "X_ERROR", "Y_ERROR", "Z_ERROR"}
_TWO_QUBIT_NOISE = {"DEPOLARIZE2"}
_SUPPORTED_NOISE_TYPES = _SINGLE_QUBIT_NOISE | _TWO_QUBIT_NOISE


def _inject_noise_into_circuit(
    circuit: stim.Circuit, noise_type: str, probability: float
) -> stim.Circuit:
    noisy = stim.Circuit()
    is_two_qubit = noise_type in _TWO_QUBIT_NOISE

    for instruction in circuit.flattened():
        noisy.append(instruction)
        gate_data = stim.gate_data(instruction.name)
        if not gate_data.is_unitary:
            continue
        targets = instruction.targets_copy()
        if is_two_qubit and gate_data.is_two_qubit_gate:
            for i in range(0, len(targets), 2):
                noisy.append(noise_type, [targets[i], targets[i + 1]], probability)
        elif not is_two_qubit and (gate_data.is_single_qubit_gate or gate_data.is_two_qubit_gate):
            noisy.append(noise_type, targets, probability)

    return noisy


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
    noise_type: Literal["DEPOLARIZE1", "DEPOLARIZE2", "X_ERROR", "Y_ERROR", "Z_ERROR"] = "DEPOLARIZE1",
    probability: float = 0.001,
) -> str:
    """Insert noise gates after every gate in the circuit to model a noisy device.

    Iterates all instructions in the circuit and inserts the specified noise channel
    after each unitary gate. A new circuit session is created; the original is unchanged.

    Args:
        circuit_id: An active circuit session ID (source circuit).
        noise_type: The Stim noise channel to insert. Supported values:
            - 'DEPOLARIZE1': Single-qubit depolarizing noise (equal X/Y/Z mix) after 1q gates.
            - 'DEPOLARIZE2': Two-qubit depolarizing noise (equal mix of 15 Pauli pairs) after 2q gates.
            - 'X_ERROR': Bit-flip noise after 1q gates.
            - 'Y_ERROR': Y-flip noise after 1q gates.
            - 'Z_ERROR': Phase-flip noise after 1q gates.
        probability: Error probability per gate. Validated by Stim (e.g. must be in (0, 1]).

    Returns:
        JSON with a new 'noisy_circuit_id' for the noisy circuit, or an error.
    """
    try:
        session = _store.get(circuit_id)
    except KeyError as exc:
        return json.dumps({"success": False, "error": str(exc)})

    if noise_type not in _SUPPORTED_NOISE_TYPES:
        return json.dumps(
            {
                "success": False,
                "error": f"noise_type must be one of: {sorted(_SUPPORTED_NOISE_TYPES)}",
            }
        )

    circuit = session.circuit

    try:
        noisy = _inject_noise_into_circuit(circuit, noise_type, probability)
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
    mcp.tool()(log_tool_call(analyze_errors))
    mcp.tool()(log_tool_call(inject_noise))
