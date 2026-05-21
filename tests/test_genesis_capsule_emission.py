from types import SimpleNamespace

from codontrace.genesis import (
    CapsuleTransferConfig,
    CausalGraph,
    CausalGraphConfig,
    CausalNode,
    GenesisATPState,
    emit_causal_capsule,
)


def _graph():
    graph = CausalGraph(CausalGraphConfig())
    graph.add_node(CausalNode("action:WAIT", "action", "WAIT"))
    graph.add_node(CausalNode("outcome:executed", "outcome", "executed"))
    graph.add_or_update_edge(
        "action:WAIT", "outcome:executed", "predicts_local", tick=0, evidence_ref="e"
    )
    return graph


def test_disabled_low_fitness_and_successful_emission():
    graph = _graph()
    atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    organism = SimpleNamespace(id="org")
    fitness = SimpleNamespace(score=2.0)
    assert not emit_causal_capsule(
        organism, graph, fitness, atp, CapsuleTransferConfig(), tick=1
    ).succeeded
    low = CapsuleTransferConfig(enabled=True, min_source_fitness=3.0)
    assert (
        emit_causal_capsule(organism, graph, fitness, atp, low, tick=1).blocked_reason
        == "source_fitness_below_threshold"
    )
    result = emit_causal_capsule(
        organism,
        graph,
        fitness,
        atp,
        CapsuleTransferConfig(enabled=True, min_confidence=0.1),
        tick=1,
    )
    assert result.succeeded
    assert result.capsule is not None
    assert result.consumed_runtime_atp > 0
    assert result.consumed_learning_atp > 0
    assert atp.runtime_available < 5.0
    assert atp.learning_available < 5.0


def test_emission_blocks_on_insufficient_runtime_or_learning():
    graph = _graph()
    organism = SimpleNamespace(id="org")
    fitness = SimpleNamespace(score=2.0)
    cfg = CapsuleTransferConfig(enabled=True, min_confidence=0.1, emission_cost_runtime_atp=10.0)
    atp = GenesisATPState.from_runtime(1.0, learning_atp=5.0, learning_enabled=True)
    assert (
        emit_causal_capsule(organism, graph, fitness, atp, cfg, tick=1).blocked_reason
        == "insufficient_runtime_atp"
    )
    cfg2 = CapsuleTransferConfig(enabled=True, min_confidence=0.1, emission_cost_learning_atp=10.0)
    atp2 = GenesisATPState.from_runtime(5.0, learning_atp=1.0, learning_enabled=True)
    assert (
        emit_causal_capsule(organism, graph, fitness, atp2, cfg2, tick=1).blocked_reason
        == "insufficient_learning_atp"
    )
