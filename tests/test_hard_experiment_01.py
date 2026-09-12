"""Hard experiment 01: capsule source-bias vs next-gen fitness.

Measurement only. Does not claim intelligence, collective intelligence,
AGI, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.capsule import CapsuleAdoptionPolicy, CapsuleShuffleMode, apply_capsule_shuffle_control
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.hard_experiment_01 import (
    ARMS,
    CLAIM_CEILING,
    DEFAULT_DOSE_LEVELS,
    DESIGN_CLAIM_CEILING,
    RESEARCH_GRADE_SEED_COUNT,
    RESEARCH_SEED_COUNT,
    SHUFFLED_CONTROL_MODE,
    HardExperiment01ArmRecord,
    HardExperiment01SeedRecord,
    _capsule_counts,
    _complete_pair_values,
    _mean_last_tick_fitness,
    _missing_outcomes_per_arm,
    _monotone_report,
    build_hard_experiment_01_dose_spec,
    build_hard_experiment_01_spec,
    default_research_grade_seeds,
    default_research_seeds,
    evaluate_hard_experiment_01_claim,
    format_hard_experiment_01_dose_summary,
    format_hard_experiment_01_summary,
    hard_experiment_01_dag,
    hard_experiment_01_interventions,
    hard_experiment_01_shuffled_control_properties,
    hard_experiment_01_statistical_tier,
    run_hard_experiment_01,
    run_hard_experiment_01_dose_response,
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
    overlay = build_hard_experiment_01_spec(seed=7, arm="source_bias_on", tick_count=12, population=6)
    pinned = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert overlay.digest() != pinned.digest()
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
    assert by_arm["capsules_shuffled"].cuts_dag_edge == "source_identity_coupling -> capsule_content"
    assert "do(source_identity_coupling=permuted)" in by_arm["capsules_shuffled"].do_intervention
    assert all(item.to_dict()["collective_intelligence"] is False for item in mapped)


def test_hard_experiment_01_dag_names_nodes_and_cut_edges() -> None:
    dag = hard_experiment_01_dag()
    nodes = {item.node_id for item in dag.nodes}
    assert nodes == {
        "source_fitness",
        "source_identity_coupling",
        "capsule_content",
        "source_fitness_bias",
        "channel_enabled",
        "recipient_fitness",
    }
    cuts = {item.source + "->" + item.target: item.cut_by_arms for item in dag.edges}
    assert "capsules_shuffled" in cuts["source_identity_coupling->capsule_content"]
    assert "capsules_off" in cuts["channel_enabled->recipient_fitness"]
    assert "source_bias_off" in cuts["source_fitness->source_fitness_bias"]
    assert dag.to_dict()["price_equation_is_automatic_causation"] is False
    replay = hard_experiment_01_dag()
    assert replay.digest == dag.digest


def test_hard_experiment_01_shuffled_control_properties() -> None:
    props = hard_experiment_01_shuffled_control_properties()
    assert props["arm"] == "capsules_shuffled"
    assert props["shuffle_mode"] == CapsuleShuffleMode.SOURCE.value
    assert props["preserves_capsule_traffic"] is True
    assert props["destroys_source_to_content_fitness_coupling"] is True
    assert props["digest_reproducible"] is True
    assert props["is_goldsby_2012_pnas_experiment"] is False
    on_spec = build_hard_experiment_01_spec(seed=11, arm="source_bias_on")
    shuffled_spec = build_hard_experiment_01_spec(seed=11, arm="capsules_shuffled")
    off_spec = build_hard_experiment_01_spec(seed=11, arm="source_bias_off")
    none_spec = build_hard_experiment_01_spec(seed=11, arm="capsules_off")
    assert shuffled_spec.digest() != on_spec.digest()
    assert shuffled_spec.digest() != off_spec.digest()
    assert shuffled_spec.digest() != none_spec.digest()
    capsule = shuffled_spec.capsule_transfer_config
    assert capsule is not None
    assert capsule.enabled is True
    assert capsule.min_source_fitness == 2.0
    assert capsule.adoption_policy is CapsuleAdoptionPolicy.FITNESS_WEIGHTED
    assert CapsuleShuffleMode(str(capsule.shuffle_mode)) is SHUFFLED_CONTROL_MODE
    first = GenesisEngine.from_spec(shuffled_spec).run_ticks()
    second = GenesisEngine.from_spec(shuffled_spec).run_ticks()
    assert first.digest() == second.digest()


def test_source_shuffle_permutes_identity_not_content_pattern() -> None:
    from codontrace.genesis.capsule import CausalCapsule

    first = CausalCapsule("c1", "s1", 1.0, "g1", ("A",), "B", 0.9, 0, 10)
    second = CausalCapsule("c2", "s2", 4.0, "g2", ("C",), "D", 0.9, 0, 10)
    shuffled, records = apply_capsule_shuffle_control(
        (first, second),
        CapsuleShuffleMode.SOURCE,
        tick=3,
        target_organism_id="recipient",
    )
    assert records
    assert any(item.source_changed for item in records)
    assert {item.source_organism_id for item in shuffled} == {"s1", "s2"}
    assert {item.source_fitness for item in shuffled} == {1.0, 4.0}
    replay, replay_records = apply_capsule_shuffle_control(
        (first, second),
        CapsuleShuffleMode.SOURCE,
        tick=3,
        target_organism_id="recipient",
    )
    assert [item.digest() for item in shuffled] == [item.digest() for item in replay]
    assert [item.digest() for item in records] == [item.digest() for item in replay_records]


def test_hard_experiment_01_replays_all_arms_for_endpoint_seeds() -> None:
    campaign = run_hard_experiment_01(seed_count=2)
    assert campaign.seeds[0] != campaign.seeds[-1]
    assert campaign.replay_verified_seeds == (campaign.seeds[0], campaign.seeds[-1])
    expected = {
        (seed, arm)
        for seed in (campaign.seeds[0], campaign.seeds[-1])
        for arm in ARMS
    }
    observed = {(item.seed, item.arm) for item in campaign.replay_records}
    assert observed == expected
    assert all(item.matched for item in campaign.replay_records)
    assert campaign.replay_matched is True
    assert campaign.statistical_tier == hard_experiment_01_statistical_tier(2)
    assert campaign.seed_records[0].capsules_shuffled.arm == "capsules_shuffled"


def test_hard_experiment_01_twelve_seeds_replay_and_claimgate() -> None:
    assert RESEARCH_SEED_COUNT == 12
    campaign = run_hard_experiment_01()
    first = campaign.seed_records[0].source_bias_on
    replay_spec = build_hard_experiment_01_spec(seed=first.seed, arm="source_bias_on")
    replay_result = GenesisEngine.from_spec(replay_spec).run_ticks()
    assert len(campaign.seeds) == 12
    assert campaign.claim_ceiling == CLAIM_CEILING
    assert campaign.design_claim_ceiling == DESIGN_CLAIM_CEILING
    assert campaign.statistical_tier == "exploratory_only"
    assert campaign.replay_matched is True
    assert campaign.replay_verified_seeds == (campaign.seeds[0], campaign.seeds[-1])
    assert {item.arm for item in campaign.replay_records} == set(ARMS)
    assert {item.seed for item in campaign.replay_records} == {
        campaign.seeds[0],
        campaign.seeds[-1],
    }
    assert len(campaign.replay_records) == 8
    assert all(item.matched for item in campaign.replay_records)
    last = campaign.seed_records[-1]
    last_replay_spec = build_hard_experiment_01_spec(seed=last.seed, arm="capsules_off")
    last_replay_result = GenesisEngine.from_spec(last_replay_spec).run_ticks()
    assert last_replay_spec.digest() == last.capsules_off.spec_digest
    assert last_replay_result.digest() == last.capsules_off.result_digest
    shuffled_replay = build_hard_experiment_01_spec(seed=last.seed, arm="capsules_shuffled")
    shuffled_result = GenesisEngine.from_spec(shuffled_replay).run_ticks()
    assert shuffled_replay.digest() == last.capsules_shuffled.spec_digest
    assert shuffled_result.digest() == last.capsules_shuffled.result_digest
    assert replay_spec.digest() == first.spec_digest
    assert replay_result.digest() == first.result_digest
    assert campaign.to_dict()["collective_intelligence"] is False
    assert campaign.to_dict()["intelligence"] is False
    assert campaign.to_dict()["agi"] is False
    assert campaign.to_dict()["tokyo_type1_passed"] is False
    assert campaign.to_dict()["avida_replacement"] is False
    assert campaign.to_dict()["claim_gate_flags_auto_set"] is False
    assert campaign.to_dict()["results_archived"] is False
    assert dict(campaign.missing_outcomes_per_arm) == {
        "source_bias_on": 0,
        "source_bias_off": 0,
        "capsules_off": 0,
        "capsules_shuffled": 0,
    }
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
    assert len(campaign.interventions) == 4
    assert {item.arm for item in campaign.interventions} == set(ARMS)
    assert campaign.to_dict()["interventions"][1]["role"] == "mechanism_ablation"
    assert all(item.source_bias_on.spec_digest != item.capsules_off.spec_digest for item in campaign.seed_records)
    assert all(
        item.source_bias_on.spec_digest != item.source_bias_off.spec_digest for item in campaign.seed_records
    )
    assert all(
        item.source_bias_on.spec_digest != item.capsules_shuffled.spec_digest for item in campaign.seed_records
    )
    assert {item.contrast_name for item in campaign.inferential_contrasts} == {
        "vs_source_bias_off",
        "vs_capsules_off",
        "vs_capsules_shuffled",
    }
    assert all(item.pair_count == 12 for item in campaign.inferential_contrasts)
    assert all(item.holm_adjusted_p is not None for item in campaign.inferential_contrasts)
    decision = evaluate_hard_experiment_01_claim(campaign)
    assert decision.allowed is True
    assert decision.final_claim == CLAIM_CEILING
    gate = ScientificClaimGate()
    payload = campaign.to_dict()
    assert gate.decide(ClaimRequest("runtime_observation", payload)).allowed is True
    assert gate.decide(ClaimRequest("intervention_supported", payload)).allowed is False
    assert gate.decide(ClaimRequest("collective_intelligence", payload)).allowed is False
    assert gate.decide(ClaimRequest("intelligence", payload)).allowed is False
    assert gate.decide(ClaimRequest("agi", payload)).allowed is False
    assert gate.decide(ClaimRequest("tokyo_type1_passed", payload)).allowed is False
    assert gate.decide(ClaimRequest("avida_replacement", payload)).allowed is False
    summary = format_hard_experiment_01_summary(campaign)
    assert "claim_ceiling runtime_observation" in summary
    assert "design_claim_ceiling intervention_supported" in summary
    assert "statistical_tier exploratory_only" in summary
    assert "collective_intelligence False" in summary
    assert "results_archived False" in summary


def test_research_grade_thirty_seed_path_matches_statistical_policy() -> None:
    assert RESEARCH_GRADE_SEED_COUNT == 30
    seeds = default_research_grade_seeds()
    assert seeds == tuple(range(11, 41))
    assert default_research_seeds(30) == seeds
    policy = StatisticalTestPolicy()
    assert policy.tier_for_n(12) == "exploratory_only"
    assert policy.tier_for_n(30) == "research_grade_benchmark_candidate"
    assert hard_experiment_01_statistical_tier(12) == "exploratory_only"
    assert hard_experiment_01_statistical_tier(30) == "research_grade_benchmark_candidate"
    assert hard_experiment_01_statistical_tier(2) == "descriptive_only"


def test_hard_experiment_01_dose_ladder_replays_and_reports_monotone_honestly() -> None:
    assert DEFAULT_DOSE_LEVELS == (0.0, 1.0, 2.0)
    dose = run_hard_experiment_01_dose_response(seed_count=2)
    assert dose.levels == DEFAULT_DOSE_LEVELS
    assert dose.knob == "CapsuleTransferConfig.min_source_fitness"
    assert dose.claim_ceiling == CLAIM_CEILING
    assert dose.statistical_tier == "descriptive_only"
    assert dose.monotone_report in {"increasing", "decreasing", "null", "insufficient"}
    assert dose.replay_matched is True
    assert len(dose.replay_records) == 2
    assert {item.min_source_fitness for item in dose.replay_records} == {0.0, 2.0}
    first = dose.records[0]
    replay_spec = build_hard_experiment_01_dose_spec(
        seed=first.seed, min_source_fitness=first.min_source_fitness
    )
    replay_result = GenesisEngine.from_spec(replay_spec).run_ticks()
    assert replay_spec.digest() == first.spec_digest
    assert replay_result.digest() == first.result_digest
    treatment = build_hard_experiment_01_spec(seed=first.seed, arm="source_bias_on")
    high_dose = build_hard_experiment_01_dose_spec(seed=first.seed, min_source_fitness=2.0)
    assert treatment.capsule_transfer_config is not None
    assert high_dose.capsule_transfer_config is not None
    assert high_dose.capsule_transfer_config.to_dict() == treatment.capsule_transfer_config.to_dict()
    assert high_dose.engine_config.enable_capsules is True
    assert dose.to_dict()["is_goldsby_2012_pnas_experiment"] is False
    assert dose.to_dict()["results_archived"] is False
    summary = format_hard_experiment_01_dose_summary(dose)
    assert "monotone_report" in summary
    assert "results_archived False" in summary
    assert _monotone_report([1.0, 2.0, 3.0]) == "increasing"
    assert _monotone_report([3.0, 2.0, 1.0]) == "decreasing"
    assert _monotone_report([1.0, 1.0, 1.0]) == "null"
    assert _monotone_report([1.0, 3.0, 2.0]) == "null"


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
        capsules_shuffled=_arm(11, "capsules_shuffled", 0.75, missing=False),
        delta_vs_source_bias_off=1.0,
        delta_vs_capsules_off=1.5,
        delta_vs_capsules_shuffled=1.25,
    )
    incomplete = HardExperiment01SeedRecord(
        seed=12,
        source_bias_on=_arm(12, "source_bias_on", None, missing=True),
        source_bias_off=_arm(12, "source_bias_off", 1.0, missing=False),
        capsules_off=_arm(12, "capsules_off", 0.5, missing=False),
        capsules_shuffled=_arm(12, "capsules_shuffled", 0.75, missing=False),
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
    shuffled_base, shuffled_treat = _complete_pair_values(
        (complete, incomplete),
        treatment_arm="source_bias_on",
        baseline_arm="capsules_shuffled",
    )
    assert shuffled_base == [0.75]
    assert shuffled_treat == [2.0]
    assert _missing_outcomes_per_arm((complete, incomplete)) == (
        ("source_bias_on", 1),
        ("source_bias_off", 0),
        ("capsules_off", 0),
        ("capsules_shuffled", 0),
    )


def test_hard_experiment_01_docs_and_example_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "HARD_EXPERIMENT_01.md").is_file()
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
    assert "negative / specificity control" in text
    assert "Causal DAG" in text
    assert "source_fitness" in text
    assert "do()" in text
    assert "Dose-response" in text
    assert "min_source_fitness" in text
    assert "research-grade n is **30**" in text
    assert "Results: not yet recorded" in text
    assert "statistical identity" in text
    assert "intervention_supported" in text
    assert "not yet recorded" in text
    assert not text.lstrip().startswith("# Phase")
    style = (root / "STYLE.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "CodonTrace Genesis" in style
    assert "naming-order" in style
    assert "Always name the product" not in readme
    assert "eat, survive, and reproduce" in readme


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
