"""Stateful library wrapper for deterministic GENESIS population stepping."""

from __future__ import annotations

from dataclasses import dataclass, field

from codontrace.atp_ledger import WorldATPLedger
from codontrace.genesis.atp import organism_atp_accounts
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
    # Closed world ATP ledger (docs/ATP_WORLD_LEDGER.md). Pull mode: every
    # organism ATPAccount entry is booked by id, births are opened from
    # source:birth_endowment, deaths closed to sink:death_remainder, and the
    # invariant is checked every generation. Not part of any digest.
    atp_ledger: WorldATPLedger = field(
        default_factory=lambda: WorldATPLedger("genesis_population"), compare=False, repr=False
    )

    def settle_atp(self, *, close: bool = True) -> str | None:
        """Book every ATP change since the last call; close the tick if asked."""

        tick = int(self.population.generation)
        mirrors = self.atp_ledger.sync_accounts(organism_atp_accounts(self.population.organisms), tick=tick)
        if close:
            return self.atp_ledger.close_tick(tick, mirrors)
        self.atp_ledger.check(mirrors)
        return None

    def step_generation(
        self, *, seed: int | None = None, rng: RNGManager | None = None
    ) -> GenerationResult:
        """Advance one generation and store the returned PopulationState."""

        if seed is not None and rng is not None:
            msg = "Provide either seed or rng, not both."
            raise ValueError(msg)
        # Changes made between generations (observers, experiment code) are
        # booked under their own entry names before the step runs.
        self.settle_atp(close=False)
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
        self.settle_atp()
        return result
