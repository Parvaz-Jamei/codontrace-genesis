from codontrace import Trace
from codontrace.genesis import (
    CausalGraph,
    CausalGraphConfig,
    GenesisOrganism,
    predict_next_outcome,
)
from codontrace.world import World2D


def test_organism_without_causal_graph_keeps_graph_metrics_off() -> None:
    organism = GenesisOrganism.from_bits("o", "000", initial_runtime_atp=5.0)
    trace = Trace()
    event = organism.step(World2D(width=3, height=3), trace)

    assert event.world_delta["causal_graph_update_attempted"] is False
    assert event.world_delta["causal_graph_digest_before"] is None
    assert organism.causal_graph is None


def test_organism_with_graph_updates_digest_and_spends_learning_atp() -> None:
    graph = CausalGraph(CausalGraphConfig(update_cost=0.5))
    organism = GenesisOrganism.from_bits(
        "o",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=2.0,
        causal_graph=graph,
    )
    before = graph.digest()
    trace = Trace()

    event = organism.step(World2D(width=3, height=3), trace)

    assert event.world_delta["causal_graph_update_attempted"] is True
    assert event.world_delta["causal_graph_update_succeeded"] is True
    assert event.world_delta["causal_graph_digest_before"] == before
    assert event.world_delta["causal_graph_digest_after"] == graph.digest()
    assert graph.digest() != before
    assert organism.atp_state.learning_available == 1.5


def test_causal_update_fails_controlled_when_learning_atp_is_insufficient() -> None:
    graph = CausalGraph(CausalGraphConfig(update_cost=2.0))
    organism = GenesisOrganism.from_bits(
        "o",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=0.5,
        causal_graph=graph,
    )
    before = graph.digest()
    trace = Trace()

    event = organism.step(World2D(width=3, height=3), trace)

    assert event.world_delta["causal_graph_update_attempted"] is True
    assert event.world_delta["causal_graph_update_succeeded"] is False
    assert event.world_delta["causal_graph_update_reason"] == "insufficient_atp_learning"
    assert graph.digest() == before


def test_lightweight_prediction_is_deterministic_after_evidence_exists() -> None:
    graph = CausalGraph(CausalGraphConfig(update_cost=0.0))
    organism = GenesisOrganism.from_bits(
        "o",
        "000000",
        initial_runtime_atp=5.0,
        initial_learning_atp=0.0,
        learning_enabled=True,
        causal_graph=graph,
    )
    world = World2D(width=3, height=3)
    trace = Trace()

    organism.step(world, trace)
    prediction = predict_next_outcome(graph, "WAIT")
    second = organism.step(world, trace)

    assert prediction.predicted_outcome == "executed"
    assert prediction.confidence == 1.0
    assert second.world_delta["causal_prediction_attempted"] is True
    assert second.world_delta["causal_prediction_correct"] is True
