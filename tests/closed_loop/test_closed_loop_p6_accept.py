"""P6 accept: matching-allele debit on the existing ATP clock.

The biological claim stays blocked. ``red_queen_proved`` stays false.
``pattern_holds`` on the development seed is not an evaluation result.
Generation 0 is the same for every seed, because every parasite still
carries the ancestral window. A frozen stock never leaves that window.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import (
    MATCH_LEDGER_REASON,
    ClosedLoopP6Clock,
    classify_oscillation,
    debit_backed_cycle,
    digital_red_queen_pattern,
    frequency_cycles,
    holling_type2_cost,
    mate_outcross,
    run_match_arm,
    run_matching_allele_factorial,
    run_shared_modifier,
    specificity_weight,
    strict_match_alpha,
)
from codontrace.genesis.host_parasite_life_plugin import (
    MATCH_BIT_START,
    OUTCROSS_OUT_BITS,
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
    result = run_matching_allele_factorial()
    by_key = {(arm.mating, arm.passage): arm for arm in result.arms}
    assert result.pattern_holds is False
    assert result.debit_threshold is None
    assert result.first_tested_success is None
    assert result.threshold_kind == "first_tested_grid_value"
    assert result.development_seed is True
    assert result.low_debit_gap is True
    assert result.coevo_cycles is False
    assert by_key[("outcross", "coevolve")].cycles is False
    assert by_key[("outcross", "coevolve")].oscillation != "stable"
    assert by_key[("selfing", "coevolve")].extinct is True
    assert by_key[("outcross", "coevolve")].extinct is False
    assert len(result.grid) == 7
    assert result.grid[0][0].virulence == 0.0
    assert result.grid[-1][0].virulence == 64.0
    assert by_key[("outcross", "coevolve")].birth_atp == 10.0
    assert by_key[("outcross", "coevolve")].digest
    assert result.red_queen_proved is False
    assert result.biological_red_queen_proved is False
    assert result.to_dict()["sexual_maintenance_claimed"] is False
    assert result.to_dict()["energy_model"] == "passage_reset_not_ecological_closure"
    assert result.claim_ceiling == "runtime_observation"
    assert result.to_dict()["euler_stepper_used"] is False
    assert result.to_dict()["holling"] == "type_ii"
    again = run_matching_allele_factorial()
    assert [arm.to_dict() for arm in again.arms] == [arm.to_dict() for arm in result.arms]


def test_neighbor_seed_does_not_meet_the_pattern() -> None:
    result = run_matching_allele_factorial(seed=1)
    assert result.pattern_holds is False
    assert result.red_queen_proved is False
    assert result.debit_threshold is None


def test_four_generations_do_not_finish_the_chase() -> None:
    arm = run_match_arm(mating="selfing", passage="coevolve", virulence=32.0, generations=4)
    assert arm.extinct is False
    assert arm.seed == 7
    assert arm.parasite_mutation == 0.7


def test_biological_claim_stays_blocked() -> None:
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")


def test_clock_debits_only_the_matched_host() -> None:
    clock = ClosedLoopP6Clock.boot(passage="coevolve")
    summary = clock.run_ticks(1, match_cost=1.0)
    assert summary["clock_api"] == "PopulationRunner.step_generation"
    assert summary["generation"] == 1
    assert summary["matched_ids"] == ["h0"]
    assert summary["antagonist_window"] == "000111"
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


def test_shared_census_uses_the_match_passage_not_the_living_window() -> None:
    """Coevolution does not copy the survivor window, and it does not reverse freeze."""

    chased = run_shared_modifier(_PAIR, passage="coevolve", virulence=20.0, generations=8)
    held = run_shared_modifier(_PAIR, passage="frozen", virulence=20.0, generations=8)
    quiet = run_shared_modifier(_PAIR, passage="absent", virulence=20.0, generations=8)
    assert chased.founding_outcross == 2 and chased.founding_selfing == 3
    assert chased.outcross_by_generation == (2, 1, 0, 0, 0, 0, 0, 0)
    assert chased.selfing_by_generation == (1, 1, 1, 1, 1, 1, 1, 1)
    assert chased.match_debits_by_generation == (2, 1, 0, 0, 0, 0, 0, 0)
    assert chased.parasite_window == "001111"
    assert chased.window_history[-1] == ("111000",)
    assert chased.parasite_window != chased.window_history[-1][0]
    assert chased.two_fold_cost_applied is False
    assert chased.cost_name == "mating_effort_atp"
    assert chased.red_queen_proved is False
    assert chased.specificity == "strict"
    assert held.outcross_by_generation == chased.outcross_by_generation
    assert held.selfing_by_generation == chased.selfing_by_generation
    assert held.parasite_window == "000111"
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
    assert chased.match_debits_by_generation == (2, 1, 0, 0, 0, 1, 0, 0)
    assert held.outcross_by_generation == (2,) * 8
    assert held.selfing_by_generation == (1,) * 8
    assert held.match_debits_by_generation == (2, 1, 0, 1, 0, 1, 0, 1)
    assert held.parasite_window == "000111"
    assert chased.red_queen_proved is False
    assert held.red_queen_proved is False


def test_graded_overlap_pays_nothing_on_a_total_mismatch() -> None:
    assert specificity_weight("000111", "000111", "strict") == 1.0
    assert specificity_weight("000111", "111000", "strict") == 0.0
    assert specificity_weight("000111", "000111", "graded") == pytest.approx(0.99)
    assert specificity_weight("000111", "111000", "graded") == 0.0
    assert specificity_weight("000111", "000000", "graded") == pytest.approx(0.451)
    with pytest.raises(ConfigurationError, match="specificity"):
        specificity_weight("000111", "000111", "euler")
    graded = run_match_arm(
        mating="selfing",
        passage="frozen",
        virulence=32.0,
        generations=1,
        specificity="graded",
    )
    strict = run_match_arm(mating="selfing", passage="frozen", virulence=32.0, generations=1)
    assert graded.specificity == "graded"
    assert strict.specificity == "strict"
    assert graded.match_debits_by_generation == strict.match_debits_by_generation == (9,)
    assert "run_type2_campaign" not in (
        _REPO / "src" / "codontrace" / "genesis" / "closed_loop_p6.py"
    ).read_text(encoding="utf-8")


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


def test_generation_zero_is_the_ancestral_window_for_every_seed() -> None:
    for seed in (1, 7, 42):
        selfing = run_match_arm(
            mating="selfing", passage="coevolve", virulence=32.0, generations=1, seed=seed
        )
        outcross = run_match_arm(
            mating="outcross", passage="coevolve", virulence=32.0, generations=1, seed=seed
        )
        assert selfing.match_debits_by_generation == (9,)
        assert selfing.final_hosts == 3
        assert selfing.extinct is False
        assert selfing.mating_fee_debits == 0
        assert outcross.match_debits_by_generation == (8,)
        assert outcross.mating_fee_debits > 0
        assert outcross.extinct is False


def test_frozen_stock_stays_ancestral_when_mutation_is_on() -> None:
    for seed in (1, 7, 42):
        for mating in ("selfing", "outcross"):
            frozen = run_match_arm(
                mating=mating,
                passage="frozen",
                virulence=32.0,
                generations=8,
                seed=seed,
                parasite_mutation=0.7,
            )
            quiet = run_match_arm(
                mating=mating, passage="absent", virulence=32.0, generations=8, seed=seed
            )
            assert frozen.parasite_window == "000111"
            assert frozen.extinct is False
            assert sum(quiet.match_debits_by_generation) == 0
            assert quiet.final_hosts == 12
            assert quiet.parasite_window == "000111"
        assert run_match_arm(
            mating="selfing", passage="frozen", virulence=32.0, generations=8, seed=seed
        ).mating_fee_debits == 0


def test_zero_mutation_does_not_leave_the_ancestral_window() -> None:
    for seed in (1, 7):
        chased = run_match_arm(
            mating="selfing",
            passage="coevolve",
            virulence=32.0,
            generations=8,
            seed=seed,
            parasite_mutation=0.0,
        )
        held = run_match_arm(
            mating="selfing", passage="frozen", virulence=32.0, generations=8, seed=seed
        )
        assert chased.parasite_window == "000111"
        assert chased.final_hosts == held.final_hosts == 3
        assert chased.match_debits_by_generation == held.match_debits_by_generation
        again = run_match_arm(
            mating="outcross",
            passage="coevolve",
            virulence=32.0,
            generations=6,
            seed=seed,
            parasite_mutation=0.0,
        )
        assert again.to_dict() == run_match_arm(
            mating="outcross",
            passage="coevolve",
            virulence=32.0,
            generations=6,
            seed=seed,
            parasite_mutation=0.0,
        ).to_dict()


def test_refused_mutation_and_generation_do_not_run() -> None:
    with pytest.raises(ConfigurationError, match="parasite_mutation"):
        run_match_arm(mating="selfing", passage="absent", parasite_mutation=1.1)
    with pytest.raises(ConfigurationError, match="generations"):
        run_match_arm(mating="selfing", passage="absent", generations=0)


def test_refused_mating_and_passage_do_not_run() -> None:
    with pytest.raises(ConfigurationError, match="mating"):
        run_match_arm(mating="mixed", passage="absent", virulence=0.0)
    with pytest.raises(ConfigurationError, match="passage"):
        run_match_arm(mating="selfing", passage="knockout", virulence=0.0)
    with pytest.raises(ConfigurationError, match="virulence"):
        run_match_arm(mating="selfing", passage="absent", virulence=-0.1)


def test_one_mating_rule_covers_a_singleton_an_odd_count_and_a_pair() -> None:
    from codontrace.genesis.closed_loop_p6 import _spawn, _tape

    def parent(index: int, window: str):
        return _spawn(f"h{index}", _tape(OUTCROSS_OUT_BITS, window), 10.0)

    alone, unmated = mate_outcross([parent(0, "000111")], generation=0, atp=10.0)
    assert alone == [] and unmated == 1
    odd, odd_unmated = mate_outcross(
        [parent(0, "000111"), parent(1, "000111"), parent(2, "111000")],
        generation=0,
        atp=10.0,
    )
    assert len(odd) == 2 and odd_unmated == 1
    pair, pair_unmated = mate_outcross(
        [parent(0, "000111"), parent(1, "111000")], generation=0, atp=10.0
    )
    assert len(pair) == 2 and pair_unmated == 0
    assert pair[0].atp_state.runtime_available == 10.0
    copied, _ = mate_outcross(
        [parent(0, "000111"), parent(1, "111000")],
        generation=0,
        atp=10.0,
        recombine=False,
    )
    assert [child.genome.to_compact()[-6:] for child in copied] == ["000111", "111000"]
    preferred, _ = mate_outcross(
        [parent(0, "000111"), parent(1, "000111"), parent(2, "111000")],
        generation=0,
        atp=10.0,
        mate_choice="disassortative",
    )
    assert [child.genome.to_compact()[-6:] for child in odd] != [
        child.genome.to_compact()[-6:] for child in preferred
    ]
    rare = run_shared_modifier(
        (("outcross", "000111"),), passage="absent", virulence=0.0, generations=1
    )
    assert rare.unmated_outcross_by_generation == (1,)
    assert rare.outcross_by_generation == (0,)
    source = (_REPO / "src" / "codontrace" / "genesis" / "closed_loop_p6.py").read_text(
        encoding="utf-8"
    )
    assert "def _outcross_children" not in source
    assert "def _paired_outcross_children" not in source


def test_non_finite_inputs_are_refused() -> None:
    with pytest.raises(ConfigurationError, match="virulence"):
        run_match_arm(mating="selfing", passage="absent", virulence=float("nan"))
    with pytest.raises(ConfigurationError, match="birth_atp"):
        run_match_arm(mating="selfing", passage="absent", birth_atp=float("inf"))
    with pytest.raises(ConfigurationError, match="generations"):
        run_match_arm(mating="selfing", passage="absent", generations=True)  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError, match="parasite_mutation"):
        run_match_arm(mating="selfing", passage="absent", parasite_mutation=float("nan"))


def test_one_paid_return_is_transient_not_a_stable_cycle() -> None:
    hosts = ((("a", 2),), (("b", 2),), (("a", 2),))
    parasites = ((("p", 2),), (("q", 2),), (("p", 2),))
    assert classify_oscillation(hosts, parasites, (0, 1, 0)) == "transient"
    repeated = hosts + ((("b", 2),), (("a", 2),))
    parasite_path = parasites + ((("r", 2),), (("p", 2),))
    assert classify_oscillation(repeated, parasite_path, (0, 1, 0, 1, 0)) == "stable"
    assert classify_oscillation(hosts, parasites, (0, 0, 0)) == "forced"
    assert debit_backed_cycle((("a",), ("b",), ("a",)), (0, 1, 0)) is True
    assert run_match_arm(
        mating="outcross", passage="coevolve", virulence=32.0, generations=4
    ).to_dict()["sexual_maintenance_claimed"] is False


def test_costless_passage_keeps_mutation_and_charges_nothing() -> None:
    costless = run_match_arm(mating="outcross", passage="costless", virulence=32.0, generations=2)
    zero = run_match_arm(mating="outcross", passage="coevolve", virulence=0.0, generations=2)
    absent = run_match_arm(mating="outcross", passage="absent", virulence=32.0, generations=2)
    assert costless.match_debits_by_generation == (0, 0)
    assert zero.match_debits_by_generation == (0, 0)
    assert absent.match_debits_by_generation == (0, 0)
    assert absent.parasite_window == "000111"
    assert costless.parasite_window != absent.parasite_window
    assert zero.parasite_frequencies != absent.parasite_frequencies
    assert costless.energy_reset is True
    assert costless.parasite_stock_fixed is True
    assert costless.parasite_n == 12
    assert len(costless.initial_frequencies) > 0
