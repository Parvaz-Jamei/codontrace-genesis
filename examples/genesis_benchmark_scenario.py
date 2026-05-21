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

from codontrace.genesis import BenchmarkScenario

scenario = BenchmarkScenario(
    benchmark_id="controlled-baseline-demo",
    description="Object-only benchmark metadata; no runner and no superiority claim.",
    baseline_method="fixed-rule baseline",
    controlled_variables=("seed", "world_size"),
    metrics=("coverage", "qd_score"),
    non_claims=("No benchmark superiority claim.",),
)
print({"benchmark": scenario.benchmark_id, "metrics": scenario.metrics})
