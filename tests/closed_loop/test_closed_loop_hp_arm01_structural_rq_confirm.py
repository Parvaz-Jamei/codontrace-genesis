"""Locks for HP-ARM01 structural RQ confirmatory (Nosek-first constants)."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01_structural_rq_confirm import (
    CONFIRM_FOOD_PATCHES,
    CONFIRM_GENERATIONS,
    CONFIRM_LOCKED_WINDOWS,
    CONFIRM_PASS_BAR,
    CONFIRM_RESOURCE_BOLUS_AMOUNT,
    CONFIRM_SEEDS,
    CONFIRM_SNAP_STRIDE,
    CONFIRM_WORLD_SIZE,
    StructuralRQConfirmArm,
    _polymorphism_ok_conjunctive,
    assert_confirm_seed_policy,
    classify_structural_confirm_outcome,
    locked_design_dict,
    structural_rq_confirm_design_digest,
    structural_rq_confirm_document_digest,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    ARM_COPASSAGED,
    ARM_FIXED,
    OUTCOME_POLYMORPHISM_HOLD,
    OUTCOME_REGIME_HOSTILE_NE,
    OUTCOME_SWEEP_FIXATION,
    PILOT_SEEDS as STRUCT_PILOT_SEEDS,
)


def test_confirm_seeds_disjoint_from_pilot_and_sealed() -> None:
    assert CONFIRM_SEEDS == (701, 702, 703, 704, 705, 706, 707, 708)
    assert_confirm_seed_policy()
    with pytest.raises(ConfigurationError):
        assert_confirm_seed_policy(STRUCT_PILOT_SEEDS)
    with pytest.raises(ConfigurationError):
        assert_confirm_seed_policy((701, 201))


def test_confirm_horizon_windows_bolus_patches() -> None:
    assert CONFIRM_GENERATIONS == 500
    assert CONFIRM_LOCKED_WINDOWS == (125, 250, 500)
    assert CONFIRM_RESOURCE_BOLUS_AMOUNT == 24.0
    assert len(CONFIRM_FOOD_PATCHES) == 20
    assert CONFIRM_WORLD_SIZE == 20
    assert CONFIRM_PASS_BAR == 6
    assert CONFIRM_SNAP_STRIDE == 25


def test_conjunctive_hold_rejects_or_soft_path() -> None:
    # Joint richness alone is insufficient without sub-locus diversity.
    snap_joint_only = {
        "joint_richness": 3,
        "joint_max_freq": 0.5,
        "sub_locus_richness": [1, 1, 1],
    }
    assert _polymorphism_ok_conjunctive(snap_joint_only) is False
    # Sub-locus diversity alone insufficient without joint R_min.
    snap_sub_only = {
        "joint_richness": 2,
        "joint_max_freq": 0.5,
        "sub_locus_richness": [2, 2, 1],
    }
    assert _polymorphism_ok_conjunctive(snap_sub_only) is False
    snap_ok = {
        "joint_richness": 3,
        "joint_max_freq": 0.5,
        "sub_locus_richness": [2, 2, 1],
    }
    assert _polymorphism_ok_conjunctive(snap_ok) is True


def test_regime_hostile_ne_never_hold() -> None:
    snaps = {
        ARM_FIXED: {
            125: {"parasite_n": 10, "census": 5, "joint_richness": 5, "joint_max_freq": 0.2, "sub_locus_richness": [2, 2, 2]},
            250: {"parasite_n": 10, "census": 20, "joint_richness": 5, "joint_max_freq": 0.2, "sub_locus_richness": [2, 2, 2]},
            500: {"parasite_n": 10, "census": 20, "joint_richness": 5, "joint_max_freq": 0.2, "sub_locus_richness": [2, 2, 2]},
        },
        ARM_COPASSAGED: {
            125: {"parasite_n": 10, "census": 20, "joint_richness": 5, "joint_max_freq": 0.2, "sub_locus_richness": [2, 2, 2]},
            250: {"parasite_n": 10, "census": 20, "joint_richness": 5, "joint_max_freq": 0.2, "sub_locus_richness": [2, 2, 2]},
            500: {"parasite_n": 10, "census": 20, "joint_richness": 5, "joint_max_freq": 0.2, "sub_locus_richness": [2, 2, 2]},
        },
    }
    turnover = {ARM_COPASSAGED: {"mid_keep_ok": True}, ARM_FIXED: {"mid_keep_ok": True}}
    assert classify_structural_confirm_outcome(arm_snaps=snaps, turnover_by_arm=turnover) == OUTCOME_REGIME_HOSTILE_NE


def test_boot_confirm_digest_pins() -> None:
    arm = StructuralRQConfirmArm.boot_confirm(arm=ARM_FIXED, seed=701)
    assert float(arm.resource_bolus_amount) == 24.0
    assert len(arm.food_patches) == 20
    assert arm.runner.configs.mutation.bit_flip_rate == 0.02
    assert arm.soft_carrying_capacity == 64


def test_design_and_document_digests_stable_shape() -> None:
    design = locked_design_dict()
    assert design["or_soft_path_removed"] is True
    assert design["resource_bolus_amount"] == 24.0
    assert design["n_food_patches"] == 20
    assert design["red_queen_proved_allowed"] is False
    assert design["snap_stride"] == 25
    assert design["parasite_class_memory_L"] == 8
    assert "601" not in str(design["seeds"])
    d1 = structural_rq_confirm_design_digest()
    d2 = structural_rq_confirm_design_digest()
    assert d1 == d2
    doc = structural_rq_confirm_document_digest()
    assert len(doc) == 64


def test_sweep_when_conjunctive_fails() -> None:
    bad = {
        "parasite_n": 10,
        "census": 20,
        "joint_richness": 1,
        "joint_max_freq": 0.95,
        "sub_locus_richness": [1, 1, 1],
    }
    good = {
        "parasite_n": 10,
        "census": 20,
        "joint_richness": 4,
        "joint_max_freq": 0.4,
        "sub_locus_richness": [2, 2, 2],
    }
    snaps = {
        ARM_FIXED: {125: bad, 250: good, 500: good},
        ARM_COPASSAGED: {125: good, 250: good, 500: good},
    }
    turnover = {ARM_COPASSAGED: {"mid_keep_ok": True}, ARM_FIXED: {"mid_keep_ok": True}}
    assert classify_structural_confirm_outcome(arm_snaps=snaps, turnover_by_arm=turnover) == OUTCOME_SWEEP_FIXATION


def test_hold_when_all_windows_conjunctive() -> None:
    good = {
        "parasite_n": 10,
        "census": 20,
        "joint_richness": 4,
        "joint_max_freq": 0.4,
        "sub_locus_richness": [2, 2, 2],
    }
    snaps = {
        ARM_FIXED: {125: good, 250: good, 500: good},
        ARM_COPASSAGED: {125: good, 250: good, 500: good},
    }
    turnover = {ARM_COPASSAGED: {"mid_keep_ok": True}, ARM_FIXED: {"mid_keep_ok": True}}
    assert classify_structural_confirm_outcome(arm_snaps=snaps, turnover_by_arm=turnover) == OUTCOME_POLYMORPHISM_HOLD
