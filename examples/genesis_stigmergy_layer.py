"""Demonstrate the in-memory NexusStigmergyLayer."""

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

from codontrace.genesis import CausalCapsule, NexusStigmergyLayer


def _capsule(capsule_id: str, tick: int) -> CausalCapsule:
    return CausalCapsule(
        capsule_id=capsule_id,
        source_organism_id="source",
        source_fitness=1.0,
        source_graph_digest="graph",
        event_pattern=("predicts_local",),
        predicted_outcome="outcome:executed",
        confidence=0.8,
        emitted_tick=tick,
        ttl=4,
    )


def main() -> None:
    layer = NexusStigmergyLayer()
    layer.deposit(_capsule("cap_a", 0), position=(0, 0))
    layer.deposit(_capsule("cap_b", 1), position=(1, 0))
    restored = NexusStigmergyLayer.from_dict(layer.to_dict())
    print("active_at_1", len(restored.active_signals(1)))
    print("digest", restored.digest())
    restored.expire(10)
    print("active_after_expire", len(restored.active_signals(10)))


if __name__ == "__main__":
    main()
