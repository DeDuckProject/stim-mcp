"""In-memory store for active Stim circuit sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import stim


@dataclass
class CircuitSession:
    circuit: stim.Circuit
    stats: dict[str, Any] = field(default_factory=dict)


class CircuitStore:
    """Thread-safe in-memory registry of active circuit sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, CircuitSession] = {}

    def create(self, circuit: stim.Circuit) -> str:
        """Store a circuit and return a new session ID."""
        circuit_id = uuid.uuid4().hex[:8]
        self._sessions[circuit_id] = CircuitSession(circuit=circuit)
        return circuit_id

    def get(self, circuit_id: str) -> CircuitSession:
        """Return the session or raise KeyError if not found."""
        if circuit_id not in self._sessions:
            raise KeyError(f"No circuit found with id '{circuit_id}'")
        return self._sessions[circuit_id]

    def update_stats(self, circuit_id: str, stats: dict[str, Any]) -> None:
        self._sessions[circuit_id].stats = stats

    def list_ids(self) -> list[str]:
        return list(self._sessions.keys())

    def delete(self, circuit_id: str) -> None:
        self._sessions.pop(circuit_id, None)
