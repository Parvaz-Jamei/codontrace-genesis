"""P6 accept: matching-allele debit on the existing ATP clock.

The biological claim stays blocked. ``red_queen_proved`` on the factorial is
only the digital knockout predicate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import (
    MATCH_LEDGER_REASON,
    ClosedLoopP6Clock,
    digital_red_queen_pattern,
    holling_type2_cost,
    run_matching_allele_factorial,
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


def test_factorial_answers_above_a_debit_threshold() -> None:
    result = run_matching_allele_factorial(generations=4)
    by_key = {(arm.mating, arm.passage): arm for arm in result.arms}
    assert result.debit_threshold == 32.0
    assert by_key[("selfing", "coevolve")].extinct
    assert not by_key[("outcross", "coevolve")].extinct
    assert by_key[("outcross", "coevolve")].cycles
    assert by_key[("outcross", "coevolve")].mating_fee_debits > 0
    assert by_key[("selfing", "coevolve")].mating_fee_debits == 0
    assert not by_key[("selfing", "frozen")].extinct
    assert not by_key[("outcross", "frozen")].extinct
    assert not by_key[("outcross", "frozen")].cycles
    assert not by_key[("selfing", "absent")].extinct
    assert not by_key[("outcross", "absent")].extinct
    assert result.low_debit_gap is False
    assert result.zero_debit_gap is False
    assert result.pattern_holds is True
    assert result.red_queen_proved is True
    assert result.biological_red_queen_proved is False
    assert result.claim_ceiling == "runtime_observation"
    assert result.to_dict()["euler_stepper_used"] is False
    assert result.to_dict()["holling"] == "type_ii"
    again = run_matching_allele_factorial(generations=4)
    assert [arm.to_dict() for arm in again.arms] == [arm.to_dict() for arm in result.arms]


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
