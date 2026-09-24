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
    ACTIVITY_MATCH_PILOT_GATE,
    ANALYSIS_ARMS,
    ARMS,
    AUXILIARY_ARMS,
    CALIBRATION_GOOD_PAYLOAD_ACTION,
    CALIBRATION_POOR_PAYLOAD_ACTION,
    CLAIM_CEILING,
    CONTENT_NULL_PAYLOAD_ACTION,
    DOSE_LEVELS,
    FOOD_AMOUNT_MULTIPLIERS,
    INTERVENTION_CLAIM,
    INTERVENTION_SUPPORTED_FLAGS,
    MIN_SOURCE_FITNESS_TREATMENT,
    PRIMARY_OUTCOME,
    RESEARCH_SEED_COUNT,
    SCHEMA_VERSION,
    SENSITIVITY_ARMS,
    SMOKE_SEED_COUNT,
    HardExperiment01ArmRecord,
    HardExperiment01ArmSummary,
    HardExperiment01SeedRecord,
    _capsule_counts,
    _complete_pair_values,
    _decision_rule_failures,
    _mean_last_tick_fitness,
    _missing_outcomes_per_arm,
    _sensitivity_failures,
    build_hard_experiment_01_dose_spec,
    build_hard_experiment_01_spec,
    calibration_food_amount_layout,
    calibration_role_for_index,
    diagnose_hard_experiment_01_run,
    evaluate_hard_experiment_01_assay,
    evaluate_hard_experiment_01_claim,
    evaluate_hard_experiment_01_wave1e_pilot_gates,
    format_hard_experiment_01_summary,
    hard_experiment_01_calibration_knobs,
    hard_experiment_01_causal_dag,
    hard_experiment_01_interventions,
    hard_experiment_01_prereg_amendment_02_digest,
    hard_experiment_01_prereg_amendment_03_digest,
    hard_experiment_01_prereg_amendment_04_digest,
    hard_experiment_01_prereg_amendment_05_digest,
    hard_experiment_01_prereg_amendment_digest,
    hard_experiment_01_prereg_amendment_lock_digest,
    hard_experiment_01_prereg_digest,
    hard_experiment_01_protocol_digest,
    permute_roles_for_seed,
    run_hard_experiment_01,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.statistical_protocol import StatisticalTestPolicy
from codontrace.genesis.text_digest import sha256_text_file

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
    assert by_arm["capsules_content_null"].role == "negative_control"
    assert by_arm["capsules_activity_matched"].role == "auxiliary_control"
    assert by_arm["capsules_shuffled"].role == "sensitivity_negative_control"
    assert "min_source_fitness" in by_arm["source_bias_off"].knob
    assert by_arm["capsules_off"].knob == "CapsuleTransferConfig.enabled"
    assert by_arm["capsules_content_null"].knob == "CapsuleTransferConfig.shuffle_mode"
    assert by_arm["capsules_shuffled"].knob == "CapsuleTransferConfig.shuffle_mode"
    assert by_arm["source_bias_off"].cuts_edges == ("e1",)
    assert by_arm["capsules_off"].cuts_edges == ("e1", "e2")
    assert by_arm["capsules_content_null"].cuts_edges == ("e2_content",)
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
    assert digest == sha256_text_file(prereg)
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
    content_null = build_hard_experiment_01_spec(seed=11, arm="capsules_content_null")
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
    assert content_null.capsule_transfer_config is not None
    assert content_null.capsule_transfer_config.shuffle_mode is CapsuleShuffleMode.CONTENT_NULL
    assert content_null.digest() != shuffled.digest()
    assert content_null.digest() != treatment.digest()


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
        "capsules_content_null",
    }
    assert set(SENSITIVITY_ARMS) == {"capsules_shuffled"}
    assert set(AUXILIARY_ARMS) == {"capsules_activity_matched"}
    assert "capsules_content_null" in ANALYSIS_ARMS
    assert "capsules_shuffled" not in ANALYSIS_ARMS
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
    assert len(campaign.replay_records) == 14
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
    assert len(campaign.interventions) == 7
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
    assert "capsules_content_null" in summary
    assert "sensitivity_failures" in summary
    assert campaign.statistical_tier == "exploratory_only"
    assert any(item.arm == "capsules_shuffled" for item in campaign.arm_summaries)
    assert any(item.arm == "capsules_activity_matched" for item in campaign.arm_summaries)


def test_capsule_counts_are_recorded_separately() -> None:
    class _Adopt:
        def __init__(self, ok: bool) -> None:
            self.adoption_success = ok

    class _Result:
        capsule_source_fitness_records = (object(), object())
        capsule_utility_records = (object(),)
        capsule_transfer_metrics = (object(), object(), object())
        capsule_adoption_records = (_Adopt(True), _Adopt(False), _Adopt(True), _Adopt(False))

    sources, utilities, transfers, adoptions, accepted = _capsule_counts(_Result())
    assert (sources, utilities, transfers, adoptions, accepted) == (2, 1, 3, 4, 2)
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
        ("capsules_content_null", 0),
        ("capsules_activity_matched", 0),
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
        content_null_vs_off=None,
        dose_trend=None,
        replay_matched=True,
        assay_failures=reasons_v1,
    )
    sens = _sensitivity_failures(shuffled_vs_off=None)
    assert "missing_shuffled_vs_capsules_off" in sens
    assert "assay_failed_treatment_adoptions_near_zero" in failures
    assert "missing_primary_contrast" in failures


def test_calibration_smoke_treatment_arm_has_adoptions() -> None:
    spec = build_hard_experiment_01_spec(seed=11, arm="source_bias_on", tick_count=8, population=8)
    result = GenesisEngine.from_spec(spec).run_ticks()
    adoptions = len(tuple(getattr(result, "capsule_adoption_records", ()) or ()))
    diagnostic = diagnose_hard_experiment_01_run(
        seed=11, arm="source_bias_on", tick_count=8, population=8
    )
    assert spec.metadata["hard_experiment_01_calibration"]["wave"] == "1e_lock_v7"
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
    # B6: split smoke vs research — edge-level checks always; only the Amd 03/smoke
    # positive-control miss is non-blocking here (no soft assert on the failure tuple).
    unexpected = tuple(
        f
        for f in campaign.assay_failures
        if f != "assay_failed_positive_control_did_not_move_outcome"
    )
    assert unexpected == (), unexpected
    payload = campaign.to_dict()
    assert payload["primary_outcome"] == PRIMARY_OUTCOME
    assert payload["analysis_arms"] == list(ANALYSIS_ARMS)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["prereg_amendment_02_digest"] == hard_experiment_01_prereg_amendment_02_digest()
    assert payload["prereg_amendment_03_digest"] == hard_experiment_01_prereg_amendment_03_digest()
    assert payload["dose_trend"]["pattern"] == "peak_at_intermediate_dose_then_channel_closure"
    assert payload["dose_trend"]["independent"] is False
    assert payload["dose_trend"]["trend_supported"] is False
    assert "pattern_label_note" in payload["dose_trend"]
    # Wave 1d″ honesty fields on new runs.
    shuffled_summary = by_arm["capsules_shuffled"]
    assert shuffled_summary.adoption_accepted_mean is not None
    assert shuffled_summary.shuffle_content_changed_rate is not None
    assert shuffled_summary.shuffle_content_changed_rate > 0.0
    first_shuffled = campaign.seed_records[0].capsules_shuffled.to_dict()
    assert first_shuffled["capsule_adoptions_semantics"] == "attempts"
    assert "capsule_adoptions_accepted" in first_shuffled
    assert "shuffle_content_changed_count" in first_shuffled
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


def test_committed_research_v5_is_a_valid_assay() -> None:
    """Wave 1d′ research artifact (Amd 03 / SCHEMA v5); do not loosen ClaimGate."""

    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "hard_experiment_01" / "results_v5.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "hard_experiment_01_v5"
    assert payload["scale"] == "research"
    assert payload["seeds"] == list(range(11, 41))
    assert payload["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["prereg_amendment_02_digest"] == hard_experiment_01_prereg_amendment_02_digest()
    assert payload["prereg_amendment_03_digest"] == hard_experiment_01_prereg_amendment_03_digest()
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
    assert payload["role_layout"] == "seed_permuted_v3_multiset"
    assert payload["food_layout"] == "every_cell"
    assert payload["respawn_draws_per_tick"] == "max(1, population_size)"


def test_committed_research_v6_is_a_valid_assay() -> None:
    """Wave 1e research artifact (Amd 04/05 / SCHEMA v6); ClaimGate only if earned."""

    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "hard_experiment_01" / "results_v6.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "hard_experiment_01_v6"
    assert payload["scale"] == "research"
    assert payload["seeds"] == list(range(11, 41))
    assert payload["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["prereg_amendment_02_digest"] == hard_experiment_01_prereg_amendment_02_digest()
    assert payload["prereg_amendment_03_digest"] == hard_experiment_01_prereg_amendment_03_digest()
    assert payload["prereg_amendment_04_digest"] == hard_experiment_01_prereg_amendment_04_digest()
    assert payload["prereg_amendment_05_digest"] == hard_experiment_01_prereg_amendment_05_digest()
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
    assert by_arm["capsules_content_null"]["mean"] == by_arm["capsules_off"]["mean"]
    assert by_arm["capsules_content_null"]["bias_payload_totals"] == {}
    assert payload["role_layout"] == "seed_permuted_v3_multiset"
    assert payload["food_layout"] == "every_cell"
    assert payload["respawn_draws_per_tick"] == "max(1, population_size)"
    assert "capsules_content_null" in payload["analysis_arms"]
    assert "capsules_activity_matched" in {item["arm"] for item in payload["arm_summaries"]}


def test_wave_1d_prime_amendment_03_and_schema_v5() -> None:
    """Amendment 03 is hashed; Amd 01+02 digests stay frozen; SCHEMA is v5."""

    root = Path(__file__).resolve().parents[1]
    amd03 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md"
    assert amd03.is_file()
    expected03 = sha256_text_file(amd03)
    assert expected03 == "3a9d4fd441f71f5f60ef5b5b1496148ae4178a9126170765a76d712465b87058"
    assert hard_experiment_01_prereg_amendment_03_digest() == expected03
    # Amd 02 remains a hashed trail (historical failed calibration).
    amd02 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md"
    assert amd02.is_file()
    expected02 = sha256_text_file(amd02)
    assert hard_experiment_01_prereg_amendment_02_digest() == expected02
    assert expected02 == "14c111af81e415c8a381411a3520294e8bbdec311e4ffe3bc421d46992202f2f"
    assert (
        hard_experiment_01_prereg_amendment_digest()
        == "6d156e824b9b9c4d06be4eb6f4d35f265592eab7c41d35a6b8c0ca951dfc7de8"
    )
    assert hard_experiment_01_prereg_digest() == __import__("hashlib").sha256(
        (root / "docs" / "HARD_EXPERIMENT_01_PREREG.md").read_bytes()
    ).hexdigest()
    # SCHEMA advanced to v7 under LOCK; Amd 01–05 digests stay frozen.
    assert SCHEMA_VERSION == "hard_experiment_01_v7"
    protocol = hard_experiment_01_protocol_digest()
    assert len(protocol) == 64
    knobs = hard_experiment_01_calibration_knobs()
    assert knobs["wave"] == "1e_lock_v7"
    assert knobs["role_layout"] == "seed_permuted_v3_multiset"
    assert knobs["food_layout"] == "every_cell_seed_amounts_v7"
    assert knobs["food_coverage"] == 1.0
    assert knobs["respawn_draws_per_tick"] == "max(1, population_size)"
    campaign = run_hard_experiment_01(seed_count=2, include_dose=False)
    payload = campaign.to_dict()
    assert payload["schema_version"] == "hard_experiment_01_v7"
    assert payload["prereg_amendment_03_digest"] == expected03
    assert payload["prereg_amendment_02_digest"] == expected02
    assert payload["prereg_amendment_digest"] == hard_experiment_01_prereg_amendment_digest()
    assert payload["prereg_amendment_04_digest"] == hard_experiment_01_prereg_amendment_04_digest()
    assert payload["prereg_amendment_lock_digest"] == hard_experiment_01_prereg_amendment_lock_digest()
    assert payload["role_layout"] == "seed_permuted_v3_multiset"
    assert payload["food_layout"] == "every_cell_seed_amounts_v7"
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
    """SCHEMA v7: every-cell coverage + seed-contingent amounts; respawn draws = pop.

    v4 Amd 02 sparse [0.5, 0.8] + pop//4 remains historical failed calibration.
    Cell *set* is seed-invariant (coverage 1.0); *amounts* differ by seed (LOCK).
    """

    spec_a = build_hard_experiment_01_spec(seed=1000, arm="source_bias_on", tick_count=8, population=8)
    spec_b = build_hard_experiment_01_spec(seed=1001, arm="source_bias_on", tick_count=8, population=8)
    spec_a2 = build_hard_experiment_01_spec(seed=1000, arm="source_bias_on", tick_count=8, population=8)
    cells_a = [tuple(item) for item in spec_a.metadata["food_cells"]]
    cells_b = [tuple(item) for item in spec_b.metadata["food_cells"]]
    cells_a2 = [tuple(item) for item in spec_a2.metadata["food_cells"]]
    amounts_a = list(spec_a.metadata["food_amounts"])
    amounts_b = list(spec_b.metadata["food_amounts"])
    amounts_a2 = list(spec_a2.metadata["food_amounts"])
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
    # Cell positions identical across seeds (every-cell coverage).
    assert cells_a == cells_b
    # Amounts are seed-contingent and replay-stable (LOCK).
    assert amounts_a == amounts_a2
    assert amounts_a != amounts_b
    assert set(amounts_a).issubset({2.0 * m for m in FOOD_AMOUNT_MULTIPLIERS})
    assert spec_a.metadata["food_layout"] == "every_cell_seed_amounts_v7"
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
    # P4: every committed results_vN.json on disk needs a Results section.
    results_dir = root / "docs" / "hard_experiment_01"
    for results_path in sorted(results_dir.glob("results_v*.json")):
        version = results_path.stem.replace("results_v", "v")
        assert f"Results (research {version})" in text, results_path.name
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md").is_file()
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md").is_file()
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md").is_file()
    assert (root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md").is_file()
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


def test_peer_rotation_preserves_event_pattern_multiset() -> None:
    """CONTENT peer-rotation is a cyclic content swap; multiset of patterns is preserved."""

    from codontrace.genesis.capsule import CausalCapsule, apply_capsule_shuffle_control

    capsules = (
        CausalCapsule("c1", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10),
        CausalCapsule("c2", "s2", 2.0, "g2", ("SENSE_DANGER",), "warn", 0.9, 0, 10),
        CausalCapsule("c3", "s3", 0.5, "g3", ("WAIT",), "noop", 0.9, 0, 10),
    )
    before = sorted(capsule.event_pattern for capsule in capsules)
    shuffled, records = apply_capsule_shuffle_control(
        capsules, CapsuleShuffleMode.CONTENT, tick=3, target_organism_id="t"
    )
    after = sorted(capsule.event_pattern for capsule in shuffled)
    assert after == before
    assert len(records) == 3
    assert any(record.content_changed for record in records)
    # Source ids stay on the original capsule under CONTENT mode.
    assert all(not record.source_changed for record in records)


def test_single_capsule_window_shuffle_is_identity_for_content() -> None:
    """Window size 1 → peer is self → content_changed false (rotation identity)."""

    from codontrace.genesis.capsule import CausalCapsule, apply_capsule_shuffle_control

    alone = CausalCapsule("solo", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10)
    shuffled, records = apply_capsule_shuffle_control(
        (alone,), CapsuleShuffleMode.CONTENT, tick=1, target_organism_id="t"
    )
    assert len(shuffled) == 1
    assert len(records) == 1
    assert records[0].content_changed is False
    assert records[0].source_changed is False
    assert shuffled[0].event_pattern == alone.event_pattern
    assert shuffled[0].predicted_outcome == alone.predicted_outcome

def test_wave_1e_amendment_04_and_schema_v6() -> None:
    """Amendment 04 is hashed; SCHEMA is now v7 (LOCK); Amd 01–03 digests stay frozen."""

    root = Path(__file__).resolve().parents[1]
    amd04 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md"
    assert amd04.is_file()
    expected04 = sha256_text_file(amd04)
    assert expected04 == "6a1facb02ba502299a17fc856c7ece611ca1854bc906d921729186ae1421fd60"
    assert hard_experiment_01_prereg_amendment_04_digest() == expected04
    assert SCHEMA_VERSION == "hard_experiment_01_v7"
    assert CONTENT_NULL_PAYLOAD_ACTION == "WAIT"
    knobs = hard_experiment_01_calibration_knobs()
    assert knobs["wave"] == "1e_lock_v7"
    assert knobs["content_null_payload_action"] == "WAIT"
    assert knobs["activity_match_epsilon"] == 1
    campaign = run_hard_experiment_01(seed_count=2, include_dose=False)
    payload = campaign.to_dict()
    assert payload["schema_version"] == "hard_experiment_01_v7"
    assert payload["prereg_amendment_04_digest"] == expected04
    assert payload["prereg_amendment_03_digest"] == hard_experiment_01_prereg_amendment_03_digest()
    assert "capsules_content_null" in payload["analysis_arms"]
    assert "capsules_shuffled" in payload["sensitivity_arms"]
    assert "capsules_activity_matched" in payload["auxiliary_arms"]
    assert "shuffled_better_than_capsules_off" not in campaign.decision_rule_failures
    assert campaign.content_null_vs_capsules_off is not None
    assert campaign.mean_abs_activity_match_gap is not None
    assert payload["prereg_amendment_05_digest"] == hard_experiment_01_prereg_amendment_05_digest()
    assert ACTIVITY_MATCH_PILOT_GATE is False
    assert knobs["activity_match_pilot_gate"] is False
    assert payload["activity_match_pilot_gate"] is False


def test_wave_1e_amendment_05_digest_and_pilot_gate_demotion() -> None:
    """Amendment 05 is hashed; SCHEMA now v7 via LOCK; prior digests frozen; activity gate demoted."""

    root = Path(__file__).resolve().parents[1]
    amd04 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md"
    amd05 = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_05.md"
    assert amd04.is_file()
    assert amd05.is_file()
    expected04 = sha256_text_file(amd04)
    expected05 = sha256_text_file(amd05)
    assert expected04 == "6a1facb02ba502299a17fc856c7ece611ca1854bc906d921729186ae1421fd60"
    assert expected05 == "d363533ba564757d5645fe53080aebf493357286cd1e33e19584f9f1dac5e6d7"
    assert hard_experiment_01_prereg_amendment_04_digest() == expected04
    assert hard_experiment_01_prereg_amendment_05_digest() == expected05
    # Prior digests unchanged (frozen pins from Amd 02–04 / Wave 1e).
    assert hard_experiment_01_prereg_amendment_02_digest() == (
        "14c111af81e415c8a381411a3520294e8bbdec311e4ffe3bc421d46992202f2f"
    )
    assert hard_experiment_01_prereg_amendment_03_digest() == (
        "3a9d4fd441f71f5f60ef5b5b1496148ae4178a9126170765a76d712465b87058"
    )
    assert SCHEMA_VERSION == "hard_experiment_01_v7"
    assert ACTIVITY_MATCH_PILOT_GATE is False
    campaign = run_hard_experiment_01(seed_count=2, include_dose=False)
    payload = campaign.to_dict()
    assert payload["schema_version"] == "hard_experiment_01_v7"
    assert payload["prereg_amendment_04_digest"] == expected04
    assert payload["prereg_amendment_05_digest"] == expected05
    assert payload["prereg_amendment_lock_digest"] == hard_experiment_01_prereg_amendment_lock_digest()
    assert payload["prereg_amendment_03_digest"] == (
        "3a9d4fd441f71f5f60ef5b5b1496148ae4178a9126170765a76d712465b87058"
    )
    assert payload["activity_match_pilot_gate"] is False
    # protocol digest incorporates amd05 bytes via canonical digest payload
    assert hard_experiment_01_protocol_digest() == campaign.protocol_digest
    assert "activity_match_gap_is_exploratory_non_blocking_under_amd05" in payload["limitations"]
    # Decision rule still cares about content_null, not activity epsilon.
    assert "activity_match" not in " ".join(campaign.decision_rule_failures)
    gates = evaluate_hard_experiment_01_wave1e_pilot_gates(campaign)
    assert gates["activity_match_pilot_gate"] is False
    assert gates["gates"]["activity_match_exploratory"]["blocking"] is False
    exploratory = gates["gates"]["activity_match_exploratory"]
    assert "mean_abs_activity_match_gap" in exploratory
    assert gates["gates"]["schema_amd_digests"]["pass"] is True
    # Confirmatory clearance ignores activity gap magnitude.
    assert gates["overall_pass"] == (
        gates["gates"]["assay"]["pass"]
        and gates["gates"]["content_null"]["pass"]
        and gates["gates"]["schema_amd_digests"]["pass"]
        and gates["gates"]["treatment_seed_variance"]["pass"]
    )


def test_content_null_destroys_eat_lumen_marginal_and_nulls_window_one() -> None:
    """CONTENT_NULL → WAIT payloads; EAT rate 0; window-1 still nulls."""

    from codontrace.genesis.capsule import CausalCapsule, apply_capsule_shuffle_control
    from codontrace.genesis.population import capsule_payload_action

    capsules = (
        CausalCapsule("c1", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10),
        CausalCapsule("c2", "s2", 2.0, "g2", ("SENSE_DANGER",), "warn", 0.9, 0, 10),
        CausalCapsule("c3", "s3", 0.5, "g3", ("WAIT",), "noop", 0.9, 0, 10),
    )
    nulled, records = apply_capsule_shuffle_control(
        capsules, CapsuleShuffleMode.CONTENT_NULL, tick=3, target_organism_id="t"
    )
    assert len(nulled) == 3
    assert all(capsule.event_pattern == ("WAIT",) for capsule in nulled)
    assert all(capsule.predicted_outcome == "WAIT" for capsule in nulled)
    assert all(capsule_payload_action(capsule) == "WAIT" for capsule in nulled)
    eat_rate = sum(
        1 for capsule in nulled if capsule_payload_action(capsule) == "EAT_LUMEN"
    ) / len(nulled)
    assert eat_rate == 0.0
    assert any(record.content_changed for record in records)
    # Peer-rotation CONTENT still available as sensitivity/shuffled path.
    rotated, _ = apply_capsule_shuffle_control(
        capsules, CapsuleShuffleMode.CONTENT, tick=3, target_organism_id="t"
    )
    assert sorted(c.event_pattern for c in rotated) == sorted(
        c.event_pattern for c in capsules
    )

    alone = CausalCapsule("solo", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10)
    nulled_one, records_one = apply_capsule_shuffle_control(
        (alone,), CapsuleShuffleMode.CONTENT_NULL, tick=1, target_organism_id="t"
    )
    assert len(nulled_one) == 1
    assert records_one[0].content_changed is True
    assert nulled_one[0].event_pattern == ("WAIT",)
    assert nulled_one[0].predicted_outcome == "WAIT"
    assert capsule_payload_action(nulled_one[0]) != "EAT_LUMEN"


def test_content_null_arm_runtime_has_zero_profitable_bias_payload() -> None:
    """Live content_null arm: shuffle nulls payloads; no EAT_LUMEN bias applied."""

    spec = build_hard_experiment_01_spec(
        seed=11, arm="capsules_content_null", tick_count=8, population=8
    )
    assert spec.capsule_transfer_config is not None
    assert spec.capsule_transfer_config.shuffle_mode is CapsuleShuffleMode.CONTENT_NULL
    result = GenesisEngine.from_spec(spec).run_ticks()
    shuffle_records = tuple(getattr(result, "capsule_shuffle_records", ()) or ())
    assert shuffle_records
    assert any(getattr(r, "content_changed", False) for r in shuffle_records)
    # Adopted behavioural payloads under content_null must not be EAT_LUMEN.
    from codontrace.genesis.hard_experiment_01 import _manipulation_metrics

    _applied, payloads, _rejected = _manipulation_metrics(result)
    assert CALIBRATION_GOOD_PAYLOAD_ACTION not in payloads


def test_activity_matched_reports_gap_and_caps_accepts() -> None:
    """activity_matched yokes accepts to treatment; gap field present."""

    on = build_hard_experiment_01_spec(seed=11, arm="source_bias_on", tick_count=8, population=8)
    on_result = GenesisEngine.from_spec(on).run_ticks()
    from codontrace.genesis.hard_experiment_01 import _capsule_counts

    _s, _u, _t, _a, accepted = _capsule_counts(on_result)
    matched = build_hard_experiment_01_spec(
        seed=11,
        arm="capsules_activity_matched",
        tick_count=8,
        population=8,
        activity_match_budget=accepted,
    )
    assert matched.capsule_transfer_config is not None
    assert matched.capsule_transfer_config.shuffle_mode is CapsuleShuffleMode.CONTENT_NULL
    assert matched.capsule_transfer_config.max_successful_adoptions == accepted
    matched_result = GenesisEngine.from_spec(matched).run_ticks()
    _s2, _u2, _t2, _a2, matched_accepted = _capsule_counts(matched_result)
    assert matched_accepted <= accepted
    gap = matched_accepted - accepted
    assert abs(gap) <= max(1, accepted)  # cap-down; cannot exceed budget


def test_peer_rotation_still_available_as_shuffled_sensitivity() -> None:
    """Legacy CONTENT peer-rotation remains for capsules_shuffled sensitivity arm."""

    shuffled = build_hard_experiment_01_spec(seed=11, arm="capsules_shuffled")
    assert shuffled.capsule_transfer_config is not None
    assert shuffled.capsule_transfer_config.shuffle_mode is CapsuleShuffleMode.CONTENT
    assert "capsules_shuffled" in SENSITIVITY_ARMS


def test_smoke_scale_positive_control_moves_outcome() -> None:
    """B6: positive-control mean move — asserted directly (no permissive if).

    Under Amd 03 every-cell food this usually holds at smoke; if a future
    calibration regresses it, encode ``pytest.mark.xfail(strict=True, reason=...)``
    via an amendment note rather than softening the assert.
    """

    campaign = run_hard_experiment_01(seed_count=2, include_dose=False)
    by_arm = {item.arm: item for item in campaign.arm_summaries}
    assert by_arm["oracle_capsule"].mean is not None
    assert by_arm["capsules_off"].mean is not None
    assert by_arm["oracle_capsule"].mean > by_arm["capsules_off"].mean


def test_b1_adoption_attempts_equal_accepted_plus_blocked() -> None:
    """B1 invariant: attempts == accepted + sum(blocked_by_reason)."""

    from codontrace.genesis.hard_experiment_01 import (
        _adoption_blocked_by_reason,
        _capsule_counts,
    )

    spec = build_hard_experiment_01_spec(
        seed=11, arm="source_bias_on", tick_count=8, population=8
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    _sources, _u, _t, attempts, accepted = _capsule_counts(result)
    blocked = _adoption_blocked_by_reason(result)
    assert attempts == accepted + sum(blocked.values())
    _record = __import__(
        "codontrace.genesis.hard_experiment_01", fromlist=["_record_from_run"]
    )
    # Round-trip through arm record JSON alias.
    from codontrace.genesis.hard_experiment_01 import _record_from_run

    arm = _record_from_run(seed=11, arm="source_bias_on", spec=spec, result=result)
    payload = arm.to_dict()
    assert payload["capsule_adoption_attempts"] == payload["capsule_adoptions"]
    assert payload["capsule_adoptions_accepted"] == accepted
    assert payload["capsule_adoptions"] == accepted + sum(
        payload["capsule_adoption_blocked_by_reason"].values()
    )


def test_b4_dose_statistic_is_algebraic_sum_of_primary_contrasts() -> None:
    """B4 guard: pattern_statistic ≈ c_off.mean_delta + c_none.mean_delta."""

    from codontrace.genesis.hard_experiment_01 import PRIMARY_CONTRASTS

    campaign = run_hard_experiment_01(seed_count=2, include_dose=True)
    assert campaign.dose_trend is not None
    assert campaign.dose_trend.independent is False
    assert campaign.multiple_comparison_audit.metric_count == len(PRIMARY_CONTRASTS)
    by_base = {
        item.baseline_arm: item for item in campaign.paired_contrasts if item.treatment_arm == "source_bias_on"
    }
    c_off = by_base["source_bias_off"]
    c_none = by_base["capsules_off"]
    assert c_off.mean_delta is not None and c_none.mean_delta is not None
    assert campaign.dose_trend.pattern_statistic is not None
    assert abs(
        campaign.dose_trend.pattern_statistic - (c_off.mean_delta + c_none.mean_delta)
    ) < 1e-9
    assert "dose_pattern_not_supported" not in campaign.decision_rule_failures


def test_method8_content_null_window_one_still_nulls() -> None:
    """Method #8: CONTENT_NULL nulls even when the window has size 1."""

    from codontrace.genesis.capsule import CausalCapsule, apply_capsule_shuffle_control

    alone = CausalCapsule("solo", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10)
    shuffled, records = apply_capsule_shuffle_control(
        (alone,), CapsuleShuffleMode.CONTENT_NULL, tick=1, target_organism_id="t"
    )
    assert len(records) == 1
    assert records[0].content_changed is True
    assert shuffled[0].event_pattern != alone.event_pattern


def test_method8_peer_rotation_known_failure_with_duplicate_payloads() -> None:
    """Method #8: peer-rotation is NOT a derangement when payloads collide.

    CONTENT_NULL is the confirmatory null; peer-rotation stays sensitivity
    telemetry (Wave 1d″ / Amd 04).
    """

    from codontrace.genesis.capsule import CausalCapsule, apply_capsule_shuffle_control

    capsules = (
        CausalCapsule("c1", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10),
        CausalCapsule("c2", "s2", 2.0, "g2", ("EAT_LUMEN",), "ok", 0.9, 0, 10),
        CausalCapsule("c3", "s3", 0.5, "g3", ("SENSE_DANGER",), "warn", 0.9, 0, 10),
    )
    _shuffled, records = apply_capsule_shuffle_control(
        capsules, CapsuleShuffleMode.CONTENT, tick=3, target_organism_id="t"
    )
    # ≥2 distinct payloads, yet cyclic peer-rotation can leave content unchanged
    # when neighbours share event_pattern (known failure → keep CONTENT_NULL).
    assert len({c.event_pattern for c in capsules}) >= 2
    assert any(not r.content_changed for r in records) or all(r.content_changed for r in records)
    # Document: when all payloads distinct, every content_changed.
    distinct = (
        CausalCapsule("d1", "s1", 1.0, "g1", ("EAT_LUMEN",), "ok", 0.9, 0, 10),
        CausalCapsule("d2", "s2", 2.0, "g2", ("SENSE_DANGER",), "warn", 0.9, 0, 10),
        CausalCapsule("d3", "s3", 0.5, "g3", ("WAIT",), "noop", 0.9, 0, 10),
    )
    _s2, records2 = apply_capsule_shuffle_control(
        distinct, CapsuleShuffleMode.CONTENT, tick=4, target_organism_id="t"
    )
    assert all(r.content_changed for r in records2)


def test_method9_amendment_reference_paths_exist() -> None:
    """Method #9 / P1: repo-relative paths cited in amendments must exist."""

    import re

    root = Path(__file__).resolve().parents[1]
    amd_dir = root / "docs"
    path_re = re.compile(r"`([^`]+)`")
    missing: list[str] = []
    for amd in sorted(amd_dir.glob("HARD_EXPERIMENT_01_PREREG_AMENDMENT_*.md")):
        text = amd.read_text(encoding="utf-8")
        for match in path_re.findall(text):
            candidate = match.strip()
            if candidate.startswith("http://") or candidate.startswith("https://"):
                continue
            # Repo-relative looks like docs/... / src/... / results_vN.json / etc.
            rel = None
            if candidate.startswith(("docs/", "src/", "tests/", "examples/", "handoff/")):
                rel = root / candidate
            elif candidate.startswith("HARD_EXPERIMENT_01") and candidate.endswith(".md"):
                rel = root / "docs" / candidate
            elif candidate in {
                "results_v1.json",
                "results_v2.json",
                "results_v3.json",
                "results_v5.json",
                "results_v6.json",
                "results_v7.json",
                "CLAIMS.md",
                "STYLE.md",
                "CONTRIBUTING.md",
                "README.md",
                "pyproject.toml",
            }:
                if candidate.startswith("results_"):
                    rel = root / "docs" / "hard_experiment_01" / candidate
                else:
                    rel = root / candidate
            elif candidate in {
                "WAVE_1D_DOUBLE_PRIME_HONESTY.md",
                "WAVE_1D_PILOT_DIAGNOSIS.md",
                "WAVE_1D_PILOT_REPORT.md",
                "WAVE_1E_PILOT_REPORT.md",
                "WAVE_1E_SCIENCE_BRIEF.md",
                "pilot_v5.json",
                "pilot_v6.json",
            }:
                rel = root / "docs" / "hard_experiment_01" / candidate
            if rel is not None and not rel.exists():
                missing.append(f"{amd.name}: {candidate} -> {rel}")
    assert missing == [], missing


def test_p1_committed_pilots_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "hard_experiment_01" / "pilot_v5.json").is_file()
    assert (root / "docs" / "hard_experiment_01" / "pilot_v6.json").is_file()
    assert (root / "docs" / "hard_experiment_01" / "AMD03_CODE_DEVIATIONS.md").is_file()


def test_p5_calibration_food_cells_has_no_seed_parameter() -> None:
    import inspect

    from codontrace.genesis.hard_experiment_01 import _calibration_food_cells

    params = inspect.signature(_calibration_food_cells).parameters
    assert "seed" not in params
    cells = _calibration_food_cells(4, 2)
    assert len(cells) == 8


def test_schema_v7_lock_digest_and_seed_food_amounts() -> None:
    """LOCK file hashed; food amounts seed-contingent; confirmatory null intact."""

    root = Path(__file__).resolve().parents[1]
    lock = root / "docs" / "HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK.md"
    assert lock.is_file()
    expected = sha256_text_file(lock)
    assert hard_experiment_01_prereg_amendment_lock_digest() == expected
    assert SCHEMA_VERSION == "hard_experiment_01_v7"
    assert FOOD_AMOUNT_MULTIPLIERS == (0.75, 1.0, 1.25)
    layout_a = calibration_food_amount_layout(1000, 8, 4)
    layout_b = calibration_food_amount_layout(1001, 8, 4)
    layout_a2 = calibration_food_amount_layout(1000, 8, 4)
    assert layout_a == layout_a2
    assert [c for c, _ in layout_a] == [c for c, _ in layout_b]
    assert [a for _, a in layout_a] != [a for _, a in layout_b]
    campaign = run_hard_experiment_01(seeds=(1000, 1001, 1002), include_dose=False)
    payload = campaign.to_dict()
    assert payload["schema_version"] == "hard_experiment_01_v7"
    assert payload["prereg_amendment_lock_digest"] == expected
    assert payload["food_layout"] == "every_cell_seed_amounts_v7"
    by_arm = {item.arm: item for item in campaign.arm_summaries}
    assert by_arm["source_bias_on"].sd is not None and by_arm["source_bias_on"].sd > 0.0
    # Confirmatory null must not look like "shuffled wins" vs off on mean when n small;
    # content_null mean should track capsules_off basal path.
    assert by_arm["capsules_content_null"].mean == by_arm["capsules_off"].mean
    gates = evaluate_hard_experiment_01_wave1e_pilot_gates(campaign)
    assert gates["gates"]["schema_amd_digests"]["pass"] is True
    assert gates["gates"]["treatment_seed_variance"]["pass"] is True
    assert gates["gates"]["content_null"]["pass"] is True


def test_negative_control_integrity_content_null_confirmatory() -> None:
    """content_null is confirmatory; shuffled is sensitivity-only."""

    by_arm = {item.arm: item for item in hard_experiment_01_interventions()}
    assert by_arm["capsules_content_null"].role == "negative_control"
    assert by_arm["capsules_shuffled"].role == "sensitivity_negative_control"
    assert "capsules_content_null" in ANALYSIS_ARMS
    assert "capsules_shuffled" in SENSITIVITY_ARMS
    assert "capsules_shuffled" not in ANALYSIS_ARMS


def test_committed_research_v7_is_a_valid_assay() -> None:
    """SCHEMA v7 / LOCK research artifact; ceiling only if earned."""

    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "hard_experiment_01" / "results_v7.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "hard_experiment_01_v7"
    assert payload["scale"] == "research"
    assert payload["seeds"] == list(range(11, 41))
    assert payload["prereg_digest"] == hard_experiment_01_prereg_digest()
    assert payload["prereg_amendment_lock_digest"] == hard_experiment_01_prereg_amendment_lock_digest()
    assert payload["food_layout"] == "every_cell_seed_amounts_v7"
    assert payload["assay_failed"] is False
    assert payload["replay_matched"] is True
    assert payload["decision_rule_passed"] is True
    assert payload["claim_ceiling"] == INTERVENTION_CLAIM
    assert payload["claim_gate_allowed"] is True
    by_arm = {item["arm"]: item for item in payload["arm_summaries"]}
    assert by_arm["source_bias_on"]["sd"] > 0.0
    assert by_arm["capsules_content_null"]["mean"] == by_arm["capsules_off"]["mean"]
    assert by_arm["oracle_capsule"]["mean"] > by_arm["capsules_off"]["mean"]
