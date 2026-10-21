"""Bounded minimax co-adaptation of pipelines and nuisance families on training data.

The loop is ``codontrace.genesis.coevolution.minimax_coevolve``; this module
supplies the pipeline and disturbance proposals and the paired score. Draw
order per round (namespace ``swarm/coevolution``): one carrier draw per
reference, then three challengers (bias draw, frequency draw), then three
defenders through ``HillClimbEmitter`` over ``DEFENDER_SPACE`` (alpha draw,
clip draw).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from codontrace.genesis.coevolution import minimax_coevolve
from codontrace.genesis.qd_parametric import HillClimbEmitter, MutationRule, ParameterBound, ParameterSpace
from codontrace.rng import RNGManager
from codontrace.swarm.policies import Pipeline
from codontrace.swarm.protocol import integer, number
from codontrace.swarm.research import mse

# The int upper bound 1 is deliberate: min(1, x) returns the int 1, and the
# original loop produced exactly that value.
DEFENDER_SPACE = ParameterSpace((
    ParameterBound('alpha', 0.01, 1.0, 1.0, MutationRule('additive', .5, low=.01, high=1)),
    ParameterBound('clip', 0.01, 1e6, 5.0, MutationRule('multiplicative', .5, low=.01)),
))


def coevolve(references: list[float], *, seed: int, rounds: int = 8,
             disturbance_budget: float = 1.0) -> dict[str, Any]:
    integer(seed); integer(rounds, high=32); number(disturbance_budget, low=0.01, high=1e6)
    if not 8 <= len(references) <= 4096 or rounds < 1:
        raise ValueError('bounded training sequence and positive rounds required')
    for v in references:
        number(v)
    rng = RNGManager(seed=seed, namespace='swarm/coevolution')
    emitter = HillClimbEmitter()

    def begin_round(generation: int) -> list[float]:
        # Common disturbance carriers across policies make comparisons paired.
        return [2*rng.random()-1 for _ in references]

    def score(candidate: Pipeline, disturbance: dict[str, Any], carrier: list[float]) -> float:
        values = [r + disturbance['bias'] + disturbance['amplitude'] * carrier[i//disturbance['frequency']]
                  for i, r in enumerate(references)]
        output, _ = candidate.process(values)
        return mse(output, references)

    def propose_challengers(nuisance: dict[str, Any], carrier: list[float]) -> list[dict[str, Any]]:
        challengers = [nuisance]
        for _ in range(3):
            bias = (2*rng.random()-1)*disturbance_budget
            challengers.append({'amplitude': disturbance_budget-abs(bias), 'bias': bias,
                                'frequency': rng.randrange(1, 5)})
        return challengers

    def propose_defenders(policy: Pipeline, carrier: list[float]) -> list[Pipeline]:
        parent = {'alpha': policy.alpha, 'clip': policy.clip}
        return [policy] + [Pipeline(**emitter.emit(DEFENDER_SPACE, parent, rng)) for _ in range(3)]

    result = minimax_coevolve(Pipeline(), {'amplitude': disturbance_budget, 'bias': 0.0, 'frequency': 1},
                              rounds=rounds, begin_round=begin_round, propose_challengers=propose_challengers,
                              propose_defenders=propose_defenders, score=score)
    history = [{'generation': r.generation, 'training_worst_mse': r.worst_score,
                'pipeline': asdict(r.defender), 'disturbance': dict(r.challenger)} for r in result.rounds]
    return {'pipeline': asdict(result.defender), 'disturbance': result.challenger, 'history': history,
            'rng': rng.snapshot(), 'scope': 'training_only_bounded_coadaptation',
            'red_queen_proved': None, 'hypothesis_verdict': None}
