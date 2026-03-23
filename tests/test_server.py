"""Tests for the Stim MCP Server tools and circuit store."""

from __future__ import annotations

import json

import pytest
import stim
from mcp.server.fastmcp import Image

from stim_mcp_server.circuit_store import CircuitStore
# Import server to trigger registration (sets _store in all tool modules)
from stim_mcp_server.server import _store  # noqa: F401
from stim_mcp_server.tools.health import hello_quantum
from stim_mcp_server.tools.circuit_management import (
    create_circuit,
    append_operation,
    generate_circuit,
)
from stim_mcp_server.tools.simulation import sample_circuit
from stim_mcp_server.tools.analysis import analyze_errors, inject_noise
from stim_mcp_server.tools.visualization import get_circuit_diagram


# ---------------------------------------------------------------------------
# CircuitStore unit tests
# ---------------------------------------------------------------------------


class TestCircuitStore:
    def test_create_and_get(self):
        store = CircuitStore()
        circuit = stim.Circuit("H 0\nM 0")
        cid = store.create(circuit)
        assert len(cid) == 32
        session = store.get(cid)
        assert session.circuit == circuit

    def test_get_missing_raises(self):
        store = CircuitStore()
        with pytest.raises(KeyError, match="No circuit found"):
            store.get("nonexistent")

    def test_update_stats(self):
        store = CircuitStore()
        cid = store.create(stim.Circuit("H 0\nM 0"))
        store.update_stats(cid, {"shots": 100})
        assert store.get(cid).stats["shots"] == 100

    def test_list_ids(self):
        store = CircuitStore()
        cid1 = store.create(stim.Circuit("H 0"))
        cid2 = store.create(stim.Circuit("H 1"))
        ids = store.list_ids()
        assert cid1 in ids and cid2 in ids

    def test_delete(self):
        store = CircuitStore()
        cid = store.create(stim.Circuit("H 0"))
        store.delete(cid)
        with pytest.raises(KeyError):
            store.get(cid)


# ---------------------------------------------------------------------------
# hello_quantum
# ---------------------------------------------------------------------------


class TestHelloQuantum:
    def test_returns_ok(self):
        result = json.loads(hello_quantum())
        assert result["status"] == "ok"
        assert "stim_version" in result
        assert isinstance(result["active_sessions"], int)


# ---------------------------------------------------------------------------
# create_circuit
# ---------------------------------------------------------------------------


BELL_CIRCUIT = "H 0\nCNOT 0 1\nM 0 1"
REP_CODE = stim.Circuit.generated(
    "repetition_code:memory", rounds=3, distance=3, before_round_data_depolarization=0.01
)


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


# ---------------------------------------------------------------------------
# append_operation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# sample_circuit
# ---------------------------------------------------------------------------


class TestSampleCircuit:
    def test_basic_sampling(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(sample_circuit(cid, shots=100))
        assert result["success"] is True
        assert result["shots"] == 100
        assert len(result["measurement_flip_rates"]) == 2

    def test_shots_clamped_to_max(self):
        cid = json.loads(create_circuit("H 0\nM 0"))["circuit_id"]
        result = json.loads(sample_circuit(cid, shots=999_999_999))
        assert result["shots"] == 1_000_000

    def test_shots_clamped_to_min(self):
        cid = json.loads(create_circuit("H 0\nM 0"))["circuit_id"]
        result = json.loads(sample_circuit(cid, shots=0))
        assert result["shots"] == 1

    def test_missing_circuit(self):
        result = json.loads(sample_circuit("nope", shots=10))
        assert result["success"] is False

    def test_logical_error_rate_reported(self):
        cid = json.loads(create_circuit(str(REP_CODE)))["circuit_id"]
        result = json.loads(sample_circuit(cid, shots=200))
        assert result["success"] is True
        assert "logical_error_rates" in result
        assert isinstance(result["logical_error_rates"], list)

    def test_no_measurements_circuit(self):
        cid = json.loads(create_circuit("H 0\nH 1"))["circuit_id"]
        result = json.loads(sample_circuit(cid, shots=10))
        assert result["success"] is True
        assert result["measurement_flip_rates"] == []


# ---------------------------------------------------------------------------
# analyze_errors
# ---------------------------------------------------------------------------


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
        # No detectors → DEM is empty or error
        # Either way should not raise an unhandled exception
        assert "success" in result

    def test_missing_circuit(self):
        result = json.loads(analyze_errors("missing"))
        assert result["success"] is False


# ---------------------------------------------------------------------------
# get_circuit_diagram
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# inject_noise
# ---------------------------------------------------------------------------


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

    def test_invalid_probability(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        result = json.loads(inject_noise(cid, probability=0.0))
        assert result["success"] is False

        result2 = json.loads(inject_noise(cid, probability=0.9))
        assert result2["success"] is False

    def test_missing_circuit(self):
        result = json.loads(inject_noise("ghost"))
        assert result["success"] is False

    def test_original_circuit_unchanged(self):
        cid = json.loads(create_circuit(BELL_CIRCUIT))["circuit_id"]
        original_text = str(stim.Circuit(BELL_CIRCUIT))
        inject_noise(cid, probability=0.05)
        from stim_mcp_server.server import _store
        assert str(_store.get(cid).circuit) == original_text


# ---------------------------------------------------------------------------
# generate_circuit
# ---------------------------------------------------------------------------


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

        # sample it
        sample_result = json.loads(sample_circuit(cid, shots=100))
        assert sample_result["success"] is True
        assert sample_result["shots"] == 100
        assert "logical_error_rates" in sample_result

        # analyze it
        analysis_result = json.loads(analyze_errors(cid))
        assert analysis_result["success"] is True
        assert analysis_result["num_errors"] > 0

        # diagram it
        diag_result = json.loads(get_circuit_diagram(cid, diagram_type="crumble"))
        assert diag_result["success"] is True
        assert "url" in diag_result
