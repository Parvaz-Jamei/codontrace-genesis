"""Bounded minimax co-adaptation of a defender against challengers (domain-free).

Each round: ``begin_round`` prepares shared context (e.g. common random
carriers, so every comparison in the round is paired); the incumbent
challenger and new proposals compete for the highest score against the
current defender; then the incumbent defender and new proposals compete for
the lowest worst-case score over that round's challengers. This is the
alternating best-response scheme of competitive coevolution (Hillis 1990,
doi:10.1016/0167-2789(90)90076-2; Rosin & Belew 1997,
doi:10.1162/evco.1997.5.1.1) restricted to small candidate sets. It is a
training-time search procedure; it does not test a Red Queen hypothesis.

Ties keep list order (the incumbent first), and all proposals come from the
caller, so randomness stays in the caller's ``RNGManager``.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

__all__ = ['CoevolutionResult', 'CoevolutionRound', 'minimax_coevolve']

D = TypeVar('D')
C = TypeVar('C')
X = TypeVar('X')


@dataclass(frozen=True, slots=True)
class CoevolutionRound(Generic[D, C]):
    generation: int
    worst_score: float
    defender: D
    challenger: C


@dataclass(frozen=True, slots=True)
class CoevolutionResult(Generic[D, C]):
    defender: D
    challenger: C
    rounds: tuple[CoevolutionRound[D, C], ...]


def minimax_coevolve(defender: D, challenger: C, *, rounds: int,
                     begin_round: Callable[[int], X],
                     propose_challengers: Callable[[C, X], Sequence[C]],
                     propose_defenders: Callable[[D, X], Sequence[D]],
                     score: Callable[[D, C, X], float]) -> CoevolutionResult[D, C]:
    """``propose_*`` return the candidate list for the round, incumbent first."""
    if rounds < 1:
        raise ValueError('positive rounds required')
    history: list[CoevolutionRound[D, C]] = []
    for generation in range(rounds):
        context = begin_round(generation)
        challengers = list(propose_challengers(challenger, context))
        challenger = max(challengers, key=lambda c: score(defender, c, context))
        defenders = list(propose_defenders(defender, context))
        defender = min(defenders, key=lambda d: max(score(d, c, context) for c in challengers))
        worst = max(score(defender, c, context) for c in challengers)
        history.append(CoevolutionRound(generation, worst, defender, challenger))
    return CoevolutionResult(defender, challenger, tuple(history))
