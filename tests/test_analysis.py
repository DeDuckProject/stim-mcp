"""Tests for analysis tools (tools/analysis.py)."""

from __future__ import annotations

import json

import pytest
import stim

from .helpers import BELL_CIRCUIT, REP_CODE
from stim_mcp_server.server import _store

from stim_mcp_server.tools.analysis import analyze_errors, inject_noise
from stim_mcp_server.tools.circuit_management import create_circuit
from stim_mcp_server.tools.simulation import sample_circuit


class TestAnalyzeErrors:
    def test_rep_code_analysis(self):
        cid = json.loads(create_circuit(str(REP_CODE)))["circuit_id"]
        result = json.loads(analyze_errors(cid))
        assert result["success"] is True
        assert "dem" in result
        assert result["num_errors"] > 0
        # code distance for repetition_code distance=3 should be 3
        assert result["code_distance_lower_bound"] == 3

    def test_no_detectors(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(analyze_errors(cid))
        # No detectors → DEM is empty or error; either way no unhandled exception
        assert "success" in result

    def test_missing_circuit(self):
        result = json.loads(analyze_errors("missing"))
        assert result["success"] is False


class TestInjectNoise:
    def test_depolarize1(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="DEPOLARIZE1", probability=0.01))
        assert result["success"] is True
        assert result["noisy_circuit_id"] != cid
        assert result["source_circuit_id"] == cid

    def test_x_error(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="X_ERROR", probability=0.01))
        assert result["success"] is True

    def test_y_error(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="Y_ERROR", probability=0.01))
        assert result["success"] is True
        assert result["noisy_circuit_id"] != cid

    def test_z_error(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="Z_ERROR", probability=0.01))
        assert result["success"] is True
        assert result["noisy_circuit_id"] != cid

    def test_depolarize2(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="DEPOLARIZE2", probability=0.01))
        assert result["success"] is True
        assert result["noisy_circuit_id"] != cid

    def test_noise_actually_inserted(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="DEPOLARIZE1", probability=0.01))
        noisy_text = str(_store.get(result["noisy_circuit_id"]).circuit)
        assert "DEPOLARIZE1" in noisy_text

    def test_invalid_noise_type(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, noise_type="INVALID"))  # type: ignore[arg-type]
        assert result["success"] is False

    def test_invalid_probability(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        # negative probability is rejected by stim
        result = json.loads(inject_noise(cid, probability=-0.1))
        assert result["success"] is False

    def test_missing_circuit(self):
        result = json.loads(inject_noise("ghost"))
        assert result["success"] is False

    def test_original_circuit_unchanged(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        original_text = str(stim.Circuit(BELL_CIRCUIT))
        inject_noise(cid, probability=0.05)
        assert str(_store.get(cid).circuit) == original_text

    # --- e2e: noise must actually change simulation output ---
    # inject_noise only adds noise after unitary gates, so we need at least one
    # gate in the circuit (e.g. X 0) before the measurement.

    def test_x_error_p1_cancels_x_gate(self):
        # X gate on |0> → |1> (flip_rate=1.0); X_ERROR(1.0) after X gate flips back → |0> (flip_rate=0.0)
        cid = json.loads(create_circuit("X 0\nM 0"))["circuit_id"]
        ideal = json.loads(sample_circuit(cid, shots=100))
        assert ideal["measurement_flip_rates"][0] == pytest.approx(1.0)

        noisy = json.loads(inject_noise(cid, noise_type="X_ERROR", probability=1.0))
        assert noisy["success"] is True
        sample = json.loads(sample_circuit(noisy["noisy_circuit_id"], shots=100))
        assert sample["measurement_flip_rates"][0] == pytest.approx(0.0)

    def test_z_error_does_not_affect_z_basis_measurement(self):
        # Z_ERROR after X gate leaves qubit in |1> (Z flips phase, not measurement outcome)
        cid = json.loads(create_circuit("X 0\nM 0"))["circuit_id"]
        noisy = json.loads(inject_noise(cid, noise_type="Z_ERROR", probability=1.0))
        assert noisy["success"] is True
        sample = json.loads(sample_circuit(noisy["noisy_circuit_id"], shots=100))
        # Z on |1> = -|1>, Z-basis measurement still gives 1
        assert sample["measurement_flip_rates"][0] == pytest.approx(1.0)

    def test_depolarize1_p1_depolarises_measurement(self):
        # X gate → |1>. DEPOLARIZE1(1.0) fully depolarizes: P(measure 1) = 1/3.
        # (X and Y each flip |1> to |0>; only Z leaves it as |1>)
        cid = json.loads(create_circuit("X 0\nM 0"))["circuit_id"]
        noisy = json.loads(inject_noise(cid, noise_type="DEPOLARIZE1", probability=1.0))
        assert noisy["success"] is True
        sample = json.loads(sample_circuit(noisy["noisy_circuit_id"], shots=2000))
        flip_rate = sample["measurement_flip_rates"][0]
        # Expected ~1/3; ideal without noise is 1.0 — so noise clearly changed the output
        assert flip_rate < 0.5

    def test_noise_circuit_text_present_for_all_types(self):
        # Each noise type should appear by name in the noisy circuit text.
        for noise_type in ("X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"):
            cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
            result = json.loads(inject_noise(cid, noise_type=noise_type, probability=0.01))
            assert result["success"] is True, f"{noise_type} inject failed"
            noisy_text = str(_store.get(result["noisy_circuit_id"]).circuit)
            assert noise_type in noisy_text, f"{noise_type} not found in circuit text"
