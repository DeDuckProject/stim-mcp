"""Background cleanup job: evicts stale circuit sessions."""

from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta

from .circuit_store import CircuitStore

_TTL = timedelta(weeks=1)
_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours

_log = logging.getLogger(__name__)


def start_cleanup_thread(store: CircuitStore) -> None:
    """Start a daemon thread that evicts stale circuit sessions once per day."""
    def _run() -> None:
        while True:
            time.sleep(_CLEANUP_INTERVAL_SECONDS)
            removed = store.cleanup_expired(_TTL)
            if removed:
                _log.info("Circuit TTL cleanup: removed %d stale session(s).", removed)

    threading.Thread(target=_run, daemon=True, name="circuit-ttl-cleanup").start()
