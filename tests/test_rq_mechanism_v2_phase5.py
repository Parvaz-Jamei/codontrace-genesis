"""Phase-5 gates. Expectations are computed here, not copied from a run."""

from __future__ import annotations

import math
import statistics
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_HOST_BIT_FLIP
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_COEVOLVE, PASSAGE_FROZEN
from codontrace.genesis.rq_bidirectional_timeshift_confirm import MEASUREMENT_FLOOR, student_t_ppf
from codontrace.genesis.rq_mechanism_v2_phase4 import WINDOW_A, WINDOW_B
from codontrace.genesis.rq_mechanism_v2_phase5 import (
    ALPHA,
    ARM_ADAPTATION_CUT,
    ARM_COEVOLVE,
    ARM_CONSTANT_PARASITE,
    NO_CONFIRMATORY_SENTENCE,
    PLANNING_SIGMA_A,
    PLANNING_SIGMA_B,
    PRECISION_A,
    PRECISION_B,
    PROBE_SEED,
    VERDICT_BLOCKED,
    VERDICT_NEGATIVE,
    VERDICT_NOT_DECLARED,
    VERDICT_SUPPORTED,
    assert_measurement_floor,
    assert_output_dir,
    assess_phase5,
    build_phase5_arm,
    census_wave_supports_claim_b,
    choose_lag_and_horizon,
    contemporary_minus_past,
    descendant_fitness,
    design_from_probe,
    direction_reversal,
    frequency_is_measured,
    history_count_from_power,
    lineage_relative_fitness,
    locked_confirmatory_seeds,
    phase5_mde,
    render_phase5_lock,
    resolve_workers,
)


def _lower(values: list[float]) -> float:
    mean = statistics.fmean(values)
    se = statistics.stdev(values) / math.sqrt(len(values))
    return mean - student_t_ppf(1.0 - ALPHA, len(values) - 1) * se


def _upper_ci(values: list[float]) -> float:
    mean = statistics.fmean(values)
    se = statistics.stdev(values) / math.sqrt(len(values))
    return mean + student_t_ppf(0.975, len(values) - 1) * se


_EVIDENCE = {"config_digest": "cfg-unit", "identity": "unit-history", "provenance": "unit-test"}


def _row(seed: int, claim_a: float | None, *, reversal: bool | None, contact: float | None = 1.2) -> dict[str, object]:
    return {
        "census_wave": False,
        "claim_a": claim_a,
        "config_digest": _EVIDENCE["config_digest"],
        "contact_pressure": contact,
        "contacts": 10 if contact is not None else None,
        "evidence_id": _EVIDENCE["identity"],
        "fitness_measured": True if reversal is not None else None,
        "frequency": {WINDOW_A: 30, WINDOW_B: 30},
        "provenance": _EVIDENCE["provenance"],
        "reversal": reversal,
        "seed": seed,
    }


def test_measurement_floor_is_not_lowered() -> None:
    assert MEASUREMENT_FLOOR == 12
    assert assert_measurement_floor() == 12
    with pytest.raises(ConfigurationError, match="must not be lowered"):
        assert_measurement_floor(11)
    with pytest.raises(ConfigurationError):
        locked_confirmatory_seeds(11)
    source = Path("src/codontrace/genesis/rq_mechanism_v2_phase5.py").read_text(encoding="utf-8")
    assert "MEASUREMENT_FLOOR =" not in source
    assert "red_queen_proved = True" not in source


def test_claim_gates_are_separate_and_importance_blocks_support() -> None:
    seeds = list(range(9601, 9613))
    positive = [0.40] * 6 + [0.60] * 6
    assert _lower(positive) > 0.05
    reversals = [True] * 6 + [False] * 6
    rows = [
        _row(seed, positive[index], reversal=reversals[index])
        for index, seed in enumerate(seeds)
    ]
    half = [1.0] * 6 + [0.0] * 6
    assert _lower(half) < 0.30 < _lower(positive)
    separated = assess_phase5(rows, seeds, importance_bound=0.30, mde_a=1.0, mde_b=1.0, evidence=_EVIDENCE)
    assert separated["claim_a"]["verdict"] == VERDICT_SUPPORTED
    assert separated["claim_b"]["verdict"] != VERDICT_SUPPORTED
    assert separated["claim_a"]["verdict"] != separated["claim_b"]["verdict"]
    assert separated["red_queen_proved"] is False
    assert separated["public_flag_is_in_model_claim"] is False
    assert separated["evidence"]["bound"] is True
    assert separated["importance_is_mde"] is False
    undeclared = assess_phase5(rows, seeds, importance_bound=None, mde_a=1.0, mde_b=1.0)
    assert undeclared["claim_a"]["verdict"] == VERDICT_NOT_DECLARED
    assert undeclared["claim_a"]["verdict"] != VERDICT_SUPPORTED
    assert undeclared["claim_b"]["verdict"] != VERDICT_SUPPORTED
    assert undeclared["supported_forbidden"] is True
    assert undeclared["red_queen_proved"] is False
    assert undeclared["measurement_floor"] == 12


def test_claim_b_can_prove_only_when_its_own_criterion_is_met() -> None:
    seeds = list(range(9601, 9613))
    positive = [0.40] * 6 + [0.60] * 6
    # Ten reversals and two failures. The rate is not 1, so the SE is not 0.
    flags = [True] * 10 + [False] * 2
    rate = [1.0] * 10 + [0.0] * 2
    importance = 0.2
    assert _lower(positive) >= importance
    assert _lower(rate) >= importance
    assert statistics.stdev(rate) > 0.0
    rows = [_row(seed, positive[index], reversal=flags[index]) for index, seed in enumerate(seeds)]
    report = assess_phase5(rows, seeds, importance_bound=importance, evidence=_EVIDENCE)
    assert report["claim_b"]["verdict"] == VERDICT_SUPPORTED
    assert report["claim_b"]["criterion_met"] is True
    assert report["in_model_support"] is True
    assert report["red_queen_proved"] is False
    assert report["public_flag_is_in_model_claim"] is False
    assert report["claim_a"]["verdict"] == VERDICT_SUPPORTED
    bare = assess_phase5(rows, seeds, importance_bound=importance)
    assert bare["claim_b"]["verdict"] != VERDICT_SUPPORTED
    assert bare["in_model_support"] is False
    assert bare["red_queen_proved"] is False


def test_census_wave_alone_cannot_support_claim_b() -> None:
    assert census_wave_supports_claim_b([{WINDOW_A: 48}, {WINDOW_A: 12}, {WINDOW_A: 48}]) is False
    assert frequency_is_measured({"renamed-class": 60}) is False
    seeds = list(range(9601, 9613))
    rows = []
    for index, seed in enumerate(seeds):
        rows.append(
            {
                "census_wave": True,
                "claim_a": 0.5,
                "contact_pressure": None,
                "contacts": None,
                "fitness_measured": None,
                "frequency": {WINDOW_A: 48 if index % 2 == 0 else 12, WINDOW_B: 12 if index % 2 == 0 else 48},
                "reversal": None,
                "seed": seed,
            }
        )
    report = assess_phase5(rows, seeds, importance_bound=0.05)
    assert report["claim_b"]["verdict"] == VERDICT_BLOCKED
    assert report["claim_b"]["verdict"] != VERDICT_SUPPORTED
    assert report["claim_b"]["used_census_wave_as_estimand"] is False
    assert report["claim_b"]["mean"] is None
    assert report["red_queen_proved"] is False


def test_unmeasurable_is_not_zero_and_incomplete_seeds_are_blocked() -> None:
    assert contemporary_minus_past(None, 0.2) is None
    assert contemporary_minus_past(0.0, 0.0) == 0.0
    assert direction_reversal(0.0, 0.2) is None
    seeds = list(range(9601, 9613))
    negative = [-0.40] * 5 + [-0.20] * 6
    assert len(negative) == 11
    assert _upper_ci(negative) < 0.0
    rows = [
        _row(seed, negative[offset], reversal=False)
        for offset, seed in enumerate(seed for seed in seeds if seed != 9605)
    ]
    assert len(rows) == 11
    blocked = assess_phase5(rows, seeds, importance_bound=0.05)
    assert blocked["claim_a"]["verdict"] == VERDICT_BLOCKED
    assert blocked["claim_a"]["verdict"] != VERDICT_NEGATIVE
    assert blocked["claim_a"]["mean"] is None
    assert blocked["claim_a"]["n_locked"] == 12
    assert blocked["claim_a"]["n_used"] == 11
    assert blocked["claim_a"]["dropped_seeds"] == [9605]
    present = [float(row["claim_a"]) for row in rows]
    assert statistics.fmean(present) != 0.0
    imputed = statistics.fmean(present + [0.0])
    assert blocked["claim_a"]["mean"] != imputed
    hole = [_row(seed, None if seed == 9605 else 0.3, reversal=True) for seed in seeds]
    missing_value = assess_phase5(hole, seeds, importance_bound=0.05)
    assert missing_value["claim_a"]["verdict"] == VERDICT_BLOCKED
    assert missing_value["claim_a"]["mean"] is None


def test_complete_negative_direction_stays_negative() -> None:
    seeds = list(range(9601, 9613))
    negative = [-0.40] * 6 + [-0.20] * 6
    assert _upper_ci(negative) < 0.0
    rows = [_row(seed, negative[index], reversal=False) for index, seed in enumerate(seeds)]
    report = assess_phase5(rows, seeds, importance_bound=0.05)
    assert report["claim_a"]["verdict"] == VERDICT_NEGATIVE
    assert report["claim_a"]["mean"] == pytest.approx(statistics.fmean(negative))
    assert report["red_queen_proved"] is False
    assert report["claim_b"]["verdict"] == VERDICT_NEGATIVE
    assert report["claim_b"]["interval"]["wald_se_zero"] is True
    assert report["claim_b"]["interval"]["p_two_sided"] not in (None, 0.0)
    assert report["claim_b"]["interval"]["lower"] == 0.0


def test_lineage_fitness_uses_births_not_a_missing_class_as_zero() -> None:
    start = [WINDOW_A, WINDOW_A, WINDOW_B, WINDOW_B]
    births = [{"parent_window": WINDOW_A}] * 3 + [{"parent_window": WINDOW_B}]
    scored = lineage_relative_fitness(start, births, deaths=[])
    assert scored["measured"] is True
    by_window = scored["by_window"]
    assert isinstance(by_window, dict)
    # Offspring share 0.75 over start frequency 0.5 is 1.5. The other class is 0.5.
    assert by_window[WINDOW_A] == pytest.approx(1.5)
    assert by_window[WINDOW_B] == pytest.approx(0.5)
    absent = lineage_relative_fitness(None, births, deaths=[])
    assert absent["measured"] is False
    assert absent["by_window"] is None
    no_births = lineage_relative_fitness(start, [], deaths=[])
    assert no_births["measured"] is False
    assert no_births["by_window"] is None

    start_hosts = [{"id": "h1", "window": WINDOW_A}, {"id": "h2", "window": WINDOW_B}]
    births = [{"id": "c1", "parent_id": "h1", "parent_window": WINDOW_A}]
    living = [
        {"id": "c1", "parent_id": "h1", "window": WINDOW_A},
        {"id": "h2", "parent_id": None, "window": WINDOW_B},
    ]
    descendants = descendant_fitness(start_hosts, births, living, deaths_recorded=True)
    assert descendants["measured"] is True
    assert descendants["by_window"][WINDOW_A] == pytest.approx(1.0)
    assert descendants["by_window"][WINDOW_B] == pytest.approx(1.0)
    broken = descendant_fitness(start_hosts, [], [{"id": "c1", "parent_id": "missing"}], True)
    assert broken["measured"] is False
    assert broken["by_window"] is None


def test_lag_and_n_are_not_chosen_from_a_contrast() -> None:
    chosen = choose_lag_and_horizon(mean_newborns=26.0, census=60, measurable=True)
    assert chosen["primary_lag"] == round(60 / 26)
    assert chosen["horizon"] == max(math.ceil(3 * (60 / 26)), round(60 / 26) + 1)
    assert chosen["horizon"] == 7
    assert chosen["primary_lag"] == 2
    with pytest.raises(ConfigurationError, match="not 0"):
        choose_lag_and_horizon(mean_newborns=None, census=60, measurable=False)
    with pytest.raises(ConfigurationError, match="claim contrast"):
        design_from_probe(
            {
                "census": 60,
                "claim_a": 0.9,
                "mean_seated_newborns": 26.0,
                "measurable": True,
                "sigma_a": PLANNING_SIGMA_A,
                "sigma_b": PLANNING_SIGMA_B,
            }
        )
    power = history_count_from_power(PLANNING_SIGMA_A, PLANNING_SIGMA_B)
    assert int(power["n"]) >= 12
    assert phase5_mde(PLANNING_SIGMA_A, int(power["n"])) <= PRECISION_A
    assert phase5_mde(PLANNING_SIGMA_B, int(power["n"])) <= PRECISION_B
    if int(power["n"]) > 12:
        assert phase5_mde(PLANNING_SIGMA_A, int(power["n"]) - 1) > PRECISION_A or phase5_mde(
            PLANNING_SIGMA_B, int(power["n"]) - 1
        ) > PRECISION_B
    seeds = locked_confirmatory_seeds(int(power["n"]))
    assert seeds[0] == 9601
    assert seeds[-1] == 9600 + int(power["n"])
    assert PROBE_SEED not in seeds
    assert resolve_workers(7) == 7
    with pytest.raises(ConfigurationError):
        resolve_workers(8)
    with pytest.raises(ConfigurationError):
        assert_output_dir(Path("runs/rq-mechanism-v2/phase4b-fitness"))


def test_lock_text_has_the_sentence_and_separate_claims() -> None:
    design = design_from_probe(
        {
            "census": 60,
            "mean_seated_newborns": 26.0,
            "measurable": True,
            "sigma_a": PLANNING_SIGMA_A,
            "sigma_b": PLANNING_SIGMA_B,
        }
    )
    text = render_phase5_lock(design, code_commit="abc123")
    assert text.splitlines()[2] == NO_CONFIRMATORY_SENTENCE
    assert text.strip().splitlines()[-1] == NO_CONFIRMATORY_SENTENCE
    assert "Claim A" in text and "Claim B" in text
    assert "adaptation_cut" in text and "constant_parasite" in text
    assert "shuffled_labels" in text
    assert "Importance for this estimand is undeclared" in text
    assert "is not the importance bound" in text
    assert "workers" in text and "7" in text
    assert "9600" in text
    assert "contemporary_minus_past" in text or "Contemporary parasite performance" in text


def test_controls_keep_reproduction_and_do_not_delete_parasites() -> None:
    coevolve = build_phase5_arm(ARM_COEVOLVE, 9590)
    cut = build_phase5_arm(ARM_ADAPTATION_CUT, 9590)
    held = build_phase5_arm(ARM_CONSTANT_PARASITE, 9590)
    assert coevolve.passage == PASSAGE_COEVOLVE
    assert coevolve.runner.configs.reproduction.enabled is True
    assert coevolve.runner.configs.mutation.bit_flip_rate == pytest.approx(STRUCT_HOST_BIT_FLIP)
    assert coevolve.runner.configs.sexual_recombination.uses_birth_chamber is True
    assert cut.passage == PASSAGE_FROZEN
    assert cut.passage != "shuffled_labels"
    assert cut.runner.configs.reproduction.enabled is True
    assert cut.host_inheritance == "transmit"
    assert cut.runner.configs.mutation.bit_flip_rate == pytest.approx(0.0)
    assert cut.host_composition_hold is not None
    assert held.passage == PASSAGE_FROZEN
    assert held.passage != "absent"
    assert held.runner.configs.reproduction.enabled is True
    assert held.runner.configs.mutation.bit_flip_rate == pytest.approx(STRUCT_HOST_BIT_FLIP)
    assert held.host_composition_hold is None
    assert held.antagonist_pop is not None and len(held.antagonist_pop.units) > 0
    assert len(cut._hosts()) == 60


def _unit(window: str, index: int, *, atp: float = 0.01) -> dict[str, object]:
    return {"energy": 0.2, "runtime_atp": atp, "unit_id": f"p{index}", "window": window}


def _host(window: str, index: int, *, atp: float = 0.01) -> dict[str, object]:
    return {"id": f"h{index}", "runtime_atp": atp, "window": window}


def _gen(arm: str, generation: int, hosts: list[str], parasites: list[str]) -> dict[str, object]:
    return {
        "arm": arm,
        "generation": generation,
        "hosts": [_host(window, index) for index, window in enumerate(hosts)],
        "parasites": [_unit(window, index) for index, window in enumerate(parasites)],
    }


def _seat_mean(hosts: list[str], parasites: list[str]) -> float:
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import graded_affinity

    pair_n = min(len(hosts), len(parasites))
    return sum(graded_affinity(hosts[index], parasites[index]) for index in range(pair_n)) / pair_n


def test_control_inputs_are_not_copies_and_constant_parasite_is_host_change() -> None:
    from codontrace.genesis.rq_mechanism_v2_phase5 import (
        score_arm_contrast,
        score_constant_parasite_contrast,
    )

    hosts_now = ["000000", "000000"]
    hosts_past = ["000000", "111111"]
    parasites = ["000000", "000000"]
    rows = [
        _gen(ARM_CONSTANT_PARASITE, 10, hosts_now, parasites),
        _gen(ARM_CONSTANT_PARASITE, 7, hosts_past, parasites),
        _gen(ARM_COEVOLVE, 10, hosts_now, parasites),
        _gen(ARM_COEVOLVE, 7, hosts_past, ["111111", "111111"]),
    ]
    # Same hosts against two identical parasite rosters. The rejected contrast cannot move.
    assert score_arm_contrast(rows, ARM_CONSTANT_PARASITE, lag=3, horizon=10) == 0.0
    held = score_constant_parasite_contrast(rows, lag=3, horizon=10)
    expected = _seat_mean(hosts_now, parasites) - _seat_mean(hosts_past, parasites)
    assert expected == pytest.approx(0.5)
    assert held["past_parasite_used_as_second_input"] is False
    assert held["parasite_inputs"] == "single_horizon_roster"
    assert held["hosts_differ"] is True
    assert held["inputs_are_copies"] is False
    assert held["value"] == pytest.approx(expected)
    assert held["value"] != 0.0
    # Claim A still assays horizon hosts against the two parasite generations.
    claim_a = score_arm_contrast(rows, ARM_COEVOLVE, lag=3, horizon=10)
    assert claim_a == pytest.approx(_seat_mean(hosts_now, parasites) - _seat_mean(hosts_now, ["111111", "111111"]))
    assert claim_a != held["value"]


def test_adaptation_cut_is_nonzero_when_one_window_differs() -> None:
    from codontrace.genesis.rq_mechanism_v2_phase5 import score_adaptation_cut_contrast

    hosts = ["000000"] * 64
    parasites_now = ["000111"] * 64
    parasites_past = ["111111"] + ["000111"] * 63
    assert parasites_now != parasites_past
    rows = [
        _gen(ARM_ADAPTATION_CUT, 10, hosts, parasites_now),
        _gen(ARM_ADAPTATION_CUT, 7, hosts, parasites_past),
    ]
    now = _seat_mean(hosts, parasites_now)
    past = _seat_mean(hosts, parasites_past)
    # One seat drops from 3/6 to 0/6. The mean moves by 0.5/64. Not copied from a run.
    assert now == pytest.approx(0.5)
    assert past == pytest.approx((63 * 0.5) / 64)
    assert now - past == pytest.approx(0.5 / 64)
    scored = score_adaptation_cut_contrast(rows, lag=3, horizon=10)
    assert scored["parasites_differ"] is True
    assert scored["inputs_are_copies"] is False
    assert scored["value"] == pytest.approx(now - past)
    assert scored["value"] != 0.0

    hosts_now = ["000000", "111111"]
    hosts_past = ["000000", "000000"]
    shared = ["000000", "111111"]
    host_rows = [
        _gen(ARM_ADAPTATION_CUT, 10, hosts_now, shared),
        _gen(ARM_ADAPTATION_CUT, 7, hosts_past, shared),
    ]
    host_shift = score_adaptation_cut_contrast(host_rows, lag=3, horizon=10)
    assert host_shift["hosts_differ"] is True
    assert host_shift["parasites_differ"] is False
    assert host_shift["inputs_are_copies"] is False
    assert host_shift["value"] == pytest.approx(_seat_mean(hosts_now, shared) - _seat_mean(hosts_past, shared))
    assert host_shift["value"] == pytest.approx(0.5)


def test_phase5b_lock_keeps_claim_gates_and_forbids_support() -> None:
    from codontrace.genesis.rq_mechanism_v2_phase5 import (
        PHASE5B_HORIZON,
        PHASE5B_LAG,
        assert_phase5b_output_dir,
        locked_phase5b_seeds,
        render_phase5b_lock,
    )

    seeds = list(locked_phase5b_seeds())
    assert seeds == list(range(9701, 9713))
    assert PHASE5B_LAG == 3 and PHASE5B_HORIZON == 10
    assert PROBE_SEED not in seeds
    assert not (set(seeds) & set(range(9600, 9613)))
    text = render_phase5b_lock(code_commit="abc123")
    assert text.splitlines()[2] == NO_CONFIRMATORY_SENTENCE
    assert text.strip().splitlines()[-1] == NO_CONFIRMATORY_SENTENCE
    assert "9701" in text and "9712" in text
    assert "Importance for this estimand is undeclared. SUPPORTED is forbidden." in text
    assert "is not the importance bound" in text
    assert "workers" in text and "7" in text
    assert "-0.004783199264088665" not in text
    assert "I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at the horizon)" in text
    positive = [0.40] * 6 + [0.60] * 6
    rows = [_row(seed, positive[index], reversal=True) for index, seed in enumerate(seeds)]
    undeclared = assess_phase5(rows, seeds, importance_bound=None, mde_a=1.0, mde_b=1.0)
    assert undeclared["claim_a"]["verdict"] != VERDICT_SUPPORTED
    assert undeclared["claim_b"]["verdict"] != VERDICT_SUPPORTED
    assert undeclared["supported_forbidden"] is True
    assert undeclared["red_queen_proved"] is False
    missing = rows[:-1]
    blocked = assess_phase5(missing, seeds, importance_bound=None)
    assert blocked["claim_a"]["verdict"] == VERDICT_BLOCKED
    assert blocked["claim_b"]["verdict"] == VERDICT_BLOCKED
    assert blocked["claim_a"]["mean"] is None
    with pytest.raises(ConfigurationError):
        assert_phase5b_output_dir(Path("runs/rq-mechanism-v2/phase5-coevolution"))


def test_duplicate_histories_and_generations_are_rejected() -> None:
    half = list(range(9601, 9607))
    rows = [_row(seed, 0.4, reversal=True) for seed in half]
    doubled_seeds = half + half
    with pytest.raises(ConfigurationError, match="duplicate seeds"):
        assess_phase5(rows + rows, doubled_seeds, importance_bound=0.05, evidence=_EVIDENCE)
    with pytest.raises(ConfigurationError, match="duplicate seeds"):
        assess_phase5(rows, doubled_seeds, importance_bound=0.05, evidence=_EVIDENCE)
    locked = list(range(9601, 9613))
    full = [_row(seed, 0.4, reversal=False) for seed in locked]
    full.append(_row(9601, 0.9, reversal=True))
    with pytest.raises(ConfigurationError, match="contradictory rows"):
        assess_phase5(full, locked, importance_bound=None)
    copied = [_row(seed, 0.4, reversal=True) for seed in locked]
    copied[0]["generations"] = [1, 2, 2]
    with pytest.raises(ConfigurationError, match="duplicate generations"):
        assess_phase5(copied, locked, importance_bound=None)
    from codontrace.genesis.rq_mechanism_v2_phase5 import wilson_interval

    none = wilson_interval(0, 12)
    every = wilson_interval(12, 12)
    assert none["lower"] == 0.0
    assert none["upper"] < 0.5
    assert none["p_two_sided"] == pytest.approx(2.0 / 4096.0)
    assert none["p_one_sided"] != 0.0
    assert none["se_zero"] is False
    assert none["wald_se_zero"] is True
    assert every["upper"] == 1.0
    assert every["lower"] > 0.5
    assert every["p_two_sided"] == pytest.approx(2.0 / 4096.0)
    # Ten of twelve still clears the in-model bound. The public flag does not.
    assert report_boundary_is_not_the_public_flag()


def report_boundary_is_not_the_public_flag() -> bool:
    seeds = list(range(9601, 9613))
    rows = [_row(seed, 0.5, reversal=True) for seed in seeds]
    report = assess_phase5(rows, seeds, importance_bound=0.2, evidence=_EVIDENCE)
    assert report["claim_b"]["interval"]["upper"] == 1.0
    assert report["claim_b"]["verdict"] == VERDICT_SUPPORTED
    assert report["in_model_support"] is True
    assert report["red_queen_proved"] is False
    return True


def test_genotype_hold_does_not_reset_atp_or_memory() -> None:
    arm = build_phase5_arm(ARM_ADAPTATION_CUT, 9591)
    host = arm._hosts()[0]
    before = float(host.atp_state.runtime_available)
    host.atp_state.debit_runtime(
        1.0,
        tick=0,
        organism_id=host.id,
        codon="000",
        action="HOLD_CHECK",
        reason="genotype hold must not resupply",
    )
    spent = float(host.atp_state.runtime_available)
    assert spent == pytest.approx(before - 1.0)
    sentinel = object()
    host.episodic_memory = sentinel  # type: ignore[assignment]
    assert arm.host_composition_hold is not None
    arm.host_composition_hold(arm)
    again = next(org for org in arm._hosts() if org.id == host.id)
    assert again is host
    assert float(again.atp_state.runtime_available) == pytest.approx(spent)
    assert again.episodic_memory is sentinel
    ledger = list(arm.intervention_ledger)
    assert all(item["kind"] != "energy_resupply" for item in ledger)
    assert all(item.get("resupply") is not True for item in ledger)
    assert ledger == []
    # A missing id is a replacement, not a silent resupply of the others.
    from dataclasses import replace as dc_replace

    survivors = tuple(org for org in arm.runner.population.organisms if org.id != host.id)
    arm.runner.population = dc_replace(arm.runner.population, organisms=survivors)
    kept = next(iter(arm._hosts()))
    kept_atp = float(kept.atp_state.runtime_available)
    arm.host_composition_hold(arm)
    restored = next(org for org in arm._hosts() if org.id == host.id)
    assert restored is not host
    assert float(kept.atp_state.runtime_available) == pytest.approx(kept_atp)
    kinds = [item["kind"] for item in arm.intervention_ledger]
    assert kinds == ["replacement"]
    assert arm.intervention_ledger[0]["host_id"] == host.id
    assert arm.intervention_ledger[0]["resupply"] is False
