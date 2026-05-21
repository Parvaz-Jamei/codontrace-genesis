"""Compact D0 baseline object example for CodonTrace GENESIS."""

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

from codontrace.genesis import D0BaselineConfig, D0BaselineRun, calibrate_d0_baseline


def main() -> None:
    runs = tuple(
        D0BaselineRun(
            run_id=f"d0-{seed}",
            seed=seed,
            config_digest="config-demo",
            behavior_descriptor={"novelty": float(seed), "complexity": float(seed) / 2.0},
            behavior_digest=f"behavior-{seed}",
            trace_digest=f"trace-{seed}",
            population_digest=f"population-{seed}",
            graph_digest=f"graph-{seed}",
            vocabulary_digest=f"vocabulary-{seed}",
            capsule_store_digest=f"capsule-{seed}",
        )
        for seed in (1, 2)
    )
    result = calibrate_d0_baseline(
        runs, D0BaselineConfig(enabled=True, min_reference_runs=2, min_seeds=2)
    )
    print(
        {
            "succeeded": result.succeeded,
            "run_count": result.run_count,
            "baseline_digest": result.baseline_digest[:12],
        }
    )


if __name__ == "__main__":
    main()
