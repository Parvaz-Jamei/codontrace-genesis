"""Closed-loop Phase 1: one clock — both roles as GenesisOrganism under step_population."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_life_plugin import (
    ID_PREFIX_PRIMARY,
    ID_PREFIX_SECONDARY,
    ClosedLoopHPLifeConfig,
    role_of,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.world import World2D


def _genome_digest(organism: GenesisOrganism) -> str:
    return canonical_digest(
        {"id": organism.id, "g": organism.genome.to_compact()}, prefix="clp1g"
    )


def _atp_of(organism: GenesisOrganism) -> float:
    return float(organism.atp_state.runtime.current_atp)


@dataclass
class ClosedLoopP1Session:
    """One-clock session: primary+secondary as GenesisOrganisms; no HP world.tick."""

    seed: int
    runner: PopulationRunner
    roles: dict[str, str] = field(default_factory=dict)
    tick_index: int = 0
    history_digests: list[str] = field(default_factory=list)

    @classmethod
    def boot(
        cls,
        *,
        seed: int = 7,
        n_primary: int = 2,
        n_secondary: int = 2,
        initial_atp: float = 12.0,
        world_size: int = 8,
    ) -> ClosedLoopP1Session:
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        founders = ("000111000111", "111000111000", "010101010101", "101010101010")
        for i in range(n_primary):
            oid = f"{ID_PREFIX_PRIMARY}{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    founders[i % len(founders)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 0),
                )
            )
            roles[oid] = "primary"
        for i in range(n_secondary):
            oid = f"{ID_PREFIX_SECONDARY}{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    founders[(i + 2) % len(founders)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 1),
                )
            )
            roles[oid] = "secondary"

        configs = PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            mutation=MutationConfig(bit_flip_rate=0.0),
            closed_loop_hp_life=ClosedLoopHPLifeConfig(
                enabled=True,
                mutate_both_roles=True,
                point_mutation_per_tick=True,
            ),
        )
        population = PopulationState(
            generation=0,
            tick=0,
            organisms=tuple(organisms),
            lineage=(),
            fitness=(),
        )
        runner = PopulationRunner(
            population=population,
            world=World2D(width=world_size, height=world_size),
            configs=configs,
        )
        return cls(seed=seed, runner=runner, roles=roles)

    def run_ticks(self, ticks: int) -> dict[str, Any]:
        if ticks < 0:
            raise ConfigurationError("ticks must be non-negative")
        for i in range(ticks):
            self.runner.step_generation(seed=self.seed + self.tick_index + i)
            self.tick_index += 1
            self.roles = {
                org.id: (role_of(org.id) or self.roles.get(org.id, "unknown"))
                for org in self.runner.population.organisms
            }
            self.history_digests.append(self.snapshot_digest())
        return self.summary()

    def snapshot_digest(self) -> str:
        orgs = sorted(self.runner.population.organisms, key=lambda o: o.id)
        payload = {
            "tick": self.tick_index,
            "generation": self.runner.population.generation,
            "ids": [o.id for o in orgs],
            "genomes": [_genome_digest(o) for o in orgs],
            "atp": [_atp_of(o) for o in orgs],
            "roles": {o.id: self.roles.get(o.id) for o in orgs},
        }
        return canonical_digest(payload, prefix="clp1snap")

    def summary(self) -> dict[str, Any]:
        primary = [o for o in self.runner.population.organisms if role_of(o.id) == "primary"]
        secondary = [
            o for o in self.runner.population.organisms if role_of(o.id) == "secondary"
        ]
        return {
            "tick_index": self.tick_index,
            "population_tick": self.runner.population.tick,
            "population_generation": self.runner.population.generation,
            "n_primary": len(primary),
            "n_secondary": len(secondary),
            "organism_ids": [o.id for o in self.runner.population.organisms],
            "snapshot_digest": self.snapshot_digest(),
            "claim_ceiling": "candidate_evidence",
            "red_queen_proved": False,
            "one_clock": True,
            "dual_path_used": False,
        }

    def secondary_genome_digests(self) -> dict[str, str]:
        return {
            o.id: _genome_digest(o)
            for o in self.runner.population.organisms
            if role_of(o.id) == "secondary"
        }


def replay_bit_identical(*, seed: int, ticks: int) -> tuple[str, str]:
    a = ClosedLoopP1Session.boot(seed=seed)
    b = ClosedLoopP1Session.boot(seed=seed)
    a.run_ticks(ticks)
    b.run_ticks(ticks)
    return a.snapshot_digest(), b.snapshot_digest()
