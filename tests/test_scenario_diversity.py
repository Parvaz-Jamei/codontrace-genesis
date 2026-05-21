from __future__ import annotations

import copy

import pytest

from codontrace import (
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    WorldConfig,
    WorldFactory,
)
from codontrace.errors import ConfigurationError
from codontrace.metrics.diversity import (
    diversity_report,
    object_type_distribution,
    reproducibility_report,
    scenario_reproducibility_metadata,
    scenario_summary,
    traversable_ratio,
)


def test_world_config_invalid_size_and_density() -> None:
    with pytest.raises(ConfigurationError):
        WorldConfig(width=0, height=5)
    with pytest.raises(ConfigurationError):
        WorldConfig(width=5, height=5, resource_density=1.1)


def test_scenario_config_json_roundtrip_hash_stable() -> None:
    config = ScenarioConfig(
        name="roundtrip",
        seed=7,
        world=WorldConfig(
            width=8, height=8, seed=7, resource_density=0.1, resource_distribution="uniform"
        ),
        profiles=(ScenarioAgentProfile(name="collector", count=3, genome_length_range=(3, 4)),),
    )

    restored = ScenarioConfig.from_json(config.to_json())

    assert restored == config
    assert restored.config_hash == config.config_hash


def test_world_factory_same_seed_same_digest_and_different_seed_changes() -> None:
    config_a = WorldConfig(
        width=12,
        height=12,
        seed=1,
        wall_density=0.12,
        wall_pattern="uniform",
        resource_density=0.12,
        resource_distribution="uniform",
    )
    config_b = WorldConfig(
        width=12,
        height=12,
        seed=2,
        wall_density=0.12,
        wall_pattern="uniform",
        resource_density=0.12,
        resource_distribution="uniform",
    )

    world_a1 = WorldFactory.from_config(config_a)
    world_a2 = WorldFactory.from_config(config_a)
    world_b = WorldFactory.from_config(config_b)

    assert world_a1.digest() == world_a2.digest()
    assert world_a1.digest() != world_b.digest()


def test_world_factory_prevents_resource_wall_overlap() -> None:
    world = WorldFactory.from_config(
        WorldConfig(
            width=10,
            height=10,
            seed=3,
            wall_density=0.2,
            wall_pattern="uniform",
            resource_density=0.2,
            resource_distribution="uniform",
        )
    )

    assert set(world.resources).isdisjoint(world.walls)


def test_world_factory_hazard_and_beacon_object_layers() -> None:
    world = WorldFactory.from_config(
        WorldConfig(
            width=10,
            height=10,
            seed=4,
            hazard_density=0.08,
            hazard_distribution="uniform",
            beacon_density=0.08,
            beacon_distribution="uniform",
        )
    )

    distribution = object_type_distribution(world)

    assert distribution["hazard"] > 0
    assert distribution["beacon"] > 0


def test_scenario_factory_returns_reproducible_digests() -> None:
    config = ScenarioConfig(
        name="factory",
        seed=11,
        world=WorldConfig(
            width=12, height=12, seed=11, resource_density=0.1, resource_distribution="clusters"
        ),
        profiles=(
            ScenarioAgentProfile(
                name="collector",
                count=4,
                genome_length_range=(3, 5),
                atp_range=(4.0, 6.0),
                codon_bias={"111": 3.0},
                placement_zone="near_resources",
            ),
        ),
    )

    scenario_a = ScenarioFactory.from_config(config)
    scenario_b = ScenarioFactory.from_config(config)

    assert scenario_a.config_hash == config.config_hash
    assert scenario_a.initial_world_digest == scenario_b.initial_world_digest
    assert scenario_a.initial_agent_digest == scenario_b.initial_agent_digest
    assert len(scenario_a.agents) == 4
    assert all(not scenario_a.world.is_wall(agent.position) for agent in scenario_a.agents)


def test_scenario_summary_and_reproducibility_report() -> None:
    config = ScenarioConfig(
        seed=12,
        world=WorldConfig(width=8, height=8, seed=12, wall_density=0.1, wall_pattern="uniform"),
        profiles=(ScenarioAgentProfile(name="default", count=2),),
    )
    scenario = ScenarioFactory.from_config(config)

    summary = scenario_summary(scenario)
    restored = ScenarioFactory.from_config(ScenarioConfig.from_json(config.to_json()))
    report = reproducibility_report(scenario, restored)
    metadata = scenario_reproducibility_metadata(scenario)

    assert summary["config_hash"] == config.config_hash
    assert report["match"] is True
    assert metadata["config_roundtrip_hash"] == config.config_hash
    assert 0.0 <= traversable_ratio(scenario.world) <= 1.0


def test_diversity_metrics_do_not_mutate_inputs() -> None:
    config = ScenarioConfig(
        seed=13,
        world=WorldConfig(
            width=8, height=8, seed=13, resource_density=0.1, resource_distribution="uniform"
        ),
        profiles=(ScenarioAgentProfile(name="default", count=3),),
    )
    scenario = ScenarioFactory.from_config(config)
    world_before = copy.deepcopy(scenario.world.to_dict())
    agent_digests = tuple(agent.genome.digest() for agent in scenario.agents)

    report = diversity_report(scenario)

    assert report["agent_count"] == 3
    assert scenario.world.to_dict() == world_before
    assert tuple(agent.genome.digest() for agent in scenario.agents) == agent_digests
