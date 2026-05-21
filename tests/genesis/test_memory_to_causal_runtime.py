from codontrace import Trace
from codontrace.genesis import CausalGraph, CausalGraphConfig, EpisodicMemory, GenesisOrganism
from codontrace.world import World2D


def test_memory_event_id_is_attached_to_causal_update() -> None:
    graph = CausalGraph(CausalGraphConfig(update_cost=0.5))
    organism = GenesisOrganism.from_bits(
        "o",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=2.0,
        causal_graph=graph,
    )
    organism.episodic_memory = EpisodicMemory()
    trace = Trace()

    event = organism.step(World2D(width=3, height=3), trace)

    assert event.world_delta["memory_write_succeeded"] is True
    assert event.world_delta["causal_graph_update_succeeded"] is True
    assert organism.episodic_memory.events
    assert any(edge.relation == "leads_to_memory_write" for edge in graph.edges)
    # 0.1 memory write + 0.5 causal update
    assert round(organism.atp_state.learning_available, 10) == 1.4


def test_causal_update_works_without_memory() -> None:
    graph = CausalGraph(CausalGraphConfig(update_cost=0.5))
    organism = GenesisOrganism.from_bits(
        "o",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=1.0,
        causal_graph=graph,
    )
    trace = Trace()

    event = organism.step(World2D(width=3, height=3), trace)

    assert "memory_write_succeeded" not in event.world_delta
    assert event.world_delta["causal_graph_update_succeeded"] is True
    assert len(graph.edges) > 0
