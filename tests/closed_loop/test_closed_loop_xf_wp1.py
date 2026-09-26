"""XF-WP-1: Pearl-pair taxonomy and fail-closed debit-stream gates.

Anchored to sealed confirmatory 101–108 honest FAIL at tip 610f46f.
Does not promote red_queen_proved. Does not loosen ClaimGate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import debit_backed_cycle, run_match_arm
from codontrace.genesis.closed_loop_xf_wp1 import (
    CLAIM_CEILING,
    PASSAGE_ABSENT,
    PASSAGE_COSTLESS,
    PASSAGE_FROZEN,
    antagonist_removal_passage,
    assert_passage_taxonomy,
    cusum_onset_declared,
    debit_backed_cycle_capability,
    evaluate_xf_wp1_clauses,
    observer_residual_coherent,
    pearl_knockout_passages,
    pearl_pair_survival_gap_absent,
    predicted_match_cost,
    require_pearl_knockout,
    shewhart_in_control,
)

_REPO = Path(__file__).resolve().parents[2]


def test_claimgate_still_refuses_red_queen_proved() -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed("red_queen_proved")
    # Harness keeps the biological flag false by construction; ClaimGate
    # blocks the digital claim name on the host_parasite profile.
    report = evaluate_xf_wp1_clauses(
        history=(("a",), ("b",), ("a",)),
        match_debits=(0, 1, 0),
        frozen_outcross_extinct=False,
        frozen_selfing_extinct=False,
        costless_outcross_extinct=False,
        costless_selfing_extinct=False,
    )
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False


def test_passage_taxonomy_is_non_aliasable() -> None:
    meanings = assert_passage_taxonomy()
    assert meanings[PASSAGE_FROZEN] != meanings[PASSAGE_COSTLESS]
    assert meanings[PASSAGE_ABSENT] != meanings[PASSAGE_COSTLESS]
    assert meanings[PASSAGE_ABSENT] != meanings[PASSAGE_FROZEN]
    assert pearl_knockout_passages() == (PASSAGE_FROZEN, PASSAGE_COSTLESS)
    assert antagonist_removal_passage() == PASSAGE_ABSENT
    assert PASSAGE_ABSENT not in pearl_knockout_passages()
    assert require_pearl_knockout("frozen") == PASSAGE_FROZEN
    assert require_pearl_knockout("costless") == PASSAGE_COSTLESS
    with pytest.raises(ConfigurationError, match="antagonist removal"):
        require_pearl_knockout("absent")
    with pytest.raises(ConfigurationError, match="Pearl knockout"):
        require_pearl_knockout("coevolve")
    with pytest.raises(ConfigurationError, match="aliases are forbidden"):
        assert_passage_taxonomy(refuse_aliases=False)


def test_costless_is_not_absent_on_live_arms() -> None:
    costless = run_match_arm(
        mating="outcross", passage="costless", virulence=32.0, generations=6, seed=101
    )
    absent = run_match_arm(
        mating="outcross", passage="absent", virulence=32.0, generations=6, seed=101
    )
    frozen = run_match_arm(
        mating="outcross", passage="frozen", virulence=32.0, generations=6, seed=101
    )
    assert costless.passage == PASSAGE_COSTLESS
    assert absent.passage == PASSAGE_ABSENT
    assert frozen.passage == PASSAGE_FROZEN
    assert costless.match_debits_by_generation == (0,) * 6
    assert absent.match_debits_by_generation == (0,) * 6
    # costless keeps updating the stock; absent removes the antagonist path.
    assert costless.parasite_frequencies != absent.parasite_frequencies


def test_shewhart_and_cusum_fail_closed() -> None:
    assert shewhart_in_control((), center=1.0, sigma=1.0) is False
    assert shewhart_in_control((1, 2, 1), center=1.0, sigma=0.0) is False
    assert shewhart_in_control((1, 2, 1), center=1.0, sigma=-1.0) is False
    assert shewhart_in_control((1, 1, 1), center=1.0, sigma=1.0) is True
    assert shewhart_in_control((1, 10, 1), center=1.0, sigma=1.0, limit_sigma=3.0) is False
    assert cusum_onset_declared((), reference=0.0, slack_k=0.5, decision_h=2.0) is False
    assert cusum_onset_declared((0, 0, 0), reference=0.0, slack_k=0.5, decision_h=2.0) is False
    assert cusum_onset_declared((0, 0, 0), reference=0.0, slack_k=0.5, decision_h=0.0) is False
    # Strong positive shift crosses a small decision interval.
    assert cusum_onset_declared((5, 5, 5), reference=0.0, slack_k=0.5, decision_h=2.0) is True


def test_observer_residual_fail_closed_and_predicted_cost() -> None:
    assert observer_residual_coherent((), (), band=1.0) is False
    assert observer_residual_coherent((1, 2), (1,), band=1.0) is False
    assert observer_residual_coherent((1, 2), (1, 2), band=-0.1) is False
    assert observer_residual_coherent((1.0, 2.0), (1.0, 2.0), band=0.0) is True
    assert observer_residual_coherent((1.0, 2.0), (1.0, 9.0), band=1.0) is False
    pred = predicted_match_cost(virulence=2.0, type_count=1, specificity_weight=1.0)
    assert pred == 1.0
    with pytest.raises(ConfigurationError):
        predicted_match_cost(virulence=2.0, type_count=1, specificity_weight=1.5)


def test_capability_gates_cannot_invent_a_cycle_or_grant_rq() -> None:
    unpaid = (("a",), ("b",), ("a",))
    unpaid_debits = (0, 0, 0)
    assert debit_backed_cycle(unpaid, unpaid_debits) is False
    assert (
        debit_backed_cycle_capability(
            unpaid,
            unpaid_debits,
            require_shewhart=True,
            shewhart_center=0.0,
            shewhart_sigma=1.0,
        )
        is False
    )
    paid = (("a",), ("b",), ("a",))
    paid_debits = (0, 1, 0)
    assert debit_backed_cycle(paid, paid_debits) is True
    # SPC deny of an otherwise paid cycle.
    assert (
        debit_backed_cycle_capability(
            paid,
            paid_debits,
            require_shewhart=True,
            shewhart_center=0.0,
            shewhart_sigma=0.1,
            shewhart_limit_sigma=1.0,
        )
        is False
    )
    # Missing required SPC parameters fail closed.
    assert (
        debit_backed_cycle_capability(
            paid, paid_debits, require_shewhart=True, shewhart_center=None, shewhart_sigma=1.0
        )
        is False
    )
    report = evaluate_xf_wp1_clauses(
        history=paid,
        match_debits=paid_debits,
        frozen_outcross_extinct=False,
        frozen_selfing_extinct=False,
        costless_outcross_extinct=False,
        costless_selfing_extinct=False,
        shewhart_center=0.0,
        shewhart_sigma=1.0,
        predicted_debits=(0, 1, 0),
        observer_band=0.0,
    )
    assert report.pearl_taxonomy_ok is True
    assert report.pearl_gap_absent is True
    assert report.debit_backed_cycle_raw is True
    assert report.debit_backed_cycle_gated is True
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.claim_ceiling == CLAIM_CEILING
    payload = report.to_dict()
    assert payload["red_queen_proved"] is False
    assert payload["antagonist_removal"] == PASSAGE_ABSENT


def test_pearl_pair_gap_clause() -> None:
    assert (
        pearl_pair_survival_gap_absent(
            frozen_outcross_extinct=False,
            frozen_selfing_extinct=False,
            costless_outcross_extinct=False,
            costless_selfing_extinct=False,
        )
        is True
    )
    # Gap under frozen alone fails the Pearl-pair clause.
    assert (
        pearl_pair_survival_gap_absent(
            frozen_outcross_extinct=False,
            frozen_selfing_extinct=True,
            costless_outcross_extinct=False,
            costless_selfing_extinct=False,
        )
        is False
    )


def test_engine_has_no_infection_tokens() -> None:
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine
