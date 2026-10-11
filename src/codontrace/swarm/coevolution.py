"""Bounded minimax co-adaptation of pipelines and nuisance families on training data."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from codontrace.rng import RNGManager
from codontrace.swarm.policies import Pipeline
from codontrace.swarm.protocol import integer, number
from codontrace.swarm.research import mse


def coevolve(references: list[float], *, seed: int, rounds: int = 8,
             disturbance_budget: float = 1.0) -> dict[str, Any]:
    integer(seed); integer(rounds, high=32); number(disturbance_budget, low=0.01, high=1e6)
    if not 8 <= len(references) <= 4096 or rounds < 1:
        raise ValueError('bounded training sequence and positive rounds required')
    for v in references:
        number(v)
    rng = RNGManager(seed=seed, namespace='swarm/coevolution')
    policy = Pipeline(); nuisance = {'amplitude': disturbance_budget, 'bias': 0.0, 'frequency': 1}
    history = []
    for generation in range(rounds):
        # Common disturbance carriers across policies make comparisons paired.
        carrier = [2*rng.random()-1 for _ in references]
        def score(candidate: Pipeline, disturbance: dict[str, Any]) -> float:
            values = [r + disturbance['bias'] + disturbance['amplitude'] * carrier[i//disturbance['frequency']]
                      for i, r in enumerate(references)]
            output, _ = candidate.process(values)
            return mse(output, references)
        challengers = [nuisance]
        for _ in range(3):
            bias = (2*rng.random()-1)*disturbance_budget
            challengers.append({'amplitude': disturbance_budget-abs(bias), 'bias': bias,
                                'frequency': rng.randrange(1, 5)})
        nuisance = max(challengers, key=lambda n: score(policy, n))
        defenders = [policy]
        for _ in range(3):
            defenders.append(Pipeline(alpha=max(.01, min(1, policy.alpha+(rng.random()-.5)*.5)),
                                      clip=max(.01, policy.clip*(.5+rng.random()))))
        policy = min(defenders, key=lambda p: max(score(p, n) for n in challengers))
        history.append({'generation': generation, 'training_worst_mse': max(score(policy,n) for n in challengers),
                        'pipeline': asdict(policy), 'disturbance': dict(nuisance)})
    return {'pipeline': asdict(policy), 'disturbance': nuisance, 'history': history,
            'rng': rng.snapshot(), 'scope': 'training_only_bounded_coadaptation',
            'red_queen_proved': None, 'hypothesis_verdict': None}
