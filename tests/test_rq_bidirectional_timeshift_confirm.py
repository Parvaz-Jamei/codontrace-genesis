"""Confirmatory time-shift lock, assay and verdict. No 600-generation run."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.genesis.measurements.antagonist_population import AntagonistPopulation
from codontrace.genesis.rq_bidirectional_timeshift_confirm import (
    ALPHA,
    CONFIRMATORY_SEEDS,
    EXCLUDED_SEEDS,
    VERDICT_BLOCKED,
    VERDICT_INCONCLUSIVE,
    VERDICT_NEGATIVE,
    VERDICT_SUPPORTED,
    analysis_centers,
    assert_confirmatory_seeds,
    chi2_df3_ppf,
    decide_verdict,
    infectivity,
    infectivity_pairwise,
    one_sample_t,
    run_one_history,
    student_t_ppf,
    student_t_sf,
)


def test_quantiles_match_the_locked_reference() -> None:
    assert abs(student_t_ppf(0.975, 23) - 2.0686576104190486) < 1e-9
    assert abs(student_t_ppf(1.0 - ALPHA, 23) - 2.3978750646571103) < 1e-8
    assert abs(chi2_df3_ppf(0.20) - 1.0051740130523492) < 1e-9
    critical = student_t_ppf(1.0 - ALPHA, 23)
    assert abs(student_t_sf(critical, 23) - ALPHA) < 1e-8


def test_centers_and_seeds() -> None:
    assert analysis_centers() == (200, 240, 280, 320, 360, 400, 440, 480, 520, 560)
    assert len(CONFIRMATORY_SEEDS) == 24
    assert set(CONFIRMATORY_SEEDS).isdisjoint(EXCLUDED_SEEDS)
    assert_confirmatory_seeds(CONFIRMATORY_SEEDS)


def test_frequency_shortcut_matches_pairs_and_missing_is_not_zero() -> None:
    hosts = [{"window": "000000"}, {"window": "000000"}, {"window": "111000"}]
    parasites = [{"window": "000000"}, {"window": "111000"}]
    assert infectivity(hosts, parasites) == infectivity_pairwise(hosts, parasites)
    assert infectivity([], parasites) is None


def test_verdict_gates_do_not_prove_red_queen() -> None:
    practical = 0.05
    # Constant samples have SE 0. Student-t p is undefined. They must not
    # support, and a point CI must not be treated as a negative result.
    constant_high = one_sample_t([0.2] * 24, practical)
    constant_low = one_sample_t([-0.02] * 24, practical)
    assert constant_high["se_zero"] is True
    assert constant_high["p_one_sided"] is None
    assert constant_high["reject"] is False
    assert constant_low["p_one_sided"] is None
    names = ("CH_A", "CP_A", "S_A_minus_S_B", "S_A_minus_S_C")
    assert decide_verdict(
        {name: constant_high for name in names},
        verification_ok=True,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_INCONCLUSIVE
    assert decide_verdict(
        {name: constant_low for name in names},
        verification_ok=True,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_INCONCLUSIVE
    # Non-constant negative: every history is below the importance bound and
    # the sample is not degenerate. Upper CI must fall below the bound.
    negative = one_sample_t([-0.20] * 12 + [-0.30] * 12, practical)
    assert negative["se_zero"] is False
    assert negative["reject"] is False
    assert decide_verdict(
        {name: negative for name in names},
        verification_ok=True,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_NEGATIVE
    positive = one_sample_t([0.30] * 12 + [0.50] * 12, practical, mde=1.0)
    assert positive["se_zero"] is False
    assert positive["p_one_sided"] not in (None, 0.0)
    assert positive["mde"] == 1.0
    assert positive["mde_is_importance_bound"] is False
    assert positive["reject"] is True
    assert decide_verdict(
        {name: positive for name in names},
        verification_ok=True,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_SUPPORTED
    mixed = {name: negative for name in names}
    mixed["CH_A"] = positive
    assert decide_verdict(
        mixed,
        verification_ok=True,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_INCONCLUSIVE
    assert decide_verdict(
        {name: positive for name in names},
        verification_ok=False,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_BLOCKED
    short = one_sample_t([0.2] * 11, practical)
    assert decide_verdict(
        {name: short for name in names},
        verification_ok=True,
        archive_ok=True,
        practical_effect=practical,
    ) == VERDICT_BLOCKED


def test_short_history_keeps_four_arms_and_bounded_ids(tmp_path: Path) -> None:
    (tmp_path / "live.log").write_text("", encoding="utf-8")
    outcome = run_one_history(9301, str(tmp_path), 2, "unit", 2)
    assert outcome["red_queen_proved"] is False
    arms = outcome["arms"]
    assert set(arms) == {"A", "B", "C", "D"}
    assert all(arms[name]["failed"] is None for name in arms)
    assert arms["C"]["generations_completed"] == 2
    archive = tmp_path / "confirmatory" / "by_seed" / "seed9301" / "archive.jsonl"
    rows = [json.loads(line) for line in archive.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 8
    assert all(len(unit["unit_id"]) <= 64 for row in rows for unit in row["parasites"])
    assert all(row["red_queen_proved"] is False for row in rows)
    initial = json.loads((tmp_path / "confirmatory" / "by_seed" / "seed9301" / "initial.json").read_text())
    assert len({item["digest"] for item in initial["arms"].values()}) == 1


def test_child_ids_do_not_embed_the_parent_chain() -> None:
    pop = AntagonistPopulation.founders(("000000",) * 4, mutation_rate=0.0, maintenance_cost=0.01)
    from codontrace.rng import RNGManager

    rng = RNGManager(seed=7, namespace="id-bound")
    pop.advance(
        matched_windows=("000000",),
        served_contacts=(("000000", 1.0),) * 4,
        mode="coevolve",
        generation=1,
        rng=rng,
        mutate_window=lambda window, _rng: window,
    )
    for unit in pop.units:
        assert len(unit.unit_id) <= 64
        if unit.parent_id is not None:
            assert unit.parent_id in pop.known_unit_ids
            assert unit.parent_id != unit.unit_id
