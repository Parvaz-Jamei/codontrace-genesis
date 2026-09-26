"""Pure measurement helpers for closed-loop frequency clocks.

These helpers never set ``red_queen_proved`` or ``biological_red_queen_proved``.
Lagged NFDS / RQ-earn scoring is evaluated on debit-active arms only.
"""

from __future__ import annotations

from codontrace.genesis.measurements.rq_frequency_clocks import (
    dominant_class_series,
    lagged_nfds_score,
    per_sublocus_richness_series,
    phase_lag_host_parasite,
)

__all__ = [
    "dominant_class_series",
    "lagged_nfds_score",
    "per_sublocus_richness_series",
    "phase_lag_host_parasite",
]
