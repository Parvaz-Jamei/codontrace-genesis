"""Phase 4: submitted rows are not independent runs.

The witness is two paired deltas, 1 and 2. Treated as twenty rows by repeating
the same two objects, the old report narrowed the interval and became
claim-eligible. Repeating a unit, or adding a checkpoint of the same history,
must not do either.

The unit rule is Hurlbert's simple pseudoreplication (Ecological Monographs,
1984): one experimental history is one replicate. The claim floor is
claimgate.auditor.LEVEL4_MIN_SEEDS.
"""

from __future__ import annotations

from codontrace.claimgate.auditor import LEVEL4_MIN_SEEDS
from codontrace.genesis.causal_validation import (
    INDEPENDENT_RUN_FLOOR,
    CausalInterventionRunPair,
    InterventionSpec,
    build_causal_evidence_report,
    paired_mean_interval,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (
    CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS,
)


def _spec(*, isolated: bool = True, extra: bool = False, settings: bool = True) -> InterventionSpec:
    baseline = {"factor": "off", "other": "same"}
    treatment = {"factor": "on", "other": "changed" if extra else "same"}
    return InterventionSpec(
        "i",
        "factor",
        "baseline-config",
        "treatment-config",
        "seed-family",
        isolated_factor=isolated,
        baseline_settings=baseline if settings else (),
        treatment_settings=treatment if settings else (),
    )


def _pair(
    delta: float,
    *,
    run_id: str,
    seed: int,
    history_id: str,
    checkpoint_id: str = "",
    spec: InterventionSpec | None = None,
) -> CausalInterventionRunPair:
    return CausalInterventionRunPair(
        spec or _spec(),
        "baseline-outcome",
        "treatment-outcome",
        0.0,
        delta,
        run_id=run_id,
        seed=seed,
        history_id=history_id,
        checkpoint_id=checkpoint_id,
    )


def test_claim_floor_matches_the_claimgate_auditor() -> None:
    assert INDEPENDENT_RUN_FLOOR == LEVEL4_MIN_SEEDS == CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS == 16


def test_repeating_two_pairs_does_not_narrow_the_interval() -> None:
    first = _pair(1.0, run_id="r1", seed=1, history_id="h1")
    second = _pair(2.0, run_id="r2", seed=2, history_id="h2")
    honest = build_causal_evidence_report((first, second))
    padded = build_causal_evidence_report((first, second) * 10)
    inflated = paired_mean_interval([1.0, 2.0] * 10)

    assert honest.effect.sample_count == 2
    assert honest.effect.confidence_interval is not None
    assert honest.effect.confidence_interval[0] < 0.0 < honest.effect.confidence_interval[1]
    assert honest.effect.statistical_support is False
    assert honest.claim_eligible is False

    assert padded.submitted_count == 20
    assert padded.historical_sample_count == 20
    assert padded.independent_count == 2
    assert padded.effect.sample_count == 2
    assert padded.dropped_duplicate_count == 18
    assert padded.effect.confidence_interval == honest.effect.confidence_interval
    assert padded.failure_status == "duplicate_units_removed"
    assert padded.claim_eligible is False
    assert inflated.n == 20 and inflated.statistical_support is True
    assert padded.effect.statistical_support is False


def test_exact_copies_without_ids_still_do_not_become_twenty_samples() -> None:
    bare = InterventionSpec("i", "factor", "b", "t", "s")
    first = CausalInterventionRunPair(bare, "b", "t", 0.0, 1.0)
    second = CausalInterventionRunPair(bare, "b", "t", 0.0, 2.0)
    report = build_causal_evidence_report((first, second) * 10)
    assert report.submitted_count == 20
    assert report.independent_count == 2
    assert report.effect.sample_count == 2
    assert report.claim_eligible is False


def test_checkpoints_of_one_history_are_one_unit() -> None:
    early = _pair(1.0, run_id="r", seed=1, history_id="h", checkpoint_id="t0")
    late = _pair(5.0, run_id="r", seed=1, history_id="h", checkpoint_id="t1")
    other = _pair(2.0, run_id="r2", seed=2, history_id="h2")
    report = build_causal_evidence_report((early, late, other))
    assert report.checkpoint_conflict_count == 1
    assert report.independent_count == 1
    assert report.effect.sample_count == 1
    assert report.failure_status == "checkpoint_not_independent"
    assert report.claim_eligible is False

    same = _pair(1.0, run_id="r", seed=1, history_id="h", checkpoint_id="t1")
    collapsed = build_causal_evidence_report((early, same))
    assert collapsed.independent_count == 1
    assert collapsed.effect.sample_count == 1
    assert collapsed.submitted_count == 2
    assert collapsed.failure_status == "checkpoint_not_independent"
    assert collapsed.claim_eligible is False


def test_self_declared_isolation_is_not_enough() -> None:
    pairs = tuple(
        _pair(1.0 + i * 0.01, run_id=f"r{i}", seed=i, history_id=f"h{i}", spec=_spec(settings=False))
        for i in range(INDEPENDENT_RUN_FLOOR)
    )
    declared = build_causal_evidence_report(pairs)
    assert declared.effect.statistical_support is True
    assert declared.isolation_status == "isolation_unverified"
    assert declared.claim_eligible is False

    contaminated = tuple(
        _pair(1.0 + i * 0.01, run_id=f"r{i}", seed=i, history_id=f"h{i}", spec=_spec(extra=True))
        for i in range(INDEPENDENT_RUN_FLOOR)
    )
    mixed = build_causal_evidence_report(contaminated)
    assert mixed.isolation_status == "intervention_not_isolated"
    assert mixed.claim_eligible is False

    refused = tuple(
        _pair(
            1.0 + i * 0.01,
            run_id=f"r{i}",
            seed=i,
            history_id=f"h{i}",
            spec=_spec(isolated=False),
        )
        for i in range(INDEPENDENT_RUN_FLOOR)
    )
    assert build_causal_evidence_report(refused).isolation_status == "intervention_not_isolated"


def test_a_different_intervention_on_the_same_run_is_not_a_checkpoint() -> None:
    knock_a = _pair(1.0, run_id="r", seed=1, history_id="h", spec=_spec())
    knock_b = _pair(
        2.0,
        run_id="r",
        seed=1,
        history_id="h",
        spec=InterventionSpec(
            "other-factor",
            "factor",
            "baseline-config",
            "treatment-config",
            "seed-family",
            baseline_settings={"factor": "off", "other": "same"},
            treatment_settings={"factor": "on", "other": "same"},
        ),
    )
    report = build_causal_evidence_report((knock_a, knock_b))
    assert report.independent_count == 2
    assert report.checkpoint_conflict_count == 0
    assert report.effect.sample_count == 2
    assert report.failure_status == "passed"


def test_claim_requires_the_auditor_floor_and_an_interval_that_excludes_zero() -> None:
    positive = tuple(
        _pair(1.0 + i * 0.01, run_id=f"r{i}", seed=i, history_id=f"h{i}")
        for i in range(INDEPENDENT_RUN_FLOOR)
    )
    ready = build_causal_evidence_report(positive)
    assert ready.failure_status == "passed"
    assert ready.identity_complete is True
    assert ready.isolation_status == "isolated"
    assert ready.effect.statistical_support is True
    assert ready.claim_eligible is True
    assert ready.claim_blockers == ()

    short = build_causal_evidence_report(positive[:-1])
    assert short.failure_status == "passed"
    assert short.independent_count == INDEPENDENT_RUN_FLOOR - 1
    assert short.claim_eligible is False
    assert "below_claimgate_seed_floor" in short.claim_blockers

    straddling = tuple(
        _pair(1.0 if i % 2 == 0 else -1.0, run_id=f"r{i}", seed=i, history_id=f"h{i}")
        for i in range(INDEPENDENT_RUN_FLOOR)
    )
    null = build_causal_evidence_report(straddling)
    assert null.failure_status == "passed"
    assert null.effect.statistical_support is False
    assert null.claim_eligible is False
    assert "interval_includes_zero" in null.claim_blockers
