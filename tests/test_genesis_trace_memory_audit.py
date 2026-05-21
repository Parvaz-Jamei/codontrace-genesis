from __future__ import annotations

from codontrace.genesis import EpisodicMemory, GenesisATPState, GenesisOrganism
from codontrace.trace import Trace
from codontrace.world import World2D


def test_memory_enabled_step_records_trace_event_world_delta() -> None:
    organism = GenesisOrganism.from_bits("o", "000", initial_runtime_atp=5.0, position=(0, 0))
    organism.atp_state = GenesisATPState.from_runtime(5.0, learning_atp=1.0, learning_enabled=True)
    organism.episodic_memory = EpisodicMemory()
    trace = Trace()

    event = organism.step(World2D(2, 2), trace)

    assert trace.events[-1] == event
    assert event.world_delta["memory_write_attempted"] is True
    assert event.world_delta["memory_write_succeeded"] is True
    assert event.world_delta["memory_size_before"] == 0
    assert event.world_delta["memory_size_after"] == 1
    assert event.world_delta["learning_ledger_entry_id"] == 0
    assert event.world_delta["atp_learning_before"] == 1.0
    assert event.world_delta["atp_learning_after"] == 0.9


def test_insufficient_learning_atp_records_memory_block_reason() -> None:
    organism = GenesisOrganism.from_bits("o", "000", initial_runtime_atp=5.0, position=(0, 0))
    organism.atp_state = GenesisATPState.from_runtime(5.0, learning_atp=0.0, learning_enabled=True)
    organism.episodic_memory = EpisodicMemory()
    trace = Trace()

    event = organism.step(World2D(2, 2), trace)

    assert event.world_delta["memory_write_attempted"] is True
    assert event.world_delta["memory_write_succeeded"] is False
    assert event.world_delta["memory_write_blocked_reason"] == "insufficient_learning_atp"
    assert event.world_delta["memory_size_before"] == 0
    assert event.world_delta["memory_size_after"] == 0
    assert len(organism.episodic_memory.events) == 0


def test_memory_disabled_step_does_not_add_misleading_memory_fields() -> None:
    organism = GenesisOrganism.from_bits("o", "000", initial_runtime_atp=5.0, position=(0, 0))
    trace = Trace()

    event = organism.step(World2D(2, 2), trace)

    assert "memory_write_attempted" not in event.world_delta
