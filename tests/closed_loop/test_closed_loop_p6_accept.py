"""P6 accept: matching-allele debit on the existing ATP clock.

The biological claim stays blocked. ``red_queen_proved`` stays false.
Virulence 32 is a witness of an unpaid name-set orbit, not a debit onset.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import (
    MATCH_LEDGER_REASON,
    ClosedLoopP6Clock,
    debit_backed_cycle,
    digital_red_queen_pattern,
    frequency_cycles,
    holling_type2_cost,
    run_match_arm,
    run_matching_allele_factorial,
    run_shared_modifier,
    strict_match_alpha,
)
from codontrace.genesis.host_parasite_life_plugin import (
    MATCH_BIT_START,
    ClosedLoopHPLifeConfig,
    coding_bits_for_execution,
)
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME

_REPO = Path(__file__).resolve().parents[2]


def test_exact_window_is_the_diagonal_not_the_euler_stepper() -> None:
    assert strict_match_alpha("000111", "000111") == 1.0
    assert strict_match_alpha("000111", "111000") == 0.0
    assert strict_match_alpha("", "000111") == 0.0


def test_holling_debit_depends_on_density() -> None:
    assert holling_type2_cost(2.0, 0) == 0.0
    rare = holling_type2_cost(2.0, 1)
    common = holling_type2_cost(2.0, 3)
    assert rare == 1.0
    assert common > rare


def test_predicate_is_the_storm_rule_not_the_gap_alone() -> None:
    full = dict(
        coevo_outcross_extinct=False,
        coevo_selfing_extinct=True,
        frozen_outcross_extinct=False,
        frozen_selfing_extinct=False,
        zero_outcross_extinct=False,
        zero_selfing_extinct=False,
        coevo_cycles=True,
        frozen_cycles=False,
        low_debit_gap=False,
        debit_threshold=32.0,
    )
    assert digital_red_queen_pattern(**full)
    assert not digital_red_queen_pattern(**{**full, "coevo_cycles": False})
    assert not digital_red_queen_pattern(**{**full, "frozen_cycles": True})
    assert not digital_red_queen_pattern(**{**full, "low_debit_gap": True})
    assert not digital_red_queen_pattern(**{**full, "zero_selfing_extinct": True})
    assert not digital_red_queen_pattern(**{**full, "debit_threshold": None})


def test_factorial_does_not_set_the_flag() -> None:
    result = run_matching_allele_factorial(generations=4)
    by_key = {(arm.mating, arm.passage): arm for arm in result.arms}
    assert result.debit_threshold is None
    assert by_key[("outcross", "coevolve")].mating_fee_debits > 0
    assert by_key[("selfing", "coevolve")].mating_fee_debits == 0
    assert by_key[("outcross", "coevolve")].cycles is False
    assert result.red_queen_proved is False
    assert result.pattern_holds is False
    assert result.biological_red_queen_proved is False
    assert result.claim_ceiling == "runtime_observation"
    assert result.to_dict()["euler_stepper_used"] is False
    assert result.to_dict()["holling"] == "type_ii"
    again = run_matching_allele_factorial(generations=4)
    assert [arm.to_dict() for arm in again.arms] == [arm.to_dict() for arm in result.arms]


def test_unpaid_name_orbit_is_not_the_cycle_clause() -> None:
    """Virulence 32 witnesses the exchange orbit. It is not an onset."""

    arm = run_match_arm(mating="outcross", passage="coevolve", virulence=32.0, generations=4)
    assert arm.match_debits_by_generation == (2, 0, 0, 0)
    history = arm.window_history
    assert history[0] == ("000000", "111111")
    assert history[1] == ("000111", "111000")
    assert history[2] == history[0]
    assert history[3] == history[1]
    assert frequency_cycles(history) is True
    assert debit_backed_cycle(history, arm.match_debits_by_generation) is False
    assert arm.cycles is False


def test_biological_claim_stays_blocked() -> None:
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")


def test_clock_debits_only_the_matched_host() -> None:
    clock = ClosedLoopP6Clock.boot(passage="coevolve")
    summary = clock.run_ticks(1, match_cost=1.0)
    assert summary["clock_api"] == "PopulationRunner.step_generation"
    assert summary["generation"] == 1
    assert summary["matched_ids"] == ["h0"]
    assert summary["antagonist_window"] == "111000"
    assert summary["red_queen_proved"] is False
    frozen = ClosedLoopP6Clock.boot(passage="frozen")
    frozen_summary = frozen.run_ticks(1, match_cost=1.0)
    assert frozen_summary["antagonist_window"] == "000111"
    assert frozen_summary["matched_ids"] == ["h0"]
    hosts = [
        org
        for org in frozen.runner.population.organisms
        if org.id != "p0"
    ]
    reasons = {
        org.id: [
            entry.get("reason")
            for entry in org.atp_state.runtime.to_dict()["ledger"]
            if isinstance(entry, dict)
        ]
        for org in hosts
    }
    assert MATCH_LEDGER_REASON in reasons["h0"]
    assert MATCH_LEDGER_REASON not in reasons["h1"]
    assert MATCH_LEDGER_REASON not in reasons["h2"]


def test_recognition_stays_off_the_brain_and_out_of_the_default_config() -> None:
    tape = LIFE_LOOP_EATER_GENOME + "100000" + "001" + "000111"
    plain = ClosedLoopHPLifeConfig(enabled=True, outcross_enabled=True)
    # Match off: kappa and the mating codon drop, and the tail slides onto the brain.
    assert coding_bits_for_execution(tape, plain) == LIFE_LOOP_EATER_GENOME + "000111"
    matched = ClosedLoopHPLifeConfig(
        enabled=True, outcross_enabled=True, match_locus_enabled=True
    )
    assert coding_bits_for_execution(tape, matched) == LIFE_LOOP_EATER_GENOME
    assert "match_locus_enabled" not in ClosedLoopHPLifeConfig().to_dict()
    restored = ClosedLoopHPLifeConfig.from_dict(
        {"match_locus_enabled": True, "match_bit_start": 18, "match_bit_width": 6}
    )
    assert restored.match_locus_enabled is True
    assert MATCH_BIT_START == 18
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine
    source = (_REPO / "src" / "codontrace" / "genesis" / "closed_loop_p6.py").read_text(
        encoding="utf-8"
    )
    assert "HostParasiteWorld" not in source
    assert "run_type2_campaign" not in source


def test_debit_inside_the_repeat_is_the_cycle_not_the_first_visit() -> None:
    orbit = (("000000",), ("111111",), ("000000",))
    assert frequency_cycles(orbit) is True
    assert frequency_cycles((("000000",), ("000000",))) is False
    assert debit_backed_cycle(orbit, (1, 0, 0)) is False
    assert debit_backed_cycle(orbit, (0, 1, 0)) is True
    with pytest.raises(ConfigurationError, match="match debits"):
        debit_backed_cycle(orbit, (0, 0))


def test_holling_crosses_the_birth_account_with_density() -> None:
    """Birth ATP is 10. H=1 is virulence/2. Three copies use 3/4 of virulence."""

    assert holling_type2_cost(16.0, 1) == 8.0
    assert holling_type2_cost(16.0, 3) == 12.0
    assert holling_type2_cost(20.0, 1) == 10.0
    assert holling_type2_cost(32.0, 1) == 16.0
    with pytest.raises(ConfigurationError, match="virulence"):
        holling_type2_cost(-1.0, 1)


def test_density_keeps_one_selfing_host_at_16_and_kills_the_arm_at_20() -> None:
    lived = run_match_arm(mating="selfing", passage="coevolve", virulence=16.0, generations=4)
    assert lived.extinct is False
    assert lived.final_hosts == 1
    assert lived.cycles is False
    assert lived.match_debits_by_generation == (3, 1, 1, 1)
    assert lived.window_history == (("111000",), ("111000",), ("111000",), ("111000",))
    assert lived.parasite_window == "111000"
    frozen = run_match_arm(mating="selfing", passage="frozen", virulence=16.0, generations=4)
    assert frozen.extinct is False
    assert frozen.parasite_window == "000111"
    assert frozen.match_debits_by_generation == (3, 0, 0, 0)
    for virulence in (20.0, 32.0):
        dead = run_match_arm(
            mating="selfing", passage="coevolve", virulence=virulence, generations=4
        )
        assert dead.extinct is True
        assert dead.cycles is False
        assert dead.match_debits_by_generation == (3, 1, 0, 0)


def test_outcross_survival_gap_is_an_unpaid_orbit_from_16_through_32() -> None:
    for virulence in (16.0, 20.0, 32.0):
        arm = run_match_arm(
            mating="outcross", passage="coevolve", virulence=virulence, generations=4
        )
        assert arm.extinct is False
        assert arm.cycles is False
        assert arm.match_debits_by_generation == (2, 0, 0, 0)
        assert frequency_cycles(arm.window_history) is True


def test_frozen_paid_flip_does_not_become_the_factorial_cycle() -> None:
    paid = run_match_arm(mating="outcross", passage="frozen", virulence=16.0, generations=4)
    assert paid.match_debits_by_generation == (2, 1, 0, 1)
    assert paid.cycles is True
    assert paid.parasite_window == "000111"
    assert paid.window_history[2] == paid.window_history[0]
    absent = run_match_arm(mating="outcross", passage="absent", virulence=32.0, generations=4)
    assert absent.match_debits_by_generation == (0, 0, 0, 0)
    assert absent.final_hosts == 4
    assert absent.parasite_window == "000111"
    assert "000111" in absent.window_history[0]
    result = run_matching_allele_factorial(generations=4)
    assert result.arms[0].virulence == 64.0
    assert result.low_debit_gap is True
    assert result.frozen_cycles is False
    assert result.coevo_cycles is False
    assert result.zero_debit_gap is False
    assert result.pattern_holds is False
    assert result.debit_threshold is None
    assert result.red_queen_proved is False


def test_selfing_extinction_needs_the_chase_and_still_is_not_the_flag() -> None:
    """A frozen miss keeps the rare window. Updating onto it removes the lineage."""

    for virulence in (20.0, 32.0):
        chased = run_match_arm(
            mating="selfing", passage="coevolve", virulence=virulence, generations=4
        )
        held = run_match_arm(
            mating="selfing", passage="frozen", virulence=virulence, generations=4
        )
        skipped = run_match_arm(
            mating="selfing", passage="absent", virulence=virulence, generations=4
        )
        sexual = run_match_arm(
            mating="outcross", passage="coevolve", virulence=virulence, generations=4
        )
        assert chased.extinct is True
        assert chased.match_debits_by_generation == (3, 1, 0, 0)
        assert chased.parasite_window == "111000"
        assert chased.window_history[0] == ("111000",)
        assert chased.window_history[1] == ()
        assert held.extinct is False
        assert held.final_hosts == 1
        assert held.parasite_window == "000111"
        assert held.match_debits_by_generation == (3, 0, 0, 0)
        assert held.window_history == (("111000",), ("111000",), ("111000",), ("111000",))
        assert skipped.match_debits_by_generation == (0, 0, 0, 0)
        assert skipped.final_hosts == 4
        assert sexual.extinct is False
        assert sexual.cycles is False
        assert sexual.match_debits_by_generation == (2, 0, 0, 0)


def test_host_parasite_profile_blocks_intelligence_words() -> None:
    for claim in ("intelligence", "collective_intelligence", "agi", "tokyo_type1_passed"):
        with pytest.raises(ConfigurationError, match="blocked"):
            assert_claim_allowed(claim)


_PAIR = (
    ("selfing", "000111"),
    ("selfing", "000111"),
    ("selfing", "111000"),
    ("outcross", "000111"),
    ("outcross", "111000"),
)
_RARE = (
    ("selfing", "000111"),
    ("selfing", "000111"),
    ("selfing", "111000"),
    ("outcross", "111000"),
)


def test_extinction_gap_closes_when_the_window_is_not_updated() -> None:
    """Outcross stays alive either way. Only the selfing death is passage-specific."""

    for virulence in (20.0, 32.0):
        arms = {
            (mating, passage): run_match_arm(
                mating=mating, passage=passage, virulence=virulence, generations=4
            )
            for mating in ("outcross", "selfing")
            for passage in ("coevolve", "frozen", "absent")
        }
        assert arms[("selfing", "coevolve")].extinct is True
        assert arms[("outcross", "coevolve")].extinct is False
        assert arms[("outcross", "coevolve")].cycles is False
        assert arms[("selfing", "frozen")].extinct is False
        assert arms[("outcross", "frozen")].extinct is False
        assert arms[("selfing", "absent")].extinct is False
        assert arms[("outcross", "absent")].extinct is False
    below = run_match_arm(mating="selfing", passage="coevolve", virulence=18.0, generations=4)
    assert below.extinct is False


def test_unpaid_outcross_orbit_is_still_unpaid_at_generation_20() -> None:
    arm = run_match_arm(mating="outcross", passage="coevolve", virulence=20.0, generations=20)
    assert arm.match_debits_by_generation[0] == 2
    assert set(arm.match_debits_by_generation[1:]) == {0}
    assert len(arm.match_debits_by_generation) == 20
    assert arm.cycles is False
    assert frequency_cycles(arm.window_history) is True
    assert arm.extinct is False
    assert arm.window_history[19] == arm.window_history[1]


def test_extinction_step_is_where_holling_meets_the_birth_account() -> None:
    assert holling_type2_cost(12.0, 3) == 9.0
    assert holling_type2_cost(14.0, 3) == 10.5
    assert holling_type2_cost(18.0, 1) == 9.0
    assert holling_type2_cost(20.0, 1) == 10.0
    still_common = run_match_arm(mating="selfing", passage="coevolve", virulence=12.0, generations=4)
    culled = run_match_arm(mating="selfing", passage="coevolve", virulence=14.0, generations=4)
    one_copy_lives = run_match_arm(mating="selfing", passage="coevolve", virulence=18.0, generations=4)
    assert still_common.extinct is False and still_common.final_hosts == 4
    assert culled.extinct is False and culled.final_hosts == 1
    assert one_copy_lives.extinct is False and one_copy_lives.final_hosts == 1
    for virulence in (20.0, 22.0, 32.0):
        dead = run_match_arm(mating="selfing", passage="coevolve", virulence=virulence, generations=4)
        held = run_match_arm(mating="selfing", passage="frozen", virulence=virulence, generations=4)
        sexual = run_match_arm(mating="outcross", passage="coevolve", virulence=virulence, generations=4)
        assert dead.extinct is True
        assert held.extinct is False and held.final_hosts == 1
        assert sexual.extinct is False and sexual.cycles is False


def test_shared_passage_flips_which_codon_remains() -> None:
    chased = run_shared_modifier(_PAIR, passage="coevolve", virulence=20.0, generations=8)
    held = run_shared_modifier(_PAIR, passage="frozen", virulence=20.0, generations=8)
    quiet = run_shared_modifier(_PAIR, passage="absent", virulence=20.0, generations=8)
    assert chased.founding_outcross == 2 and chased.founding_selfing == 3
    assert chased.outcross_by_generation == (2, 2, 2, 2, 2, 2, 2, 2)
    assert chased.selfing_by_generation == (1, 1, 0, 0, 0, 0, 0, 0)
    assert chased.match_debits_by_generation == (2, 0, 1, 0, 0, 0, 0, 0)
    assert debit_backed_cycle(chased.window_history, chased.match_debits_by_generation) is True
    assert chased.two_fold_cost_applied is False
    assert chased.cost_name == "mating_effort_atp"
    assert chased.red_queen_proved is False
    assert held.outcross_by_generation == (2, 1, 0, 0, 0, 0, 0, 0)
    assert held.selfing_by_generation == (1,) * 8
    assert held.parasite_window == "000111"
    assert held.window_history[-1] == ("111000",)
    assert held.red_queen_proved is False
    assert quiet.outcross_by_generation == (2,) * 8
    assert quiet.selfing_by_generation == (3,) * 8
    assert quiet.match_debits_by_generation == (0,) * 8
    again = run_shared_modifier(_PAIR, passage="coevolve", virulence=20.0, generations=8)
    assert again.to_dict() == chased.to_dict()


def test_sublethal_shared_debit_is_not_specific_to_coevolution() -> None:
    chased = run_shared_modifier(_PAIR, passage="coevolve", virulence=16.0, generations=8)
    held = run_shared_modifier(_PAIR, passage="frozen", virulence=16.0, generations=8)
    assert chased.outcross_by_generation == (2,) * 8
    assert chased.selfing_by_generation == (1,) * 8
    assert chased.match_debits_by_generation == (2, 0, 1, 0, 1, 0, 1, 0)
    assert held.outcross_by_generation == (2,) * 8
    assert held.selfing_by_generation == (1,) * 8
    assert held.match_debits_by_generation == (2, 1, 0, 1, 0, 1, 0, 1)
    assert chased.red_queen_proved is False
    assert held.red_queen_proved is False


def test_one_outcross_codon_is_unmated_and_identical_windows_do_not_escape() -> None:
    rare = run_shared_modifier(_RARE, passage="absent", virulence=0.0, generations=4)
    assert rare.founding_outcross == 1
    assert rare.unmated_outcross_by_generation == (1, 0, 0, 0)
    assert rare.outcross_by_generation == (0, 0, 0, 0)
    assert rare.red_queen_proved is False
    same = (
        ("selfing", "000111"),
        ("selfing", "000111"),
        ("outcross", "000111"),
        ("outcross", "000111"),
    )
    caught = run_shared_modifier(same, passage="coevolve", virulence=20.0, generations=4)
    spared = run_shared_modifier(same, passage="absent", virulence=20.0, generations=4)
    assert caught.outcross_by_generation == (0, 0, 0, 0)
    assert caught.selfing_by_generation == (0, 0, 0, 0)
    assert spared.outcross_by_generation == (2, 2, 2, 2)
    assert spared.selfing_by_generation == (2, 2, 2, 2)


def test_refused_mating_and_passage_do_not_run() -> None:
    with pytest.raises(ConfigurationError, match="mating"):
        run_match_arm(mating="mixed", passage="absent", virulence=0.0)
    with pytest.raises(ConfigurationError, match="passage"):
        run_match_arm(mating="selfing", passage="knockout", virulence=0.0)
    with pytest.raises(ConfigurationError, match="virulence"):
        run_match_arm(mating="selfing", passage="absent", virulence=-0.1)
