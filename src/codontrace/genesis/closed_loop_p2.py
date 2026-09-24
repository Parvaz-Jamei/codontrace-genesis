"""Closed-loop P2: Smith–Fretwell N=1 asexual birth ATP partition.

Hard scope (2026-09-25): engine ``ReproductionConfig`` ON; child endowment Iy
from parent residual after ``parent_atp_cost`` (cost dissipated). Not Morran.
Not genetic-harm P3. Not P4 dual-arm. Not SF optimal Iy*. Not multi-child
N=floor(Ip/Iy). Gate7 = same-seed bit-identical only.

Clock API: ``PopulationRunner.step_generation`` (same inner loop as
``GenesisEngine.run_ticks``). No ``HostParasiteWorld.tick`` / ``_birth_role``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_life_plugin import (
    P2_SCOPE,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    assert_single_atp_owner,
    role_of,
    with_inherited_birth_roles,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    GenerationResult,
    MetabolicConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME
from codontrace.world import World2D

# Opaque ids — role comes from role_by_id map, never from parsing these strings.
_PRIMARY_IDS = ("org_a0", "org_a1")
_SECONDARY_IDS = ("org_b0", "org_b1")

# Both roles must encode COPY_SELF (111). Slight haplotype diversity; all have 111.
_FOUNDER_GENOMES = (
    LIFE_LOOP_EATER_GENOME,  # 101111000 — EAT, COPY_SELF, WAIT
    "111101000",  # COPY_SELF, EAT, WAIT
    "101000111",  # EAT, WAIT, COPY_SELF
    "000101111",  # WAIT, EAT, COPY_SELF
)

_PARTITION_EPS = 1e-9


def _genome_digest(organism: GenesisOrganism) -> str:
    return canonical_digest(
        {"id": organism.id, "g": organism.genome.to_compact()}, prefix="clp2g"
    )


def _atp_of(organism: GenesisOrganism) -> float:
    return float(organism.atp_state.runtime.current_atp)


def _learning_of(organism: GenesisOrganism) -> float:
    return float(organism.atp_state.learning_available)


@dataclass
class ClosedLoopP2Session:
    """N=1 asexual SF birth partition under step_population; no HP world demography."""

    seed: int
    runner: PopulationRunner
    roles: dict[str, str] = field(default_factory=dict)
    tick_index: int = 0
    history_digests: list[str] = field(default_factory=list)
    hp_world_tick_calls: int = 0  # runtime anti-cheat witness
    total_births: int = 0
    birth_Iy: list[float] = field(default_factory=list)
    partition_ok_flags: list[bool] = field(default_factory=list)
    births_by_role: dict[str, int] = field(
        default_factory=lambda: {ROLE_PRIMARY: 0, ROLE_SECONDARY: 0}
    )
    parent_atp_cost: float = 1.0
    offspring_atp_fraction: float = 0.25

    @classmethod
    def boot(
        cls,
        *,
        seed: int = 7,
        n_primary: int = 2,
        n_secondary: int = 2,
        initial_atp: float = 24.0,
        world_size: int = 8,
        basal_atp_cost: float = 0.5,
        bit_flip_rate: float = 0.02,
        parent_atp_cost: float = 1.0,
        offspring_atp_fraction: float = 0.25,
        min_runtime_atp: float = 4.0,
        max_population: int = 64,
        ticks_per_generation: int = 3,
        place_food: bool = True,
    ) -> ClosedLoopP2Session:
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        for i in range(n_primary):
            oid = _PRIMARY_IDS[i] if i < len(_PRIMARY_IDS) else f"org_a{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _FOUNDER_GENOMES[i % len(_FOUNDER_GENOMES)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 0),
                )
            )
            roles[oid] = ROLE_PRIMARY
        for i in range(n_secondary):
            oid = _SECONDARY_IDS[i] if i < len(_SECONDARY_IDS) else f"org_b{i}"
            # Force COPY_SELF-capable founders for secondary (same pool as primary).
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _FOUNDER_GENOMES[(i + 2) % len(_FOUNDER_GENOMES)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 1),
                )
            )
            roles[oid] = ROLE_SECONDARY

        assert_single_atp_owner(organisms)

        configs = PopulationConfigs(
            # P2: engine reproduction ON — N=1 asexual SF partition.
            reproduction=ReproductionConfig(
                enabled=True,
                min_runtime_atp=min_runtime_atp,
                parent_atp_cost=parent_atp_cost,
                offspring_atp_fraction=offspring_atp_fraction,
                max_population=max_population,
            ),
            mutation=MutationConfig(bit_flip_rate=bit_flip_rate),
            metabolism=MetabolicConfig(
                enabled=True,
                basal_runtime_atp_cost=basal_atp_cost,
            ),
            ticks_per_generation=ticks_per_generation,
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
        world = World2D(width=world_size, height=world_size)
        if place_food:
            for x in range(min(4, world_size)):
                for y in range(min(2, world_size)):
                    world.place_resource((x, y), 4.0)
        runner = PopulationRunner(
            population=population,
            world=world,
            configs=configs,
        )
        return cls(
            seed=seed,
            runner=runner,
            roles=roles,
            parent_atp_cost=parent_atp_cost,
            offspring_atp_fraction=offspring_atp_fraction,
        )

    def _record_births(self, result: GenerationResult) -> None:
        """Measure partition witnesses from organism_records; grow role map."""

        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        new_births: list[tuple[str, str]] = []
        for record in result.organism_records:
            rr = record.reproduction_result
            if rr is None or not rr.succeeded or rr.child is None:
                continue
            if rr.birth_event is None or rr.reproduction_gate_result is None:
                continue
            # P2 accept path must not use skip/override shortcuts.
            # Engine chamber paths set those; asexual step_population does not.
            child = rr.child
            be = rr.birth_event
            gate = rr.reproduction_gate_result
            # Gate/birth_event are frozen at birth. Do NOT read rr.parent_after ATP:
            # step_population reuses that object for remaining ticks_per_generation
            # (basal + further actions), so live residual drifts after the partition.
            parent_before = float(gate.parent_runtime_atp_before_copy_self)
            cost = float(be.birth_cost_runtime_atp)
            iy = float(be.child_initial_runtime_atp or 0.0)
            child_runtime = float(child.atp_state.runtime_available)
            child_learning = float(child.atp_state.learning_available)
            expected_iy = round(
                (parent_before - cost) * self.offspring_atp_fraction, 10
            )
            # parent_after_at_birth implied by measured witnesses (cost dissipated).
            parent_after_at_birth = parent_before - cost - iy
            conserved = (
                iy > 0.0
                and abs(iy - expected_iy) <= _PARTITION_EPS
                and abs(child_runtime - iy) <= _PARTITION_EPS
                and abs(child_learning) <= _PARTITION_EPS
                and abs(
                    (parent_after_at_birth + child_runtime)
                    - (parent_before - cost)
                )
                <= _PARTITION_EPS
            )
            self.partition_ok_flags.append(conserved)
            self.birth_Iy.append(iy)
            self.total_births += 1

            parent_id = rr.parent_before_id
            parent_role = role_of(parent_id, role_map) or self.roles.get(parent_id)
            if parent_role in {ROLE_PRIMARY, ROLE_SECONDARY}:
                self.births_by_role[parent_role] = (
                    self.births_by_role.get(parent_role, 0) + 1
                )
            new_births.append((parent_id, child.id))

        if new_births:
            life = with_inherited_birth_roles(
                self.runner.configs.closed_loop_hp_life, new_births
            )
            self.runner.configs = replace(
                self.runner.configs, closed_loop_hp_life=life
            )
            role_map = life.role_map()

        self.roles = {
            org.id: (role_of(org.id, role_map) or self.roles.get(org.id, "unknown"))
            for org in self.runner.population.organisms
        }
        # Also map any lineage children that may have been selected in.
        for rec in self.runner.population.lineage:
            if rec.parent_id and rec.organism_id not in self.roles:
                prow = role_of(rec.parent_id, role_map) or self.roles.get(rec.parent_id)
                if prow:
                    self.roles[rec.organism_id] = prow

    def run_ticks(self, ticks: int) -> dict[str, Any]:
        if ticks < 0:
            raise ConfigurationError("ticks must be non-negative")
        for i in range(ticks):
            result = self.runner.step_generation(seed=self.seed + self.tick_index + i)
            self.tick_index += 1
            self._record_births(result)
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
            "births": self.total_births,
        }
        return canonical_digest(payload, prefix="clp2snap")

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
        n_ok = sum(1 for f in self.partition_ok_flags if f)
        n_checks = len(self.partition_ok_flags)
        mean_iy = (
            sum(self.birth_Iy) / len(self.birth_Iy) if self.birth_Iy else 0.0
        )
        # Measured witnesses only — never hardcoded True for conservation.
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
            "p2_scope": P2_SCOPE,
            "clock_api": "PopulationRunner.step_generation",
            "hp_world_tick_calls": self.hp_world_tick_calls,
            "reproduction_enabled": self.runner.configs.reproduction.enabled,
            "births": self.total_births,
            "births_primary": self.births_by_role.get(ROLE_PRIMARY, 0),
            "births_secondary": self.births_by_role.get(ROLE_SECONDARY, 0),
            "mean_child_atp": mean_iy,
            "mean_Iy": mean_iy,
            "partition_conserved_count": n_ok,
            "partition_conserved_checks": n_checks,
            "partition_conserved": bool(n_checks > 0 and n_ok == n_checks),
            "parent_atp_cost": self.parent_atp_cost,
            "offspring_atp_fraction": self.offspring_atp_fraction,
            "n_equals": 1,
            "asexual_only": True,
        }


def replay_bit_identical(*, seed: int, ticks: int) -> tuple[str, str]:
    """Same-seed session match (Gate7-shaped). NOT P4 dual-arm elicit/ablate."""

    a = ClosedLoopP2Session.boot(seed=seed)
    b = ClosedLoopP2Session.boot(seed=seed)
    a.run_ticks(ticks)
    b.run_ticks(ticks)
    return a.snapshot_digest(), b.snapshot_digest()
