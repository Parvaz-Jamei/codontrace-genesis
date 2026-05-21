from __future__ import annotations

import pytest

from codontrace.genesis import (
    AliveGateConfig,
    FitnessConfig,
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    PopulationRunner,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.rng import RNGManager
from codontrace.world import World2D


def _configs(
    policy: OffspringPlacementPolicy = OffspringPlacementPolicy.SAME_CELL,
) -> PopulationConfigs:
    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=0.5,
            max_population=4,
            offspring_atp_fraction=0.1,
            offspring_placement=policy,
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


def test_population_configs_from_empty_keeps_fatal_default() -> None:
    assert PopulationConfigs.from_dict({}).fatal_alive_reasons == ("negative_runtime_atp",)
    roundtrip = PopulationConfigs.from_dict(PopulationConfigs().to_dict())
    assert roundtrip.to_dict() == PopulationConfigs().to_dict()
    assert PopulationConfigs.from_dict({"fatal_alive_reasons": []}).fatal_alive_reasons == ()


def test_offspring_same_cell_policy_preserves_current_behavior() -> None:
    parent = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0, position=(1, 1))
    result = step_population(
        PopulationState(0, 0, (parent,), (), ()),
        World2D(4, 4),
        _configs(),
        seed=1,
    )
    assert result.births == 1
    assert result.population.organisms[-1].position == (1, 1)


def test_offspring_adjacent_free_policy_uses_deterministic_neighbor() -> None:
    parent = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0, position=(1, 1))
    result = step_population(
        PopulationState(0, 0, (parent,), (), ()),
        World2D(4, 4),
        _configs(OffspringPlacementPolicy.ADJACENT_FREE),
        seed=2,
    )
    assert result.births == 1
    assert result.population.organisms[-1].position == (1, 0)


def test_offspring_blocked_if_no_space_blocks_with_clear_reason() -> None:
    parent = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0, position=(1, 1))
    world = World2D(3, 3, walls={(1, 0), (2, 1), (1, 2), (0, 1)})
    result = step_population(
        PopulationState(0, 0, (parent,), (), ()),
        world,
        _configs(OffspringPlacementPolicy.BLOCKED_IF_NO_SPACE),
        seed=3,
    )
    assert result.births == 0
    assert result.blocked_reproduction == 1
    assert (
        result.traces[0].events[-1].world_delta["reproduction_blocked_reason"]
        == "offspring_no_free_space"
    )


def test_population_world_after_agent_position_is_neutral() -> None:
    parent = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0, position=(1, 1))
    result = step_population(
        PopulationState(0, 0, (parent,), (), ()),
        World2D(4, 4),
        _configs(),
        seed=4,
    )
    assert result.world_after.agent_position is None
    assert result.population.organisms[0].position == (1, 1)


def test_population_runner_accepts_rng_and_rejects_seed_rng_conflict() -> None:
    parent_a = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0, position=(1, 1))
    parent_b = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0, position=(1, 1))
    runner_a = PopulationRunner(
        PopulationState(0, 0, (parent_a,), (), ()), World2D(4, 4), _configs()
    )
    runner_b = PopulationRunner(
        PopulationState(0, 0, (parent_b,), (), ()), World2D(4, 4), _configs()
    )

    left = runner_a.step_generation(rng=RNGManager(seed=10))
    right = runner_b.step_generation(rng=RNGManager(seed=10))

    assert left.population.digest() == right.population.digest()
    with pytest.raises(ValueError, match="either seed or rng"):
        runner_a.step_generation(seed=1, rng=RNGManager(seed=1))
