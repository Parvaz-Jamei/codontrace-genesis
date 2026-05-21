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

from codontrace.genesis import AblationFactor, AblationRunRecord, compare_ablation_runs

factor = AblationFactor(
    factor_id="no_adf",
    name="Disable ADF",
    disabled_components=("adf",),
    config_overrides={"adf_enabled": False},
    rationale="Estimate whether macro vocabulary scaffolding changes behavior metrics.",
)
baseline = (
    AblationRunRecord("b1", "baseline", 1, "cfg", "trace", "behavior", 1.0),
    AblationRunRecord("b2", "baseline", 2, "cfg", "trace", "behavior", 1.4),
)
treatment = (
    AblationRunRecord("t1", "no_adf", 1, "cfg", "trace", "behavior", 0.8),
    AblationRunRecord("t2", "no_adf", 2, "cfg", "trace", "behavior", 1.0),
)
comparison = compare_ablation_runs(baseline, treatment, compared_factor_id=factor.factor_id)
print(
    {
        "factor": factor.factor_id,
        "mean_delta": comparison.mean_delta,
        "seed_count": comparison.seed_count,
    }
)
