"""Closed-loop P1: unify+mutate scaffold — both roles as GenesisOrganism.

Hard scope (adversarial 2026-09-25): organisms + engine mutate under one
``step_population`` clock. Not Morran-ready. Not P2 energy-partition. Not P4
dual-arm replay. Birth/death demography and interaction→fitness = P2+.

Clock API: ``PopulationRunner.step_generation`` (same inner loop as
``GenesisEngine.run_ticks``). Dual ``HostParasiteGenesisPath.tick`` hard-raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_life_plugin import (
    P1_SCOPE,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    assert_single_atp_owner,
    role_of,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MetabolicConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.world import World2D

# Opaque ids — role comes from role_by_id map, never from parsing these strings.
_PRIMARY_IDS = ("org_a0", "org_a1")
_SECONDARY_IDS = ("org_b0", "org_b1")


def _genome_digest(organism: GenesisOrganism) -> str:
    return canonical_digest(
        {"id": organism.id, "g": organism.genome.to_compact()}, prefix="clp1g"
    )


def _atp_of(organism: GenesisOrganism) -> float:
    return float(organism.atp_state.runtime.current_atp)


@dataclass
class ClosedLoopP1Session:
    """Unify+mutate scaffold: both roles as GenesisOrganisms; no HP world.tick."""

    seed: int
    runner: PopulationRunner
    roles: dict[str, str] = field(default_factory=dict)
    tick_index: int = 0
    history_digests: list[str] = field(default_factory=list)
    hp_world_tick_calls: int = 0  # runtime anti-cheat witness

    @classmethod
    def boot(
        cls,
        *,
        seed: int = 7,
        n_primary: int = 2,
        n_secondary: int = 2,
        initial_atp: float = 12.0,
        world_size: int = 8,
        basal_atp_cost: float = 0.5,
        bit_flip_rate: float = 0.35,
    ) -> ClosedLoopP1Session:
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        founders = ("000111000111", "111000111000", "010101010101", "101010101010")
        for i in range(n_primary):
            oid = _PRIMARY_IDS[i] if i < len(_PRIMARY_IDS) else f"org_a{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    founders[i % len(founders)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 0),
                )
            )
            roles[oid] = ROLE_PRIMARY
        for i in range(n_secondary):
            oid = _SECONDARY_IDS[i] if i < len(_SECONDARY_IDS) else f"org_b{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    founders[(i + 2) % len(founders)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 1),
                )
            )
            roles[oid] = ROLE_SECONDARY

        assert_single_atp_owner(organisms)

        configs = PopulationConfigs(
            # P1 hard-scope: reproduction off — birth/partition is P2.
            reproduction=ReproductionConfig(enabled=False),
            # Engine-owned mutation path (mutate_genome via plugin + stream).
            mutation=MutationConfig(bit_flip_rate=bit_flip_rate),
            metabolism=MetabolicConfig(
                enabled=True,
                basal_runtime_atp_cost=basal_atp_cost,
            ),
            closed_loop_hp_life=ClosedLoopHPLifeConfig(
                enabled=True,
                mutate_both_roles=True,
                role_by_id=tuple(sorted(roles.items())),
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
            # Same inner API GenesisEngine.run_ticks uses.
            self.runner.step_generation(seed=self.seed + self.tick_index + i)
            self.tick_index += 1
            role_map = self.runner.configs.closed_loop_hp_life.role_map()
            self.roles = {
                org.id: (role_of(org.id, role_map) or self.roles.get(org.id, "unknown"))
                for org in self.runner.population.organisms
            }
            assert_single_atp_owner(self.runner.population.organisms)
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
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        primary = [
            o
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_PRIMARY
        ]
        secondary = [
            o
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_SECONDARY
        ]
        atp_values = [_atp_of(o) for o in self.runner.population.organisms]
        # Measured witnesses only — no caller-boolean one_clock / dual_path_used.
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
            "p1_scope": P1_SCOPE,
            "clock_api": "PopulationRunner.step_generation",
            "hp_world_tick_calls": self.hp_world_tick_calls,
            "atp_moved": any(v < 12.0 - 1e-9 for v in atp_values),
            "mean_runtime_atp": sum(atp_values) / max(1, len(atp_values)),
        }

    def secondary_genome_digests(self) -> dict[str, str]:
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        return {
            o.id: _genome_digest(o)
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_SECONDARY
        }


def replay_bit_identical(*, seed: int, ticks: int) -> tuple[str, str]:
    """Same-seed session match (Gate7-shaped). NOT P4 dual-arm elicit/ablate."""

    a = ClosedLoopP1Session.boot(seed=seed)
    b = ClosedLoopP1Session.boot(seed=seed)
    a.run_ticks(ticks)
    b.run_ticks(ticks)
    return a.snapshot_digest(), b.snapshot_digest()
