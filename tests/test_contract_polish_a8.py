from __future__ import annotations

from codontrace import (
    ObstacleConfig,
    ResourceConfig,
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    World2D,
    WorldConfig,
)


def test_world_config_preserves_first_class_resource_and_obstacle_configs() -> None:
    resources = ResourceConfig(
        kind="food",
        density=0.1,
        amount_range=(2.0, 3.0),
        distribution="uniform",
        respawn=True,
        respawn_rate=0.2,
    )
    obstacles = ObstacleConfig(
        density=0.0,
        pattern="none",
        block_movement=False,
        block_sight=False,
    )
    config = WorldConfig(
        width=9,
        height=9,
        seed=7,
        boundary="open",
        resource_config=resources,
        obstacle_config=obstacles,
    )

    restored = WorldConfig.from_dict(config.to_dict())

    assert restored.resource_config == resources
    assert restored.obstacle_config == obstacles
    assert restored.to_dict()["resource_config"] == resources.to_dict()
    assert restored.to_dict()["obstacle_config"] == obstacles.to_dict()


def test_scenario_config_hash_changes_for_preserved_resource_and_obstacle_fields() -> None:
    base_world = WorldConfig(
        width=8,
        height=8,
        seed=11,
        boundary="open",
        resource_config=ResourceConfig(
            kind="food",
            density=0.1,
            amount_range=(1.0, 1.0),
            distribution="uniform",
            respawn=False,
            respawn_rate=0.0,
        ),
        obstacle_config=ObstacleConfig(block_movement=True, block_sight=True),
    )
    respawn_world = WorldConfig(
        width=8,
        height=8,
        seed=11,
        boundary="open",
        resource_config=ResourceConfig(
            kind="food",
            density=0.1,
            amount_range=(1.0, 1.0),
            distribution="uniform",
            respawn=True,
            respawn_rate=0.2,
        ),
        obstacle_config=ObstacleConfig(block_movement=True, block_sight=True),
    )
    sight_world = WorldConfig(
        width=8,
        height=8,
        seed=11,
        boundary="open",
        resource_config=ResourceConfig(
            kind="food",
            density=0.1,
            amount_range=(1.0, 1.0),
            distribution="uniform",
            respawn=False,
            respawn_rate=0.0,
        ),
        obstacle_config=ObstacleConfig(block_movement=True, block_sight=False),
    )

    base = ScenarioConfig(seed=11, world=base_world)
    changed_respawn = ScenarioConfig(seed=11, world=respawn_world)
    changed_sight = ScenarioConfig(seed=11, world=sight_world)

    assert changed_respawn.config_hash != base.config_hash
    assert changed_sight.config_hash != base.config_hash


def test_scenario_run_is_non_mutating_and_repeatable_on_same_object() -> None:
    config = ScenarioConfig(
        name="repeatable",
        seed=23,
        max_steps=6,
        world=WorldConfig(width=8, height=8, seed=23, boundary="open"),
        agents=(ScenarioAgentProfile(name="runner", count=2, genome_length_range=(2, 2)),),
    )
    scenario = ScenarioFactory.from_config(config)
    initial_agent_digests = tuple(agent.state_digest() for agent in scenario.agents)

    result_a = scenario.run()
    result_b = scenario.run()

    assert result_a.trace.digest() == result_b.trace.digest()
    assert result_a.final_world_digest == result_b.final_world_digest
    assert scenario.initial_world_digest == ScenarioFactory.from_config(config).initial_world_digest
    assert tuple(agent.state_digest() for agent in scenario.agents) == initial_agent_digests


def test_scenario_result_convenience_properties_with_trace_disabled() -> None:
    config = ScenarioConfig(
        seed=29,
        max_steps=4,
        trace_enabled=False,
        replay_enabled=False,
        metadata={"purpose": "contract-polish"},
        world=WorldConfig(width=8, height=8, seed=29, boundary="open"),
        agents=(ScenarioAgentProfile(name="runner", count=1, genome_length_range=(1, 1)),),
    )

    result = ScenarioFactory.run(config)
    states = result.agent_states
    states[0]["id"] = "mutated-copy"
    bundle = result.to_viewer_bundle()

    assert len(result.trace.events) == 0
    assert isinstance(result.final_world, World2D)
    assert result.world_digest == result.final_world_digest
    assert result.trace_digest == result.trace.digest()
    assert result.agent_states[0]["id"] != "mutated-copy"
    assert bundle["scenario"]["trace_enabled"] is False
    assert bundle["scenario"]["replay_enabled"] is False
    assert bundle["agent_states"]
