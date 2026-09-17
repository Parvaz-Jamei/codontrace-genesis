from __future__ import annotations

from codontrace.claimgate.adapters.codontrace_he02 import bundle_from_hard_experiment_02


def test_he02_adapter_overlays_v1b_when_results_dz_is_null() -> None:
    bundle = bundle_from_hard_experiment_02()
    assert bundle.comparisons
    assert all(item.effect_size is not None for item in bundle.comparisons)
    shuffled = next(item for item in bundle.comparisons if item.b == "capsules_shuffled")
    assert shuffled.p is not None and float(shuffled.p) >= 0.05
