"""Paired champion/challenger evaluation of two processors on one recorded window.

Both processors see the same inputs and are scored against the same
references, so the comparison is paired (common random numbers; the
difference has lower variance than two independent runs). Two statistics are
kept apart because their floating-point results differ:

* ``paired_mse_gain``: mean of per-sample squared-error differences
  ``mean((b - y)^2 - (a - y)^2)``;
* ``paired_shadow``: difference of the two mean squared errors
  ``mse(b) - mse(a)``, with a qualification or monitoring decision.

Qualification accepts a candidate whose gain exceeds ``minimum_gain``;
monitoring advises falling back when the gain drops below
``-maximum_regression``. This is an engineering comparison (like shadow and
champion/challenger deployment in online experiments); it carries no
statistical safety guarantee and performs no deployment.
"""
from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

__all__ = ['SHADOW_PHASES', 'Processor', 'ShadowEvaluation', 'paired_mse_gain', 'paired_shadow']

SHADOW_PHASES = ('qualification', 'monitoring')


class Processor(Protocol):
    def process(self, values: list[float]) -> tuple[list[float], list[int]]: ...


def paired_mse_gain(candidate: Processor, baseline: Processor, values: list[float],
                    references: Sequence[float]) -> float:
    a, _ = candidate.process(values)
    b, _ = baseline.process(values)
    return statistics.mean((x-y)**2 - (z-y)**2 for x, z, y in zip(b, a, references, strict=True))


@dataclass(frozen=True, slots=True)
class ShadowEvaluation:
    phase: str
    candidate_mse: float
    baseline_mse: float
    gain_mse: float
    accepted: bool
    rollback_advised: bool
    keep_candidate: bool
    candidate_events: tuple[int, ...]
    baseline_events: tuple[int, ...]


def paired_shadow(candidate: Processor, baseline: Processor, values: list[float], references: Sequence[float], *,
                  phase: str = 'qualification', minimum_gain: float = 0.,
                  maximum_regression: float = 0.) -> ShadowEvaluation:
    if phase not in SHADOW_PHASES:
        raise ValueError('unknown shadow phase')
    a, events_a = candidate.process(values)
    b, events_b = baseline.process(values)
    candidate_mse = statistics.mean((v-r)**2 for v, r in zip(a, references, strict=True))
    baseline_mse = statistics.mean((v-r)**2 for v, r in zip(b, references, strict=True))
    gain = baseline_mse-candidate_mse
    rollback = phase == 'monitoring' and gain < -maximum_regression
    accepted = phase == 'qualification' and gain > minimum_gain
    keep = accepted or (phase == 'monitoring' and not rollback)
    return ShadowEvaluation(phase, candidate_mse, baseline_mse, gain, accepted, rollback, keep,
                            tuple(events_a), tuple(events_b))
