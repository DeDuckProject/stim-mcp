"""In-memory store for active Stim circuit sessions."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import stim


@dataclass
class CircuitSession:
    circuit: stim.Circuit
    stats: dict[str, Any] = field(default_factory=dict)
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitStore:
    """Thread-safe in-memory registry of active circuit sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, CircuitSession] = {}
        self._lock = threading.Lock()

    def create(self, circuit: stim.Circuit) -> str:
        """Store a circuit and return a new session ID."""
        circuit_id = uuid.uuid4().hex[:8]
        with self._lock:
            self._sessions[circuit_id] = CircuitSession(circuit=circuit)
        return circuit_id

    def get(self, circuit_id: str) -> CircuitSession:
        """Return the session or raise KeyError if not found."""
        with self._lock:
            if circuit_id not in self._sessions:
                raise KeyError(f"No circuit found with id '{circuit_id}'")
            return self._sessions[circuit_id]

    def update_stats(self, circuit_id: str, stats: dict[str, Any]) -> None:
        with self._lock:
            self._sessions[circuit_id].stats = stats
            self._sessions[circuit_id].last_accessed_at = datetime.now(timezone.utc)

    def touch(self, circuit_id: str) -> None:
        """Reset the staleness timer for a session."""
        with self._lock:
            if circuit_id in self._sessions:
                self._sessions[circuit_id].last_accessed_at = datetime.now(timezone.utc)

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def delete(self, circuit_id: str) -> None:
        with self._lock:
            self._sessions.pop(circuit_id, None)

    def cleanup_expired(self, ttl: timedelta) -> int:
        """Delete sessions stale for longer than ttl. Returns the number removed."""
        cutoff = datetime.now(timezone.utc) - ttl
        with self._lock:
            expired = [cid for cid, s in self._sessions.items() if s.last_accessed_at < cutoff]
            for cid in expired:
                del self._sessions[cid]
        return len(expired)
