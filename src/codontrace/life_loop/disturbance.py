"""Disturbance family for stress-testing processors: additive bias, bounded
uniform noise and random dropout.

Per value, in order: one draw decides dropout (``random() < dropout``), one
draw gives noise ``(2 * random() - 1) * amplitude``; a dropped value becomes
``None`` (a missing sample, never a fake zero). These are the bias, noise and
missing-data fault classes of sensor fault taxonomies (Ni et al. 2009,
"Sensor network data fault types", ACM TOSN 5(3), doi:10.1145/1525856.1525863;
Sharma, Golubchik & Govindan 2010, ACM TOSN 6(3), doi:10.1145/1754414.1754419).
All randomness comes from the ``RNGManager`` passed in.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.rng import RNGManager

SCHEMA_VERSION = "life_loop_disturbance_v1"

__all__ = ["SCHEMA_VERSION", "DisturbanceFamily", "apply_disturbance"]


def _finite(value: float, name: str, low: float | None = None, high: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigurationError(f"{name} must be finite.")
    if (low is not None and value < low) or (high is not None and value > high):
        raise ConfigurationError(f"{name} out of range.")
    return value


@dataclass(frozen=True, slots=True)
class DisturbanceFamily:
    amplitude: float = 1.0
    bias: float = 0.0
    dropout: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.amplitude, "amplitude", 0.0)
        _finite(self.bias, "bias")
        _finite(self.dropout, "dropout", 0.0, 1.0)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": SCHEMA_VERSION, "amplitude": self.amplitude, "bias": self.bias,
                "dropout": self.dropout}

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="disturbance")


def _check_value(value: float) -> object:
    return _finite(value, "value")


def apply_disturbance(values: Sequence[float], family: DisturbanceFamily, rng: RNGManager, *,
                      check: Callable[[float], object] = _check_value) -> list[float | None]:
    """Disturb ``values``; each value is checked just before its draws (``check``
    lets a caller keep its own validation errors)."""
    result: list[float | None] = []
    for value in values:
        check(value)
        lost = rng.random() < family.dropout
        noise = (rng.random()*2-1)*family.amplitude
        result.append(None if lost else value + family.bias + noise)
    return result
