"""Circuit management tools: create_circuit, append_operation, generate_circuit."""

from __future__ import annotations

import json

import stim

from stim_mcp_server.analytics import log_tool_call

SUPPORTED_TASKS = [
    "repetition_code:memory",
    "surface_code:rotated_memory_x",
    "surface_code:rotated_memory_z",
    "surface_code:unrotated_memory_x",
    "surface_code:unrotated_memory_z",
    "color_code:memory_xyz",
]

_store = None


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


def generate_circuit(
    code_task: str,
    rounds: int,
    distance: int,
    after_clifford_depolarization: float = 0.0,
    before_round_data_depolarization: float = 0.0,
    before_measure_flip_probability: float = 0.0,
    after_reset_flip_probability: float = 0.0,
) -> str:
    """Generate a standard quantum error correction circuit using Stim's built-in generator.

    Args:
        code_task: The code and task, e.g. 'surface_code:rotated_memory_z'.
            Supported values: repetition_code:memory,
            surface_code:rotated_memory_x, surface_code:rotated_memory_z,
            surface_code:unrotated_memory_x, surface_code:unrotated_memory_z,
            color_code:memory_xyz.
        rounds: Number of syndrome measurement rounds.
        distance: Code distance.
        after_clifford_depolarization: Depolarizing noise after Clifford gates (0–1).
        before_round_data_depolarization: Depolarizing noise on data qubits before each round.
        before_measure_flip_probability: Bit-flip probability before measurements.
        after_reset_flip_probability: Bit-flip probability after resets.

    Returns:
        JSON with 'success', 'circuit_id', 'num_qubits', 'num_measurements',
        'num_detectors', 'num_observables', and 'circuit_text' on success,
        or 'success': false, 'error', and 'supported_tasks' on failure.
    """
    try:
        circuit = stim.Circuit.generated(
            code_task,
            rounds=rounds,
            distance=distance,
            after_clifford_depolarization=after_clifford_depolarization,
            before_round_data_depolarization=before_round_data_depolarization,
            before_measure_flip_probability=before_measure_flip_probability,
            after_reset_flip_probability=after_reset_flip_probability,
        )
    except Exception as exc:
        return json.dumps(
            {
                "success": False,
                "error": str(exc),
                "supported_tasks": SUPPORTED_TASKS,
            }
        )

    circuit_id = _store.create(circuit)
    return json.dumps(
        {
            "success": True,
            "circuit_id": circuit_id,
            "num_qubits": circuit.num_qubits,
            "num_measurements": circuit.num_measurements,
            "num_detectors": circuit.num_detectors,
            "num_observables": circuit.num_observables,
            "circuit_text": str(circuit),
        }
    )


def register(mcp, store) -> None:
    global _store
    _store = store
    mcp.tool()(log_tool_call(create_circuit))
    mcp.tool()(log_tool_call(append_operation))
    mcp.tool()(log_tool_call(generate_circuit))
