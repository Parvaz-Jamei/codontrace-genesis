from __future__ import annotations

from codontrace.genesis import EpisodicEvent, EpisodicMemory, EpisodicMemoryConfig, GenesisATPState


def _event(tick: int, action: str = "WAIT") -> EpisodicEvent:
    return EpisodicEvent(
        tick=tick,
        organism_id="o",
        action=action,
        status="executed",
        position_before=(0, 0),
        position_after=(tick, 0),
        atp_runtime_before=1.0,
        atp_runtime_after=0.9,
        atp_learning_before=1.0,
        atp_learning_after=0.9,
        world_digest_before="w",
        trace_event_digest=f"e{tick}",
        observation={"x": tick},
        outcome={"ok": True},
    )


def test_memory_append_ring_buffer_digest_and_roundtrip() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(capacity=2))
    memory.append(_event(0))
    memory.append(_event(1, "MOVE"))
    first_digest = memory.digest()
    memory.append(_event(2, "EAT"))

    assert len(memory.events) == 2
    assert memory.events[0].tick == 1
    assert memory.digest() != first_digest
    restored = EpisodicMemory.from_dict(memory.to_dict())
    assert restored.to_dict() == memory.to_dict()
    assert restored.digest() == memory.digest()
    assert restored.by_action("EAT")[0].tick == 2
    assert restored.recent(1)[0].tick == 2


def test_memory_write_costs_learning_atp_and_blocks_when_insufficient() -> None:
    state = GenesisATPState.from_runtime(2.0, learning_atp=0.1, learning_enabled=True)
    memory = EpisodicMemory()

    blocked = memory.write_event(_event(0), state, cost=0.2)
    assert not blocked.written
    assert blocked.blocked_reason == "insufficient_learning_atp"
    assert len(memory.events) == 0

    written = memory.write_event(_event(1), state, cost=0.1)
    assert written.written
    assert written.learning_ledger_entry_id == 0
    assert state.learning_available == 0.0
    assert len(memory.events) == 1
