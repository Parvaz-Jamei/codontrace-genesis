"""Phase-3 frequency panel. Expectations are computed here, not copied from the module's last return.

No measurement history is started. Seeds 9501-9504 are not booted.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    _DISTINCT_WINDOWS,
    STRUCT_BIRTH_ATP,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
)
from codontrace.genesis.rq_bidirectional_timeshift_confirm import MEASUREMENT_FLOOR, VERDICT_BLOCKED
from codontrace.genesis.rq_mechanism_v2_phase3 import (
    ARCHIVE_SCHEMA,
    BRANCH_COMMON_A,
    BRANCH_LOCKED,
    MAX_WORKERS,
    NO_MEASUREMENT_D_SENTENCE,
    PHASE3_CENSUS,
    PHASE3_FORBIDDEN_SEEDS,
    PHASE3_SEEDS,
    PHASE3_SELECTION_SEED,
    TURNOVER_MULTIPLE,
    VERDICT_NOT_DECLARED,
    _parasite_founders,
    assay_archive,
    assert_phase3_seeds,
    assess_phase3,
    build_host_seats,
    build_phase3_arm,
    choose_host_pair,
    control_gap,
    estimand_d,
    execute_phase3,
    horizon_from_turnover,
    host_genome,
    recognition_table,
    render_phase3_lock,
    resolve_workers,
    run_branch,
)

# Independent instrument. Not read back from a previous call.
SCALE = float(STRUCT_VIRULENCE) * float(STRUCT_STEAL_FRACTION)
TEST_SEED = 9490


def _mismatch(left: str, right: str) -> float:
    matches = sum(1 for a, b in zip(left, right, strict=True) if a == b)
    return matches / 6.0


def test_two_hosts_are_genomes_not_class_labels() -> None:
    genome_a = host_genome("000000")
    genome_b = host_genome("111111")
    # The tape is the program, the mating codon, and the 6-bit window.
    assert len(genome_a) == len(genome_b)
    assert len(genome_a) > 6
    assert genome_a != "000000"
    assert genome_b != "111111"
    assert genome_a.endswith("000000")
    assert genome_b.endswith("111111")
    assert genome_a[: len(genome_a) - 6] == genome_b[: len(genome_b) - 6]
    assert "class" not in genome_a
    seats = build_host_seats("000000", "111111", common="A")
    assert {seat["host_id"] for seat in seats if seat["window"] == "000000"}
    assert all(seat["genome"] == genome_a for seat in seats if seat["window"] == "000000")
    assert all(seat["genome"] == genome_b for seat in seats if seat["window"] == "111111")
    # 4/5 and 1/5 of 60, from the interleave rule, not from a returned count field.
    assert sum(1 for seat in seats if seat["window"] == "000000") == 60 - 60 // 5
    assert sum(1 for seat in seats if seat["window"] == "111111") == 60 // 5


def test_chooser_matches_an_independent_bit_rule() -> None:
    rows = recognition_table()
    # Every unordered pair of the 16 structural windows: C(16, 2) = 120.
    assert len(rows) == 16 * 15 // 2
    best_gap = -1.0
    best_pair: tuple[str, str] | None = None
    for left in _DISTINCT_WINDOWS:
        for right in _DISTINCT_WINDOWS:
            if left >= right:
                continue
            # A parasite whose window is `left` has affinity `left` vs `left` = 1
            # and affinity `left` vs `right` = matching bits / 6. Birth ATP is
            # above the debit, so infectivity equals affinity.
            gap = 1.0 - _mismatch(left, right)
            pair = (left, right)
            if gap > best_gap or (gap == best_gap and (best_pair is None or pair < best_pair)):
                best_gap = gap
                best_pair = pair
    assert best_pair == ("000000", "111111")
    assert best_gap == pytest.approx(1.0)
    chosen = choose_host_pair(rows)
    assert (chosen["window_first"], chosen["window_second"]) == best_pair
    assert float(chosen["recognition_gap"]) == pytest.approx(1.0)
    assert chosen["outcross_cost_first"] == chosen["outcross_cost_second"]
    assert str(chosen["genome_first"]).endswith("000000")
    assert str(chosen["genome_second"]).endswith("111111")


def test_host_mix_stays_fixed_and_there_is_no_be_common_reward(tmp_path: Path) -> None:
    source = Path("src/codontrace/genesis/rq_mechanism_v2_phase3.py").read_text(encoding="utf-8")
    for banned in ("be_common", "frequency_reward", "common_bonus", "host_frequency_score", "cpu_count"):
        assert banned not in source
    seats = build_host_seats("000000", "111111", common="A")
    founders = _parasite_founders()
    arm = build_phase3_arm(TEST_SEED, BRANCH_COMMON_A, seats, founders)
    expected_a = PHASE3_CENSUS - PHASE3_CENSUS // 5
    expected_b = PHASE3_CENSUS // 5
    for _generation in range(2):
        arm.run_generations(1)
        seen = Counter(arm.last_contact_host_windows)
        assert seen["000000"] == expected_a
        assert seen["111111"] == expected_b
        assert sum(seen.values()) == PHASE3_CENSUS
    account = arm.antagonist_pop.energy_accounts[-1]
    # The books close with contact income only. A be-common bonus would be a
    # second income the residual identity does not have.
    assert account.reproduction_cost == 0.0
    assert abs(account.residual()) < 1e-9
    assert not hasattr(account, "frequency_income")
    archive = tmp_path / "archive.jsonl"
    summary = run_branch(
        seed=TEST_SEED,
        branch=BRANCH_COMMON_A,
        seats=seats,
        founders=founders,
        generations=1,
        archive_path=archive,
    )
    assert summary["failed"] is None
    row = json.loads(archive.read_text(encoding="utf-8").splitlines()[0])
    assert row["schema"] == ARCHIVE_SCHEMA
    assert row["red_queen_proved"] is False
    assert Counter(row["contact_host_windows"])["000000"] == expected_a


def test_assay_does_not_mutate_the_conditioning_archive(tmp_path: Path) -> None:
    seats = build_host_seats("000000", "111111", common="A")
    founders = _parasite_founders()
    archive = tmp_path / "archive.jsonl"
    summary = run_branch(
        seed=TEST_SEED,
        branch=BRANCH_COMMON_A,
        seats=seats,
        founders=founders,
        generations=1,
        archive_path=archive,
    )
    assert summary["failed"] is None
    before = archive.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    genome_a = host_genome("000000")
    genome_b = host_genome("111111")
    scored = assay_archive(
        archive,
        window_a="000000",
        genome_a=genome_a,
        window_b="111111",
        genome_b=genome_b,
    )
    assert archive.read_bytes() == before
    assert scored["archive_sha256"] == digest
    assert scored["archive_unchanged"] is True
    assert scored["evolution"] is False
    assert scored["red_queen_proved"] is False
    # Birth ATP does not clip a perfect match: scale is virulence * steal.
    assert SCALE == pytest.approx(1.2)
    assert STRUCT_BIRTH_ATP > SCALE


def test_unmeasurable_is_not_zero() -> None:
    missing = estimand_d(None, 0.2, 0.3, 0.4)
    assert missing is None
    assert missing != 0.0
    assert control_gap(None, 0.2) is None
    assert control_gap(None, 0.2) != 0.0
    # Hand values. D = (0.80 - 0.20) - (0.30 - 0.70) = 0.60 - (-0.40) = 1.00.
    measured = estimand_d(0.80, 0.20, 0.30, 0.70)
    assert measured == pytest.approx((0.80 - 0.20) - (0.30 - 0.70))
    assert measured == pytest.approx(1.0)
    # The control gap is reported beside D and is not written over it.
    assert control_gap(0.55, 0.25) == pytest.approx(0.30)
    assert control_gap(0.55, 0.25) != measured


def test_incomplete_locked_seeds_are_blocked_not_negative() -> None:
    assert MEASUREMENT_FLOOR == 12
    # Three negative histories and one missing seed. Their mean is -0.4.
    # Filling the hole with zero would move that mean to -0.3. Neither number
    # is a verdict.
    present_mean = (-0.4 + -0.5 + -0.3) / 3.0
    assert present_mean == pytest.approx(-0.4)
    imputed = (-0.4 + -0.5 + -0.3 + 0.0) / 4.0
    assert imputed == pytest.approx(-0.3)
    report = assess_phase3(
        {
            9501: {"D": -0.4, "control_gap": 0.1},
            9502: {"D": -0.5, "control_gap": 0.1},
            9503: {"D": -0.3, "control_gap": 0.1},
        },
        PHASE3_SEEDS,
    )
    assert report["verdict"] == VERDICT_BLOCKED
    assert report["verdict"] != "NEGATIVE_IN_MODEL"
    assert report["verdict"] != "SUPPORTED_IN_MODEL"
    assert report["n_locked"] == 4
    assert report["n_used"] == 3
    assert report["dropped_seeds"] == [9504]
    assert report["D_mean"] is None
    assert report["D_mean"] != present_mean
    assert report["D_mean"] != imputed
    assert report["importance_bound"] is None
    assert report["supported_forbidden"] is True
    assert report["mde_is_importance_bound"] is False
    assert report["measurement_floor"] == 12
    assert report["red_queen_proved"] is False
    missing_row = next(row for row in report["per_seed"] if row["seed"] == 9504)
    assert missing_row["D"] is None
    assert missing_row["D"] != 0.0


def test_complete_sample_cannot_be_supported_while_importance_is_undeclared() -> None:
    report = assess_phase3(
        {seed: {"D": 1.0, "control_gap": 0.0} for seed in PHASE3_SEEDS},
        PHASE3_SEEDS,
    )
    assert report["n_locked"] == 4
    assert report["n_used"] == 4
    assert report["dropped_seeds"] == []
    assert report["D_mean"] == pytest.approx(1.0)
    assert report["verdict"] == VERDICT_NOT_DECLARED
    assert report["verdict"] != "SUPPORTED_IN_MODEL"
    assert report["supported_forbidden"] is True
    assert report["importance_bound"] is None
    assert report["red_queen_proved"] is False
    with pytest.raises(ConfigurationError, match="forbidden"):
        assert_phase3_seeds([PHASE3_SELECTION_SEED])
    with pytest.raises(ConfigurationError, match="forbidden"):
        assert_phase3_seeds([9401])
    assert 9401 in PHASE3_FORBIDDEN_SEEDS
    assert PHASE3_SELECTION_SEED not in PHASE3_SEEDS


def test_horizon_comes_from_turnover_and_unmeasurable_is_not_a_horizon() -> None:
    # census 60, 30 seated newborns: replacement time is 2 generations.
    # Three replacement times, pre-declared, is 6. Not a D sign.
    locked = horizon_from_turnover(mean_newborns=30.0, census=60, measurable=True)
    assert locked["replacement_generations"] == pytest.approx(2.0)
    assert locked["turnover_multiple"] == TURNOVER_MULTIPLE == 3
    assert locked["conditioning_generations"] == 6
    with pytest.raises(ConfigurationError, match="unmeasurable"):
        horizon_from_turnover(mean_newborns=0.0, census=60, measurable=True)
    with pytest.raises(ConfigurationError, match="unmeasurable"):
        horizon_from_turnover(mean_newborns=30.0, census=60, measurable=False)


def test_non_evolving_branch_does_not_change_parasite_genotypes() -> None:
    seats_a = build_host_seats("000000", "111111", common="A")
    seats_b = build_host_seats("000000", "111111", common="B")
    assert sum(1 for seat in seats_b if seat["window"] == "111111") == 48
    assert sum(1 for seat in seats_b if seat["window"] == "000000") == 12
    founders = _parasite_founders()
    founder_counts = Counter(unit.window for unit in founders.units)
    for seats in (seats_a, seats_b):
        arm = build_phase3_arm(TEST_SEED, BRANCH_LOCKED, seats, founders)
        assert arm.passage == "frozen"
        arm.run_generations(3)
        pop = arm.antagonist_pop
        assert Counter(pop.windows()) == founder_counts
        assert sum(int(ledger.mutation_events) for ledger in pop.ledgers) == 0
        assert all(ledger.mode == "frozen" for ledger in pop.ledgers)
    evolving = build_phase3_arm(TEST_SEED, BRANCH_COMMON_A, seats_a, founders)
    assert evolving.passage == "coevolve"
    assert evolving.passage != "frozen"


def test_workers_cap_and_lock_has_no_measurement_d() -> None:
    assert resolve_workers(None) == 4
    assert resolve_workers(4) == MAX_WORKERS == 4
    with pytest.raises(ConfigurationError, match="workers"):
        resolve_workers(7)
    with pytest.raises(ConfigurationError, match="workers"):
        resolve_workers(8)
    selection = {
        "chosen_pair": {
            "exemplar_id_a": "host-A-001",
            "exemplar_id_b": "host-B-001",
            "genome_a": host_genome("000000"),
            "genome_b": host_genome("111111"),
            "outcross_cost_a": 1.0,
            "outcross_cost_b": 1.0,
            "recognition_gap": 1.0,
            "shared_prefix": host_genome("000000")[:-6],
            "window_a": "000000",
            "window_b": "111111",
        },
        "horizon": {
            "census": 60,
            "conditioning_generations": 6,
            "generation_time": "one antagonist advance per engine generation",
            "mean_seated_newborns": 30.0,
            "replacement_generations": 2.0,
            "turnover_multiple": 3,
        },
        "measurement_D": None,
        "measurement_histories_run": False,
    }
    text = render_phase3_lock(selection, code_commit="abc123")
    assert NO_MEASUREMENT_D_SENTENCE in text
    assert text.count(NO_MEASUREMENT_D_SENTENCE) >= 2
    assert "9501, 9502, 9503, 9504" in text
    assert "undeclared" in text
    assert "SUPPORTED is forbidden" in text
    assert "at most 4" in text
    assert "D =" not in text
    assert "D=" not in text
    poisoned = dict(selection)
    poisoned["measurement_D"] = 0.25
    with pytest.raises(ConfigurationError, match="measurement D"):
        render_phase3_lock(poisoned, code_commit="abc123")
    # The runner entry point must not be implied by importing execute.
    assert callable(execute_phase3)
