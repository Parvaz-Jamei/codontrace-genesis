"""Demonstrate typed Capsule/Nexus hooks without full capsule exchange."""

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

from codontrace.genesis import CausalCapsule


def main() -> None:
    capsule = CausalCapsule(
        capsule_id="capsule-demo",
        source_organism_id="org-a",
        source_fitness=1.0,
        source_graph_digest="graph-digest-demo",
        event_pattern=("WAIT", "MOVE_TOWARD"),
        predicted_outcome="executed",
        confidence=0.75,
        emitted_tick=4,
        ttl=32,
        metadata={"note": "hook only; no full exchange in this phase"},
    )
    restored = CausalCapsule.from_dict(capsule.to_dict())
    print("Capsule digest:", restored.digest())
    print("Capsule hook only:", True)


if __name__ == "__main__":
    main()
