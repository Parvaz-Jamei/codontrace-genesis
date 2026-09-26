"""RQ-earn confirm locks: proved false; hostile_ne excluded; avi ignored; freeze≠absent."""

from __future__ import annotations

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import ARM_AVIRULENT, ARM_COPASSAGED, ARM_FIXED
from codontrace.genesis.closed_loop_hp_arm01_rq_earn import score_lagged_nfds_on_debit_arms
from codontrace.genesis.closed_loop_hp_arm01_rq_earn_confirm import (
    ESTIMAND_FORK,
    OUTCOME_RQ_EARN_SEED_PASS,
    RQ_EARN_CONFIRM_PASS_BAR,
    RQ_EARN_CONFIRM_SEEDS,
    STAGE0_WINNER_BOLUS,
    STAGE0_WINNER_N_PATCHES,
    assert_rq_earn_confirm_seed_policy,
    evaluate_pearl_contrasts,
    pin_stage0_winner,
    rq_earn_confirm_design_dict,
    rq_earn_confirm_design_digest,
    score_pearl_passage_lag,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    OUTCOME_REGIME_HOSTILE_NE,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
    assert_passage_taxonomy,
)


def test_proved_flags_false_on_design() -> None:
    design = rq_earn_confirm_design_dict()
    assert design["red_queen_proved_allowed"] is False
    assert design["biological_red_queen_proved_allowed"] is False
    assert design["sex_by_rq_claim_allowed"] is False
    assert design["p4_claimgate_allowlist_not_flipped_here"] is True
    assert ESTIMAND_FORK == "A"
    d1 = rq_earn_confirm_design_digest()
    d2 = rq_earn_confirm_design_digest()
    assert d1 == d2


def test_claimgate_still_refuses_red_queen_proved() -> None:
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")


def test_hostile_ne_excluded_from_lag_fraction() -> None:
    result = score_lagged_nfds_on_debit_arms(
        {}, typed_outcome=OUTCOME_REGIME_HOSTILE_NE
    )
    assert result["excluded_regime_hostile_ne"] is True
    assert result["pass_prelim"] is False
    assert result["red_queen_proved"] is False
    design = rq_earn_confirm_design_dict()
    assert design["regime_hostile_ne_excluded_from_lagged_nfds_pass_fraction"] is True


def test_avi_ignored_for_lag_credit() -> None:
    design = rq_earn_confirm_design_dict()
    assert design["avi_absent_never_grant_rq_earn_credit"] is True
    # Empty debit arms only — avirulent snaps must not create a debit score entry.
    dense = {
        ARM_AVIRULENT: {25: {"joint_freq": {"a": 1.0}, "parasite_class_hist": {}}},
        ARM_FIXED: {},
        ARM_COPASSAGED: {},
    }
    scored = score_lagged_nfds_on_debit_arms(dense)
    assert ARM_AVIRULENT not in (scored.get("arm_scores") or {})
    assert scored.get("avi_absent_ignored") is True


def test_freeze_neq_absent_pearl_passages() -> None:
    meanings = assert_passage_taxonomy()
    assert PASSAGE_FROZEN != PASSAGE_ABSENT
    assert meanings[PASSAGE_FROZEN] != meanings[PASSAGE_ABSENT]
    design = rq_earn_confirm_design_dict()
    assert design["pearl_freeze_neq_absent"] is True
    assert design["ecology_arm_fixed_is_not_pearl_frozen_alone"] is True
    assert list(design["pearl_passage_modes"]) == [
        PASSAGE_COEVOLVE,
        PASSAGE_FROZEN,
        PASSAGE_ABSENT,
    ]

    # Live contrast scorer treats passages as separate named cuts.
    pearl = evaluate_pearl_contrasts(
        {
            ARM_COPASSAGED: {},
            ARM_FIXED: {},
            ARM_AVIRULENT: {},
        }
    )
    assert pearl["freeze_neq_absent"] is True
    assert pearl["live_pearl_passages"] is True
    assert pearl["red_queen_proved"] is False
    assert PASSAGE_COEVOLVE in pearl["passage_scores"]
    assert PASSAGE_FROZEN in pearl["passage_scores"]
    assert PASSAGE_ABSENT in pearl["passage_scores"]
    assert pearl["passage_scores"][PASSAGE_FROZEN] is not pearl["passage_scores"][PASSAGE_ABSENT]


def test_seed_policy_forbids_sealed_and_demography() -> None:
    assert_rq_earn_confirm_seed_policy(RQ_EARN_CONFIRM_SEEDS)
    with pytest.raises(ConfigurationError, match="structural_confirm"):
        assert_rq_earn_confirm_seed_policy([701])
    with pytest.raises(ConfigurationError, match="demography"):
        assert_rq_earn_confirm_seed_policy([751])
    assert RQ_EARN_CONFIRM_PASS_BAR == 12
    assert len(RQ_EARN_CONFIRM_SEEDS) == 16


def test_pin_stage0_winner_updates_design() -> None:
    pin_stage0_winner(bolus=28.0, n_patches=20)
    from codontrace.genesis import closed_loop_hp_arm01_rq_earn_confirm as M

    assert M.STAGE0_WINNER_BOLUS == 28.0
    assert M.STAGE0_WINNER_N_PATCHES == 20
    assert M.STAGE0_WINNER_PINNED is True
    design = rq_earn_confirm_design_dict()
    assert design["resource_bolus_amount"] == 28.0
    assert design["n_food_patches"] == 20
    assert design["stage0_winner_pinned"] is True
    # Restore placeholder so other tests see default (24×20) unless re-pinned.
    pin_stage0_winner(bolus=24.0, n_patches=20)
    # Keep pinned True after restore — Stage 0 paste is authoritative.
    assert STAGE0_WINNER_BOLUS == 24.0
    assert STAGE0_WINNER_N_PATCHES == 20


def test_score_pearl_passage_lag_never_proved() -> None:
    score = score_pearl_passage_lag({})
    assert score["red_queen_proved"] is False
    assert score["biological_red_queen_proved"] is False
    assert score["pass_prelim"] is False


def test_success_smoke_proved_still_false() -> None:
    """Even a synthetic SUCCESS envelope must keep proved flags False."""

    from codontrace.genesis.closed_loop_hp_arm01_rq_earn_confirm import (
        RQEarnConfirmCampaignReport,
        RQEarnConfirmSeedResult,
    )

    fake_seeds = []
    for i, seed in enumerate(RQ_EARN_CONFIRM_SEEDS):
        fake_seeds.append(
            RQEarnConfirmSeedResult(
                seed=seed,
                typed_outcome=OUTCOME_RQ_EARN_SEED_PASS if i < 12 else "lag_fail",
                rq_earn_seed_pass=(i < 12),
                polymorphism_hold=True,
                excluded_from_lag_fraction=False,
                claim_ceiling="candidate_evidence" if i < 12 else "runtime_observation",
                snaps_by_arm={},
                dense_snaps_by_arm={},
                turnover_by_arm={},
                terminal_census_by_arm={},
                lagged_nfds={},
                pearl={},
                digest="x",
                red_queen_proved=False,
                biological_red_queen_proved=False,
            )
        )
    # Avoid document digest requirement: build report fields manually.
    n_pass = sum(1 for r in fake_seeds if r.rq_earn_seed_pass)
    assert n_pass >= 12
    report = RQEarnConfirmCampaignReport(
        seeds=tuple(r.seed for r in fake_seeds),
        seed_results=tuple(fake_seeds),
        typed_outcome_counts={OUTCOME_RQ_EARN_SEED_PASS: n_pass, "lag_fail": 16 - n_pass},
        rq_earn_seed_pass_count=n_pass,
        campaign_success=True,
        campaign_mixed=False,
        campaign_fail=False,
        claim_ceiling="candidate_evidence",
        design_digest="d",
        document_digest="doc",
        digest="r",
        notes="smoke",
        red_queen_proved=False,
        biological_red_queen_proved=False,
    )
    payload = report.to_dict()
    assert payload["red_queen_proved"] is False
    assert payload["biological_red_queen_proved"] is False
    assert payload["campaign_success"] is True
    assert payload["p4_claimgate_allowlist_not_flipped_here"] is True
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")
