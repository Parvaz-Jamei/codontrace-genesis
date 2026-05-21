"""Compact Discovery Witness scaffold example for CodonTrace GENESIS."""

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

from codontrace.genesis import (
    D0BaselineConfig,
    D0BaselineRun,
    build_discovery_witness,
    calibrate_d0_baseline,
    evaluate_discovery_candidate,
)


def _run(seed: int) -> D0BaselineRun:
    return D0BaselineRun(
        run_id=f"d0-{seed}",
        seed=seed,
        config_digest="config-demo",
        behavior_descriptor={"novelty": 1.0, "complexity": 1.0},
        behavior_digest=f"behavior-{seed}",
        trace_digest=f"trace-{seed}",
        population_digest=f"population-{seed}",
        graph_digest=f"graph-{seed}",
        vocabulary_digest=f"vocabulary-{seed}",
        capsule_store_digest=f"capsule-{seed}",
    )


def main() -> None:
    calibration = calibrate_d0_baseline(
        (_run(1), _run(2), _run(3)),
        D0BaselineConfig(enabled=True, min_reference_runs=3, min_seeds=3),
    )
    assert calibration.baseline_set is not None
    candidate = evaluate_discovery_candidate(
        candidate_id="candidate-demo",
        source_run_id="run-demo",
        behavior_descriptor={"novelty": 4.0, "complexity": 3.0},
        behavior_digest="behavior-demo",
        baseline_set=calibration.baseline_set,
        persistence_ticks=5,
        evidence_refs=("trace-demo",),
    )
    witness = build_discovery_witness(
        witness_id="witness-demo",
        candidate=candidate,
        baseline_digest=calibration.baseline_digest,
        trace_digest="trace-demo",
        replay_digest="replay-demo",
        graph_digest="graph-demo",
        vocabulary_digest="vocabulary-demo",
        capsule_store_digest="capsule-demo",
        required_ablation_ids=("ablation-a",),
        supporting_ablation_ids=("ablation-a",),
        witness_seeds=(1, 2, 3),
    )
    print(
        {
            "status": witness.status,
            "claim_level": witness.claim_level.value,
            "digest": witness.digest()[:12],
        }
    )


if __name__ == "__main__":
    main()
