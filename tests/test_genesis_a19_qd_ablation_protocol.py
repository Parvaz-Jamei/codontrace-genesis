from codontrace.genesis import (
    AblationFactor,
    AblationRunRecord,
    BehaviorDescriptorSchema,
    D0BaselineConfig,
    D0BaselineRun,
    D0DistanceMetricConfig,
    DiscoveryClaimLevel,
    DiscoveryWitness,
    DiscoveryWitnessConfig,
    EffectSizeResult,
    QDArchive,
    QDArchiveBatchUpdateResult,
    QDArchiveConfig,
    QDArchivePolicy,
    QDArchiveSummary,
    QDElite,
    StatisticalProtocolConfig,
    WitnessValidationResult,
    assign_behavior_bin,
    build_discovery_witness,
    calibrate_d0_baseline,
    compare_ablation_runs,
    descriptor_distance,
    estimate_effect_size_lite,
    evaluate_discovery_candidate,
    measure_distance_to_d0,
    normalize_descriptor,
    update_qd_archive,
    update_qd_archive_many,
    validate_descriptor_against_schema,
)


def _run(seed: int, novelty: float, complexity: float | None = None) -> D0BaselineRun:
    complexity = novelty if complexity is None else complexity
    return D0BaselineRun(
        run_id=f"r{seed}",
        seed=seed,
        config_digest="cfg",
        behavior_descriptor={"novelty": novelty, "complexity": complexity},
        behavior_digest=f"b{seed}",
        trace_digest=f"t{seed}",
        population_digest=f"p{seed}",
        graph_digest=f"g{seed}",
        vocabulary_digest=f"v{seed}",
        capsule_store_digest=f"c{seed}",
    )


def _schema() -> BehaviorDescriptorSchema:
    return BehaviorDescriptorSchema(
        descriptor_names=("novelty", "complexity"),
        bins_per_descriptor={"novelty": 4, "complexity": 4},
        min_values={"novelty": 0.0, "complexity": 0.0},
        max_values={"novelty": 4.0, "complexity": 4.0},
    )


def _elite(name: str, fitness: float, novelty: float, complexity: float) -> QDElite:
    descriptor = {"novelty": novelty, "complexity": complexity}
    return QDElite(
        organism_id=name,
        fitness=fitness,
        behavior_descriptor=descriptor,
        behavior_bin=assign_behavior_bin(descriptor, _schema()),
        genome_digest=f"genome:{name}",
        trace_digest=f"trace:{name}",
        metadata={"novelty": novelty},
    )


def test_d0_enabled_semantics_and_metrics() -> None:
    disabled = calibrate_d0_baseline([_run(1, 1.0)], D0BaselineConfig())
    assert disabled.reasons == ("d0_disabled",)
    config = D0BaselineConfig(
        enabled=True,
        min_reference_runs=3,
        min_seeds=3,
        behavior_descriptor_bins={"novelty": 4, "complexity": 4},
    )
    result = calibrate_d0_baseline([_run(1, 1.0), _run(2, 1.5), _run(3, 2.0)], config)
    assert result.succeeded
    assert result.baseline_set is not None
    z = measure_distance_to_d0(
        {"novelty": 3.0, "complexity": 2.0},
        result.baseline_set,
        D0DistanceMetricConfig(metric="z_score_lite"),
    )
    bins = measure_distance_to_d0(
        {"novelty": 3.0, "complexity": 2.0},
        result.baseline_set,
        D0DistanceMetricConfig(metric="bin_distance"),
    )
    envelope = measure_distance_to_d0(
        {"novelty": 3.0, "complexity": 2.0},
        result.baseline_set,
        D0DistanceMetricConfig(metric="out_of_envelope_count"),
    )
    assert z.succeeded and z.distance > 0
    assert bins.succeeded and bins.distance >= 0
    assert envelope.succeeded and envelope.distance == 1.0


def test_witness_config_ablation_coverage_and_soft_claim() -> None:
    config = D0BaselineConfig(enabled=True, min_reference_runs=3, min_seeds=3)
    calibration = calibrate_d0_baseline([_run(1, 1.0), _run(2, 1.2), _run(3, 1.3)], config)
    assert calibration.baseline_set is not None
    candidate = evaluate_discovery_candidate(
        candidate_id="cand",
        source_run_id="source",
        behavior_descriptor={"novelty": 3.0, "complexity": 3.0},
        behavior_digest="behavior",
        baseline_set=calibration.baseline_set,
        novelty_threshold=0.1,
        persistence_ticks=2,
        evidence_refs=("trace:1",),
    )
    blocked = build_discovery_witness(
        witness_id="w-blocked",
        candidate=candidate,
        baseline_digest=calibration.baseline_digest,
        trace_digest="trace",
        replay_digest="replay",
        graph_digest="graph",
        vocabulary_digest="vocab",
        capsule_store_digest="capsule",
        required_ablation_ids=("no_adf", "no_capsule"),
        supporting_ablation_ids=("no_adf",),
        witness_seeds=(1, 2, 3),
    )
    assert blocked.status == "blocked"
    assert blocked.ablation_validation is not None
    assert blocked.ablation_validation.missing_ablation_ids == ("no_capsule",)
    supported = build_discovery_witness(
        witness_id="w-supported",
        candidate=candidate,
        baseline_digest=calibration.baseline_digest,
        trace_digest="trace",
        replay_digest="replay",
        graph_digest="graph",
        vocabulary_digest="vocab",
        capsule_store_digest="capsule",
        required_ablation_ids=("no_adf", "no_capsule"),
        supporting_ablation_ids=("no_adf", "no_capsule"),
        witness_seeds=(1, 2),
        config=DiscoveryWitnessConfig(min_witness_seeds=2),
        statistical_protocol_digest="stat",
        qd_archive_digest="qd",
    )
    assert supported.claim_level is DiscoveryClaimLevel.EVIDENCE_SUPPORTED
    assert supported.status == "supported_scaffold"
    assert DiscoveryWitness.from_dict(supported.to_dict()).digest() == supported.digest()
    assert isinstance(supported.ablation_validation, WitnessValidationResult)


def test_qd_archive_policy_roundtrip_and_batch_update() -> None:
    policy = QDArchivePolicy(replacement_policy="first_wins")
    config = QDArchiveConfig(schema=_schema(), policy=policy, archive_id="archive:test")
    archive = QDArchive.empty(config)
    first = update_qd_archive(archive, _elite("a", 1.0, 0.5, 0.5)).archive
    rejected_result = update_qd_archive(first, _elite("b", 9.0, 0.6, 0.6))
    assert rejected_result.rejected
    assert rejected_result.archive.rejected
    assert QDArchiveConfig.from_dict(config.to_dict()).digest() == config.digest()
    assert (
        rejected_result.digest()
        == type(rejected_result).from_dict(rejected_result.to_dict()).digest()
    )

    better_policy = QDArchivePolicy(replacement_policy="higher_fitness")
    better_archive = QDArchive.empty(QDArchiveConfig(schema=_schema(), policy=better_policy))
    batch = update_qd_archive_many(
        better_archive,
        (_elite("a", 1.0, 0.5, 0.5), _elite("b", 2.0, 0.6, 0.6), _elite("c", 0.5, 3.5, 3.5)),
    )
    assert isinstance(batch, QDArchiveBatchUpdateResult)
    assert batch.candidates_seen == 3
    assert batch.inserted_count == 2
    assert batch.replaced_count == 1
    assert QDArchiveBatchUpdateResult.from_dict(batch.to_dict()).digest() == batch.digest()
    summary = batch.summary
    assert isinstance(summary, QDArchiveSummary)
    assert summary.total_bins == 16
    assert summary.coverage_percent > 0
    assert QDArchiveSummary.from_dict(summary.to_dict()).digest() == summary.digest()


def test_descriptor_helpers_are_pure_python_and_validate_bool() -> None:
    schema = _schema()
    assert validate_descriptor_against_schema({"novelty": 1.0, "complexity": 1.0}, schema) == ()
    assert "novelty:missing_or_non_numeric" in validate_descriptor_against_schema(
        {"novelty": True, "complexity": 1.0}, schema
    )
    normalized = normalize_descriptor({"novelty": 2.0, "complexity": 4.0}, schema)
    assert normalized == {"novelty": 0.5, "complexity": 1.0}
    assert (
        descriptor_distance(
            {"novelty": 0.0, "complexity": 0.0}, {"novelty": 4.0, "complexity": 4.0}, schema
        )
        == 1.0
    )


def test_ablation_and_statistical_protocol_hooks_roundtrip() -> None:
    factor = AblationFactor(
        "no_adf", "Disable ADF", ("adf",), {"adf_enabled": False}, "isolate macro effect"
    )
    assert AblationFactor.from_dict(factor.to_dict()).digest() == factor.digest()
    baseline = [
        AblationRunRecord("b1", "baseline", 1, "cfg", "t", "bd", 1.0),
        AblationRunRecord("b2", "baseline", 2, "cfg", "t", "bd", 2.0),
    ]
    treatment = [
        AblationRunRecord("t1", "no_adf", 1, "cfg", "t", "bd", 0.5),
        AblationRunRecord("t2", "no_adf", 2, "cfg", "t", "bd", 1.0),
    ]
    comparison = compare_ablation_runs(baseline, treatment, compared_factor_id="no_adf")
    assert comparison.seed_count == 2
    assert comparison.mean_delta == -0.75
    assert type(comparison).from_dict(comparison.to_dict()).digest() == comparison.digest()
    protocol = StatisticalProtocolConfig(metric_names=("fitness",), min_seeds=2)
    assert StatisticalProtocolConfig.from_dict(protocol.to_dict()).digest() == protocol.digest()
    effect = estimate_effect_size_lite("fitness", [1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
    assert isinstance(effect, EffectSizeResult)
    assert EffectSizeResult.from_dict(effect.to_dict()).digest() == effect.digest()
