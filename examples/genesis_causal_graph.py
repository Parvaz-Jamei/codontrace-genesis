"""Demonstrate local CausalGraph scaffold without file output or UI."""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace import (
    AliveGateConfig,
    CausalGraph,
    CausalGraphConfig,
    EpisodicMemory,
    GenesisATPState,
    GenesisOrganism,
    LearningATPConfig,
    World2D,
    update_causal_graph_from_trace,
)

world = World2D(4, 4)
organism = GenesisOrganism.from_bits("cg-1", "000000000", initial_runtime_atp=5.0, position=(1, 1))
organism.atp_state = GenesisATPState.from_runtime(5.0, learning_atp=2.0, learning_enabled=True)
organism.episodic_memory = EpisodicMemory()
organism.learning_config = LearningATPConfig(memory_write_cost=0.1)

run = organism.run(
    world,
    ticks=3,
    alive_config=AliveGateConfig(
        min_ticks=1,
        min_executed_actions=0,
        require_positive_runtime_atp=False,
    ),
)

graph = CausalGraph(CausalGraphConfig(update_cost=0.5))
update = update_causal_graph_from_trace(
    graph,
    run.trace,
    organism.atp_state,
    graph.config,
    tick=len(run.trace.events),
    organism_id=organism.id,
)

print("version: genesis_causal_graph_demo")
print(f"nodes: {len(graph.nodes)}")
print(f"edges: {len(graph.edges)}")
print(f"update_succeeded: {update.succeeded}")
print(f"learning_atp_after_update: {organism.atp_state.learning_available:.2f}")
print(f"graph_digest: {graph.digest()}")
