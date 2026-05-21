from __future__ import annotations

from codontrace.genesis import (
    CausalGraph,
    CausalGraphConfig,
    EpisodicEvent,
    EpisodicMemory,
    GenesisATPState,
)
from codontrace.genesis.causal_graph import update_causal_graph_from_memory


def _event(tick: int, action: str = "WAIT") -> EpisodicEvent:
    return EpisodicEvent(
        tick=tick,
        organism_id="o",
        action=action,
        status="executed",
        position_before=(0, 0),
        position_after=(0, 0),
        atp_runtime_before=1.0,
        atp_runtime_after=0.9,
        atp_learning_before=1.0,
        atp_learning_after=0.9,
        world_digest_before="w",
        trace_event_digest=f"e{tick}",
        observation={"x": tick},
        outcome={"reason": ""},
    )


def test_update_from_memory_is_deterministic_and_does_not_mutate_memory() -> None:
    memory = EpisodicMemory()
    memory.append(_event(0, "WAIT"))
    before = memory.digest()
    state1 = GenesisATPState.from_runtime(5.0, learning_atp=1.0, learning_enabled=True)
    state2 = GenesisATPState.from_runtime(5.0, learning_atp=1.0, learning_enabled=True)
    graph1 = CausalGraph()
    graph2 = CausalGraph()

    result1 = update_causal_graph_from_memory(
        graph1, memory, state1, CausalGraphConfig(update_cost=0.2), tick=1, organism_id="o"
    )
    result2 = update_causal_graph_from_memory(
        graph2, memory, state2, CausalGraphConfig(update_cost=0.2), tick=1, organism_id="o"
    )

    assert result1.succeeded and result2.succeeded
    assert graph1.digest() == graph2.digest()
    assert memory.digest() == before
    assert graph1.edges[0].evidence_refs == ("e0",)
