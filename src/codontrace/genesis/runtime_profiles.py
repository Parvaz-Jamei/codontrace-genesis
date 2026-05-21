"""Official runtime profiles for GENESIS smoke and pilot runs.

Profiles are library helpers, not success-forcers: they only assemble worlds,
configs, codon tables, and evidence statuses so callers can run honest pilots.
"""

from __future__ import annotations

from dataclasses import replace

from codontrace.codon import CodonTable
from codontrace.genesis.engine import GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.capsule import CapsuleAdoptionPolicy, CapsuleTransferConfig
from codontrace.genesis.population import MutationConfig, PopulationConfigs, ReproductionConfig, RuntimeResourcePolicy
from codontrace.genesis.selection import EvolutionConfig
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.world import World2D, WorldObject


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
