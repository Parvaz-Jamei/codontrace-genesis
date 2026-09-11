"""Hard experiment 01: capsule source-bias vs next-gen fitness.

Measurement only. Does not claim intelligence, collective intelligence,
AGI, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.hard_experiment_01 import (
    CLAIM_CEILING,
    RESEARCH_SEED_COUNT,
    HardExperiment01ArmRecord,
    HardExperiment01SeedRecord,
    _capsule_counts,
    _complete_pair_values,
    _mean_last_tick_fitness,
    _missing_outcomes_per_arm,
    build_hard_experiment_01_spec,
    evaluate_hard_experiment_01_claim,
    format_hard_experiment_01_summary,
    hard_experiment_01_interventions,
    run_hard_experiment_01,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


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
    assert {item.arm for item in mapped} == {"source_bias_on", "source_bias_off", "capsules_off"}
    by_arm = {item.arm: item for item in mapped}
    assert by_arm["source_bias_on"].role == "treatment"
    assert by_arm["source_bias_off"].role == "mechanism_ablation"
    assert by_arm["capsules_off"].role == "channel_off"
    assert "min_source_fitness" in by_arm["source_bias_off"].knob
    assert by_arm["capsules_off"].knob == "CapsuleTransferConfig.enabled"
    assert all(item.to_dict()["collective_intelligence"] is False for item in mapped)


def test_hard_experiment_01_replays_all_arms_for_endpoint_seeds() -> None:
    campaign = run_hard_experiment_01(seed_count=2)
    assert campaign.seeds[0] != campaign.seeds[-1]
    assert campaign.replay_verified_seeds == (campaign.seeds[0], campaign.seeds[-1])
    expected = {
        (campaign.seeds[0], "source_bias_on"),
        (campaign.seeds[0], "source_bias_off"),
        (campaign.seeds[0], "capsules_off"),
        (campaign.seeds[-1], "source_bias_on"),
        (campaign.seeds[-1], "source_bias_off"),
        (campaign.seeds[-1], "capsules_off"),
    }
    observed = {(item.seed, item.arm) for item in campaign.replay_records}
    assert observed == expected
    assert all(item.matched for item in campaign.replay_records)
    assert campaign.replay_matched is True


def test_hard_experiment_01_twelve_seeds_replay_and_claimgate() -> None:
    assert RESEARCH_SEED_COUNT == 12
    campaign = run_hard_experiment_01()
    first = campaign.seed_records[0].source_bias_on
    replay_spec = build_hard_experiment_01_spec(seed=first.seed, arm="source_bias_on")
    replay_result = GenesisEngine.from_spec(replay_spec).run_ticks()
    assert len(campaign.seeds) == 12
    assert campaign.claim_ceiling == CLAIM_CEILING
    assert campaign.replay_matched is True
    assert campaign.replay_verified_seeds == (campaign.seeds[0], campaign.seeds[-1])
    assert {item.arm for item in campaign.replay_records} == {
        "source_bias_on",
        "source_bias_off",
        "capsules_off",
    }
    assert {item.seed for item in campaign.replay_records} == {
        campaign.seeds[0],
        campaign.seeds[-1],
    }
    assert len(campaign.replay_records) == 6
    assert all(item.matched for item in campaign.replay_records)
    last = campaign.seed_records[-1]
    last_replay_spec = build_hard_experiment_01_spec(seed=last.seed, arm="capsules_off")
    last_replay_result = GenesisEngine.from_spec(last_replay_spec).run_ticks()
    assert last_replay_spec.digest() == last.capsules_off.spec_digest
    assert last_replay_result.digest() == last.capsules_off.result_digest
    assert replay_spec.digest() == first.spec_digest
    assert replay_result.digest() == first.result_digest
    assert campaign.to_dict()["collective_intelligence"] is False
    assert campaign.to_dict()["intelligence"] is False
    assert campaign.to_dict()["agi"] is False
    assert campaign.to_dict()["tokyo_type1_passed"] is False
    assert campaign.to_dict()["avida_replacement"] is False
    assert campaign.to_dict()["claim_gate_flags_auto_set"] is False
    assert dict(campaign.missing_outcomes_per_arm) == {
        "source_bias_on": 0,
        "source_bias_off": 0,
        "capsules_off": 0,
    }
    assert all(
        arm.outcome_missing is False
        for item in campaign.seed_records
        for arm in (item.source_bias_on, item.source_bias_off, item.capsules_off)
    )
    sample_arm = campaign.seed_records[0].source_bias_on.to_dict()
    assert "capsule_emissions" not in sample_arm
    assert {
        "capsule_source_count",
        "capsule_utility_count",
        "capsule_transfer_count",
        "capsule_adoptions",
    } <= set(sample_arm)
    assert len(campaign.interventions) == 3
    assert {item.arm for item in campaign.interventions} == {
        "source_bias_on",
        "source_bias_off",
        "capsules_off",
    }
    assert campaign.to_dict()["interventions"][1]["role"] == "mechanism_ablation"
    assert all(item.source_bias_on.spec_digest != item.capsules_off.spec_digest for item in campaign.seed_records)
    assert all(
        item.source_bias_on.spec_digest != item.source_bias_off.spec_digest for item in campaign.seed_records
    )
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
    summary = format_hard_experiment_01_summary(campaign)
    assert "claim_ceiling runtime_observation" in summary
    assert "collective_intelligence False" in summary


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
        delta_vs_source_bias_off=1.0,
        delta_vs_capsules_off=1.5,
    )
    incomplete = HardExperiment01SeedRecord(
        seed=12,
        source_bias_on=_arm(12, "source_bias_on", None, missing=True),
        source_bias_off=_arm(12, "source_bias_off", 1.0, missing=False),
        capsules_off=_arm(12, "capsules_off", 0.5, missing=False),
        delta_vs_source_bias_off=None,
        delta_vs_capsules_off=None,
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
