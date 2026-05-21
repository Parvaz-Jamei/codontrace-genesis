from __future__ import annotations

from codontrace.genesis import CausalGraph, CausalGraphConfig, GenesisATPState
from codontrace.genesis.causal_graph import update_causal_graph_from_trace
from codontrace.trace import TraceEvent


def _event(
    action: str,
    delta: dict[str, object] | None = None,
    *,
    status: str = "executed",
    reason: str = "",
) -> TraceEvent:
    return TraceEvent(
        step=0,
        agent_id="o",
        codon="000",
        action=action,
        atp_before=5.0,
        atp_after=4.0,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta={} if delta is None else delta,  # type: ignore[arg-type]
        status=status,
        reason=reason,
    )


def _updated_graph(events: list[TraceEvent]) -> CausalGraph:
    graph = CausalGraph()
    state = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    result = update_causal_graph_from_trace(
        graph, events, state, CausalGraphConfig(update_cost=0.1), tick=0, organism_id="o"
    )
    assert result.succeeded
    return graph


def test_wait_event_creates_action_to_outcome_edge() -> None:
    graph = _updated_graph([_event("WAIT")])
    assert any(
        edge.source == "action:WAIT" and edge.target == "outcome:executed" for edge in graph.edges
    )


def test_blocked_event_creates_action_to_blocked_reason_edge() -> None:
    graph = _updated_graph([_event("MOVE_TOWARD", status="blocked", reason="occupied_blocked")])
    assert any(
        edge.relation == "leads_to_block" and edge.target == "blocked_reason:occupied_blocked"
        for edge in graph.edges
    )


def test_lumen_memory_and_reproduction_evidence_edges() -> None:
    graph = _updated_graph(
        [
            _event("EAT_LUMEN", {"lumen_interaction": True}),
            _event("WAIT", {"memory_write_succeeded": True}),
            _event(
                "COPY_SELF",
                {"reproduction_attempted": True, "reproduction_succeeded": True},
            ),
        ]
    )
    relations = {(edge.source, edge.relation, edge.target) for edge in graph.edges}
    assert ("action:EAT_LUMEN", "leads_to_resource_gain", "resource:lumen") in relations
    assert ("action:WAIT", "leads_to_memory_write", "memory:write") in relations
    assert (
        "reproduction:attempt",
        "leads_to_reproduction_success",
        "reproduction:success",
    ) in relations
