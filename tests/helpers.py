"""Shared test constants."""

from __future__ import annotations

import stim

BELL_CIRCUIT = "H 0\nCNOT 0 1\nM 0 1"
REP_CODE = stim.Circuit.generated(
    "repetition_code:memory", rounds=3, distance=3, before_round_data_depolarization=0.01
)
