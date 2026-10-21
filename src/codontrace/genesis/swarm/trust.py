"""Per-channel trust from reference comparisons.

``reliability = 1 / (1 + |value - reference| / scale)``; the weight is an
exponential moving average ``0.8 * old + 0.2 * reliability`` starting at 1.0.
Trust is reset when a channel's processing version or descriptor changes.
"""
from __future__ import annotations

from typing import Any

__all__ = ['TRUST_DECAY', 'TRUST_GAIN', 'reliability', 'update_trust']

# Two literals, not 1 - decay: 1 - 0.8 != 0.2 in binary floating point.
TRUST_DECAY = 0.8
TRUST_GAIN = 0.2


def reliability(value: float, reference: float, scale: float) -> float:
    return 1 / (1 + abs(value - reference) / scale)


def update_trust(old: dict[str, Any] | None, value: float, reference: float, scale: float,
                 reference_id: str) -> dict[str, Any]:
    old = old or {'weight': 1.0, 'samples': 0}
    return {'weight': TRUST_DECAY * old['weight'] + TRUST_GAIN * reliability(value, reference, scale),
            'samples': old['samples'] + 1, 'reference_id': reference_id}
