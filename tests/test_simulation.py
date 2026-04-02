"""Tests for simulation tools (tools/simulation.py)."""

from __future__ import annotations

import json

from .helpers import BELL_CIRCUIT, REP_CODE

from stim_mcp_server.tools.circuit_management import create_circuit
from stim_mcp_server.tools.simulation import sample_circuit


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
