from __future__ import annotations

from codontrace import (
    AgentFactory,
    InitializationConfig,
    Simulation,
    SimulationConfig,
    SimulationResult,
    Trace,
    World2D,
    WorldObject,
)


def test_trace_jsonl_string_roundtrip() -> None:
    world = World2D(3, 3)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=1, seed=1, placement_strategy="grid"),
    )
    result = Simulation.run(world=world, agents=agents, config=SimulationConfig(steps=2))
    restored = Trace.from_jsonl_string(result.trace.to_jsonl_string())
    assert restored.digest() == result.trace.digest()


def test_simulation_result_to_dict_from_dict_roundtrip() -> None:
    world = World2D(4, 4)
    world.add_object((1, 1), WorldObject(kind="FOOD", amount=2.0, metadata={"unit": "ATP"}))
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=2, seed=2, placement_strategy="grid"),
    )
    result = Simulation.run(world=world, agents=agents, config=SimulationConfig(steps=2, seed=2))
    restored = SimulationResult.from_dict(result.to_dict())
    assert restored.trace_digest == result.trace_digest
    assert restored.world_digest == result.world_digest
    assert restored.agent_states == result.agent_states


def test_world_object_is_explicitly_unhashable() -> None:
    obj = WorldObject(kind="LIGHT", metadata={"mutable": True})
    try:
        hash(obj)
    except TypeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("WorldObject must be unhashable")


def test_simulation_result_is_explicitly_unhashable() -> None:
    result = Simulation.run(
        world=World2D(3, 3),
        agents=AgentFactory.create_many(
            world=World2D(3, 3),
            config=InitializationConfig(count=1, seed=1, placement_strategy="grid"),
        ),
        config=SimulationConfig(steps=0),
    )
    try:
        hash(result)
    except TypeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("SimulationResult must be unhashable")
