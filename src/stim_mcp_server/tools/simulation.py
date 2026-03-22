"""Simulation tool: sample_circuit."""

from __future__ import annotations

import json

_store = None


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


def register(mcp, store) -> None:
    global _store
    _store = store
    mcp.tool()(sample_circuit)
