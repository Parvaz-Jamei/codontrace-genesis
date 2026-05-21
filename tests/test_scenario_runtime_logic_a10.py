from __future__ import annotations

import pytest

from codontrace import (
    ActionContext,
    ActionResult,
    Codon,
    CodonTable,
    Scenario,
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    Simulation,
    SimulationConfig,
    Trace,
    WhiteBoxAgent,
    World2D,
    WorldConfig,
    default_action_registry,
)


@pytest.mark.parametrize(
    ("codon", "start", "expected"),
    (
        ("101", (2, 1), (0, 1)),  # MOVE_EAST
        ("110", (0, 1), (2, 1)),  # MOVE_WEST
        ("011", (1, 0), (1, 2)),  # MOVE_NORTH
        ("100", (1, 2), (1, 0)),  # MOVE_SOUTH
    ),
)
def test_white_box_agent_step_respects_wrap_boundary(
    codon: str, start: tuple[int, int], expected: tuple[int, int]
) -> None:
    world = World2D(3, 3, boundary="wrap")
    agent = WhiteBoxAgent.quick(codon, initial_atp=3.0, position=start)

    event = agent.step(world, Trace())

    assert event.reason == "moved"
    assert event.position_after == expected
    assert agent.position == expected


def test_simulation_run_respects_wrap_boundary() -> None:
    world = World2D(3, 3, boundary="wrap")
    agent = WhiteBoxAgent.quick("101", initial_atp=3.0, position=(2, 1))

    result = Simulation.run(world=world, agents=(agent,), config=SimulationConfig(steps=1))

    assert result.agent_states[0]["position"] == [0, 1]
    assert result.trace.events[0].reason == "moved"


def test_scenario_run_respects_wrap_boundary_with_explicit_runtime_objects() -> None:
    config = ScenarioConfig(
        name="wrap-runtime",
        seed=101,
        max_steps=1,
        world=WorldConfig(width=3, height=3, boundary="wrap", wall_pattern="none"),
    )
    world = World2D(3, 3, boundary="wrap")
    agent = WhiteBoxAgent.quick("101", initial_atp=3.0, position=(2, 1), agent_id="edge-000")
    scenario = Scenario(
        config=config,
        world=world,
        agents=(agent,),
        config_hash=config.config_hash,
        initial_world_digest=world.digest(),
        initial_agent_digest=agent.state_digest(),
    )

    result = scenario.run()

    assert result.agent_states[0]["position"] == [0, 1]
    assert result.trace.events[0].reason == "moved"
    assert scenario.initial_world_digest == world.digest()


def test_scenario_run_repeatability_still_holds_after_runtime_patch() -> None:
    config = ScenarioConfig(
        seed=202,
        max_steps=4,
        world=WorldConfig(width=6, height=6, seed=202, boundary="wrap"),
        agents=(ScenarioAgentProfile(name="runner", count=2, genome_length_range=(2, 2)),),
    )
    scenario = ScenarioFactory.from_config(config)

    result_a = scenario.run()
    result_b = scenario.run()

    assert result_a.trace.digest() == result_b.trace.digest()
    assert result_a.final_world_digest == result_b.final_world_digest
    assert scenario.initial_world_digest == scenario.world.digest()


def test_allow_agent_on_wall_true_scenario_runs_instead_of_failing_at_runtime() -> None:
    wait_table = CodonTable((Codon("000", "WAIT", 0.1, "wait"),))
    config = ScenarioConfig(
        seed=303,
        max_steps=1,
        world=WorldConfig(
            width=3,
            height=3,
            seed=303,
            boundary="closed",
            wall_pattern="border",
            allow_agent_on_wall=True,
        ),
        agents=(
            ScenarioAgentProfile(
                name="edge",
                count=1,
                genome_length_range=(1, 1),
                placement_zone="edges",
                min_distance=0,
            ),
        ),
    )
    scenario = ScenarioFactory.from_config(config, codon_table=wait_table)

    assert scenario.world.is_wall(scenario.agents[0].position)
    result = scenario.run()

    assert result.agent_states[0]["position"] == list(scenario.agents[0].position)
    assert result.trace.events[0].reason == "waited"


def test_default_simulation_still_rejects_agent_on_wall() -> None:
    world = World2D(3, 3)
    world.walls.add((1, 1))
    agent = WhiteBoxAgent.quick("000", position=(1, 1))

    with pytest.raises(Exception, match="starts on a wall"):
        Simulation.run(world=world, agents=(agent,), config=SimulationConfig(steps=1))


def test_custom_action_added_wall_persists_under_simulation() -> None:
    def add_wall(ctx: ActionContext) -> ActionResult:
        ctx.world.walls.add((2, 2))
        return ActionResult.executed(
            reason="wall_added",
            position_after=ctx.position,
            world_delta={"added_wall": [2, 2]},
        )

    registry = default_action_registry().replace("WAIT", add_wall)
    world = World2D(4, 4)
    agent = WhiteBoxAgent.quick("000", position=(1, 1), action_registry=registry)

    result = Simulation.run(world=world, agents=(agent,), config=SimulationConfig(steps=1))

    assert (2, 2) in result.final_world.walls


def test_custom_action_removed_wall_persists_under_simulation() -> None:
    def remove_wall(ctx: ActionContext) -> ActionResult:
        ctx.world.walls.discard((2, 2))
        return ActionResult.executed(
            reason="wall_removed",
            position_after=ctx.position,
            world_delta={"removed_wall": [2, 2]},
        )

    registry = default_action_registry().replace("WAIT", remove_wall)
    world = World2D(4, 4)
    world.walls.add((2, 2))
    agent = WhiteBoxAgent.quick("000", position=(1, 1), action_registry=registry)

    result = Simulation.run(world=world, agents=(agent,), config=SimulationConfig(steps=1))

    assert (2, 2) not in result.final_world.walls


def test_collision_virtual_walls_do_not_leak_into_final_world() -> None:
    world = World2D(4, 4)
    left = WhiteBoxAgent.quick("000", position=(1, 1), agent_id="left")
    right = WhiteBoxAgent.quick("110", position=(2, 1), agent_id="right")

    result = Simulation.run(
        world=world,
        agents=(left, right),
        config=SimulationConfig(steps=1, collision_policy="block"),
    )

    assert result.trace.events[1].reason == "occupied_blocked"
    assert (1, 1) not in result.final_world.walls


def test_trace_disabled_result_and_digests_stay_available() -> None:
    config = ScenarioConfig(
        seed=404,
        max_steps=2,
        trace_enabled=False,
        replay_enabled=False,
        world=WorldConfig(width=5, height=5, seed=404),
        agents=(ScenarioAgentProfile(name="runner", count=1, genome_length_range=(1, 1)),),
    )
    scenario = ScenarioFactory.from_config(config)

    result = scenario.run()

    assert len(result.trace.events) == 0
    assert result.final_world is not None
    assert result.agent_states
    assert result.config_hash == config.config_hash
    assert scenario.initial_world_digest == scenario.world.digest()
