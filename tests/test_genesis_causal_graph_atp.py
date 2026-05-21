from __future__ import annotations

from codontrace.genesis import CausalGraph, CausalGraphConfig, GenesisATPState
from codontrace.genesis.causal_graph import update_causal_graph_from_trace
from codontrace.trace import TraceEvent


def _event() -> TraceEvent:
    return TraceEvent(
        step=0,
        agent_id="o",
        codon="000",
        action="WAIT",
        atp_before=5.0,
        atp_after=4.9,
        position_before=(0, 0),
        position_after=(0, 0),
        status="executed",
    )


def test_graph_update_consumes_learning_not_runtime() -> None:
    state = GenesisATPState.from_runtime(5.0, learning_atp=1.0, learning_enabled=True)
    graph = CausalGraph()

    result = update_causal_graph_from_trace(
        graph, [_event()], state, CausalGraphConfig(update_cost=0.5), tick=0, organism_id="o"
    )

    assert result.succeeded
    assert result.learning_ledger_entry_id == 0
    assert state.runtime_available == 5.0
    assert state.learning_available == 0.5
    assert len(state.runtime.ledger) == 0
    assert len(state.learning.ledger) == 1


def test_insufficient_learning_blocks_without_runtime_fallback() -> None:
    state = GenesisATPState.from_runtime(5.0, learning_atp=0.1, learning_enabled=True)
    graph = CausalGraph()

    result = update_causal_graph_from_trace(
        graph, [_event()], state, CausalGraphConfig(update_cost=0.5), tick=0, organism_id="o"
    )

    assert not result.succeeded
    assert result.blocked_reason == "insufficient_learning_atp"
    assert state.runtime_available == 5.0
    assert state.learning_available == 0.1
    assert len(graph.nodes) == 0
