"""Tests for CircuitStore (circuit_store.py)."""

from __future__ import annotations

import pytest
import stim

from stim_mcp_server.circuit_store import CircuitStore


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
