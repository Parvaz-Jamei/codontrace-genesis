"""Hard experiment 01: preregistered capsule source-bias causal design.

Measurement only. Does not claim intelligence, collective intelligence,
AGI, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.capsule import CapsuleAdoptionPolicy, CapsuleShuffleMode
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.hard_experiment_01 import (
    ANALYSIS_ARMS,
    ARMS,
    CALIBRATION_GOOD_PAYLOAD_ACTION,
    CALIBRATION_POOR_PAYLOAD_ACTION,
    CLAIM_CEILING,
    DOSE_LEVELS,
    INTERVENTION_CLAIM,
    INTERVENTION_SUPPORTED_FLAGS,
    MIN_SOURCE_FITNESS_TREATMENT,
    PRIMARY_OUTCOME,
    RESEARCH_SEED_COUNT,
    SMOKE_SEED_COUNT,
    HardExperiment01ArmRecord,
    HardExperiment01ArmSummary,
    HardExperiment01SeedRecord,
    _capsule_counts,
    _complete_pair_values,
    _decision_rule_failures,
    _mean_last_tick_fitness,
    _missing_outcomes_per_arm,
    build_hard_experiment_01_dose_spec,
    build_hard_experiment_01_spec,
    diagnose_hard_experiment_01_run,
    evaluate_hard_experiment_01_assay,
    evaluate_hard_experiment_01_claim,
    format_hard_experiment_01_summary,
    SCHEMA_VERSION,
    calibration_role_for_index,
    hard_experiment_01_calibration_knobs,
    hard_experiment_01_causal_dag,
    hard_experiment_01_interventions,
    hard_experiment_01_prereg_amendment_02_digest,
    hard_experiment_01_prereg_amendment_03_digest,
    hard_experiment_01_prereg_amendment_digest,
    hard_experiment_01_prereg_digest,
    hard_experiment_01_protocol_digest,
    permute_roles_for_seed,
    run_hard_experiment_01,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.statistical_protocol import StatisticalTestPolicy

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_phase_a_life_loop_digest_pin_unchanged_by_hard_experiment_01() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_hard_experiment_01_overlay_does_not_alias_default_life_loop_digest() -> None:
    overlay = build_hard_experiment_01_spec(
        seed=7, arm="source_bias_on", tick_count=12, population=6
    )
    shuffled = build_hard_experiment_01_spec(
        seed=7, arm="capsules_shuffled", tick_count=12, population=6
    )
    pinned = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert overlay.digest() != pinned.digest()
    assert shuffled.digest() != pinned.digest()
    assert shuffled.digest() != overlay.digest()
    assert pinned.digest() == LIFE_LOOP_SPEC_DIGEST


def test_hard_experiment_01_interventions_map_each_arm() -> None:
    mapped = hard_experiment_01_interventions()
    assert {item.arm for item in mapped} == set(ARMS)
    by_arm = {item.arm: item for item in mapped}
    assert by_arm["source_bias_on"].role == "treatment"
    assert by_arm["source_bias_off"].role == "mechanism_ablation"
    assert by_arm["capsules_off"].role == "channel_off"
    assert by_arm["capsules_shuffled"].role == "negative_control"
    assert "min_source_fitness" in by_arm["source_bias_off"].knob
    assert by_arm["capsules_off"].knob == "CapsuleTransferConfig.enabled"
    assert by_arm["capsules_shuffled"].knob == "CapsuleTransferConfig.shuffle_mode"
    assert by_arm["source_bias_off"].cuts_edges == ("e1",)
    assert by_arm["capsules_off"].cuts_edges == ("e1", "e2")
    assert by_arm["capsules_shuffled"].cuts_edges == ("e2_content",)
    assert all(item.to_dict()["collective_intelligence"] is False for item in mapped)


def test_hard_experiment_01_dag_and_prereg_are_frozen() -> None:
    dag = hard_experiment_01_causal_dag()
    assert dag["path"] == "gate → which capsule is adopted → action → ATP → terminal fitness"
    assert dag["nodes"] == [
        "gate",
        "which_capsule_is_adopted",
        "action",
        "ATP",
        "terminal_fitness",
    ]
    root = Path(__file__).resolve().parents[1]
    prereg = root / "docs" / "HARD_EXPERIMENT_01_PREREG.md"
    assert prereg.is_file()
    digest = hard_experiment_01_prereg_digest()
    assert digest == __import__("hashlib").sha256(prereg.read_bytes()).hexdigest()
    assert len(digest) == 64
    text = prereg.read_text(encoding="utf-8")
    assert "source_bias_on` > `source_bias_off" in text
    assert "capsules_shuffled" in text
    assert "Okasha" in text
    assert "intervention_supported" in text
    assert "collective_intelligence" in text


def test_dose_two_matches_treatment_spec() -> None:
    treatment = build_hard_experiment_01_spec(seed=11, arm="source_bias_on")
    dose_two = build_hard_experiment_01_dose_spec(
        seed=11, min_source_fitness=MIN_SOURCE_FITNESS_TREATMENT
    )
    shuffled = build_hard_experiment_01_spec(seed=11, arm="capsules_shuffled")
    assert treatment.digest() == dose_two.digest()
    assert treatment.capsule_transfer_config is not None
    assert (
        treatment.capsule_transfer_config.adoption_policy
        == CapsuleAdoptionPolicy.FITNESS_WEIGHTED
    )
    assert treatment.capsule_transfer_config.shuffle_mode is CapsuleShuffleMode.OFF
    assert shuffled.capsule_transfer_config is not None
    assert shuffled.capsule_transfer_config.shuffle_mode is CapsuleShuffleMode.CONTENT
    assert shuffled.capsule_transfer_config.shuffle_mode is not CapsuleShuffleMode.OFF
    assert shuffled.digest() != treatment.digest()


def test_hard_experiment_01_replays_all_arms_for_endpoint_seeds() -> None:
    campaign = run_hard_experiment_01(seed_count=2, include_dose=True)
    assert campaign.seeds[0] != campaign.seeds[-1]
    assert campaign.replay_verified_seeds == (campaign.seeds[0], campaign.seeds[-1])
    expected = {(seed, arm) for seed in (campaign.seeds[0], campaign.seeds[-1]) for arm in ARMS}
    observed = {(item.seed, item.arm) for item in campaign.replay_records}
    assert observed == expected
    assert all(item.matched for item in campaign.replay_records)
    assert campaign.replay_matched is True
    assert campaign.prereg_digest == hard_experiment_01_prereg_digest()
    assert campaign.scale == "smoke"
    assert campaign.claim_ceiling == CLAIM_CEILING
    assert "not_research_scale" in campaign.decision_rule_failures
    assert campaign.dose_trend is not None
    assert campaign.dose_trend.min_source_fitness == DOSE_LEVELS
    assert len(campaign.paired_contrasts) == 3
    assert campaign.multiple_comparison_audit is not None
    assert campaign.multiple_comparison_audit.metric_count == 3
    assert {item.baseline_arm for item in campaign.paired_contrasts} == {
        "source_bias_off",
        "capsules_off",
        "capsules_shuffled",
    }
    assert all(item.p_holm is not None for item in campaign.paired_contrasts)
    assert campaign.shuffled_vs_capsules_off is not None
    assert StatisticalTestPolicy().tier_for_n(2) == "descriptive_only"


def test_hard_experiment_01_twelve_seeds_replay_and_claimgate() -> None:
    assert SMOKE_SEED_COUNT == 12
    assert RESEARCH_SEED_COUNT == 30
    assert StatisticalTestPolicy().tier_for_n(12) == "exploratory_only"
    assert StatisticalTestPolicy().tier_for_n(30) == "research_grade_benchmark_candidate"
    campaign = run_hard_experiment_01()
    first = campaign.seed_records[0].source_bias_on
    replay_spec = build_hard_experiment_01_spec(seed=first.seed, arm="source_bias_on")
    replay_result = GenesisEngine.from_spec(replay_spec).run_ticks()
    assert len(campaign.seeds) == 12
    assert campaign.seeds == tuple(range(11, 23))
    assert campaign.claim_ceiling == CLAIM_CEILING
    assert campaign.replay_matched is True
    assert campaign.replay_verified_seeds == (campaign.seeds[0], campaign.seeds[-1])
    assert {item.arm for item in campaign.replay_records} == set(ARMS)
    assert {item.seed for item in campaign.replay_records} == {
        campaign.seeds[0],
        campaign.seeds[-1],
    }
    assert len(campaign.replay_records) == 10
    assert all(item.matched for item in campaign.replay_records)
    last = campaign.seed_records[-1]
    last_replay_spec = build_hard_experiment_01_spec(seed=last.seed, arm="capsules_off")
    last_replay_result = GenesisEngine.from_spec(last_replay_spec).run_ticks()
    assert last_replay_spec.digest() == last.capsules_off.spec_digest
    assert last_replay_result.snapshot.digest() == last.capsules_off.result_digest
    shuffled_replay_spec = build_hard_experiment_01_spec(seed=last.seed, arm="capsules_shuffled")
    shuffled_replay_result = GenesisEngine.from_spec(shuffled_replay_spec).run_ticks()
    assert shuffled_replay_spec.digest() == last.capsules_shuffled.spec_digest
    assert shuffled_replay_result.snapshot.digest() == last.capsules_shuffled.result_digest
    assert replay_spec.digest() == first.spec_digest
    assert replay_result.snapshot.digest() == first.result_digest
    assert campaign.to_dict()["collective_intelligence"] is False
    assert campaign.to_dict()["intelligence"] is False
    assert campaign.to_dict()["agi"] is False
    assert campaign.to_dict()["tokyo_type1_passed"] is False
    assert campaign.to_dict()["avida_replacement"] is False
    assert campaign.to_dict()["claim_gate_flags_auto_set"] is False
    assert campaign.to_dict()["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert dict(campaign.missing_outcomes_per_arm) == {arm: 0 for arm in ARMS}
    assert all(
        arm.outcome_missing is False
        for item in campaign.seed_records
        for arm in (
            item.source_bias_on,
            item.source_bias_off,
            item.capsules_off,
            item.capsules_shuffled,
        )
    )
    sample_arm = campaign.seed_records[0].source_bias_on.to_dict()
    assert "capsule_emissions" not in sample_arm
    assert {
        "capsule_source_count",
        "capsule_utility_count",
        "capsule_transfer_count",
        "capsule_adoptions",
    } <= set(sample_arm)
    assert len(campaign.interventions) == 5
    assert {item.arm for item in campaign.interventions} == set(ARMS)
    assert campaign.to_dict()["interventions"][1]["role"] == "mechanism_ablation"
    assert all(
        item.source_bias_on.spec_digest != item.capsules_off.spec_digest
        for item in campaign.seed_records
    )
    assert all(
        item.source_bias_on.spec_digest != item.source_bias_off.spec_digest
        for item in campaign.seed_records
    )
    assert all(
        item.source_bias_on.spec_digest != item.capsules_shuffled.spec_digest
        for item in campaign.seed_records
    )
    for contrast in campaign.paired_contrasts:
        if contrast.ci_low is not None and contrast.ci_high is not None:
            includes_zero = contrast.ci_low <= 0.0 <= contrast.ci_high
            assert contrast.claim_downgraded is includes_zero or contrast.paired_result is None
    decision = evaluate_hard_experiment_01_claim(campaign)
    assert decision.allowed is True
    assert decision.final_claim == CLAIM_CEILING
    gate = ScientificClaimGate()
    payload = campaign.to_dict()
    assert gate.decide(ClaimRequest("runtime_observation", payload)).allowed is True
    assert gate.decide(ClaimRequest("collective_intelligence", payload)).allowed is False
    assert gate.decide(ClaimRequest("intelligence", payload)).allowed is False
    assert gate.decide(ClaimRequest("agi", payload)).allowed is False
    assert gate.decide(ClaimRequest("tokyo_type1_passed", payload)).allowed is False
    assert gate.decide(ClaimRequest("avida_replacement", payload)).allowed is False
    assert gate.decide(
        ClaimRequest(INTERVENTION_CLAIM, {name: True for name in INTERVENTION_SUPPORTED_FLAGS})
    ).allowed is True
    summary = format_hard_experiment_01_summary(campaign)
    assert "claim_ceiling runtime_observation" in summary
    assert "collective_intelligence False" in summary
    assert "capsules_shuffled" in summary
    assert campaign.statistical_tier == "exploratory_only"


def test_capsule_counts_are_recorded_separately() -> None:
    class _Result:
        capsule_source_fitness_records = (object(), object())
        capsule_utility_records = (object(),)
        capsule_transfer_metrics = (object(), object(), object())
        capsule_adoption_records = (object(), object(), object(), object())

    sources, utilities, transfers, adoptions = _capsule_counts(_Result())
    assert (sources, utilities, transfers, adoptions) == (2, 1, 3, 4)
    # The old helper used max(sources, utilities, transfers) as "emissions".
    assert sources != utilities
    assert max(sources, utilities, transfers) == 3


def test_mean_last_tick_fitness_is_none_when_tick_missing() -> None:
    class _EmptyResult:
        ticks = ()

    class _TickWithoutGeneration:
        generation_result = None

    class _ResultWithoutGeneration:
        ticks = (_TickWithoutGeneration(),)

    class _EmptyFitness:
        fitness = ()

    class _GenerationWithoutScores:
        selection_mean_fitness = None
        population = _EmptyFitness()

    class _ResultWithoutScores:
        ticks = (type("Tick", (), {"generation_result": _GenerationWithoutScores()})(),)

    assert _mean_last_tick_fitness(_EmptyResult()) is None
    assert _mean_last_tick_fitness(_ResultWithoutGeneration()) is None
    assert _mean_last_tick_fitness(_ResultWithoutScores()) is None


def test_arm_record_marks_missing_outcome_without_zero_fill() -> None:
    record = HardExperiment01ArmRecord(
        seed=11,
        arm="capsules_off",
        terminal_mean_fitness=None,
        births=0,
        capsule_source_count=0,
        capsule_utility_count=0,
        capsule_transfer_count=0,
        capsule_adoptions=0,
        spec_digest="a" * 64,
        result_digest="b" * 64,
        next_generation_observed=False,
        outcome_missing=True,
    )
    assert record.outcome_missing is True
    assert record.terminal_mean_fitness is None
    assert record.to_dict()["outcome_missing"] is True


def _arm(
    seed: int,
    arm: str,
    fitness: float | None,
    *,
    missing: bool,
) -> HardExperiment01ArmRecord:
    return HardExperiment01ArmRecord(
        seed=seed,
        arm=arm,  # type: ignore[arg-type]
        terminal_mean_fitness=fitness,
        births=0,
        capsule_source_count=0,
        capsule_utility_count=0,
        capsule_transfer_count=0,
        capsule_adoptions=0,
        spec_digest="a" * 64,
        result_digest="b" * 64,
        next_generation_observed=False,
        outcome_missing=missing,
    )


def test_missing_arm_is_dropped_from_paired_analysis() -> None:
    complete = HardExperiment01SeedRecord(
        seed=11,
        source_bias_on=_arm(11, "source_bias_on", 2.0, missing=False),
        source_bias_off=_arm(11, "source_bias_off", 1.0, missing=False),
        capsules_off=_arm(11, "capsules_off", 0.5, missing=False),
        capsules_shuffled=_arm(11, "capsules_shuffled", 0.6, missing=False),
        delta_vs_source_bias_off=1.0,
        delta_vs_capsules_off=1.5,
        delta_vs_capsules_shuffled=1.4,
    )
    incomplete = HardExperiment01SeedRecord(
        seed=12,
        source_bias_on=_arm(12, "source_bias_on", None, missing=True),
        source_bias_off=_arm(12, "source_bias_off", 1.0, missing=False),
        capsules_off=_arm(12, "capsules_off", 0.5, missing=False),
        capsules_shuffled=_arm(12, "capsules_shuffled", 0.6, missing=False),
        delta_vs_source_bias_off=None,
        delta_vs_capsules_off=None,
        delta_vs_capsules_shuffled=None,
    )
    baseline, treatment = _complete_pair_values(
        (complete, incomplete),
        treatment_arm="source_bias_on",
        baseline_arm="source_bias_off",
    )
    assert baseline == [1.0]
    assert treatment == [2.0]
    assert _missing_outcomes_per_arm((complete, incomplete)) == (
        ("source_bias_on", 1),
        ("source_bias_off", 0),
        ("capsules_off", 0),
        ("capsules_shuffled", 0),
        ("oracle_capsule", 0),
    )


def test_assay_failed_when_treatment_extinctions_or_adoptions_uninterpretable() -> None:
    extinct = HardExperiment01ArmSummary(
        arm="source_bias_on",
        n=30,
        mean=0.0,
        sd=0.0,
        births_mean=2.0,
        extinction_rate=1.0,
        adoption_mean=0.0,
        missing=0,
    )
    living_silent = HardExperiment01ArmSummary(
        arm="source_bias_on",
        n=30,
        mean=1.0,
        sd=0.1,
        births_mean=2.0,
        extinction_rate=0.0,
        adoption_mean=0.0,
        missing=0,
    )
    living_active = HardExperiment01ArmSummary(
        arm="source_bias_on",
        n=30,
        mean=1.0,
        sd=0.1,
        births_mean=2.0,
        extinction_rate=0.0,
        adoption_mean=1.5,
        missing=0,
    )
    failed_extinct, reasons_extinct = evaluate_hard_experiment_01_assay((extinct,))
    failed_silent, reasons_silent = evaluate_hard_experiment_01_assay((living_silent,))
    failed_ok, reasons_ok = evaluate_hard_experiment_01_assay((living_active,))
    assert failed_extinct is True
    assert "assay_failed_treatment_extinction_near_one" in reasons_extinct
    assert "assay_failed_treatment_adoptions_near_zero" in reasons_extinct
    assert failed_silent is True
    assert reasons_silent == ("assay_failed_treatment_adoptions_near_zero",)
    assert failed_ok is False
    assert reasons_ok == ()
    v1_payload = {
        "arm": "source_bias_on",
        "adoption_mean": 0.0,
        "extinction_rate": 1.0,
    }
    failed_v1, reasons_v1 = evaluate_hard_experiment_01_assay((v1_payload,))
    assert failed_v1 is True
    assert "assay_failed_treatment_adoptions_near_zero" in reasons_v1
    assert "assay_failed_treatment_extinction_near_one" in reasons_v1
    failures = _decision_rule_failures(
        scale="research",
        statistical_tier="research_grade_benchmark_candidate",
        contrasts=(),
        shuffled_vs_off=None,
        dose_trend=None,
        replay_matched=True,
        assay_failures=reasons_v1,
    )
    assert "assay_failed_treatment_adoptions_near_zero" in failures
    assert "missing_primary_contrast" in failures


def test_calibration_smoke_treatment_arm_has_adoptions() -> None:
    spec = build_hard_experiment_01_spec(seed=11, arm="source_bias_on", tick_count=8, population=8)
    result = GenesisEngine.from_spec(spec).run_ticks()
    adoptions = len(tuple(getattr(result, "capsule_adoption_records", ()) or ()))
    diagnostic = diagnose_hard_experiment_01_run(
        seed=11, arm="source_bias_on", tick_count=8, population=8
    )
    assert spec.metadata["hard_experiment_01_calibration"]["wave"] == "1d_prime"
    assert hard_experiment_01_calibration_knobs()["life_loop_defaults_unchanged"] is True
    assert adoptions > 0
    assert diagnostic.total_adoptions > 0
    assert diagnostic.extinct is False
    assert diagnostic.final_population not in {None, 0}
    assert diagnostic.any_agent_reached_min_source_fitness is True
    off = build_hard_experiment_01_spec(seed=11, arm="capsules_off", tick_count=8, population=8)
    off_result = GenesisEngine.from_spec(off).run_ticks()
    assert len(tuple(getattr(off_result, "capsule_adoption_records", ()) or ())) == 0


def test_committed_research_results_match_prereg_and_ceiling() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "hard_experiment_01" / "results_v1.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["scale"] == "research"
    assert payload["seeds"] == list(range(11, 41))
    assert payload["tick_count"] == 40
    assert payload["population"] == 16
    assert payload["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert payload["claim_ceiling"] == CLAIM_CEILING
    assert payload["collective_intelligence"] is False
    assert payload["intelligence"] is False
    assert payload["replay_matched"] is True
    assert len(payload["paired_contrasts"]) == 3
    assert payload["multiple_comparison_audit"]["metric_count"] == 3
    assert payload["decision_rule_passed"] is False
    claims = (root / "CLAIMS.md").read_text(encoding="utf-8")
    assert "runtime_observation" in claims
    assert "HARD_EXPERIMENT_01 Wave 1" in claims
    start = claims.find("### 4.4")
    end = claims.find("## 5.")
    assert "proved collective intelligence" not in claims[start:end]


def test_committed_research_v2_exercises_source_bias_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "hard_experiment_01" / "results_v2.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["scale"] == "research"
    assert payload["seeds"] == list(range(11, 41))
    assert payload["tick_count"] == 40
    assert payload["population"] == 16
    assert payload["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert payload["claim_ceiling"] == CLAIM_CEILING
    assert payload["assay_failed"] is False
    assert payload["assay_failures"] == []
    assert payload["decision_rule_passed"] is False
    assert payload["replay_matched"] is True
    assert payload["collective_intelligence"] is False
    by_arm = {item["arm"]: item for item in payload["arm_summaries"]}
    assert by_arm["source_bias_on"]["adoption_mean"] > 0
    assert by_arm["source_bias_on"]["extinction_rate"] < 1.0
    assert by_arm["capsules_off"]["adoption_mean"] == 0.0


def test_wave_1c_manipulation_check_passes_at_smoke_scale() -> None:
    """The v2 defect: identical arms. Wave 1c/1d′ must exercise every DAG edge.

    SCHEMA v5 (Amd 03) restores every-cell food + population respawn draws, so
    the aggregate positive-control clause is expected to hold at smoke scale
    again. Edge-level manipulation checks below must still pass. (Amd 02 / v4
    sparse-food calibration failure remains historical.)
    """

    campaign = run_hard_experiment_01(seed_count=2, include_dose=True)
    by_arm = {item.arm: item for item in campaign.arm_summaries}
    assert set(by_arm) == set(ARMS)
    assert by_arm["source_bias_on"].bias_applied_mean > 0
    assert by_arm["source_bias_on"].rejected_by_source_fitness_mean > 0
    assert set(by_arm["source_bias_on"].bias_payload_totals) == {CALIBRATION_GOOD_PAYLOAD_ACTION}
    assert CALIBRATION_POOR_PAYLOAD_ACTION in by_arm["source_bias_off"].bias_payload_totals
    assert by_arm["capsules_off"].bias_applied_mean == 0.0
    assert by_arm["capsules_off"].adoption_mean == 0.0
    assert by_arm["capsules_shuffled"].adoption_mean > 0
    assert any(
        item.source_bias_on.result_digest != item.source_bias_off.result_digest
        for item in campaign.seed_records
    )
    # v2 defect must stay gone: treatment vs off are not bitwise-identical.
    assert any(
        item.source_bias_on.result_digest != item.capsules_off.result_digest
        for item in campaign.seed_records
    )
    # Assay may only fail the Amd 02 smoke-scale positive-control clause.
    if campaign.assay_failed:
        assert campaign.assay_failures == ("assay_failed_positive_control_did_not_move_outcome",)
    payload = campaign.to_dict()
    assert payload["primary_outcome"] == PRIMARY_OUTCOME
    assert payload["analysis_arms"] == list(ANALYSIS_ARMS)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["prereg_amendment_02_digest"] == hard_experiment_01_prereg_amendment_02_digest()
    assert payload["prereg_amendment_03_digest"] == hard_experiment_01_prereg_amendment_03_digest()
    assert payload["dose_trend"]["pattern"] == "step_up_then_saturate"
    first_on = campaign.seed_records[0].source_bias_on.to_dict()
    assert first_on["legacy_terminal_selection_fitness"] is not None


def test_wave_1c_engine_knobs_default_off_and_serialize_conditionally() -> None:
    from codontrace.genesis.capsule import CapsuleTransferConfig
    from codontrace.genesis.population import RuntimeResourcePolicy

    legacy = CapsuleTransferConfig(enabled=True)
    assert legacy.adoption_effect_action is False
    assert "adoption_effect_action" not in legacy.to_dict()
    coupled = CapsuleTransferConfig(enabled=True, adoption_effect_action=True)
    assert coupled.to_dict()["adoption_effect_action"] is True
    assert CapsuleTransferConfig.from_dict(coupled.to_dict()).digest() == coupled.digest()
    assert CapsuleTransferConfig.from_dict(legacy.to_dict()).digest() == legacy.digest()
    policy = RuntimeResourcePolicy(respawn_enabled=True, respawn_rate=1.0, max_resources=4)
    assert "respawn_under_organisms" not in policy.to_dict()
    renewable = RuntimeResourcePolicy(
        respawn_enabled=True,
        respawn_rate=1.0,
        max_resources=4,
        respawn_under_organisms=True,
        respawn_draws_per_tick=3,
    )
    assert RuntimeResourcePolicy.from_dict(renewable.to_dict()).digest() == renewable.digest()
    assert renewable.digest() != policy.digest()


def test_committed_research_v3_is_a_valid_assay() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "hard_experiment_01" / "results_v3.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "hard_experiment_01_v3"
    assert payload["scale"] == "research"
    assert payload["seeds"] == list(range(11, 41))
    assert payload["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["primary_outcome"] == PRIMARY_OUTCOME
    assert payload["assay_failed"] is False
    assert payload["assay_failures"] == []
    assert payload["replay_matched"] is True
    assert payload["collective_intelligence"] is False
    assert payload["claim_ceiling"] in {CLAIM_CEILING, INTERVENTION_CLAIM}
    if payload["claim_ceiling"] == INTERVENTION_CLAIM:
        assert payload["decision_rule_passed"] is True
        assert payload["claim_gate_allowed"] is True
    by_arm = {item["arm"]: item for item in payload["arm_summaries"]}
    assert by_arm["source_bias_on"]["rejected_by_source_fitness_mean"] > 0
    assert by_arm["capsules_off"]["adoption_mean"] == 0.0
    assert by_arm["oracle_capsule"]["mean"] > by_arm["capsules_off"]["mean"]



def test_wave_1d_prime_amendment_03_and_schema_v5() -> None:
    """Amendment 03 is hashed; Amd 01+02 digests stay frozen; SCHEMA is v5."""

    root = Path(__file__).resolve().parents[1]
    amd03 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md"
    assert amd03.is_file()
    expected03 = __import__("hashlib").sha256(amd03.read_bytes()).hexdigest()
    assert expected03 == "3a9d4fd441f71f5f60ef5b5b1496148ae4178a9126170765a76d712465b87058"
    assert hard_experiment_01_prereg_amendment_03_digest() == expected03
    # Amd 02 remains a hashed trail (historical failed calibration).
    amd02 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md"
    assert amd02.is_file()
    expected02 = __import__("hashlib").sha256(amd02.read_bytes()).hexdigest()
    assert hard_experiment_01_prereg_amendment_02_digest() == expected02
    assert expected02 == "14c111af81e415c8a381411a3520294e8bbdec311e4ffe3bc421d46992202f2f"
    assert (
        hard_experiment_01_prereg_amendment_digest()
        == "6d156e824b9b9c4d06be4eb6f4d35f265592eab7c41d35a6b8c0ca951dfc7de8"
    )
    assert hard_experiment_01_prereg_digest() == __import__("hashlib").sha256(
        (root / "docs" / "HARD_EXPERIMENT_01_PREREG.md").read_bytes()
    ).hexdigest()
    assert SCHEMA_VERSION == "hard_experiment_01_v5"
    protocol = hard_experiment_01_protocol_digest()
    assert len(protocol) == 64
    knobs = hard_experiment_01_calibration_knobs()
    assert knobs["wave"] == "1d_prime"
    assert knobs["role_layout"] == "seed_permuted_v3_multiset"
    assert knobs["food_layout"] == "every_cell"
    assert knobs["food_coverage"] == 1.0
    assert knobs["respawn_draws_per_tick"] == "max(1, population_size)"
    # In-memory smoke campaign payload must carry SCHEMA v5 + Amd 03 digest.
    campaign = run_hard_experiment_01(seed_count=2, include_dose=False)
    payload = campaign.to_dict()
    assert payload["schema_version"] == "hard_experiment_01_v5"
    assert payload["prereg_amendment_03_digest"] == expected03
    assert payload["prereg_amendment_02_digest"] == expected02
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["role_layout"] == "seed_permuted_v3_multiset"
    assert payload["food_layout"] == "every_cell"
    assert payload["respawn_draws_per_tick"] == "max(1, population_size)"
    assert campaign.protocol_digest == hard_experiment_01_protocol_digest()


def test_wave_1d_seed_permuted_roles_preserve_multiset() -> None:
    from collections import Counter

    n = 8
    base = tuple(calibration_role_for_index(i) for i in range(n))
    roles_a = permute_roles_for_seed(1000, n)
    roles_b = permute_roles_for_seed(1001, n)
    roles_a_again = permute_roles_for_seed(1000, n)
    assert Counter(roles_a) == Counter(base)
    assert Counter(roles_b) == Counter(base)
    assert roles_a == roles_a_again
    assert roles_a != roles_b
    oracle_a = permute_roles_for_seed(1000, n, oracle=True)
    oracle_base = tuple(calibration_role_for_index(i, oracle=True) for i in range(n))
    assert Counter(oracle_a) == Counter(oracle_base)
    assert "poor_emitter" not in oracle_a
    spec_a = build_hard_experiment_01_spec(seed=1000, arm="source_bias_on", tick_count=8, population=8)
    spec_b = build_hard_experiment_01_spec(seed=1001, arm="source_bias_on", tick_count=8, population=8)
    spec_a2 = build_hard_experiment_01_spec(seed=1000, arm="source_bias_on", tick_count=8, population=8)
    assert spec_a.metadata["genome_roles"] == list(roles_a)
    assert spec_b.metadata["genome_roles"] == list(roles_b)
    assert spec_a.metadata["genome_roles"] == spec_a2.metadata["genome_roles"]
    assert spec_a.metadata["genome_roles"] != spec_b.metadata["genome_roles"]


def test_wave_1d_prime_every_cell_food_and_population_respawn_draws() -> None:
    """SCHEMA v5: every-cell food (Amd 01/v3); respawn draws = population.

    v4 Amd 02 sparse [0.5, 0.8] + pop//4 remains historical failed calibration.
    """

    spec_a = build_hard_experiment_01_spec(seed=1000, arm="source_bias_on", tick_count=8, population=8)
    spec_b = build_hard_experiment_01_spec(seed=1001, arm="source_bias_on", tick_count=8, population=8)
    spec_a2 = build_hard_experiment_01_spec(seed=1000, arm="source_bias_on", tick_count=8, population=8)
    cells_a = [tuple(item) for item in spec_a.metadata["food_cells"]]
    cells_b = [tuple(item) for item in spec_b.metadata["food_cells"]]
    cells_a2 = [tuple(item) for item in spec_a2.metadata["food_cells"]]
    n = int(spec_a.world_width) * int(spec_a.world_height)
    coverage_a = float(spec_a.metadata["food_coverage"])
    coverage_b = float(spec_b.metadata["food_coverage"])
    assert coverage_a == 1.0
    assert coverage_b == 1.0
    assert len(cells_a) == n
    assert len(cells_b) == n
    assert abs(coverage_a - len(cells_a) / n) < 1e-12
    assert abs(coverage_b - len(cells_b) / n) < 1e-12
    assert spec_a.metadata["initial_food_patches"] == len(cells_a)
    assert cells_a == cells_a2
    # Placement ignores seed: identical across seeds under every-cell layout.
    assert cells_a == cells_b
    policy = spec_a.population_configs.runtime_resource_policy
    assert policy.respawn_draws_per_tick == max(1, 8)  # smoke 8→8
    assert policy.respawn_draws_per_tick == 8
    research = build_hard_experiment_01_spec(
        seed=1000, arm="source_bias_on", tick_count=40, population=16
    )
    assert research.population_configs.runtime_resource_policy.respawn_draws_per_tick == 16
    assert float(research.metadata["food_coverage"]) == 1.0


def test_hard_experiment_01_docs_and_example_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "HARD_EXPERIMENT_01.md").is_file()
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG.md").is_file()
    assert (root / "docs" / "ENGINE_REPLAY_CONTRACT.md").is_file()
    assert (root / "docs" / "PHASE_INDEX.md").is_file()
    assert (root / "STYLE.md").is_file()
    assert (root / "CONTRIBUTING.md").is_file()
    assert (root / "examples" / "genesis_hard_experiment_01.py").is_file()
    text = (root / "docs" / "HARD_EXPERIMENT_01.md").read_text(encoding="utf-8")
    assert "runtime_observation" in text
    assert "collective_intelligence" in text
    assert "mechanism ablation" in text
    assert "capsules_shuffled" in text
    assert "Okasha" in text
    assert "Results (research v1)" in text
    assert "Limitations / Diagnostics" in text
    assert "assay_failed" in text
    assert "Results (research v2)" in text
    assert "Results (research v3)" in text
    assert "claim_downgraded" in text
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md").is_file()
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md").is_file()
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md").is_file()
    assert not text.lstrip().startswith("# Phase")
    style = (root / "STYLE.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "CodonTrace Genesis" in style
    assert "naming-order" in style
    assert "Always name the product" not in readme
    assert "eat, survive, and reproduce" in readme
    version = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.3.0b4.dev0"' in version


def test_probe_junk_is_not_in_the_tree() -> None:
    root = Path(__file__).resolve().parents[1]
    junk = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and (
            path.name.startswith(".grok_write_probe")
            or (path.name.startswith(".size_test_") and path.suffix == ".txt")
            or "_FULL_RESTORE" in path.name
            or "_backup" in path.name
            or path.suffix == ".orig"
        )
    ]
    assert junk == []
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert ".grok_write_probe" in gitignore
    assert ".size_test_" in gitignore
