from __future__ import annotations

from codontrace.genesis import (
    AliveGateConfig,
    FitnessConfig,
    GenerationResult,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.world import World2D


def _configs(max_population: int = 4) -> PopulationConfigs:
    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=0.5,
            max_population=max_population,
            offspring_atp_fraction=0.1,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=1,
    )


def test_population_generation_step_is_deterministic_with_fixed_seed() -> None:
    world_a = World2D(3, 3)
    world_b = World2D(3, 3)
    organism_a = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    organism_b = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population_a = PopulationState(0, 0, (organism_a,), (), ())
    population_b = PopulationState(0, 0, (organism_b,), (), ())

    left = step_population(population_a, world_a, _configs(), seed=5)
    right = step_population(population_b, world_b, _configs(), seed=5)

    assert left.population.digest() == right.population.digest()
    assert left.births == right.births == 1


def test_population_enforces_max_population() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())

    result = step_population(population, world, _configs(max_population=1), seed=9)

    assert result.births == 0
    assert result.blocked_reproduction == 1
    assert result.after_count == 1


def test_population_counts_death_and_keeps_lineage_history() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "000", initial_runtime_atp=0.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())

    result = step_population(population, world, _configs(), seed=3)

    assert result.deaths == 1
    assert result.after_count == 0
    assert result.population.lineage[0].organism_id == "org"
    assert result.population.lineage[0].death_tick is not None


def test_copy_self_is_blocked_outside_population_runner() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))

    result = organism.run(
        world,
        ticks=1,
        alive_config=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
    )

    event = result.trace.events[0]
    assert event.action == "COPY_SELF"
    assert event.status == "blocked"
    assert event.world_delta["reproduction_succeeded"] is False


def test_copy_self_creates_offspring_only_inside_population_lifecycle() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())

    result = step_population(population, world, _configs(), seed=13)

    assert result.reproduction_attempts == 1
    assert result.births == 1
    assert result.population.lineage[-1].parent_id == "org"


def test_step_population_does_not_mutate_inputs_and_returns_world_after() -> None:
    world = World2D(4, 3)
    organism = GenesisOrganism.from_bits("org", "011", initial_runtime_atp=10.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())
    population_before = population.digest()
    world_before = world.digest()
    organism_position_before = organism.position
    organism_atp_before = organism.atp_state.runtime_available

    result = step_population(population, world, _configs(), seed=21)

    assert population.digest() == population_before
    assert world.digest() == world_before
    assert organism.position == organism_position_before
    assert organism.atp_state.runtime_available == organism_atp_before
    assert result.world_before_digest == world_before
    assert result.world_after.digest() == result.world_after_digest


def test_generation_result_preserves_trace_audit_records() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())

    result = step_population(population, world, _configs(), seed=22)

    assert result.traces
    assert result.organism_records
    assert result.organism_records[0].trace_digest == result.traces[0].digest()
    assert result.organism_records[0].world_before_digest == result.world_before_digest


def test_successful_reproduction_event_matches_parent_atp_and_ledger() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())

    result = step_population(population, world, _configs(), seed=23)
    event = result.traces[0].events[-1]
    record = result.organism_records[0]

    assert event.world_delta["reproduction_succeeded"] is True
    assert record.reproduction_result is not None
    assert event.atp_after == record.reproduction_result.parent_after.atp_state.runtime_available
    assert set(record.reproduction_result.ledger_entry_ids).issubset(set(event.ledger_entry_ids))
    assert event.world_delta["parent_runtime_atp_after_reproduction"] == event.atp_after
    assert event.world_delta["mutation_digest"] is not None
    assert event.world_delta["child_genome_digest"] is not None


def test_mutation_config_is_single_source_for_reproduction_mutation() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=0.5,
            max_population=4,
            offspring_atp_fraction=0.1,
        ),
        mutation=MutationConfig(bit_flip_rate=1.0),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=1,
    )

    result = step_population(population, world, configs, seed=24)
    child = result.population.organisms[-1]

    assert child.genome.to_compact() == "000"


def test_max_population_capacity_does_not_double_count_processed_survivors() -> None:
    world = World2D(5, 5)
    survivor = GenesisOrganism.from_bits("a", "000", initial_runtime_atp=10.0, position=(1, 1))
    reproducer = GenesisOrganism.from_bits("b", "111", initial_runtime_atp=20.0, position=(2, 2))
    population = PopulationState(0, 0, (survivor, reproducer), (), ())

    result = step_population(population, world, _configs(max_population=3), seed=27)

    assert result.births == 1
    assert result.blocked_reproduction == 0
    assert result.after_count == 3
    assert any(organism.id.startswith("b-g1-") for organism in result.population.organisms)


def test_population_uses_live_occupancy_for_moving_agents() -> None:
    world = World2D(5, 3)
    left = GenesisOrganism.from_bits("left", "011", initial_runtime_atp=10.0, position=(1, 1))
    right = GenesisOrganism.from_bits("right", "011", initial_runtime_atp=10.0, position=(3, 1))
    world.resources[(2, 1)] = 2.0
    population = PopulationState(0, 0, (left, right), (), ())

    result = step_population(population, world, _configs(max_population=4), seed=25)
    positions = [organism.position for organism in result.population.organisms]

    assert positions.count((2, 1)) == 1
    assert any(
        event.reason == "occupied_blocked" for trace in result.traces for event in trace.events
    )


def test_population_public_objects_roundtrip() -> None:
    world = World2D(3, 3)
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())
    result = step_population(population, world, _configs(), seed=26)

    assert (
        ReproductionConfig.from_dict(_configs().reproduction.to_dict()).to_dict()
        == _configs().reproduction.to_dict()
    )
    assert (
        MutationConfig.from_dict(_configs().mutation.to_dict()).to_dict()
        == _configs().mutation.to_dict()
    )
    assert (
        FitnessConfig.from_dict(_configs().fitness.to_dict()).to_dict()
        == _configs().fitness.to_dict()
    )
    assert PopulationConfigs.from_dict(_configs().to_dict()).to_dict() == _configs().to_dict()
    assert (
        PopulationState.from_dict(result.population.to_dict()).to_dict()
        == result.population.to_dict()
    )
    assert (
        result.organism_records[0].from_dict(result.organism_records[0].to_dict()).to_dict()
        == result.organism_records[0].to_dict()
    )
    assert GenerationResult.from_dict(result.to_dict()).to_dict() == result.to_dict()
