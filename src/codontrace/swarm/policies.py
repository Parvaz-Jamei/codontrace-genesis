"""Bounded host-side policies; heuristics are candidates, never causal proof."""
from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import asdict, dataclass
from typing import Any

from codontrace.rng import RNGManager
from codontrace.swarm.protocol import canonical, number


@dataclass(frozen=True)
class Pipeline:
    alpha: float = 1.0
    clip: float = 5.0
    event_threshold: float = 2.0

    def __post_init__(self) -> None:
        number(self.alpha, low=0.01, high=1); number(self.clip, low=0.01, high=1e6)
        number(self.event_threshold, low=0.01, high=1e6)

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()

    def process(self, values: list[float]) -> tuple[list[float], list[int]]:
        if not values:
            return [], []
        for value in values:
            number(value)
        # Events are detected on RAW input before smoothing, so no erasure by design.
        state = values[0]; filtered = [state]; events: list[int] = []
        for i, value in enumerate(values[1:], 1):
            if abs(value - values[i-1]) >= self.event_threshold:
                events.append(i)
            residual = max(-self.clip, min(self.clip, value - state))
            state += self.alpha * residual
            filtered.append(state)
        return filtered, events


class PolicyArchive:
    """Small evolutionary search over pipelines, separate from ALife birth fitness."""
    def __init__(self, seed: int = 0) -> None:
        if type(seed) is not int or not 0 <= seed <= 2**53-1:
            raise ValueError("bounded integer seed required")
        self.rng = RNGManager(seed=seed, namespace='swarm/pipelines')
        self.entries: dict[str, dict[str, Any]] = {}

    def fit(self, values: list[float], references: list[float], *, rounds: int = 8) -> Pipeline:
        if not isinstance(values, list) or not isinstance(references, list) or len(values) > 4096:
            raise ValueError("bounded training arrays required")
        if type(rounds) is not int or not 1 <= rounds <= 64 or len(values) != len(references) or len(values) < 3:
            raise ValueError('paired data and 1..64 rounds required')
        for v in references:
            number(v)
        # Training-only fit; caller must use a separate device/day/history for evaluation.
        best = Pipeline(); best_loss = math.inf
        for i in range(rounds * 4):
            candidate = Pipeline() if i == 0 else Pipeline(
                alpha=max(0.01, min(1.0, best.alpha + (self.rng.random() - 0.5) * 0.4)),
                clip=max(0.01, best.clip * (0.5 + self.rng.random())),
                event_threshold=best.event_threshold,
            )
            output, _ = candidate.process(values)
            loss = statistics.mean((x-y)**2 for x, y in zip(output, references, strict=True))
            self.entries[candidate.digest] = {'pipeline': asdict(candidate), 'training_mse': loss}
            if len(self.entries) > 4096:
                del self.entries[next(iter(self.entries))]
            if loss < best_loss:
                best = candidate; best_loss = loss
        return best


def transfer_decision(candidate: Pipeline, baseline: Pipeline, values: list[float],
                      references: list[float], *, minimum_gain: float = 0.0) -> dict[str, Any]:
    number(minimum_gain, low=0, high=1e6)
    if not isinstance(values, list) or not isinstance(references, list) or not 3 <= len(values) <= 4096 or len(values) != len(references):
        raise ValueError('local paired validation data required')
    for v in references:
        number(v)
    a, _ = candidate.process(values); b, _ = baseline.process(values)
    gain = statistics.mean((x-y)**2 - (z-y)**2 for x, z, y in zip(b, a, references, strict=True))
    return {'accepted': gain > minimum_gain, 'local_mse_gain': gain,
            'candidate_digest': candidate.digest, 'sample_count': len(values),
            'claim': 'local_validation_only'}


def diagnose(values: dict[str, float], *, reference: float | None = None,
             tolerance: float = 2.0) -> dict[str, Any]:
    number(tolerance, low=0.001, high=1e6)
    for v in values.values():
        number(v)
    if not values:
        return {'status': 'insufficient_data', 'suspects': [], 'causal_proof': False}
    center = statistics.median(values.values()) if reference is None else number(reference)
    suspects = sorted(k for k, v in values.items() if abs(v-center) > tolerance)
    return {'status': 'reference_comparison' if reference is not None else 'peer_disagreement_candidate',
            'suspects': suspects, 'center': center, 'causal_proof': False,
            'identifiability': 'external_reference_required_for_common_mode_faults'}
