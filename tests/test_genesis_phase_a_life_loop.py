"""Phase A Darwinian life-loop tests.

These tests document software capability and runtime observation only. They do
not claim artificial life, intelligence, cooperation, or instinct evolution.
"""

from __future__ import annotations

from codontrace.genesis.birth import InheritancePolicy
from codontrace.genesis.death import DeathMonitoringConfig
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    FitnessConfig,
    MetabolicConfig,
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    RuntimeResourcePolicy,
    can_reproduce,
    reproduce,
    step_population,
)
from codontrace.genesis.runtime_profiles import (
    LIFE_LOOP_BASAL_COST,
    LIFE_LOOP_EATER_GENOME,
    LIFE_LOOP_FOOD_CELLS,
    LIFE_LOOP_INITIAL_RUNTIME_ATP,
    LIFE_LOOP_MAX_RESOURCES,
    LIFE_LOOP_MIN_RUNTIME_ATP,
    LIFE_LOOP_RESOURCE_AMOUNT,
    LIFE_LOOP_RESPAWN_RATE,
    LIFE_LOOP_WAITER_GENOME,
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)
from codontrace.genesis.selection import EvolutionConfig
from codontrace.world import World2D


def _life_loop_unit_configs(
    *,
    placement: OffspringPlacementPolicy = OffspringPlacementPolicy.ADJACENT_FREE,
    bit_flip_rate: float = 0.0,
    max_population: int = 8,
    enable_metabolism: bool = False,
    enable_starvation: bool = False,
    respawn_rate: float = 1.0,
    max_resources: int = 8,
) -> PopulationConfigs:
    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=LIFE_LOOP_MIN_RUNTIME_ATP,
            parent_atp_cost=1.0,
            max_population=max_population,
            offspring_atp_fraction=0.25,
            inheritance_policy=InheritancePolicy.DARWINIAN_GENETIC_ONLY,
            offspring_placement=placement,
        ),
        mutation=MutationConfig(bit_flip_rate=bit_flip_rate),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=True,
        ),
        death_monitoring=DeathMonitoringConfig(
            remove_on_runtime_atp_lte=0.0,
            starvation_floor=0.0 if enable_starvation else None,
            starvation_consecutive_ticks=1,
            starvation_reason="starvation",
        ),
        evolution=EvolutionConfig(
            max_population=max_population,
            selection_policy="fitness_proportional",
            qd_mode="disabled",
        ),
        qd_mode="disabled",
        runtime_resource_policy=RuntimeResourcePolicy(
            respawn_enabled=True,
            respawn_rate=respawn_rate,
            max_resources=max_resources,
            amount=LIFE_LOOP_RESOURCE_AMOUNT,
            status="runtime_effective_default_on",
        ),
        metabolism=MetabolicConfig(
            enabled=enable_metabolism,
            basal_runtime_atp_cost=LIFE_LOOP_BASAL_COST if enable_metabolism else 0.0,
        ),
        ticks_per_generation=1,
    )


def test_default_reproduction_placement_remains_same_cell() -> None:
    assert ReproductionConfig().offspring_placement is OffspringPlacementPolicy.SAME_CELL


def test_life_loop_profile_is_explicit_ecology_preset() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=4, population=6)
    configs = spec.population_configs
    assert configs is not None
    assert spec.metadata["runtime_profile"] == "life_loop_world"
    assert spec.metadata["claim_ceiling"] == "runtime_observation"
    assert spec.metadata["claim_allowed_for_life"] is False
    assert spec.metadata["claim_allowed_for_intelligence"] is False
    assert spec.metadata["phase_b_sexual_crossover"] == "deferred"
    assert spec.metadata["phase_c_fluctuating_environment"] == "deferred"
    assert spec.metadata["phase_d_instinct_claim_metrics"] == "hooks_only_not_implemented"
    assert spec.metadata["offspring_placement"] == "adjacent_free"
    assert spec.metadata["resource_mode"] == "limited_depletable_with_partial_respawn"
    assert spec.metadata["profile_has_basal_metabolism"] is True
    assert spec.metadata["profile_has_starvation_death"] is True
    assert spec.metadata["replace_occupied_available_as_explicit_policy"] is True
    assert spec.metadata["offspring_overwrite_is_not_research_default"] is True
    assert spec.metadata["initial_food_patches"] == len(LIFE_LOOP_FOOD_CELLS)
    assert spec.metadata["max_resources"] == LIFE_LOOP_MAX_RESOURCES
    assert spec.metadata["respawn_rate"] == LIFE_LOOP_RESPAWN_RATE
    assert spec.metadata["starvation_reason"] == "starvation"
    assert configs.reproduction.offspring_placement is OffspringPlacementPolicy.ADJACENT_FREE
    assert configs.reproduction.inheritance_policy is InheritancePolicy.DARWINIAN_GENETIC_ONLY
    assert configs.runtime_resource_policy.respawn_enabled is True
    assert configs.runtime_resource_policy.respawn_rate == LIFE_LOOP_RESPAWN_RATE
    assert configs.runtime_resource_policy.max_resources == LIFE_LOOP_MAX_RESOURCES
    assert configs.metabolism.enabled is True
    assert configs.metabolism.basal_runtime_atp_cost == LIFE_LOOP_BASAL_COST
    assert configs.death_monitoring.starvation_floor == 0.0
    assert configs.death_monitoring.starvation_reason == "starvation"
    assert configs.evolution is not None
    assert configs.evolution.resolved_policy().name == "fitness_proportional"
    assert spec.element_grid is not None
    assert spec.genome_bits.count(LIFE_LOOP_EATER_GENOME) >= 1
    assert spec.genome_bits.count(LIFE_LOOP_WAITER_GENOME) >= 1
    assert spec.initial_runtime_atp == LIFE_LOOP_INITIAL_RUNTIME_ATP
    assert configs.reproduction.min_runtime_atp == LIFE_LOOP_MIN_RUNTIME_ATP


def test_life_loop_profile_keeps_same_cell_as_explicit_policy() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(
        offspring_placement=OffspringPlacementPolicy.SAME_CELL
    )
    assert spec.population_configs is not None
    assert spec.population_configs.reproduction.offspring_placement is OffspringPlacementPolicy.SAME_CELL
    assert spec.metadata["offspring_placement"] == "same_cell"
    assert spec.metadata["same_cell_available_as_explicit_policy"] is True


def test_eat_increases_runtime_atp_on_occupied_resource() -> None:
    world = World2D(4, 4)
    world.place_resource((0, 0), LIFE_LOOP_RESOURCE_AMOUNT)
    eater = GenesisOrganism.from_bits(
        "eater",
        "101",
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(0, 0),
    )
    before = eater.atp_state.runtime_available
    result = step_population(
        PopulationState(0, 0, (eater,), (), ()),
        world,
        _life_loop_unit_configs(),
        seed=1,
    )
    after = result.population.organisms[0].atp_state.runtime_available
    assert after > before
    event = result.traces[0].events[0]
    assert event.action == "EAT_LUMEN"
    assert event.world_delta.get("lumen_interaction") is True


def test_eat_enables_reproduction_starvation_does_not() -> None:
    configs = _life_loop_unit_configs()
    food_world = World2D(4, 4)
    food_world.place_resource((0, 0), LIFE_LOOP_RESOURCE_AMOUNT)
    eater = GenesisOrganism.from_bits(
        "eater",
        LIFE_LOOP_EATER_GENOME,
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(0, 0),
    )
    fed = step_population(PopulationState(0, 0, (eater,), (), ()), food_world, configs, seed=11)
    born = step_population(fed.population, fed.world_after, configs, seed=12)

    empty_world = World2D(4, 4)
    starved = GenesisOrganism.from_bits(
        "starved",
        "111000000",
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(2, 2),
    )
    hungry = step_population(
        PopulationState(0, 0, (starved,), (), ()),
        empty_world,
        configs,
        seed=13,
    )

    assert born.births == 1
    assert hungry.births == 0
    assert "min_runtime_atp_not_met" in (
        hungry.traces[0].events[-1].world_delta.get("reproduction_blocked_reason") or ""
    )


def test_waiter_control_does_not_reproduce() -> None:
    world = World2D(4, 4)
    world.place_resource((0, 0), LIFE_LOOP_RESOURCE_AMOUNT)
    waiter = GenesisOrganism.from_bits(
        "waiter",
        LIFE_LOOP_WAITER_GENOME,
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(0, 0),
    )
    result = step_population(
        PopulationState(0, 0, (waiter,), (), ()),
        world,
        _life_loop_unit_configs(),
        seed=4,
    )
    assert result.births == 0
    assert result.reproduction_attempts == 0


def _alive(passed: bool = True) -> AliveGateResult:
    return AliveGateResult(
        passed=passed,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=24.0,
        lumen_interactions=1,
        reproduction_events=0,
        reasons=() if passed else ("blocked_ratio_exceeded",),
    )


def test_asexual_child_is_parent_copy_until_mutation() -> None:
    parent = GenesisOrganism.from_bits(
        "parent",
        LIFE_LOOP_EATER_GENOME,
        initial_runtime_atp=24.0,
    )
    alive = _alive()
    identical = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            inheritance_policy=InheritancePolicy.DARWINIAN_GENETIC_ONLY,
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=alive,
        generation=0,
        birth_tick=1,
        seed=21,
    )
    mutated = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            inheritance_policy=InheritancePolicy.DARWINIAN_GENETIC_ONLY,
        ),
        MutationConfig(bit_flip_rate=1.0),
        alive_result=alive,
        generation=0,
        birth_tick=1,
        seed=22,
    )
    assert identical.succeeded and identical.child is not None
    assert identical.child.genome.to_compact() == parent.genome.to_compact()
    assert mutated.succeeded and mutated.child is not None
    assert mutated.child.genome.to_compact() != parent.genome.to_compact()
    assert mutated.lineage is not None
    assert mutated.lineage.parent_id == "parent"
    assert "RECOMBINE" not in "".join(mutated.mutation.operations if mutated.mutation else ())


def test_adjacent_placement_is_life_loop_default_and_same_cell_stays_available() -> None:
    world = World2D(4, 4)
    world.place_resource((1, 1), LIFE_LOOP_RESOURCE_AMOUNT)
    parent = GenesisOrganism.from_bits(
        "p",
        LIFE_LOOP_EATER_GENOME,
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(1, 1),
    )
    fed = step_population(
        PopulationState(0, 0, (parent,), (), ()),
        world,
        _life_loop_unit_configs(),
        seed=31,
    )
    adjacent = step_population(
        fed.population,
        fed.world_after,
        _life_loop_unit_configs(placement=OffspringPlacementPolicy.ADJACENT_FREE),
        seed=32,
    )
    same = step_population(
        fed.population,
        fed.world_after,
        _life_loop_unit_configs(placement=OffspringPlacementPolicy.SAME_CELL),
        seed=33,
    )
    assert adjacent.births == 1
    assert same.births == 1
    child_adjacent = next(item for item in adjacent.population.organisms if item.id != "p")
    child_same = next(item for item in same.population.organisms if item.id != "p")
    parent_after_adj = next(item for item in adjacent.population.organisms if item.id == "p")
    parent_after_same = next(item for item in same.population.organisms if item.id == "p")
    assert child_adjacent.position != parent_after_adj.position
    assert child_same.position == parent_after_same.position


def test_life_loop_engine_preset_closes_eat_survive_reproduce_loop() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(first)

    assert first.digest() == second.digest()
    assert observation.lumen_eaten_events >= 1
    assert observation.births >= 1
    assert observation.parent_child_pairs >= 1
    assert observation.heritable_asexual_pairs >= 1
    assert observation.eater_births >= 1
    assert observation.waiter_births == 0
    assert observation.starvation_deaths >= 1
    assert observation.surviving_eater_lineages >= observation.surviving_waiter_lineages
    assert observation.remaining_resource_cells <= LIFE_LOOP_MAX_RESOURCES
    assert observation.adjacent_or_displaced_births >= 1
    assert observation.genesis_alive_full is False
    assert observation.phase_d_instinct_metrics == "hooks_only_not_implemented"
    assert observation.claim_ceiling == "runtime_observation"


def test_resources_respawn_deterministically_under_life_loop_policy() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=5, tick_count=16, population=3)
    run_a = GenesisEngine.from_spec(spec).run_ticks()
    run_b = GenesisEngine.from_spec(spec).run_ticks()
    events_a = [item.to_dict() for item in run_a.resource_policy_records]
    events_b = [item.to_dict() for item in run_b.resource_policy_records]
    assert events_a == events_b
    event_types = {item["event_type"] for item in events_a}
    assert event_types & {
        "resource_regenerated",
        "resource_respawn_skipped",
        "resource_pressure",
        "resource_respawn_blocked",
    }
    occupied_counts = [
        len(tick.generation_result.world_after.resources) for tick in run_a.ticks
    ]
    assert occupied_counts
    assert max(occupied_counts) <= LIFE_LOOP_MAX_RESOURCES
    assert min(occupied_counts) < len(LIFE_LOOP_FOOD_CELLS) or any(
        item["event_type"] == "resource_respawn_skipped" for item in events_a
    )


def test_low_energy_copy_is_inviable_without_food() -> None:
    parent = GenesisOrganism.from_bits(
        "hungry",
        "111",
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
    )
    # Mirror the post-COPY debit used by step_population before can_reproduce().
    parent.atp_state.debit_runtime(
        8.0,
        tick=0,
        organism_id=parent.id,
        codon="111",
        action="COPY_SELF",
        reason="copy_self_cost",
    )
    decision = can_reproduce(
        parent,
        AliveGateResult(
            passed=True,
            survived_ticks=1,
            executed_actions=1,
            blocked_actions=0,
            blocked_ratio=0.0,
            final_runtime_atp=parent.atp_state.runtime_available,
            lumen_interactions=0,
            reproduction_events=0,
            reasons=(),
        ),
        ReproductionConfig(min_runtime_atp=LIFE_LOOP_MIN_RUNTIME_ATP, parent_atp_cost=1.0),
    )
    assert not decision.allowed
    assert "min_runtime_atp_not_met" in decision.reasons


def test_default_configs_omit_opt_in_life_loop_keys() -> None:
    assert "metabolism" not in PopulationConfigs().to_dict()
    assert "starvation_floor" not in DeathMonitoringConfig().to_dict()
    assert ReproductionConfig().offspring_placement is OffspringPlacementPolicy.SAME_CELL
    pilot = GenesisRuntimeProfile.evolution_pilot_world()
    assert pilot.population_configs is not None
    assert "metabolism" not in pilot.population_configs.to_dict()
    assert "starvation_floor" not in pilot.population_configs.death_monitoring.to_dict()


def test_basal_metabolism_drains_runtime_atp_each_tick() -> None:
    world = World2D(4, 4)
    waiter = GenesisOrganism.from_bits(
        "waiter",
        LIFE_LOOP_WAITER_GENOME,
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(2, 2),
    )
    control = step_population(
        PopulationState(0, 0, (waiter,), (), ()),
        world,
        _life_loop_unit_configs(),
        seed=41,
    )
    drained = step_population(
        PopulationState(0, 0, (waiter,), (), ()),
        world,
        _life_loop_unit_configs(enable_metabolism=True),
        seed=41,
    )
    control_atp = control.population.organisms[0].atp_state.runtime_available
    drained_atp = drained.population.organisms[0].atp_state.runtime_available
    assert drained_atp < control_atp
    assert abs((control_atp - drained_atp) - LIFE_LOOP_BASAL_COST) < 1e-9
    assert abs(control_atp - (LIFE_LOOP_INITIAL_RUNTIME_ATP - 0.1)) < 1e-9


def test_starvation_death_records_reason_and_eaters_outlive_waiters() -> None:
    configs = _life_loop_unit_configs(enable_metabolism=True, enable_starvation=True)
    food_world = World2D(4, 4)
    food_world.place_resource((0, 0), LIFE_LOOP_RESOURCE_AMOUNT)
    empty_world = World2D(4, 4)
    eater = GenesisOrganism.from_bits(
        "eater",
        "101000000",
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(0, 0),
    )
    waiter = GenesisOrganism.from_bits(
        "waiter",
        LIFE_LOOP_WAITER_GENOME,
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(2, 2),
    )
    eater_state = PopulationState(0, 0, (eater,), (), ())
    waiter_state = PopulationState(0, 0, (waiter,), (), ())
    eater_world = food_world
    waiter_world = empty_world
    waiter_death_reason = None
    eater_alive_ticks = 0
    waiter_alive_ticks = 0
    for tick in range(16):
        eater_result = step_population(eater_state, eater_world, configs, seed=50 + tick)
        waiter_result = step_population(waiter_state, waiter_world, configs, seed=80 + tick)
        eater_state, eater_world = eater_result.population, eater_result.world_after
        waiter_state, waiter_world = waiter_result.population, waiter_result.world_after
        if any(item.id == "eater" for item in eater_state.organisms):
            eater_alive_ticks = tick + 1
        if any(item.id == "waiter" for item in waiter_state.organisms):
            waiter_alive_ticks = tick + 1
        if waiter_death_reason is None:
            for record in waiter_result.organism_records:
                death = record.death_classification
                if death is not None and death.actual_death_removed_from_population:
                    waiter_death_reason = death.removal_reason
    assert waiter_death_reason == "starvation"
    assert eater_alive_ticks > waiter_alive_ticks
    assert any(item.id == "eater" for item in eater_state.organisms)


def test_eat_depletes_local_and_global_food_and_limits_second_eater() -> None:
    world = World2D(4, 4)
    world.place_resource((0, 0), LIFE_LOOP_RESOURCE_AMOUNT)
    first = GenesisOrganism.from_bits(
        "a-eater",
        "101",
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(0, 0),
    )
    second = GenesisOrganism.from_bits(
        "b-eater",
        "101",
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(0, 0),
    )
    before_global = len(world.resources)
    before_local = world.resource_amount((0, 0))
    result = step_population(
        PopulationState(0, 0, (first, second), (), ()),
        world,
        _life_loop_unit_configs(respawn_rate=0.0, max_resources=LIFE_LOOP_MAX_RESOURCES),
        seed=61,
    )
    assert before_local == LIFE_LOOP_RESOURCE_AMOUNT
    assert (0, 0) not in result.world_after.resources
    assert len(result.world_after.resources) == before_global - 1
    first_event = result.traces[0].events[0]
    second_event = result.traces[1].events[0]
    assert first_event.reason == "lumen_consumed"
    assert second_event.reason == "no_lumen"
    assert second_event.status == "blocked"


def test_packed_neighborhood_blocks_adjacent_free_and_replace_occupied_displaces() -> None:
    world = World2D(3, 3)
    world.place_resource((1, 1), LIFE_LOOP_RESOURCE_AMOUNT)
    parent = GenesisOrganism.from_bits(
        "p",
        LIFE_LOOP_EATER_GENOME,
        initial_runtime_atp=LIFE_LOOP_INITIAL_RUNTIME_ATP,
        position=(1, 1),
    )
    fed = step_population(
        PopulationState(0, 0, (parent,), (), ()),
        world,
        _life_loop_unit_configs(),
        seed=71,
    )
    parent_after = next(item for item in fed.population.organisms if item.id == "p")
    occupants = tuple(
        GenesisOrganism.from_bits(
            f"n{index}",
            LIFE_LOOP_WAITER_GENOME,
            initial_runtime_atp=24.0,
            position=position,
        )
        for index, position in enumerate(((1, 0), (2, 1), (1, 2), (0, 1)))
    )
    crowded = PopulationState(1, 1, (parent_after, *occupants), (), ())
    blocked = step_population(
        crowded,
        fed.world_after,
        _life_loop_unit_configs(placement=OffspringPlacementPolicy.ADJACENT_FREE),
        seed=72,
    )
    no_space = step_population(
        crowded,
        fed.world_after,
        _life_loop_unit_configs(placement=OffspringPlacementPolicy.BLOCKED_IF_NO_SPACE),
        seed=72,
    )
    replaced = step_population(
        crowded,
        fed.world_after,
        _life_loop_unit_configs(placement=OffspringPlacementPolicy.REPLACE_OCCUPIED),
        seed=72,
    )
    assert blocked.births == 0
    assert no_space.births == 0
    parent_block = next(record for record in blocked.organism_records if record.organism_id == "p")
    assert parent_block.reproduction_result is not None
    assert "offspring_no_free_space" in parent_block.reproduction_result.decision.reasons
    assert replaced.births == 1
    occupant_ids = {item.id for item in occupants}
    remaining_occupants = {
        item.id for item in replaced.population.organisms if item.id in occupant_ids
    }
    assert len(remaining_occupants) == len(occupants) - 1
    assert replaced.deaths >= 1


def test_eat_capable_lineages_outproduce_waiter_controls_across_seeds() -> None:
    seeds = (1, 2, 3, 5, 7, 11)
    eater_births = 0
    waiter_births = 0
    eater_survivors = 0
    waiter_survivors = 0
    for seed in seeds:
        spec = GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=16, population=6)
        observation = summarize_life_loop_observation(GenesisEngine.from_spec(spec).run_ticks())
        eater_births += observation.eater_births
        waiter_births += observation.waiter_births
        eater_survivors += observation.surviving_eater_lineages
        waiter_survivors += observation.surviving_waiter_lineages
        assert observation.claim_ceiling == "runtime_observation"
        assert observation.eater_births >= observation.waiter_births
        assert observation.to_dict()["eater_births"] == observation.eater_births
    assert eater_births > waiter_births
    assert eater_survivors > waiter_survivors
