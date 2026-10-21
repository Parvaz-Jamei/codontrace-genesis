"""Peer-disagreement screening: values farther than ``tolerance`` from the peer
median (or an external reference) are suspects.

Without an external reference a common-mode fault is not identifiable; the
result says so and never claims causality.
"""
from __future__ import annotations

import statistics
from collections.abc import Mapping
from typing import Any

from codontrace.contracts.wire_validation import finite_number

__all__ = ['peer_disagreement']


def peer_disagreement(values: Mapping[str, float], *, reference: float | None = None,
                      tolerance: float = 2.0) -> dict[str, Any]:
    finite_number(tolerance, low=0.001, high=1e6)
    for v in values.values():
        finite_number(v)
    if not values:
        return {'status': 'insufficient_data', 'suspects': [], 'causal_proof': False}
    center = statistics.median(values.values()) if reference is None else finite_number(reference)
    suspects = sorted(k for k, v in values.items() if abs(v-center) > tolerance)
    return {'status': 'reference_comparison' if reference is not None else 'peer_disagreement_candidate',
            'suspects': suspects, 'center': center, 'causal_proof': False,
            'identifiability': 'external_reference_required_for_common_mode_faults'}
