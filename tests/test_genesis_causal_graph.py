from __future__ import annotations

from codontrace.genesis import CausalGraph, CausalGraphConfig, CausalNode
from codontrace.genesis.causal_graph import CausalEdge
from codontrace.trace import TraceEvent


def _event(action: str = "WAIT", status: str = "executed", reason: str = "") -> TraceEvent:
    return TraceEvent(
        step=0,
        agent_id="o",
        codon="000",
        action=action,
        atp_before=5.0,
        atp_after=4.9,
        position_before=(0, 0),
        position_after=(0, 0),
        status=status,
        reason=reason,
    )


def test_add_node_edge_digest_and_roundtrip() -> None:
    graph = CausalGraph()
    assert graph.add_node(CausalNode("action:WAIT", "action", "WAIT"))
    assert graph.add_node(CausalNode("outcome:executed", "outcome", "executed"))
    assert graph.add_or_update_edge(
        "action:WAIT", "outcome:executed", "predicts_local", tick=0, evidence_ref="e0"
    )
    assert graph.add_or_update_edge(
        "action:WAIT", "outcome:executed", "predicts_local", tick=1, evidence_ref="e1"
    )
    edge = graph.edges[0]
    assert edge.evidence_count == 2
    assert edge.weight == 2.0
    restored = CausalGraph.from_dict(graph.to_dict())
    assert restored.to_dict() == graph.to_dict()
    assert restored.digest() == graph.digest()


def test_limits_are_enforced_deterministically() -> None:
    graph = CausalGraph(CausalGraphConfig(max_nodes=1, max_edges=1))
    assert graph.add_node(CausalNode("action:WAIT", "action", "WAIT"))
    assert not graph.add_node(CausalNode("outcome:executed", "outcome", "executed"))
    assert len(graph.nodes) == 1


def test_edge_from_dict_roundtrip() -> None:
    edge = CausalEdge(
        source="action:WAIT",
        target="outcome:executed",
        relation="predicts_local",
        weight=1.0,
        evidence_count=1,
        first_tick=0,
        last_tick=0,
        evidence_refs=("e",),
    )
    assert CausalEdge.from_dict(edge.to_dict()).to_dict() == edge.to_dict()
