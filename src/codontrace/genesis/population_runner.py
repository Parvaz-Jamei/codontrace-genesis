"""Stateful library wrapper for deterministic GENESIS population stepping."""

from __future__ import annotations

from dataclasses import dataclass

from codontrace.genesis.capsule import NexusStigmergyLayer
from codontrace.genesis.population import (
    GenerationResult,
    PopulationConfigs,
    PopulationState,
    step_population,
)
from codontrace.rng import RNGManager
from codontrace.world import World2D


@dataclass(slots=True)
class PopulationRunner:
    """Hold PopulationState and step one generation deterministically.

    This is a library object only: no UI, no CLI, no report writing, no threads,
    and no hidden global randomness.
    """

    population: PopulationState
    world: World2D
    configs: PopulationConfigs
    nexus_layer: NexusStigmergyLayer | None = None

    def step_generation(
        self, *, seed: int | None = None, rng: RNGManager | None = None
    ) -> GenerationResult:
        """Advance one generation and store the returned PopulationState."""

        if seed is not None and rng is not None:
            msg = "Provide either seed or rng, not both."
            raise ValueError(msg)
        result = step_population(
            self.population,
            self.world,
            self.configs,
            seed=seed,
            rng=rng,
            nexus_layer=self.nexus_layer,
        )
        self.population = result.population
        self.world = result.world_after
        self.nexus_layer = result.nexus_layer
        return result
