from __future__ import annotations

from codontrace.genesis import (
    BehaviorDescriptorSchema,
    D0BaselineConfig,
    D0BaselineRun,
    D0DistanceMetricConfig,
    QDArchive,
    QDArchiveConfig,
    QDElite,
    assign_behavior_bin,
    build_discovery_witness,
    calibrate_d0_baseline,
    evaluate_discovery_candidate,
    summarize_qd_archive,
    update_qd_archive,
)
from codontrace.genesis.discovery import DiscoveryClaimLevel


def _run(seed: int, novelty: float) -> D0BaselineRun:
    return D0BaselineRun(
        run_id=f"r{seed}",
        seed=seed,
        config_digest="cfg",
        behavior_descriptor={"novelty": novelty, "complexity": novelty / 2},
        behavior_digest=f"b{seed}",
        trace_digest=f"t{seed}",
        population_digest=f"p{seed}",
        graph_digest=f"g{seed}",
        vocabulary_digest=f"v{seed}",
        capsule_store_digest=f"c{seed}",
    )


def test_d0_baseline_calibration_distance_and_roundtrip() -> None:
    config = D0BaselineConfig(enabled=True, min_reference_runs=2, min_seeds=2)
    result = calibrate_d0_baseline([_run(1, 1.0), _run(2, 2.0)], config)
    assert result.succeeded
    assert result.baseline_set is not None
    distance = codontrace_distance({"novelty": 4.0, "complexity": 2.0}, result.baseline_set)
    assert distance.succeeded
    assert distance.distance > 0
    assert type(result).from_dict(result.to_dict()).digest() == result.digest()


def codontrace_distance(descriptor: dict[str, float], baseline_set):
    from codontrace.genesis import measure_distance_to_d0

    return measure_distance_to_d0(descriptor, baseline_set, D0DistanceMetricConfig())


def test_discovery_candidate_and_witness_require_evidence() -> None:
    calibration = calibrate_d0_baseline(
        [_run(1, 1.0), _run(2, 1.2)],
        D0BaselineConfig(enabled=True, min_reference_runs=2, min_seeds=2),
    )
    assert calibration.baseline_set is not None
    candidate = evaluate_discovery_candidate(
        candidate_id="cand1",
        source_run_id="r9",
        behavior_descriptor={"novelty": 4.0, "complexity": 2.0},
        behavior_digest="bd",
        baseline_set=calibration.baseline_set,
        novelty_threshold=0.1,
        persistence_ticks=5,
        evidence_refs=("trace:1",),
    )
    assert candidate.claim_level is DiscoveryClaimLevel.CANDIDATE
    blocked = build_discovery_witness(
        witness_id="w1",
        candidate=candidate,
        baseline_digest=calibration.baseline_digest,
        trace_digest="td",
        replay_digest="rd",
        graph_digest="gd",
        vocabulary_digest="vd",
        capsule_store_digest="cd",
        required_ablation_ids=("a1",),
        supporting_ablation_ids=(),
        witness_seeds=(1,),
    )
    assert blocked.status == "blocked"
    assert "ablation_metadata_missing" in blocked.reasons
    supported = build_discovery_witness(
        witness_id="w2",
        candidate=candidate,
        baseline_digest=calibration.baseline_digest,
        trace_digest="td",
        replay_digest="rd",
        graph_digest="gd",
        vocabulary_digest="vd",
        capsule_store_digest="cd",
        required_ablation_ids=("a1",),
        supporting_ablation_ids=("a1",),
        witness_seeds=(1, 2, 3),
    )
    assert supported.claim_level is DiscoveryClaimLevel.EVIDENCE_SUPPORTED
    assert type(supported).from_dict(supported.to_dict()).digest() == supported.digest()


def test_no_discovery_claim_by_default() -> None:
    calibration = calibrate_d0_baseline(
        [_run(1, 1.0), _run(2, 1.2)],
        D0BaselineConfig(enabled=True, min_reference_runs=2, min_seeds=2),
    )
    assert calibration.baseline_set is not None
    candidate = evaluate_discovery_candidate(
        candidate_id="weak",
        source_run_id="r3",
        behavior_descriptor={"novelty": 1.0, "complexity": 0.5},
        behavior_digest="weak",
        baseline_set=calibration.baseline_set,
    )
    assert candidate.claim_level is DiscoveryClaimLevel.NONE


def test_qd_archive_hooks() -> None:
    schema = BehaviorDescriptorSchema(
        descriptor_names=("novelty", "complexity"),
        bins_per_descriptor={"novelty": 2, "complexity": 2},
        min_values={"novelty": 0.0, "complexity": 0.0},
        max_values={"novelty": 10.0, "complexity": 10.0},
    )
    archive = QDArchive.empty(QDArchiveConfig(schema=schema))
    behavior_bin = assign_behavior_bin({"novelty": 8.0, "complexity": 1.0}, schema)
    low = QDElite("o1", 1.0, {"novelty": 8.0, "complexity": 1.0}, behavior_bin, "g1", "t1")
    high = QDElite("o2", 3.0, {"novelty": 8.0, "complexity": 1.0}, behavior_bin, "g2", "t2")
    first = update_qd_archive(archive, low)
    second = update_qd_archive(first.archive, high)
    third = update_qd_archive(second.archive, low)
    summary = summarize_qd_archive(second.archive)
    assert first.inserted
    assert second.replaced
    assert not third.inserted and not third.replaced
    assert summary.filled_bins == 1
    assert summary.qd_score == 3.0
