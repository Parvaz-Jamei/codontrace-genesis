"""v1b wrapper exists and does not raise ClaimGate on committed rows."""

from codontrace.genesis.he02_contrasts import (
    analyze_committed_research,
    run_hard_experiment_02_v1b,
)


def test_v1b_wrapper_is_callable() -> None:
    assert callable(run_hard_experiment_02_v1b)


def test_committed_rows_stay_runtime_observation() -> None:
    report = analyze_committed_research()
    assert report["claim_ceiling"] == "runtime_observation"
    assert report["intervention_supported"] is False
