from __future__ import annotations

from pathlib import Path

import pytest

from codontrace import (
    ActionResult,
    ConfigurationError,
    Trace,
    WhiteBoxAgent,
    World2D,
    WorldObject,
)
from codontrace.actions import ActionContext, EnergyEffect


def test_from_world_infers_position_from_ascii_marker() -> None:
    world = World2D.from_ascii("""
....
.A*.
....
""")
    agent = WhiteBoxAgent.from_world(world, genome="101111000", initial_atp=5.0)
    assert agent.position == (1, 1)
    assert world.agent_position == (1, 1)


def test_from_world_accepts_compact_genome_string() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    agent = WhiteBoxAgent.from_world(world, genome="101111000")
    assert agent.genome.to_codons() == ("101", "111", "000")


def test_from_world_accepts_codon_list() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    agent = WhiteBoxAgent.from_world(world, genome=["101", "111", "000"])
    assert agent.genome.to_compact() == "101111000"


def test_from_world_missing_marker_error_is_human_readable() -> None:
    world = World2D.from_ascii("""
...
.*.
...
""")
    with pytest.raises(ConfigurationError, match="World has no agent marker 'A'"):
        WhiteBoxAgent.from_world(world, genome="101111000")


def test_run_trial_returns_agent_world_trace_and_explanation() -> None:
    world = World2D.from_ascii("""
....
.A*.
....
""")
    agent = WhiteBoxAgent.from_world(world, genome="101111000", initial_atp=5.0)
    result = agent.run_trial(world, steps=3, explain=True)
    assert result.agent is agent
    assert result.world is world
    assert len(result.trace) == 3
    assert result.explanation is not None
    assert result.explanation.summary


def test_action_result_rejects_invalid_status() -> None:
    with pytest.raises(ConfigurationError, match="Invalid ActionResult.status"):
        ActionResult(status="execuuted", reason="typo")  # type: ignore[arg-type]


def test_action_result_rejects_empty_reason() -> None:
    with pytest.raises(ConfigurationError, match="reason must not be empty"):
        ActionResult.executed(reason="")


def test_action_result_factory_helpers() -> None:
    energy = EnergyEffect(credit=0.5, reason="rest")
    executed = ActionResult.executed(reason="ok", position_after=(1, 1), energy=energy)
    blocked = ActionResult.blocked(reason="nope", world_delta={"why": "wall"})
    failed = ActionResult.failed(reason="handler_error")
    assert executed.status == "executed"
    assert executed.energy == energy
    assert blocked.status == "blocked"
    assert blocked.world_delta == {"why": "wall"}
    assert failed.status == "failed"


def test_action_context_exposes_read_only_view() -> None:
    world = World2D.from_ascii("""
.#.
.A*
...
""")
    world.set_custom_cell((0, 2), "x")
    world.add_object((1, 1), WorldObject(kind="BEACON", amount=1.0))
    ctx = ActionContext(
        agent_id="a1",
        position=(1, 1),
        codon_bits="000",
        action_name="WAIT",
        step_index=0,
        world=world,
    )
    assert ctx.view.in_bounds((1, 1))
    assert ctx.view.is_wall((1, 0))
    assert ctx.view.resource_amount((2, 1)) == 2.0
    assert ctx.view.nearby_resource((1, 1)) is True
    assert ctx.view.nearby_wall((1, 1)) is True
    assert ctx.view.get_custom_cell((0, 2)) == "x"
    assert ctx.view.objects_at((1, 1))[0].kind == "BEACON"
    assert not hasattr(ctx.view, "set_cell")
    assert not hasattr(ctx.view, "add_object")


def test_trace_events_property_is_tuple() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    agent = WhiteBoxAgent.from_world(world, genome="000")
    trace = Trace()
    event = agent.step(world, trace)
    assert trace.events == (event,)
    assert isinstance(trace.events, tuple)


def test_readme_quickstart_uses_beginner_api_only() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = readme.split("## Quick start", 1)[1].split("## Core API", 1)[0]
    assert "WhiteBoxAgent.from_world" in quickstart
    assert "run_trial" in quickstart
    assert "explain=True" in quickstart
    assert "AgentFactory" not in quickstart
    assert "AgentSpec" not in quickstart
    assert "ATPAccount" not in quickstart
    assert "Trace()" not in quickstart
    assert "SimulationConfig" not in quickstart
    assert "position=" not in quickstart
