from __future__ import annotations

from codontrace import AgentFactory, InitializationConfig, Trace, World2D


def test_create_specs_roundtrip_json() -> None:
    world = World2D(4, 4)
    config = InitializationConfig(count=2, seed=1, placement_strategy="grid")

    specs = AgentFactory.create_specs(world=world, config=config)
    text = AgentFactory.specs_to_json(specs)
    restored = AgentFactory.specs_from_json(text)

    assert restored == specs


def test_trace_jsonl_roundtrip() -> None:
    world = World2D(3, 3)
    agent = AgentFactory.create_many(world=world, config=InitializationConfig(count=1, seed=1))[0]
    trace = agent.run(world, 2)

    restored = Trace.from_jsonl(trace.to_jsonl())

    assert restored.digest() == trace.digest()
