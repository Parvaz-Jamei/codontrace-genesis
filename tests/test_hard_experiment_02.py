"""HARD_EXPERIMENT_02 knob + campaign gates. Pins A–E must stay green."""

from __future__ import annotations

from dataclasses import replace

import pytest

from codontrace.actions import default_action_registry
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.deme_selection import (
    E2_ORDINAL_PREDICTION,
    DemeSelectionCell,
    DemeSelectionConfig,
    e2_ordinal_respects_prediction,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.food_patch_signal import (
    MOVE_TOWARD_CAPSULE_TARGET,
    FoodPatchSignalConfig,
    FoodPatchSignalRecord,
    decode_patch_payload,
    encode_patch_payload,
    payload_patch_mutual_information,
    spawn_patches_for_tick,
)
from codontrace.genesis.hard_experiment_02 import (
    ARMS,
    CLAIM_CEILING,
    PILOT_SEEDS,
    build_hard_experiment_02_spec,
    evaluate_hard_experiment_02_claim,
    evaluate_hard_experiment_02_pilot_gates,
    hard_experiment_02_action_registry,
    hard_experiment_02_causal_dag,
    hard_experiment_02_interventions,
    hard_experiment_02_prereg_digest,
    run_hard_experiment_02,
)
from codontrace.genesis.population import PopulationConfigs
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.stepping_stone_reward import SteppingStoneRewardConfig

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_phase_a_life_loop_digest_pin_unchanged_by_hard_experiment_02() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_he02_knobs_default_off_omit_from_population_configs_dict() -> None:
    payload = PopulationConfigs().to_dict()
    assert "food_patch_signal" not in payload
    assert "deme_selection" not in payload
    assert "stepping_stone_reward" not in payload


def test_he02_knobs_enabled_change_digest() -> None:
    off = PopulationConfigs()
    on = replace(
        PopulationConfigs(),
        food_patch_signal=FoodPatchSignalConfig(enabled=True),
        deme_selection=DemeSelectionConfig(enabled=True, level="GERMLINE_GROUP", founder_relatedness="CLONAL"),
        stepping_stone_reward=SteppingStoneRewardConfig(enabled=True),
    )
    assert canonical_digest(off.to_dict()) != canonical_digest(on.to_dict())
    assert "food_patch_signal" in on.to_dict()


def test_move_toward_capsule_target_absent_from_default_registry() -> None:
    assert default_action_registry().get(MOVE_TOWARD_CAPSULE_TARGET) is None
    he02 = hard_experiment_02_action_registry()
    assert he02.get(MOVE_TOWARD_CAPSULE_TARGET) is not None


def test_food_patch_payload_roundtrip_and_mi() -> None:
    token = encode_patch_payload(2, 5)
    assert decode_patch_payload(token) == (2, 5)
    records = [
        FoodPatchSignalRecord(
            tick=1,
            emitter_id="e",
            receiver_id="r",
            payload_digest="d1",
            target_true=(2, 5),
            moved=True,
            ate_at_target=False,
            payload_token=token,
        ),
        FoodPatchSignalRecord(
            tick=2,
            emitter_id="e",
            receiver_id="r",
            payload_digest="d2",
            target_true=(1, 1),
            moved=False,
            ate_at_target=False,
            payload_token=encode_patch_payload(1, 1),
        ),
        FoodPatchSignalRecord(
            tick=3,
            emitter_id="e",
            receiver_id="r",
            payload_digest="d1",
            target_true=(2, 5),
            moved=True,
            ate_at_target=True,
            payload_token=token,
        ),
        FoodPatchSignalRecord(
            tick=4,
            emitter_id="e",
            receiver_id="r",
            payload_digest="d2",
            target_true=(1, 1),
            moved=True,
            ate_at_target=False,
            payload_token=encode_patch_payload(1, 1),
        ),
    ]
    assert payload_patch_mutual_information(records) > 0.0


def test_food_patch_spawn_requires_enabled() -> None:
    off = spawn_patches_for_tick(
        tick=8,
        width=4,
        height=4,
        config=FoodPatchSignalConfig(enabled=False),
        rng_draw=(0.1, 0.2),
        active=(),
    )
    assert off == ()
    on = spawn_patches_for_tick(
        tick=8,
        width=4,
        height=4,
        config=FoodPatchSignalConfig(enabled=True, patch_spawn_period_ticks=8, patch_count=1),
        rng_draw=(0.25, 0.75),
        active=(),
    )
    assert len(on) == 1


def test_deme_selection_ordinal_prediction() -> None:
    assert E2_ORDINAL_PREDICTION[0] == DemeSelectionCell.GERMLINE_CLONAL.value
    assert e2_ordinal_respects_prediction(
        {
            "GERMLINE_CLONAL": 1.0,
            "GERMLINE_MIXED": 0.6,
            "INDIVIDUAL_CLONAL": 0.55,
            "INDIVIDUAL_MIXED": 0.1,
        }
    )
    assert not e2_ordinal_respects_prediction(
        {"GERMLINE_CLONAL": 0.1, "INDIVIDUAL_MIXED": 0.9}
    )


def test_he02_overlay_does_not_alias_default_life_loop_digest() -> None:
    overlay = build_hard_experiment_02_spec(seed=7, arm="treatment", tick_count=4, population=4)
    pinned = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert overlay.digest() != pinned.digest()
    assert pinned.digest() == LIFE_LOOP_SPEC_DIGEST


def test_he02_interventions_cover_all_arms() -> None:
    mapped = hard_experiment_02_interventions()
    assert {item.arm for item in mapped} == set(ARMS)


def test_he02_claim_ceiling_is_runtime_observation() -> None:
    assert CLAIM_CEILING == "runtime_observation"
    dag = hard_experiment_02_causal_dag()
    assert dag["claim_ceiling"] == "runtime_observation"
    assert dag["collective_intelligence"] is False


def test_he02_prereg_digest_is_real() -> None:
    digest = hard_experiment_02_prereg_digest()
    assert isinstance(digest, str) and len(digest) == 64


def test_he02_smoke_campaign_runs_and_stays_at_runtime_observation() -> None:
    campaign = run_hard_experiment_02(seeds=(11,), scale="smoke", tick_count=2, population=4)
    claim = evaluate_hard_experiment_02_claim(campaign)
    assert claim["claim_ceiling"] == "runtime_observation"
    assert claim["collective_intelligence"] is False
    assert claim["intelligence"] is False
    assert claim["agi"] is False
    gates = evaluate_hard_experiment_02_pilot_gates(campaign)
    # Single-seed smoke is not required to clear pilot; it must remain honest.
    assert "overall_pass" in gates
    assert campaign.claim_ceiling == "runtime_observation"


def test_invalid_deme_level_raises() -> None:
    with pytest.raises(ConfigurationError):
        DemeSelectionConfig(enabled=True, level="NOT_A_LEVEL")  # type: ignore[arg-type]
