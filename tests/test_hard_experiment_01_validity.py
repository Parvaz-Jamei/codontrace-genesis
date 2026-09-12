"""Wave 1c HE01 assay-validity gates. Does not claim intelligence."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.capsule import CapsuleTransferConfig, tick_source_fitness_threshold
from codontrace.genesis.hard_experiment_01 import (
    ARMS,
    PRIMARY_ARMS,
    PRIMARY_CONTRASTS,
    POSITIVE_CONTROL_ARM,
    PILOT_SEEDS,
    HardExperiment01ArmRecord,
    assert_hard_experiment_01_seeds_allowed,
    evaluate_hard_experiment_01_manipulation_check,
    run_hard_experiment_01,
)
from codontrace.genesis.phase_e import PhaseEOrganismState, write_phase_e_slot_from_adopted_capsule


def _arm(
    seed: int,
    arm: str,
    *,
    fitness: float = 1.0,
    adoptions: int = 0,
    births: int = 1,
    rejected: int = 0,
    digests: tuple[str, ...] = (),
) -> HardExperiment01ArmRecord:
    return HardExperiment01ArmRecord(
        seed=seed,
        arm=arm,  # type: ignore[arg-type]
        terminal_mean_fitness=fitness,
        births=births,
        capsule_source_count=0,
        capsule_utility_count=0,
        capsule_transfer_count=0,
        capsule_adoptions=adoptions,
        spec_digest="a" * 64,
        result_digest="b" * 64,
        next_generation_observed=births > 0,
        adopted_content_digests=digests,
        rejected_by_source_fitness=rejected,
    )


def test_analysis_seeds_blocked_until_config_locked() -> None:
    with pytest.raises(ConfigurationError, match="11–40"):
        assert_hard_experiment_01_seeds_allowed((11, 12), config_locked=False)
    with pytest.raises(ConfigurationError, match="11–40"):
        run_hard_experiment_01(seeds=(11, 12), config_locked=False, include_dose=False)
    assert_hard_experiment_01_seeds_allowed(PILOT_SEEDS, config_locked=False)
    assert_hard_experiment_01_seeds_allowed((1000, 1001, 1009), config_locked=False)
    assert_hard_experiment_01_seeds_allowed((11, 40), config_locked=True)
    assert PILOT_SEEDS == tuple(range(1000, 1010))


def test_oracle_is_reported_but_not_in_primary_holm_family() -> None:
    assert POSITIVE_CONTROL_ARM == "oracle_capsule"
    assert POSITIVE_CONTROL_ARM in ARMS
    assert POSITIVE_CONTROL_ARM not in PRIMARY_ARMS
    assert POSITIVE_CONTROL_ARM not in {arm for pair in PRIMARY_CONTRASTS for arm in pair}
    assert len(PRIMARY_CONTRASTS) == 3
    assert PRIMARY_CONTRASTS == (
        ("source_bias_on", "source_bias_off"),
        ("source_bias_on", "capsules_off"),
        ("source_bias_on", "capsules_shuffled"),
    )


def test_manipulation_check_passes_only_when_construct_is_realized() -> None:
    on = _arm(
        11,
        "source_bias_on",
        adoptions=3,
        rejected=2,
        digests=("on-a", "on-b"),
    )
    off = _arm(11, "source_bias_off", adoptions=5, digests=("off-a",))
    capsules_off = _arm(11, "capsules_off", adoptions=0)
    shuffled = _arm(
        11,
        "capsules_shuffled",
        adoptions=3,
        rejected=2,
        digests=("shuf-a",),
    )
    passed, failures = evaluate_hard_experiment_01_manipulation_check(
        on=on, off=off, capsules_off=capsules_off, shuffled=shuffled
    )
    assert passed is True
    assert failures == ()


def test_manipulation_check_accepts_peer_swap_when_scramble_records_fire() -> None:
    on = _arm(11, "source_bias_on", adoptions=3, rejected=2, digests=("a", "b"))
    off = _arm(11, "source_bias_off", adoptions=5, digests=("a", "b", "c"))
    capsules_off = _arm(11, "capsules_off", adoptions=0)
    shuffled = HardExperiment01ArmRecord(
        seed=11,
        arm="capsules_shuffled",
        terminal_mean_fitness=1.0,
        births=1,
        capsule_source_count=0,
        capsule_utility_count=0,
        capsule_transfer_count=0,
        capsule_adoptions=3,
        spec_digest="a" * 64,
        result_digest="b" * 64,
        next_generation_observed=True,
        adopted_content_digests=("a", "b"),
        rejected_by_source_fitness=2,
        content_scramble_changed=4,
    )
    passed, failures = evaluate_hard_experiment_01_manipulation_check(
        on=on, off=off, capsules_off=capsules_off, shuffled=shuffled
    )
    assert passed is True
    assert failures == ()


def test_manipulation_check_fails_as_assay_invalid_when_arms_identical() -> None:
    same = ("same-digest",)
    on = _arm(11, "source_bias_on", adoptions=4, rejected=0, digests=same)
    off = _arm(11, "source_bias_off", adoptions=4, digests=same)
    capsules_off = _arm(11, "capsules_off", adoptions=2)
    shuffled = _arm(11, "capsules_shuffled", adoptions=4, digests=same)
    passed, failures = evaluate_hard_experiment_01_manipulation_check(
        on=on, off=off, capsules_off=capsules_off, shuffled=shuffled
    )
    assert passed is False
    assert failures[0] == "manipulation_not_realized"
    assert "manipulation_not_realized_on_equals_off_content" in failures
    assert "manipulation_not_realized_shuffled_equals_on_content" in failures
    assert "manipulation_not_realized_capsules_off_adoptions_nonzero" in failures
    assert "manipulation_not_realized_no_source_fitness_rejects" in failures


def test_tick_median_quantile_is_interpolated_and_empty_pool_is_zero() -> None:
    assert tick_source_fitness_threshold((), 0.5) == 0.0
    assert tick_source_fitness_threshold((0.1, 0.2, 0.3), 0.5) == 0.2
    assert tick_source_fitness_threshold((1.0, 1.0, 1.0), 0.5) == 1.0
    assert tick_source_fitness_threshold((0.0, 4.0), 0.25) == 1.0


def test_default_capsule_transfer_config_omits_optional_wave1c_keys() -> None:
    payload = CapsuleTransferConfig().to_dict()
    assert "source_fitness_quantile" not in payload
    assert "encode_source_action_in_content" not in payload
    assert "scramble_identical_peer_content" not in payload
    enabled = CapsuleTransferConfig(
        source_fitness_quantile=0.5, encode_source_action_in_content=True
    ).to_dict()
    assert enabled["source_fitness_quantile"] == 0.5
    assert enabled["encode_source_action_in_content"] is True


def test_adopted_capsule_writes_unconstrained_phase_e_slot() -> None:
    organism = SimpleNamespace(phase_e_state=None)
    assert write_phase_e_slot_from_adopted_capsule(organism, SimpleNamespace(), tick=1) is False
    state = PhaseEOrganismState()
    organism = SimpleNamespace(phase_e_state=state)
    capsule = SimpleNamespace(
        metadata={"source_preferred_action": "EAT_LUMEN"},
        event_pattern=("EAT_LUMEN", "EMIT_NEXUS"),
    )
    assert write_phase_e_slot_from_adopted_capsule(organism, capsule, tick=3) is True
    slot = state.capsule.slots[-1]
    assert slot.preferred_action == "EAT_LUMEN"
    assert slot.source == "adopted_capsule"
    assert slot.cue_regime == ""
    assert slot.cue_has_local_food is False
