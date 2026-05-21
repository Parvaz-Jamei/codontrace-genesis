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

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec


def main() -> None:
    spec = GenesisExperimentSpec(tick_count=10, genome_bits=("101110000", "110101000"))
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()
    snapshot = engine.snapshot()
    evidence = engine.export_evidence_pack()
    replay = engine.export_replay_bundle()
    review_request = engine.build_review_request()
    print("run_id", result.run.run_id)
    print("summary", result.summary().experiment.to_dict())
    print("snapshot", snapshot.digest())
    print("manifest", evidence.manifest.digest())
    print("review_request", review_request.digest())
    print("replay", replay.digest())


if __name__ == "__main__":
    main()
