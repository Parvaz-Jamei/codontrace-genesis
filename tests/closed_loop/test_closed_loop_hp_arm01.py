"""Three-arm life-loop bind: substrate, invasion estimand, ClaimGate refuse.

Anchored to sealed confirmatory 101–108 honest FAIL at tip 610f46f and to
Pearl-pair taxonomy on closed-loop/pearl-pair-spc. Does not promote
red_queen_proved. Does not loosen ClaimGate. ENGINE-BIND requires
PopulationRunner + Phase B + HostParasiteEnv; run_shared_modifier is refused
as the primary campaign substrate.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    ARM_TO_PASSAGE,
    CLAIM_CEILING_CANDIDATE,
    CLAIM_CEILING_OBSERVATION,
    HP_ARM01_ESTIMAND,
    REQUIRED_CLOCKS,
    SUBSTRATE_FORBIDDEN_PRIMARY,
    SUBSTRATE_LIFE_LOOP,
    assert_ecology_arm_taxonomy,
    campaign_handling_ablation_pair,
    ecology_arm_to_passage,
    handling_ablation_digests,
    max_allowed_claim_ceiling,
    passage_to_ecology_arm,
    per_arm_clocks_complete,
    refuse_shared_modifier_as_slowinski_pass,
    required_clocks_complete,
    run_three_arm_frequency_campaign,
    slowinski_invasion_contrast,
    slowinski_selfing_invasion_contrast,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_COSTLESS,
    PASSAGE_FROZEN,
)
from codontrace.genesis.host_parasite_env import HostParasiteEnv

_REPO = Path(__file__).resolve().parents[2]
_ARM01 = _REPO / "src" / "codontrace" / "genesis" / "closed_loop_hp_arm01.py"


def test_claimgate_still_refuses_red_queen_proved() -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed("red_queen_proved")
    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=2, seed=101
    )
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION


def test_ecology_arm_taxonomy_maps_without_costless_alias() -> None:
    meanings = assert_ecology_arm_taxonomy()
    assert meanings[ARM_AVIRULENT] != meanings[ARM_FIXED]
    assert meanings[ARM_FIXED] != meanings[ARM_COPASSAGED]
    assert ecology_arm_to_passage(ARM_AVIRULENT) == PASSAGE_ABSENT
    assert ecology_arm_to_passage(ARM_FIXED) == PASSAGE_FROZEN
    assert ecology_arm_to_passage(ARM_COPASSAGED) == PASSAGE_COEVOLVE
    assert PASSAGE_COSTLESS not in ARM_TO_PASSAGE.values()
    assert passage_to_ecology_arm(PASSAGE_ABSENT) == ARM_AVIRULENT
    with pytest.raises(ConfigurationError, match="costless|zero_debit"):
        ecology_arm_to_passage("costless")
    with pytest.raises(ConfigurationError, match="Pearl debit knockout"):
        passage_to_ecology_arm(PASSAGE_COSTLESS)
    with pytest.raises(ConfigurationError, match="aliases are forbidden"):
        assert_ecology_arm_taxonomy(refuse_aliases=False)


def test_campaign_substrate_is_life_loop_not_shared_modifier() -> None:
    """Fail if campaign primary path still calls run_shared_modifier."""

    source = _ARM01.read_text(encoding="utf-8")
    tree = ast.parse(source)
    # Importing run_shared_modifier at all as a campaign dependency is refused.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "closed_loop_p6" in node.module:
            names = {alias.name for alias in node.names}
            assert "run_shared_modifier" not in names, (
                "campaign must not import run_shared_modifier as primary substrate"
            )
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "run_shared_modifier":
                raise AssertionError("run_shared_modifier must not be the campaign substrate")
            if isinstance(func, ast.Attribute) and func.attr == "run_shared_modifier":
                raise AssertionError("run_shared_modifier must not be the campaign substrate")

    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=2, seed=101
    )
    assert report.substrate == SUBSTRATE_LIFE_LOOP
    assert report.life_loop_bound is True
    assert report.estimand == HP_ARM01_ESTIMAND
    assert report.to_dict()["shared_modifier_refused_as_primary_substrate"] is True
    assert "PopulationRunner" in source or "step_generation" in source
    assert "SEXUAL_CROSSOVER" in source
    assert "HostParasiteEnv" in source


def test_frequency_clocks_are_required_per_arm_not_concatenated() -> None:
    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=2, seed=101
    )
    assert report.clocks_complete is True
    assert report.per_arm_clocks_ok is True
    assert required_clocks_complete(report.clocks) is True
    assert per_arm_clocks_complete(report.clocks_by_arm) is True
    assert set(report.clocks) == set(REQUIRED_CLOCKS)
    # Per-arm clocks: each arm has its own mating-mode series (not concatenated).
    mating_digests = {
        arm: report.clocks_by_arm[arm]["mating_mode"].digest for arm in report.arms_present
    }
    series_lens = {
        arm: len(report.clocks_by_arm[arm]["mating_mode"].series)
        for arm in report.arms_present
    }
    assert all(length == 2 for length in series_lens.values()), series_lens
    # Treatment campaign-level mating clock equals copassaged arm only.
    assert (
        report.clocks["mating_mode"].digest
        == report.clocks_by_arm[ARM_COPASSAGED]["mating_mode"].digest
    )
    for name, clock in report.clocks.items():
        assert clock.name == name
        assert len(clock.digest) == 64
        assert clock.series
        assert clock.to_dict()["writes_red_queen_flag"] is False
    assert report.treatment_control_present is True
    # ClaimCritic: non-empty clocks alone do not grant candidate_evidence.
    assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION
    assert report.digest
    assert len(report.digest) == 64
    assert mating_digests  # used above; keep for clarity


def test_slowinski_invasion_estimand_and_refuse_shared_modifier_pass() -> None:
    assert (
        slowinski_invasion_contrast(
            intro_selfing_freq=0.2,
            final_selfing_avirulent=0.6,
            final_selfing_fixed=0.55,
            final_selfing_copassaged=0.1,
        )
        is True
    )
    assert (
        slowinski_invasion_contrast(
            intro_selfing_freq=0.2,
            final_selfing_avirulent=0.15,
            final_selfing_fixed=0.15,
            final_selfing_copassaged=0.1,
        )
        is False
    )
    # Legacy three-freq contrast is not the accept path.
    assert (
        slowinski_selfing_invasion_contrast(
            selfing_freq_avirulent=0.9,
            selfing_freq_fixed=0.8,
            selfing_freq_copassaged=0.1,
        )
        is True
    )
    with pytest.raises(ConfigurationError, match="shared-modifier"):
        refuse_shared_modifier_as_slowinski_pass(
            substrate=SUBSTRATE_FORBIDDEN_PRIMARY, contrast_holds=True
        )
    refuse_shared_modifier_as_slowinski_pass(
        substrate=SUBSTRATE_LIFE_LOOP, contrast_holds=True
    )
    # Ceiling: clocks alone insufficient.
    assert (
        max_allowed_claim_ceiling(
            clocks_complete=True,
            treatment_control_present=True,
            substrate_life_loop_bound=False,
            per_arm_clocks_ok=True,
            slowinski_invasion_holds=True,
        )
        == CLAIM_CEILING_OBSERVATION
    )
    assert (
        max_allowed_claim_ceiling(
            clocks_complete=True,
            treatment_control_present=True,
            substrate_life_loop_bound=True,
            per_arm_clocks_ok=True,
            slowinski_invasion_holds=False,
        )
        == CLAIM_CEILING_OBSERVATION
    )
    assert (
        max_allowed_claim_ceiling(
            clocks_complete=True,
            treatment_control_present=True,
            substrate_life_loop_bound=True,
            per_arm_clocks_ok=True,
            slowinski_invasion_holds=True,
        )
        == CLAIM_CEILING_CANDIDATE
    )


def test_pearl_measurement_requires_clocks_and_stays_non_promoting() -> None:
    report = run_three_arm_frequency_campaign(
        virulence=8.0,
        generations=2,
        seed=101,
        attach_pearl_measurement=True,
    )
    assert report.pearl_measurement_attached is True
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.clocks_complete is True
    assert report.per_arm_clocks_ok is True
    assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION


def test_handling_time_ablation_uses_campaign_env_path() -> None:
    """Holling ablation must run on the campaign HostParasiteEnv loop."""

    pair = campaign_handling_ablation_pair(virulence=8.0, seed=101, generations=2)
    assert pair["campaign_env_path"] is True
    assert pair["digests_distinct"] is True
    assert pair["red_queen_proved"] is False
    assert pair["claim_ceiling"] == CLAIM_CEILING_OBSERVATION

    # Standalone env probe still works for unit sanity, but campaign path is required.
    off = HostParasiteEnv(steal_fraction=0.8, handling_time=0.0)
    on = HostParasiteEnv(steal_fraction=0.8, handling_time=2.0)
    for env in (off, on):
        env.add_host("H0", ["not", "nand"])
        env.add_host("H1", ["not", "nand"])
    a0 = off.try_horizontal_inject(
        host_id="H0", parasite_id="P0", parasite_tasks=["not"], payload=(1,)
    )
    a1 = on.try_horizontal_inject(
        host_id="H0", parasite_id="P0", parasite_tasks=["not"], payload=(1,)
    )
    assert a0.injected is True and a1.injected is True
    b0 = off.try_horizontal_inject(
        host_id="H1", parasite_id="P1", parasite_tasks=["not"], payload=(2,)
    )
    b1 = on.try_horizontal_inject(
        host_id="H1", parasite_id="P1", parasite_tasks=["not"], payload=(2,)
    )
    assert b0.injected is True
    assert b1.injected is False
    assert b1.reason == "handling_busy"
    unit = handling_ablation_digests(
        handling_off=off.snapshot(), handling_on=on.snapshot()
    )
    assert unit["digests_distinct"] is True
    with pytest.raises(ConfigurationError, match="handling_time"):
        HostParasiteEnv(handling_time=-0.1)

    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=2, seed=101, handling_time=0.0
    )
    assert set(report.hp_env_ids_by_arm) == set(report.arms_present)
    assert all(isinstance(v, int) and v != 0 for v in report.hp_env_ids_by_arm.values())


def test_two_fold_cost_unpaid_and_invasion_honest_fail_ok() -> None:
    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=2, seed=101
    )
    assert report.two_fold_cost_sex_applied is False
    assert "unpaid" in report.to_dict()["two_fold_cost_sex_note"]
    assert report.confirmatory_horizon_deferred is True
    # Honest FAIL is OK; do not soft-green by inventing PASS.
    if not report.slowinski_invasion_holds:
        assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION
        assert "fail_recorded_honestly" in report.notes
    assert report.slowinski_contrast_holds == report.slowinski_invasion_holds
    assert report.to_dict()["legacy_three_freq_is_accept_path"] is False


def test_engine_has_no_infection_tokens() -> None:
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine
