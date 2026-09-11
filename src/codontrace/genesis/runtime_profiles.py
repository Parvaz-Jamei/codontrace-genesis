"""Official runtime profiles for GENESIS smoke and pilot runs.

Profiles are library helpers, not success-forcers: they only assemble worlds,
configs, codon tables, and evidence statuses so callers can run honest pilots.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from codontrace._types import JsonValue
from codontrace.codon import CodonTable
from codontrace.genesis.birth import InheritancePolicy, ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.capsule import CapsuleAdoptionPolicy, CapsuleTransferConfig
from codontrace.genesis.death import DeathMonitoringConfig
from codontrace.genesis.engine import GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.environment import EnvironmentConfig
from codontrace.genesis.liveness import AliveGateConfig
from codontrace.genesis.population import (
    FitnessConfig,
    MetabolicConfig,
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    ReproductionConfig,
    RuntimeResourcePolicy,
)
from codontrace.genesis.selection import EvolutionConfig
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.world import World2D, WorldObject

# EAT_LUMEN, COPY_SELF, WAIT — eat first so runtime ATP can cross the reproduction gate.
LIFE_LOOP_EATER_GENOME = "101111000"
# EAT_LUMEN, WAIT, COPY_SELF — second sexual parent haplotype used only when
# life_loop_world(reproduction_mode=sexual_crossover) is selected.
LIFE_LOOP_EATER_B_GENOME = "101000111"
# WAIT only — control genome that cannot collect food or attempt COPY_SELF.
LIFE_LOOP_WAITER_GENOME = "000000000"
# COPY_SELF spends 8.0 ATP during the organism step before can_reproduce()
# inspects the ledger. After that debit, eaters must still clear min_runtime_atp;
# waiters / no-food COPY attempts must not. Basal drain is profile-only.
LIFE_LOOP_INITIAL_RUNTIME_ATP = 14.0
LIFE_LOOP_MIN_RUNTIME_ATP = 8.0
LIFE_LOOP_RESOURCE_AMOUNT = 6.0
LIFE_LOOP_BASAL_COST = 1.2
LIFE_LOOP_FOOD_CELLS = ((0, 0), (1, 0))
LIFE_LOOP_MAX_RESOURCES = 3
LIFE_LOOP_RESPAWN_RATE = 0.4


class GenesisRuntimeProfile:
    """Factory namespace for official GENESIS runtime profiles."""

    @staticmethod
    def empty_world_smoke(*, seed: int = 1, tick_count: int = 3) -> GenesisExperimentSpec:
        return GenesisExperimentSpec(
            seed=seed,
            tick_count=tick_count,
            engine_config=GenesisEngineConfig(claim_level="foundation_engine", qd_mode="disabled", enable_qd=False),
            metadata={
                "default_world_profile": "empty_world_smoke",
                "resource_runtime_status": "no_resource_pressure",
                "claim_allowed_for_evolution": False,
                "scenario_status": "metadata_only_not_evidence_bearing",
            },
        )

    @staticmethod
    def evolution_pilot_world(*, seed: int = 1, tick_count: int = 50, population: int = 6) -> GenesisExperimentSpec:
        world = World2D(6, 4)
        for pos in ((0, 0), (1, 0), (2, 1), (4, 2)):
            world.place_resource(pos, 2.0)
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(max_population=max(population * 2, 12), parent_atp_cost=1.0),
            mutation=MutationConfig(bit_flip_rate=0.02),
            evolution=EvolutionConfig(max_population=max(population * 2, 12), selection_policy="novelty_weighted", qd_mode="selection_pressure"),
            qd_mode="selection_pressure",
            runtime_resource_policy=RuntimeResourcePolicy(respawn_enabled=True, respawn_rate=1.0, max_resources=8, amount=2.0),
        )
        genomes = tuple("101111000" for _ in range(population))  # EAT_LUMEN, COPY_SELF, WAIT
        return GenesisExperimentSpec(
            genome_bits=genomes,
            seed=seed,
            tick_count=tick_count,
            world_width=world.width,
            world_height=world.height,
            population_max=max(population * 2, 12),
            element_grid=world2d_to_element_grid(world),
            substrate_bridge_mode="element_grid_source",
            population_configs=configs,
            engine_config=GenesisEngineConfig(qd_mode="selection_pressure", claim_level="experimental_engine"),
            metadata={
                "runtime_profile": "evolution_pilot_world",
                "resource_runtime_status": "runtime_effective_default_off",
                "claim_allowed_for_evolution": True,
                "profile_has_resources": True,
                "profile_has_mutation": True,
                "profile_has_birth_action": True,
                "profile_has_selection_pressure": True,
            },
        )

    @staticmethod
    def toolchain_pilot_world(*, seed: int = 1, tick_count: int = 6) -> GenesisExperimentSpec:
        world = World2D(4, 4)
        # Keep this profile portable through ElementGrid: Lumen becomes a generic
        # collectable resource, then public tool primitives craft, unlock, cross,
        # and deposit it into a reward-bearing terminal transition.
        world.place_resource((0, 0), 2.0)
        return GenesisExperimentSpec(
            genome_bits=("011001111001101010110000",),
            seed=seed,
            tick_count=tick_count,
            world_width=world.width,
            world_height=world.height,
            element_grid=world2d_to_element_grid(world),
            substrate_bridge_mode="element_grid_source",
            codon_table=CodonTable.genesis_toolchain_v0(),
            metadata={
                "runtime_profile": "toolchain_pilot_world",
                "toolchain_status": "runtime_effective_default_off",
                "toolchain_expected_chain": [
                    "COLLECT_RESOURCE",
                    "CRAFT_ITEM",
                    "UNLOCK_CELL",
                    "CROSS_TERRAIN",
                    "DEPOSIT_RESOURCE",
                ],
            },
        )

    @staticmethod
    def qd_selection_pilot_world(*, seed: int = 1, tick_count: int = 8, population: int = 8) -> GenesisExperimentSpec:
        """Build a controlled runtime QD pilot with real over-capacity novelty pressure."""

        world = World2D(6, 4)
        for pos in ((0, 0), (1, 0), (2, 1), (4, 2)):
            world.place_resource(pos, 2.0)
        genomes = (
            "101000000",  # EAT_LUMEN + WAITs
            "011000000",  # MOVE_TOWARD + WAITs
            "110000000",  # EMIT_NEXUS + WAITs
            "111000000",  # COPY_SELF + WAITs
            "100000000",  # MOVE_AWAY + WAITs
            "001000000",  # SENSE_FOOD + WAITs
            "010000000",  # SENSE_DANGER + WAITs
            "011101000",  # MOVE_TOWARD + EAT_LUMEN + WAIT
        )[:population]
        capacity = max(2, min(4, len(genomes) - 1))
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(max_population=capacity, parent_atp_cost=1.0),
            mutation=MutationConfig(bit_flip_rate=0.0),
            evolution=EvolutionConfig(
                max_population=capacity,
                selection_policy="novelty_weighted",
                qd_mode="selection_pressure",
                novelty_weight=10.0,
                fitness_weight=0.1,
            ),
            qd_mode="selection_pressure",
            runtime_resource_policy=RuntimeResourcePolicy(
                respawn_enabled=True, respawn_rate=1.0, max_resources=8, amount=2.0
            ),
        )
        return GenesisExperimentSpec(
            genome_bits=genomes,
            seed=seed,
            tick_count=tick_count,
            world_width=world.width,
            world_height=world.height,
            population_max=capacity,
            element_grid=world2d_to_element_grid(world),
            substrate_bridge_mode="element_grid_source",
            population_configs=configs,
            engine_config=GenesisEngineConfig(qd_mode="selection_pressure", claim_level="experimental_engine"),
            metadata={
                "runtime_profile": "qd_selection_pilot_world",
                "qd_mode": "selection_pressure",
                "scenario_status": "runtime_effective_default_off",
                "claim_allowed_for_qd_selection": True,
                "requires_qd_changed_selection": True,
            },
        )

    @staticmethod
    def capsule_utility_pilot_world(*, seed: int = 1, tick_count: int = 8) -> GenesisExperimentSpec:
        """Build a two-agent capsule pilot with real emission/read/adoption records."""

        world = World2D(4, 4)
        capsule_config = CapsuleTransferConfig(
            enabled=True,
            read_radius=10,
            emission_cost_runtime_atp=0.0,
            emission_cost_learning_atp=0.0,
            read_cost_runtime_atp=0.0,
            adoption_cost_learning_atp=0.0,
            adoption_requires_atp_learning=False,
            min_atp_runtime_to_emit=0.0,
            max_adoptions_per_organism=2,
            max_capsules_read_per_tick=4,
            adoption_policy=CapsuleAdoptionPolicy.THRESHOLD,
        )
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(max_population=2),
            capsule_transfer=capsule_config,
            enable_nexus_stigmergy=True,
            qd_mode="disabled",
        )
        return GenesisExperimentSpec(
            genome_bits=("110000000", "000000000"),  # source emits nexus; target waits and reads.
            seed=seed,
            tick_count=tick_count,
            world_width=world.width,
            world_height=world.height,
            population_max=2,
            element_grid=world2d_to_element_grid(world),
            substrate_bridge_mode="element_grid_source",
            population_configs=configs,
            capsule_transfer_config=capsule_config,
            engine_config=GenesisEngineConfig(
                enable_capsules=True,
                enable_causal_graph=True,
                enable_memory=True,
                enable_qd=False,
                qd_mode="disabled",
                claim_level="experimental_engine",
            ),
            metadata={
                "runtime_profile": "capsule_utility_pilot_world",
                "capsule_mode": "behavioral_adoption",
                "scenario_status": "runtime_effective_default_off",
                "claim_allowed_for_capsule_usefulness": False,
            },
        )

    @staticmethod
    def social_partner_pilot_world(*, seed: int = 1, tick_count: int = 4) -> GenesisExperimentSpec:
        """Build a two-agent resource-competition world for non-capsule social events."""

        world = World2D(4, 4)
        resource_pos = (0, 0)
        resource_amount = 2.0 + float(seed % 3)
        world.place_resource(resource_pos, resource_amount)
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(max_population=2),
            qd_mode="disabled",
            runtime_resource_policy=RuntimeResourcePolicy(respawn_enabled=False),
        )
        return GenesisExperimentSpec(
            genome_bits=("101000000", "000000000"),
            seed=seed,
            tick_count=tick_count,
            world_width=world.width,
            world_height=world.height,
            population_max=2,
            element_grid=world2d_to_element_grid(world),
            substrate_bridge_mode="element_grid_source",
            population_configs=configs,
            engine_config=GenesisEngineConfig(
                enable_capsules=False,
                enable_qd=False,
                qd_mode="disabled",
                claim_level="experimental_engine",
            ),
            metadata={
                "runtime_profile": "social_partner_pilot_world",
                "social_mode": "non_capsule_resource_interaction",
                "claim_allowed_for_social_intelligence": False,
                "heldout_partner_seed": seed,
                "heldout_resource_position": [resource_pos[0], resource_pos[1]],
                "heldout_resource_amount": resource_amount,
                "heldout_distinctness_protocol": "seed_changes_resource_amount_and_event_digest",
            },
        )

    @staticmethod
    def memory_delayed_reward_pilot_world(*, seed: int = 1, tick_count: int = 8) -> GenesisExperimentSpec:
        """Build a small signal/write -> later resource reward pilot."""

        spec = GenesisRuntimeProfile.evolution_pilot_world(seed=seed, tick_count=tick_count, population=1)
        return replace(
            spec,
            genome_bits=("000101000",),  # WAIT/write signal, EAT_LUMEN reward, WAIT.
            population_max=2,
            engine_config=replace(spec.engine_config, enable_memory=True),
            metadata={
                **spec.metadata,
                "runtime_profile": "memory_delayed_reward_pilot_world",
                "memory_task_status": "runtime_effective_default_off",
                "claim_allowed_for_strong_memory": False,
            },
        )

    @staticmethod
    def life_loop_world(
        *,
        seed: int = 1,
        tick_count: int = 16,
        population: int = 6,
        offspring_placement: OffspringPlacementPolicy = OffspringPlacementPolicy.ADJACENT_FREE,
        reproduction_mode: ReproductionMode = ReproductionMode.ASEXUAL,
        environment: EnvironmentConfig | None = None,
    ) -> GenesisExperimentSpec:
        """Assemble the Phase A ecology / Darwinian life-loop preset.

        This is an explicit research preset. It does not change global
        ``ReproductionConfig`` / ``ResourceConfig`` defaults. SAME_CELL placement
        remains available by passing ``offspring_placement=OffspringPlacementPolicy.SAME_CELL``.
        ``REPLACE_OCCUPIED`` is an optional Avida-like overwrite policy and is
        not the life-loop default. Asexual COPY_SELF remains the default
        inheritance path; pass         ``reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER``
        to enable Phase B Avida-parity sexual recombination (birth chamber +
        positional continuous corresponding crossover). Direct
        ``reproduce(..., mate=...)`` remains a one-child library API.
        Pass ``environment=EnvironmentConfig(...)`` (or use
        ``dynamic_environment_world()``) for Phase C chemostat / periodic /
        fluctuating regimes. Default stays the Phase A limited-patch ecology.

        Literature grounding (software-capability only, not an Avida
        replacement): limited, depletable resources with partial inflow
        (Avida ecology / Cooper–Ofria; Frontiers digital-evolution review 2021)
        plus a basal energy-budget drain (JaxLife 2024, EEDx-style ISAL).
        Sexual opt-in follows Misevic, Ofria, Lenski 2006 Proc B and
        ``devosoft/avida`` ``avida.cfg`` ``RECOMBINATION_GROUP`` (birth chamber,
        ``RECOMBINATION_PROB``, ``SAME_LENGTH_SEX``, ``TWO_FOLD_COST_SEX``,
        ``MAX_BIRTH_WAIT_TIME``). Diploid meiosis (Aevol Eukaryote) is
        deferred as Phase B.1.

        Parameters that keep food scarce rather than infinite:
        ``LIFE_LOOP_FOOD_CELLS`` (2 patches), ``LIFE_LOOP_MAX_RESOURCES`` (3),
        ``LIFE_LOOP_RESPAWN_RATE`` (0.4). Eat removes the local patch;
        respawn may restore at most one empty cell per tick when below cap.

        Observed software capability only: organisms pay basal ATP every tick,
        eating credits runtime ATP, starvation at the configured floor records
        an explicit death reason, survivors that clear AliveGate and ATP gates
        can COPY_SELF, and children inherit a mutated copy of the parent
        genome unless sexual crossover is explicitly enabled. This is not a
        proof of life, intelligence, instinct evolution, or Avida-replacement
        status.
        """

        if population <= 0:
            raise ValueError("life_loop_world population must be > 0.")
        world = World2D(6, 4)
        for pos in LIFE_LOOP_FOOD_CELLS:
            world.place_resource(pos, LIFE_LOOP_RESOURCE_AMOUNT)
        waiter_count = 0 if population < 3 else max(1, population // 3)
        eater_count = population - waiter_count
        if reproduction_mode is ReproductionMode.SEXUAL_CROSSOVER and eater_count >= 2:
            eater_b_count = eater_count // 2
            eater_a_count = eater_count - eater_b_count
            eater_genomes = (
                [LIFE_LOOP_EATER_GENOME] * eater_a_count
                + [LIFE_LOOP_EATER_B_GENOME] * eater_b_count
            )
        else:
            eater_genomes = [LIFE_LOOP_EATER_GENOME] * eater_count
        genomes = tuple(eater_genomes + [LIFE_LOOP_WAITER_GENOME] * waiter_count)
        capacity = max(population, 8)
        selection_capacity = max(2, min(capacity - 2, population + max(1, eater_count)))
        sexual = reproduction_mode is ReproductionMode.SEXUAL_CROSSOVER
        env_cfg = environment if environment is not None else EnvironmentConfig()
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(
                max_population=capacity,
                min_runtime_atp=LIFE_LOOP_MIN_RUNTIME_ATP,
                parent_atp_cost=1.0,
                offspring_atp_fraction=0.25,
                require_alive_result=True,
                inheritance_policy=InheritancePolicy.DARWINIAN_GENETIC_ONLY,
                offspring_placement=offspring_placement,
                reproduction_mode=reproduction_mode,
            ),
            mutation=MutationConfig(bit_flip_rate=0.05),
            fitness=FitnessConfig(),
            alive_gate=AliveGateConfig(
                min_ticks=1,
                min_executed_actions=1,
                max_blocked_ratio=0.95,
                require_positive_runtime_atp=True,
                require_lumen_interaction=False,
                require_reproduction_capability=False,
            ),
            death_monitoring=DeathMonitoringConfig(
                remove_on_runtime_atp_lte=0.0,
                starvation_floor=0.0,
                starvation_consecutive_ticks=1,
                starvation_reason="starvation",
            ),
            evolution=EvolutionConfig(
                max_population=selection_capacity,
                selection_policy="fitness_proportional",
                qd_mode="disabled",
            ),
            qd_mode="disabled",
            runtime_resource_policy=RuntimeResourcePolicy(
                respawn_enabled=True,
                respawn_rate=LIFE_LOOP_RESPAWN_RATE,
                max_resources=LIFE_LOOP_MAX_RESOURCES,
                amount=LIFE_LOOP_RESOURCE_AMOUNT,
                status="runtime_effective_default_on",
            ),
            metabolism=MetabolicConfig(
                enabled=True,
                basal_runtime_atp_cost=LIFE_LOOP_BASAL_COST,
            ),
            sexual_recombination=SexualRecombinationConfig(enabled=True)
            if sexual
            else SexualRecombinationConfig(),
            environment=env_cfg,
        )
        return GenesisExperimentSpec(
            genome_bits=genomes,
            seed=seed,
            tick_count=tick_count,
            world_width=world.width,
            world_height=world.height,
            initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
            population_max=capacity,
            element_grid=world2d_to_element_grid(world),
            substrate_bridge_mode="element_grid_source",
            population_configs=configs,
            reproduction_config=configs.reproduction,
            mutation_config=configs.mutation,
            evolution_config=configs.evolution,
            engine_config=GenesisEngineConfig(
                enable_qd=False,
                qd_mode="disabled",
                claim_level="experimental_engine",
            ),
            metadata={
                "runtime_profile": "life_loop_world",
                "ecology_profile": "phase_a_life_loop",
                "resource_runtime_status": "runtime_effective_default_on",
                "profile_has_resources": True,
                "profile_has_resource_respawn": True,
                "profile_has_limited_depletable_resources": True,
                "profile_has_basal_metabolism": True,
                "profile_has_starvation_death": True,
                "profile_has_mutation": True,
                "profile_has_birth_action": True,
                "profile_has_spatial_offspring_placement": (
                    offspring_placement is not OffspringPlacementPolicy.SAME_CELL
                ),
                "offspring_placement": offspring_placement.value,
                "same_cell_available_as_explicit_policy": True,
                "replace_occupied_available_as_explicit_policy": True,
                "offspring_overwrite_is_not_research_default": True,
                "inheritance_mode": InheritancePolicy.DARWINIAN_GENETIC_ONLY.value,
                "selection_policy": "fitness_proportional",
                "basal_runtime_atp_cost": LIFE_LOOP_BASAL_COST,
                "starvation_floor": 0.0,
                "starvation_consecutive_ticks": 1,
                "starvation_reason": "starvation",
                "food_cells": [list(pos) for pos in LIFE_LOOP_FOOD_CELLS],
                "initial_food_patches": len(LIFE_LOOP_FOOD_CELLS),
                "max_resources": LIFE_LOOP_MAX_RESOURCES,
                "respawn_rate": LIFE_LOOP_RESPAWN_RATE,
                "resource_amount": LIFE_LOOP_RESOURCE_AMOUNT,
                "resource_mode": "limited_depletable_with_partial_respawn",
                "literature_grounding": (
                    "avida_limited_resources_plus_energy_budget_alife_"
                    "not_avida_replacement"
                ),
                "claim_allowed_for_evolution": False,
                "claim_allowed_for_life": False,
                "claim_allowed_for_intelligence": False,
                "claim_ceiling": "runtime_observation",
                "claim_language": (
                    "software_capability_and_runtime_observation_only_"
                    "not_life_intelligence_or_cooperation_proof"
                ),
                "phase_b_sexual_crossover": (
                    "enabled"
                    if reproduction_mode is ReproductionMode.SEXUAL_CROSSOVER
                    else "deferred"
                ),
                "phase_c_fluctuating_environment": (
                    "enabled" if env_cfg.enabled else "deferred"
                ),
                "phase_d_instinct_claim_metrics": "hooks_only_not_implemented",
                **(
                    {
                        "reproduction_mode": reproduction_mode.value,
                        "inheritance_path": "two_parent_positional_crossover",
                        "sexual_pairing": "birth_chamber",
                        "literature_grounding_sex": (
                            "misevic_ofria_lenski_2006_avida_recombination_group_"
                            "not_avida_replacement"
                        ),
                        "recombination_prob": 1.0,
                        "same_length_only": False,
                        "two_fold_cost_sex": False,
                        "max_birth_wait_ticks": None,
                        "phase_b1_diploid_meiosis": "deferred",
                    }
                    if reproduction_mode is ReproductionMode.SEXUAL_CROSSOVER
                    else {}
                ),
                **(
                    {
                        "runtime_profile": "dynamic_environment_world",
                        "resource_mode": "chemostat_periodic_or_seeded",
                        "environment_spatial_mode": env_cfg.spatial_mode,
                        "environment_schedule_kind": env_cfg.schedule.kind,
                        "environment_period_ticks": env_cfg.schedule.period_ticks,
                        "environment_config_digest": env_cfg.digest(),
                        "environment_regimes": [regime.name for regime in env_cfg.schedule.regimes],
                        "literature_grounding_environment": (
                            "ofria_wilke_2004_avida_resource_line_"
                            "cooper_ofria_chemostat_avida_ed_periodic_"
                            "not_avida_replacement_not_plasticity_claim"
                        ),
                        "profile_has_chemostat": True,
                        "profile_has_periodic_or_seeded_schedule": (
                            env_cfg.schedule.kind != "static"
                        ),
                        "claim_allowed_for_plasticity": False,
                    }
                    if env_cfg.enabled
                    else {}
                ),
            },
        )

    @staticmethod
    def dynamic_environment_world(
        *,
        seed: int = 1,
        tick_count: int = 16,
        population: int = 6,
        period_ticks: int = 4,
        schedule_kind: str = "periodic",
        spatial_mode: str = "global_and_local",
        niche_maps: bool = False,
        switch_ticks: tuple[int, ...] = (),
        diffusion_rate: float = 0.0,
        decay_rate: float = 0.0,
        reproduction_mode: ReproductionMode = ReproductionMode.ASEXUAL,
        offspring_placement: OffspringPlacementPolicy = OffspringPlacementPolicy.ADJACENT_FREE,
    ) -> GenesisExperimentSpec:
        """Phase C opt-in: life-loop ecology plus chemostat / fluctuating env.

        Default life-loop and sexual presets are unchanged. This helper enables
        an Avida ``RESOURCE`` chemostat (initial/inflow/outflow=0.01) with two
        regimes (high-food vs low-food, or two niche maps) on a periodic or
        seeded schedule. Claim ceiling remains runtime_observation; this does
        not claim that phenotypic plasticity evolved.
        """

        environment = EnvironmentConfig.fluctuating_chemostat(
            initial=LIFE_LOOP_RESOURCE_AMOUNT * len(LIFE_LOOP_FOOD_CELLS),
            inflow=2.0,
            outflow=0.01,
            period_ticks=period_ticks,
            patch_cells=LIFE_LOOP_FOOD_CELLS,
            spatial_mode=spatial_mode,
            schedule_kind=schedule_kind,
            switch_ticks=switch_ticks,
            cell_inflow=LIFE_LOOP_RESOURCE_AMOUNT,
            diffusion_rate=diffusion_rate,
            decay_rate=decay_rate,
            niche_maps=niche_maps,
        )
        return GenesisRuntimeProfile.life_loop_world(
            seed=seed,
            tick_count=tick_count,
            population=population,
            offspring_placement=offspring_placement,
            reproduction_mode=reproduction_mode,
            environment=environment,
        )


@dataclass(frozen=True, slots=True)
class LifeLoopObservation:
    """Phase A/D hook: descriptive counts from one life-loop run.

    This is a runtime observation record. It is not an instinct, intelligence,
    cooperation, or ALife-proof metric.
    """

    lumen_eaten_events: int
    reproduction_attempts: int
    births: int
    deaths: int
    resource_respawn_events: int
    parent_child_pairs: int
    heritable_asexual_pairs: int
    mutated_child_pairs: int
    adjacent_or_displaced_births: int
    same_cell_births: int
    eater_births: int
    waiter_births: int
    starvation_deaths: int
    surviving_eater_lineages: int
    surviving_waiter_lineages: int
    remaining_resource_cells: int
    replay_digest: str
    heritable_sexual_pairs: int = 0
    recombinant_child_pairs: int = 0
    two_parent_lineage_records: int = 0
    claim_ceiling: str = "runtime_observation"
    genesis_alive_full: bool = False
    phase_d_instinct_metrics: str = "hooks_only_not_implemented"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "lumen_eaten_events": self.lumen_eaten_events,
            "reproduction_attempts": self.reproduction_attempts,
            "births": self.births,
            "deaths": self.deaths,
            "resource_respawn_events": self.resource_respawn_events,
            "parent_child_pairs": self.parent_child_pairs,
            "heritable_asexual_pairs": self.heritable_asexual_pairs,
            "mutated_child_pairs": self.mutated_child_pairs,
            "adjacent_or_displaced_births": self.adjacent_or_displaced_births,
            "same_cell_births": self.same_cell_births,
            "eater_births": self.eater_births,
            "waiter_births": self.waiter_births,
            "starvation_deaths": self.starvation_deaths,
            "surviving_eater_lineages": self.surviving_eater_lineages,
            "surviving_waiter_lineages": self.surviving_waiter_lineages,
            "remaining_resource_cells": self.remaining_resource_cells,
            "replay_digest": self.replay_digest,
            "heritable_sexual_pairs": self.heritable_sexual_pairs,
            "recombinant_child_pairs": self.recombinant_child_pairs,
            "two_parent_lineage_records": self.two_parent_lineage_records,
            "claim_ceiling": self.claim_ceiling,
            "genesis_alive_full": self.genesis_alive_full,
            "phase_d_instinct_metrics": self.phase_d_instinct_metrics,
        }


def summarize_life_loop_observation(result: object) -> LifeLoopObservation:
    """Extract eat/survive/reproduce observation counts from an engine result.

    Phase D may later attach multi-generation instinct metrics to this hook.
    The current helper only reports runtime counts, asexual parent→child
    relatedness, and optional two-parent recombination counts when sexual
    lineage records are present. It does not evaluate intelligence or
    cooperation.
    """

    ticks = getattr(result, "ticks", ())
    lumen_eaten = 0
    attempts = 0
    births = 0
    deaths = 0
    respawns = 0
    starvation_deaths = 0
    remaining_resource_cells = 0
    recombination_proof = 0
    bits_by_id: dict[str, str] = {}
    position_by_id: dict[str, tuple[int, int]] = {}
    seen_lineage: dict[tuple[str, str, int], object] = {}
    final_bits: dict[str, str] = {}
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        births += int(getattr(generation, "births", 0) or 0)
        deaths += int(getattr(generation, "deaths", 0) or 0)
        attempts += int(getattr(generation, "reproduction_attempts", 0) or 0)
        world_after = getattr(generation, "world_after", None)
        resources = getattr(world_after, "resources", None)
        if isinstance(resources, dict):
            remaining_resource_cells = len(resources)
        for event in getattr(generation, "resource_policy_records", ()):
            if getattr(event, "event_type", "") == "resource_regenerated":
                respawns += 1
        for record in getattr(generation, "organism_records", ()):
            death = getattr(record, "death_classification", None)
            if death is None or not getattr(death, "actual_death_removed_from_population", False):
                continue
            reason = getattr(death, "fatal_policy_reason", None) or getattr(
                death, "removal_reason", None
            )
            if reason in {"starvation", "insufficient_atp"}:
                starvation_deaths += 1
        for record in getattr(generation, "organism_records", ()):
            reproduction = getattr(record, "reproduction_result", None)
            recombination = None if reproduction is None else getattr(
                reproduction, "recombination_record", None
            )
            if recombination is None:
                continue
            start = int(getattr(recombination, "start_index", 0) or 0)
            end = int(getattr(recombination, "end_index", 0) or 0)
            parent_a_bits = getattr(recombination, "parent_a_bits", "") or ""
            parent_b_bits = getattr(recombination, "parent_b_bits", "") or ""
            child_pre = getattr(recombination, "child_genome_bits", "") or ""
            if (
                parent_a_bits
                and parent_b_bits
                and child_pre
                and parent_a_bits[start:end] != parent_b_bits[start:end]
                and child_pre[start:end] == parent_b_bits[start:end]
            ):
                recombination_proof += 1
        for trace in getattr(generation, "traces", ()):
            for event in getattr(trace, "events", ()):
                if event.action == "EAT_LUMEN" and (
                    event.world_delta.get("lumen_interaction") is True
                    or isinstance(event.world_delta.get("lumen_consumed"), (int, float))
                    or event.reason == "lumen_consumed"
                ):
                    lumen_eaten += 1
        population = getattr(generation, "population", None)
        if population is None:
            continue
        final_bits = {}
        for organism in getattr(population, "organisms", ()):
            bits_by_id[organism.id] = organism.genome.to_compact()
            position_by_id[organism.id] = organism.position
            final_bits[organism.id] = organism.genome.to_compact()
        for lineage in getattr(population, "lineage", ()):
            parent_id = getattr(lineage, "parent_id", None)
            child_id = getattr(lineage, "organism_id", None)
            birth_tick = int(getattr(lineage, "birth_tick", 0) or 0)
            if not parent_id or not child_id:
                continue
            seen_lineage[(str(parent_id), str(child_id), birth_tick)] = lineage

    heritable_pairs = 0
    mutated_pairs = 0
    displaced_births = 0
    same_cell_births = 0
    eater_births = 0
    waiter_births = 0
    sexual_pairs = 0
    two_parent_records = 0
    for (parent_id, child_id, _birth_tick), lineage in seen_lineage.items():
        parent_bits = bits_by_id.get(parent_id, "")
        child_bits = bits_by_id.get(child_id, "")
        second_parent_id = getattr(lineage, "second_parent_id", None)
        if second_parent_id:
            two_parent_records += 1
            sexual_pairs += 1
            if getattr(lineage, "recombination_window_differed", False):
                recombination_proof += 1
        elif parent_bits and child_bits and _asexual_related(parent_bits, child_bits):
            heritable_pairs += 1
        mutation_count = int(getattr(lineage, "mutation_count", 0) or 0)
        if (parent_bits and child_bits and parent_bits != child_bits) or mutation_count > 0:
            mutated_pairs += 1
        parent_pos = position_by_id.get(parent_id)
        child_pos = position_by_id.get(child_id)
        if parent_pos is not None and child_pos is not None:
            if parent_pos != child_pos:
                displaced_births += 1
            else:
                same_cell_births += 1
        if parent_bits.startswith("101"):
            eater_births += 1
        elif parent_bits.startswith("000"):
            waiter_births += 1
    surviving_eaters = sum(1 for bits in final_bits.values() if bits.startswith("101"))
    surviving_waiters = sum(1 for bits in final_bits.values() if bits.startswith("000"))
    digest = result.digest() if hasattr(result, "digest") else ""
    return LifeLoopObservation(
        lumen_eaten_events=lumen_eaten,
        reproduction_attempts=attempts,
        births=births,
        deaths=deaths,
        resource_respawn_events=respawns,
        parent_child_pairs=len(seen_lineage),
        heritable_asexual_pairs=heritable_pairs,
        mutated_child_pairs=mutated_pairs,
        adjacent_or_displaced_births=displaced_births,
        same_cell_births=same_cell_births,
        eater_births=eater_births,
        waiter_births=waiter_births,
        starvation_deaths=starvation_deaths,
        surviving_eater_lineages=surviving_eaters,
        surviving_waiter_lineages=surviving_waiters,
        remaining_resource_cells=remaining_resource_cells,
        replay_digest=str(digest),
        heritable_sexual_pairs=sexual_pairs,
        recombinant_child_pairs=recombination_proof,
        two_parent_lineage_records=two_parent_records,
    )


def _asexual_related(parent_bits: str, child_bits: str) -> bool:
    """Return True when child bits look like a mutated copy of the parent."""

    if not parent_bits or not child_bits:
        return False
    if parent_bits == child_bits:
        return True
    if abs(len(parent_bits) - len(child_bits)) > 3:
        return False
    width = max(len(parent_bits), len(child_bits))
    left = parent_bits.ljust(width, "0")
    right = child_bits.ljust(width, "0")
    distance = sum(a != b for a, b in zip(left, right, strict=True))
    return distance <= max(1, width // 3)
