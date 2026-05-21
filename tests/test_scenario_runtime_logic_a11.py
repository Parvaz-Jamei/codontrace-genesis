from __future__ import annotations

import pytest

from codontrace import (
    ActionContext,
    ActionRegistry,
    ActionResult,
    ATPAccount,
    Codon,
    CodonTable,
    Experiment,
    GenomeStrategy,
    PlacementStrategy,
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    SemanticGenome,
    Simulation,
    SimulationConfig,
    Trace,
    WhiteBoxAgent,
    World2D,
    WorldConfig,
    __all__,
    default_action_registry,
)
from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager


def _agent(agent_id: str, genome: str, position: tuple[int, int]) -> WhiteBoxAgent:
    return WhiteBoxAgent.quick(genome, initial_atp=10.0, position=position, agent_id=agent_id)


def test_collision_occupancy_is_not_visible_as_wall_to_sense_danger() -> None:
    world = World2D(4, 4)
    sensor = _agent("a", "010", (1, 1))  # SENSE_DANGER
    neighbor = _agent("b", "000", (2, 1))

    result = Simulation.run(
        world=world,
        agents=(sensor, neighbor),
        config=SimulationConfig(steps=1, collision_policy="block"),
    )

    event = result.trace.events[0]
    assert event.agent_id == "a"
    assert event.reason == "sensed_danger"
    assert event.world_delta["nearby_wall"] is False
    assert result.final_world.walls == set()


def test_collision_world_digest_before_is_not_polluted_by_occupancy_blockers() -> None:
    world = World2D(4, 4)
    digest_world = world.clone()
    digest_world.agent_position = (1, 1)
    world_before = digest_world.digest()
    mover = _agent("a", "101", (1, 1))
    blocker = _agent("b", "000", (2, 1))

    result = Simulation.run(
        world=world,
        agents=(mover, blocker),
        config=SimulationConfig(steps=1, collision_policy="block"),
    )

    event = result.trace.events[0]
    assert event.reason == "occupied_blocked"
    assert event.world_delta["blocked_by"] == "agent"
    assert event.world_digest_before == world_before
    assert result.final_world.walls == set()


def test_custom_wall_add_remove_and_occupied_cell_wall_mutations_persist() -> None:
    def mutate_walls(ctx: ActionContext) -> ActionResult:
        ctx.world.walls.add((2, 1))  # occupied by another agent; still a real handler mutation
        ctx.world.walls.add((3, 3))
        ctx.world.walls.discard((0, 0))
        return ActionResult.executed(
            reason="walls_mutated",
            position_after=ctx.position,
            world_delta={"added": [[2, 1], [3, 3]], "removed": [0, 0]},
        )

    registry = default_action_registry().replace("WAIT", mutate_walls)
    world = World2D(4, 4)
    world.walls.add((0, 0))
    actor = _agent("a", "000", (1, 1))
    actor.action_registry = registry
    occupied = _agent("b", "000", (2, 1))

    result = Simulation.run(
        world=world,
        agents=(actor, occupied),
        config=SimulationConfig(steps=1, collision_policy="block"),
    )

    assert (2, 1) in result.final_world.walls
    assert (3, 3) in result.final_world.walls
    assert (0, 0) not in result.final_world.walls


def test_custom_action_moving_into_occupied_cell_blocks_without_wall_error() -> None:
    def move_to_occupied(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(
            reason="custom_move",
            position_after=(2, 1),
            world_delta={"requested_target": [2, 1]},
        )

    registry = default_action_registry().replace("WAIT", move_to_occupied)
    actor = _agent("a", "000", (1, 1))
    actor.action_registry = registry
    blocker = _agent("b", "000", (2, 1))

    result = Simulation.run(
        world=World2D(4, 4),
        agents=(actor, blocker),
        config=SimulationConfig(steps=1, collision_policy="block"),
    )

    event = result.trace.events[0]
    assert event.status == "blocked"
    assert event.reason == "occupied_blocked"
    assert event.world_delta["blocked_by"] == "agent"
    assert result.agent_states[0]["position"] == [1, 1]


def test_wrap_boundary_collision_blocks_as_occupancy_not_out_of_bounds() -> None:
    world = World2D(3, 3, boundary="wrap")
    mover = _agent("a", "101", (2, 1))  # MOVE_EAST wraps to (0, 1)
    blocker = _agent("b", "000", (0, 1))

    result = Simulation.run(
        world=world,
        agents=(mover, blocker),
        config=SimulationConfig(steps=1, collision_policy="block"),
    )

    event = result.trace.events[0]
    assert event.reason == "occupied_blocked"
    assert event.world_delta["movement"] == "occupied_blocked"
    assert event.world_delta["resolved_target"] == [0, 1]
    assert event.reason != "out_of_bounds"


def test_allow_overlap_policy_allows_agents_to_share_position() -> None:
    world = World2D(3, 3)
    mover = _agent("a", "101", (1, 1))
    resident = _agent("b", "000", (2, 1))

    result = Simulation.run(
        world=world,
        agents=(mover, resident),
        config=SimulationConfig(steps=1, collision_policy="allow_overlap"),
    )

    assert result.trace.events[0].reason == "moved"
    positions = [state["position"] for state in result.agent_states]
    assert positions == [[2, 1], [2, 1]]


def test_round_robin_scheduler_rotates_start_index_and_sequential_does_not() -> None:
    agents_seq = (
        _agent("a", "000", (0, 0)),
        _agent("b", "000", (1, 0)),
        _agent("c", "000", (2, 0)),
    )
    seq = Simulation.run(
        world=World2D(3, 1),
        agents=agents_seq,
        config=SimulationConfig(steps=3, scheduler="sequential"),
    )
    assert [event.agent_id for event in seq.trace.events] == ["a", "b", "c"] * 3

    agents_rr = (_agent("a", "000", (0, 0)), _agent("b", "000", (1, 0)), _agent("c", "000", (2, 0)))
    rr = Simulation.run(
        world=World2D(3, 1),
        agents=agents_rr,
        config=SimulationConfig(steps=3, scheduler="round_robin"),
    )
    assert [event.agent_id for event in rr.trace.events] == [
        "a",
        "b",
        "c",
        "b",
        "c",
        "a",
        "c",
        "a",
        "b",
    ]


def test_random_order_scheduler_is_seed_deterministic() -> None:
    def run_once() -> list[str]:
        agents = (
            _agent("a", "000", (0, 0)),
            _agent("b", "000", (1, 0)),
            _agent("c", "000", (2, 0)),
        )
        result = Simulation.run(
            world=World2D(3, 1),
            agents=agents,
            config=SimulationConfig(steps=4, scheduler="random_order", seed=123),
        )
        return [event.agent_id for event in result.trace.events]

    assert run_once() == run_once()


@pytest.mark.parametrize(
    "payload",
    (
        {"width": 3, "height": 3, "walls": [[True, False]]},
        {"width": 3, "height": 3, "resources": [[[True, False], 1.0]]},
        {"width": 3, "height": 3, "custom_cells": [[[True, False], "X"]]},
        {"width": 3, "height": 3, "objects": [[[True, False], [{"kind": "beacon"}]]]},
        {"width": 3, "height": 3, "agent_position": [True, False]},
    ),
)
def test_world_from_dict_rejects_bool_positions(payload: dict[str, object]) -> None:
    with pytest.raises(ConfigurationError, match="bool"):
        World2D.from_dict(payload)  # type: ignore[arg-type]


def test_world_from_dict_accepts_normal_integer_positions() -> None:
    world = World2D.from_dict(
        {
            "width": 3,
            "height": 3,
            "walls": [[1, 0]],
            "resources": [[[2, 0], 1.0]],
            "custom_cells": [[[0, 1], "X"]],
            "objects": [[[1, 1], [{"kind": "beacon"}]]],
            "agent_position": [0, 2],
        }
    )

    assert (1, 0) in world.walls
    assert world.resources[(2, 0)] == 1.0
    assert world.custom_cells[(0, 1)] == "X"
    assert world.objects_at((1, 1))[0].kind == "beacon"
    assert world.agent_position == (0, 2)


def test_strategy_type_aliases_are_public_exports() -> None:
    genome_strategy: GenomeStrategy = "uniform_random"
    placement_strategy: PlacementStrategy = "uniform_random"

    assert genome_strategy == "uniform_random"
    assert placement_strategy == "uniform_random"
    assert "GenomeStrategy" in __all__
    assert "PlacementStrategy" in __all__


@pytest.mark.parametrize("name", ("REST", "MOVE_EAST", "CUSTOM_ACTION_1"))
def test_action_registry_accepts_strict_uppercase_names(name: str) -> None:
    ActionRegistry().extend(name, lambda ctx: ActionResult.executed(reason="ok"))


@pytest.mark.parametrize("name", ("_MOVE", "MOVE_", "MOVE__NORTH", "move_east", "MOVE-EAST", ""))
def test_action_registry_rejects_invalid_underscore_patterns(name: str) -> None:
    with pytest.raises(ConfigurationError):
        ActionRegistry().extend(name, lambda ctx: ActionResult.executed(reason="ok"))


def test_semantic_genome_random_rejects_seed_and_rng_together() -> None:
    with pytest.raises(ValueError, match="either seed or rng"):
        SemanticGenome.random(3, seed=1, rng=RNGManager(seed=2))

    assert (
        SemanticGenome.random(3, seed=1).to_codons() == SemanticGenome.random(3, seed=1).to_codons()
    )
    rng_a = RNGManager(seed=7)
    rng_b = RNGManager(seed=7)
    assert (
        SemanticGenome.random(3, rng=rng_a).to_codons()
        == SemanticGenome.random(3, rng=rng_b).to_codons()
    )


def test_experiment_quick_ascii_marker_single_agent_and_multi_agent_warning() -> None:
    single = Experiment.quick(world_ascii="A..\n...\n...", agent_count=1, steps=0, seed=1)
    assert single.agent_states[0]["position"] == [0, 0]

    with pytest.warns(UserWarning, match="ASCII 'A' marker is ignored"):
        multi = Experiment.quick(world_ascii="A..\n...\n...", agent_count=2, steps=0, seed=1)
    assert len(multi.agent_states) == 2


def test_zero_cost_debit_is_noop_and_zero_cost_action_trace_has_no_ledger_ref() -> None:
    account = ATPAccount(1.0)
    assert account.can_pay(0.0)
    assert (
        account.debit(0.0, tick=0, agent_id="a", codon="000", action="WAIT", reason="zero") is None
    )
    assert account.current_atp == 1.0
    assert account.ledger == ()

    table = CodonTable((Codon("000", "WAIT", 0.0, "zero wait"),))
    agent = WhiteBoxAgent.quick("000", initial_atp=1.0, codon_table=table)
    event = agent.step(World2D(2, 2), Trace())
    assert event.reason == "waited"
    assert event.ledger_entry_ids == ()
    assert event.world_delta["action_cost"] == 0.0
    assert event.world_delta["net_atp_delta"] == 0.0
    assert agent.atp_account.ledger == ()


def test_scenario_run_repeatability_and_digests_remain_stable_after_a11() -> None:
    config = ScenarioConfig(
        seed=404,
        max_steps=3,
        world=WorldConfig(width=5, height=5, seed=404, boundary="wrap"),
        agents=(ScenarioAgentProfile(name="runner", count=2, genome_length_range=(2, 2)),),
    )
    scenario = ScenarioFactory.from_config(config)

    first = scenario.run()
    second = scenario.run()

    assert first.trace.digest() == second.trace.digest()
    assert first.final_world_digest == second.final_world_digest
    assert scenario.initial_world_digest == scenario.world.digest()
    assert scenario.config_hash == config.config_hash


def test_trace_disabled_result_still_exposes_world_and_agent_states_after_a11() -> None:
    config = ScenarioConfig(
        seed=405,
        max_steps=2,
        trace_enabled=False,
        replay_enabled=False,
        world=WorldConfig(width=5, height=5, seed=405),
        agents=(ScenarioAgentProfile(name="runner", count=1, genome_length_range=(1, 1)),),
    )
    scenario = ScenarioFactory.from_config(config)

    result = scenario.run()

    assert len(result.trace.events) == 0
    assert result.final_world is not None
    assert result.agent_states
    assert result.config_hash == config.config_hash
    assert scenario.initial_world_digest == scenario.world.digest()
