"""Demonstrate in-memory Causal Capsule transfer hooks.

This example does not write files, open a UI, or claim proof of knowledge
transfer. It shows environment-mediated capsule deposit/read/adoption as library
objects only.
"""

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

from types import SimpleNamespace

from codontrace.genesis import (
    CapsuleTransferConfig,
    CausalGraph,
    CausalGraphConfig,
    CausalNode,
    GenesisATPState,
    NexusStigmergyLayer,
    adopt_causal_capsule,
    emit_causal_capsule,
    estimate_capsule_transfer_effect,
    read_nexus_capsules,
)


def main() -> None:
    graph = CausalGraph(CausalGraphConfig())
    graph.add_node(CausalNode("action:WAIT", "action", "WAIT"))
    graph.add_node(CausalNode("outcome:executed", "outcome", "executed"))
    graph.add_or_update_edge(
        "action:WAIT", "outcome:executed", "predicts_local", tick=0, evidence_ref="demo"
    )

    source = SimpleNamespace(id="source")
    target = SimpleNamespace(id="target")
    fitness = SimpleNamespace(score=2.0)
    source_atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    target_atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    config = CapsuleTransferConfig(enabled=True, min_confidence=0.1)

    emission = emit_causal_capsule(source, graph, fitness, source_atp, config, tick=1)
    layer = NexusStigmergyLayer()
    if emission.capsule is not None:
        layer.deposit(emission.capsule, position=(0, 0))
    read = read_nexus_capsules(target, layer, target_atp, config, tick=2)
    adoption = None
    if read.capsules_read:
        adoption = adopt_causal_capsule(
            target, read.capsules_read[0], graph, None, target_atp, config, tick=2
        )
    effect = estimate_capsule_transfer_effect(
        source_capsule_id=emission.capsule.capsule_id if emission.capsule else "none",
        target_organism_id="target",
        pre_graph_digest=emission.capsule.source_graph_digest if emission.capsule else "",
        post_graph_digest=graph.digest(),
        confidence=emission.capsule.confidence if emission.capsule else 0.0,
    )

    print("capsule_id", emission.capsule.capsule_id if emission.capsule else None)
    print("store_digest", layer.digest())
    print("adoption_succeeded", None if adoption is None else adoption.succeeded)
    print("effect_interpretation", effect.interpretation)


if __name__ == "__main__":
    main()
