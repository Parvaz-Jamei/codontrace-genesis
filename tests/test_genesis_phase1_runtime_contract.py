from __future__ import annotations

from codontrace.genesis import BrainStepResult, GenesisOrganism, OrganismTickResult
from codontrace.trace import Trace
from codontrace.world import World2D


def test_step_remains_single_brain_step() -> None:
    organism = GenesisOrganism.from_bits("org", "000001010", initial_runtime_atp=5.0)
    trace = Trace()

    event = organism.step(World2D(3, 3), trace)

    assert event.codon == "000"
    assert len(trace.events) == 1


def test_step_brain_tick_executes_multiple_tokens_in_order() -> None:
    organism = GenesisOrganism.from_bits("org", "000001010", initial_runtime_atp=5.0)

    result = organism.step_brain_tick(World2D(3, 3), max_tokens=3)

    assert isinstance(result, OrganismTickResult)
    assert [step.event.codon for step in result.brain_steps] == ["000", "001", "010"]
    assert all(isinstance(step, BrainStepResult) for step in result.brain_steps)
    assert [event.step for event in result.trace.events] == [0, 1, 2]


def test_step_brain_tick_runtime_budget_stops_before_next_token() -> None:
    organism = GenesisOrganism.from_bits("org", "000001010", initial_runtime_atp=5.0)

    result = organism.step_brain_tick(World2D(3, 3), max_tokens=3, max_runtime_atp=0.2)

    assert [step.event.codon for step in result.brain_steps] == ["000"]
    assert result.stopped_reason == "max_runtime_atp_reached"
