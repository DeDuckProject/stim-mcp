"""Tests for circuit management tools (tools/circuit_management.py)."""

from __future__ import annotations

import json

from .helpers import BELL_CIRCUIT, REP_CODE

from stim_mcp_server.tools.circuit_management import (
    append_operation,
    create_circuit,
    generate_circuit,
)
from stim_mcp_server.tools.analysis import analyze_errors
from stim_mcp_server.tools.simulation import sample_circuit
from stim_mcp_server.tools.visualization import get_circuit_diagram


class TestCreateCircuit:
    def test_valid_circuit(self):
        result = json.loads(create_circuit(BELL_CIRCUIT))
        assert result["success"] is True
        assert len(result["circuit_id"]) == 32
        assert result["num_qubits"] == 2
        assert result["num_measurements"] == 2

    def test_invalid_syntax(self):
        result = json.loads(create_circuit("NOT_A_GATE 0"))
        assert result["success"] is False
        assert "error" in result

    def test_empty_circuit(self):
        result = json.loads(create_circuit(""))
        assert result["success"] is True
        assert result["num_qubits"] == 0


class TestAppendOperation:
    def test_append_valid(self):
        cid = json.loads(create_circuit("H 0"))["circuit_id"]
        result = json.loads(append_operation(cid, "M 0"))
        assert result["success"] is True
        assert result["num_measurements"] == 1

    def test_append_invalid_syntax(self):
        cid = json.loads(create_circuit("H 0"))["circuit_id"]
        result = json.loads(append_operation(cid, "INVALID_GATE 0"))
        assert result["success"] is False

    def test_append_missing_circuit(self):
        result = json.loads(append_operation("badid", "H 0"))
        assert result["success"] is False
        assert "badid" in result["error"]


class TestGenerateCircuit:
    def test_repetition_code(self):
        result = json.loads(generate_circuit("repetition_code:memory", rounds=5, distance=3))
        assert result["success"] is True
        assert len(result["circuit_id"]) == 32
        assert result["num_qubits"] > 0
        assert result["num_detectors"] > 0
        assert result["num_observables"] > 0
        assert isinstance(result["circuit_text"], str)

    def test_surface_code(self):
        result = json.loads(
            generate_circuit("surface_code:rotated_memory_z", rounds=3, distance=3)
        )
        assert result["success"] is True
        assert result["num_qubits"] > 0
        assert result["num_detectors"] > 0

    def test_with_noise(self):
        result = json.loads(
            generate_circuit(
                "repetition_code:memory",
                rounds=3,
                distance=3,
                after_clifford_depolarization=0.001,
                before_round_data_depolarization=0.001,
                before_measure_flip_probability=0.001,
                after_reset_flip_probability=0.001,
            )
        )
        assert result["success"] is True

    def test_invalid_code_task(self):
        result = json.loads(generate_circuit("not_a_code:task", rounds=3, distance=3))
        assert result["success"] is False
        assert "error" in result
        assert "supported_tasks" in result
        assert isinstance(result["supported_tasks"], list)
        assert len(result["supported_tasks"]) > 0

    def test_generated_circuit_usable(self):
        gen = json.loads(generate_circuit("repetition_code:memory", rounds=3, distance=3,
                                          before_round_data_depolarization=0.01))
        assert gen["success"] is True
        cid = gen["circuit_id"]

        sample_result = json.loads(sample_circuit(cid, shots=100))
        assert sample_result["success"] is True
        assert sample_result["shots"] == 100
        assert "logical_error_rates" in sample_result

        analysis_result = json.loads(analyze_errors(cid))
        assert analysis_result["success"] is True
        assert analysis_result["num_errors"] > 0

        diag_result = json.loads(get_circuit_diagram(cid, diagram_type="crumble"))
        assert diag_result["success"] is True
        assert "url" in diag_result
