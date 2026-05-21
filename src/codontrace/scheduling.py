"""Deterministic scheduler protocols and built-in scheduler presets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from codontrace.agent import WhiteBoxAgent
from codontrace.rng import RNGManager


@runtime_checkable
class SchedulerProtocol(Protocol):
    """Structural scheduler contract for multi-agent simulations."""

    @property
    def name(self) -> str:
        """Stable scheduler name for built-in serialization when available."""
        ...

    def order(
        self,
        agents: Sequence[WhiteBoxAgent],
        tick: int,
        rng: RNGManager,
        context: Mapping[str, object] | None = None,
    ) -> tuple[int, ...]:
        """Return indexes into ``agents`` in the execution order."""


@dataclass(frozen=True, slots=True)
class SequentialScheduler:
    """Stable id-sorted order."""

    name: str = "sequential"

    def order(
        self,
        agents: Sequence[WhiteBoxAgent],
        tick: int,
        rng: RNGManager,
        context: Mapping[str, object] | None = None,
    ) -> tuple[int, ...]:
        return tuple(range(len(agents)))


@dataclass(frozen=True, slots=True)
class RoundRobinScheduler:
    """Rotate deterministic id-sorted order by tick."""

    name: str = "round_robin"

    def order(
        self,
        agents: Sequence[WhiteBoxAgent],
        tick: int,
        rng: RNGManager,
        context: Mapping[str, object] | None = None,
    ) -> tuple[int, ...]:
        if not agents:
            return ()
        offset = tick % len(agents)
        indexes = tuple(range(len(agents)))
        return indexes[offset:] + indexes[:offset]


@dataclass(frozen=True, slots=True)
class RandomOrderScheduler:
    """Seeded Fisher-Yates random order."""

    name: str = "random_order"

    def order(
        self,
        agents: Sequence[WhiteBoxAgent],
        tick: int,
        rng: RNGManager,
        context: Mapping[str, object] | None = None,
    ) -> tuple[int, ...]:
        indexes = list(range(len(agents)))
        for index in range(len(indexes) - 1, 0, -1):
            swap = rng.randrange(index + 1)
            indexes[index], indexes[swap] = indexes[swap], indexes[index]
        return tuple(indexes)


@dataclass(frozen=True, slots=True)
class EnergyPriorityScheduler:
    """Run agents with higher available ATP first, then id for stability."""

    name: str = "energy_priority"

    def order(
        self,
        agents: Sequence[WhiteBoxAgent],
        tick: int,
        rng: RNGManager,
        context: Mapping[str, object] | None = None,
    ) -> tuple[int, ...]:
        return tuple(
            index
            for index, _agent in sorted(
                enumerate(agents), key=lambda item: (-item[1].atp_account.current_atp, item[1].id)
            )
        )


@dataclass(frozen=True, slots=True)
class FitnessWeightedScheduler:
    """Order by externally supplied fitness values when present."""

    name: str = "fitness_weighted"

    def order(
        self,
        agents: Sequence[WhiteBoxAgent],
        tick: int,
        rng: RNGManager,
        context: Mapping[str, object] | None = None,
    ) -> tuple[int, ...]:
        fitness: Mapping[str, float] = {}
        if context is not None:
            raw = context.get("fitness")
            if isinstance(raw, Mapping):
                fitness = {
                    str(key): float(value)
                    for key, value in raw.items()
                    if isinstance(value, int | float)
                }
        return tuple(
            index
            for index, _agent in sorted(
                enumerate(agents), key=lambda item: (-fitness.get(item[1].id, 0.0), item[1].id)
            )
        )


def scheduler_from_name(name: str) -> SchedulerProtocol:
    """Return a built-in scheduler from a stable preset name."""

    if name == "sequential":
        return SequentialScheduler()
    if name == "round_robin":
        return RoundRobinScheduler()
    if name == "random_order":
        return RandomOrderScheduler()
    if name == "energy_priority":
        return EnergyPriorityScheduler()
    if name == "fitness_weighted":
        return FitnessWeightedScheduler()
    msg = f"Unsupported scheduler {name!r}."
    raise ValueError(msg)
