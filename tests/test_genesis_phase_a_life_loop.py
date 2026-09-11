"""Phase A Darwinian life-loop tests.

These tests document software capability and runtime observation only. They do
not claim artificial life, intelligence, cooperation, or instinct evolution.
"""

from __future__ import annotations

from codontrace.genesis.birth import InheritancePolicy
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    FitnessConfig,
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
    LIFE_LOOP_EATER_GENOME,
    LIFE_LOOP_INITIAL_RUNTIME_ATP,
    LIFE_LOOP_MIN_RUNTIME_ATP,
    LIFE_LOOP_RESOURCE_AMOUNT,
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
        evolution=EvolutionConfig(
            max_population=max_population,
            selection_policy="fitness_proportional",
            qd_mode="disabled",
        ),
        qd_mode="disabled",
        runtime_resource_policy=RuntimeResourcePolicy(
            respawn_enabled=True,
            respawn_rate=1.0,
            max_resources=8,
            amount=LIFE_LOOP_RESOURCE_AMOUNT,
            status="runtime_effective_default_on",
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
    assert configs.reproduction.offspring_placement is OffspringPlacementPolicy.ADJACENT_FREE
    assert configs.reproduction.inheritance_policy is InheritancePolicy.DARWINIAN_GENETIC_ONLY
    assert configs.runtime_resource_policy.respawn_enabled is True
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
    assert observation.resource_respawn_events >= 1
    assert observation.adjacent_or_displaced_births >= 1
    assert observation.genesis_alive_full is False
    assert observation.phase_d_instinct_metrics == "hooks_only_not_implemented"
    assert observation.claim_ceiling == "runtime_observation"


def test_resources_respawn_deterministically_under_life_loop_policy() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=5, tick_count=6, population=3)
    run_a = GenesisEngine.from_spec(spec).run_ticks()
    run_b = GenesisEngine.from_spec(spec).run_ticks()
    events_a = [item.to_dict() for item in run_a.resource_policy_records]
    events_b = [item.to_dict() for item in run_b.resource_policy_records]
    assert events_a == events_b
    assert any(item["event_type"] == "resource_regenerated" for item in events_a)


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
