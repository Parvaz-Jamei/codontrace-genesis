from __future__ import annotations

from codontrace.genesis import CausalGraph, CausalGraphConfig, CausalGraphUpdateResult


def test_config_and_update_result_roundtrip() -> None:
    config = CausalGraphConfig(max_nodes=4, max_edges=5, update_cost=0.25)
    assert CausalGraphConfig.from_dict(config.to_dict()).to_dict() == config.to_dict()

    graph = CausalGraph(config)
    assert CausalGraph.from_dict(graph.to_dict()).to_dict() == graph.to_dict()

    result = CausalGraphUpdateResult(
        attempted=True,
        succeeded=False,
        blocked_reason="insufficient_learning_atp",
        consumed_learning_atp=0.0,
        learning_ledger_entry_id=None,
        nodes_before=0,
        nodes_after=0,
        edges_before=0,
        edges_after=0,
        graph_digest_before=graph.digest(),
        graph_digest_after=graph.digest(),
        evidence_events=1,
    )
    assert CausalGraphUpdateResult.from_dict(result.to_dict()).to_dict() == result.to_dict()
