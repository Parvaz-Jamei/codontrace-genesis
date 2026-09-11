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


def test_hard_experiment_01_twelve_seeds_replay_and_claimgate() -> None:
    assert RESEARCH_SEED_COUNT == 12
    campaign = run_hard_experiment_01()
    first = campaign.seed_records[0].source_bias_on
    replay_spec = build_hard_experiment_01_spec(seed=first.seed, arm="source_bias_on")
    replay_result = GenesisEngine.from_spec(replay_spec).run_ticks()
    assert len(campaign.seeds) == 12
    assert campaign.claim_ceiling == CLAIM_CEILING
    assert campaign.replay_matched is True
    assert replay_spec.digest() == first.spec_digest
    assert replay_result.digest() == first.result_digest
    assert campaign.to_dict()["collective_intelligence"] is False
    assert campaign.to_dict()["intelligence"] is False
    assert campaign.to_dict()["agi"] is False
    assert campaign.to_dict()["tokyo_type1_passed"] is False
    assert campaign.to_dict()["avida_replacement"] is False
    assert campaign.to_dict()["claim_gate_flags_auto_set"] is False
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
        and (
            path.name.startswith(".grok_write_probe")
            or (path.name.startswith(".size_test_") and path.suffix == ".txt")
        )
        and ".git" not in path.parts
    ]
    assert junk == []
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert ".grok_write_probe" in gitignore
    assert ".size_test_" in gitignore
