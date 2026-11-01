"""JR5 phase 3: the E1 cost-of-sex TOST gate against the preregistered rules.

Planted cells are built by hand, with no random draws, so every expected
number follows from the one-sample t formulas. A cell of 2k values
c - d and c + d has mean c and SD d * sqrt(2k / (2k - 1)), so with 40
populations SE = d / sqrt(39). Bounds come from PREREG.md section 3:
[1.8, 2.2] at m = 0.5 and [1.2, 1.4667] at m = 0.25, log margins
-0.1054 / +0.0953.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

import pytest

from codontrace.campaigns import jr5_e1_gate
from codontrace.campaigns.jr5_e1_gate import (
    E1GateSpec,
    E1Population,
    evaluate_e1_cell,
    evaluate_e1_gate,
    load_e1_gate_spec,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.statistical_protocol import student_t_quantile

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = ROOT / "docs" / "prereg" / "jr5" / "jr5_prereg_constants.json"
RECORD = ROOT / "docs" / "prereg" / "jr5" / "record.json"
T95_39 = student_t_quantile(39, 0.95)  # 1.684875, the 90% TOST critical value at n = 40


def _constants() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CONSTANTS.read_text(encoding="utf-8"))
    return data


def _spec() -> E1GateSpec:
    return load_e1_gate_spec(ROOT)


def _cell(centre: float, d: float, m: float = 0.5) -> list[E1Population]:
    # The preregistered seed block for ratio m (seed_split): 40 seeds.
    seeds = _spec().seeds_for(m)
    return [E1Population(seed=s, log_w=centre + (d if i % 2 else -d)) for i, s in enumerate(seeds)]


def _passing_cells() -> dict[tuple[float, int], list[E1Population]]:
    # d is chosen near the simulated SD of log w at N = 200 (PREREG section 7);
    # it is a planted spread, not a measured one.
    return {
        (0.5, 200): _cell(math.log(2.0), 0.076),
        (0.25, 200): _cell(math.log(4.0 / 3.0), 0.051, 0.25),
    }


def test_spec_reads_the_prereg_bounds() -> None:
    spec = _spec()
    assert spec.alpha == 0.05 and spec.host_n_gate == 200
    assert spec.ratio_bounds(0.5) == pytest.approx((1.8, 2.2))
    assert spec.ratio_bounds(0.25) == pytest.approx((1.2, 1.4666666666666666))
    # Log margins around log(1/(1-m)) are log 0.9 and log 1.1 at both ratios.
    for m in (0.5, 0.25):
        low, high = spec.log_bounds(m)
        centre = math.log(1.0 / (1.0 - m))
        assert low - centre == pytest.approx(-0.10536051565782628)
        assert high - centre == pytest.approx(0.09531017980432493)
    pinned = _constants()["gate_e1"]["log_margin"]
    assert pinned == {"low": pytest.approx(math.log(0.9)), "high": pytest.approx(math.log(1.1))}


def test_spec_refuses_a_ci_level_that_is_not_one_minus_two_alpha() -> None:
    # Basis: the TOST at alpha is the (1 - 2 alpha) interval inside the bounds,
    # and the bounds are (1 -/+ margin) / (1 - m); a file stating other numbers
    # is inconsistent with its own rules.
    sha = _spec().constants_sha256
    for key, value in (
        ("ci_level", 0.95),
        ("equivalence_bounds", {"0.5": [1.7, 2.2], "0.25": [1.2, 1.4666666666666666]}),
        ("theoretical_cost", {"0.5": 2.1, "0.25": 1.3333333333333333}),
        ("log_margin", {"low": -0.1, "high": 0.0953101798043249}),
        ("populations_per_cell", 39),
    ):
        block = dict(_constants()["gate_e1"])
        block[key] = value
        with pytest.raises(ConfigurationError):
            E1GateSpec.from_prereg_constants({**_constants(), "gate_e1": block}, constants_sha256=sha)


def test_spec_requires_nested_block_and_every_per_ratio_key() -> None:
    # Basis: PREREG section 3 fixes bounds, theoretical cost and the seed block
    # per sex ratio; a gate that silently falls back to a top-level block or
    # skips a missing ratio key would test against unregistered settings.
    sha = _spec().constants_sha256
    with pytest.raises(ConfigurationError):
        E1GateSpec.from_prereg_constants(_constants()["gate_e1"], constants_sha256=sha)
    for key in ("equivalence_bounds", "theoretical_cost", "seed_split"):
        block = dict(_constants()["gate_e1"])
        block[key] = {k: v for k, v in block[key].items() if k != "0.25"}
        with pytest.raises(ConfigurationError):
            E1GateSpec.from_prereg_constants({**_constants(), "gate_e1": block}, constants_sha256=sha)
    for key in ("log_margin", "populations_per_cell"):
        block = {k: v for k, v in _constants()["gate_e1"].items() if k != key}
        with pytest.raises(ConfigurationError):
            E1GateSpec.from_prereg_constants({**_constants(), "gate_e1": block}, constants_sha256=sha)


def test_loader_checks_the_constants_sha_against_the_record(tmp_path: Path) -> None:
    # Basis: the prereg is locked by the sha256 of each file in record.json;
    # settings are only preregistered if their bytes hash to the pinned value.
    pinned = dict(json.loads(RECORD.read_text(encoding="utf-8"))["manifest"]["files"])
    sha = hashlib.sha256(CONSTANTS.read_bytes()).hexdigest()
    assert pinned["docs/prereg/jr5/jr5_prereg_constants.json"] == sha
    spec = _spec()
    assert spec.constants_sha256 == sha
    assert evaluate_e1_gate(spec, _passing_cells()).to_record()["constants_sha256"] == sha
    folder = tmp_path / "docs" / "prereg" / "jr5"
    folder.mkdir(parents=True)
    shutil.copy(RECORD, folder / "record.json")
    # One changed byte (a trailing newline) breaks the pin, even with equal content.
    (folder / "jr5_prereg_constants.json").write_bytes(CONSTANTS.read_bytes() + b"\n")
    with pytest.raises(ConfigurationError):
        load_e1_gate_spec(tmp_path)
    shutil.copy(CONSTANTS, folder / "jr5_prereg_constants.json")
    assert load_e1_gate_spec(tmp_path) == spec
    (folder / "record.json").write_text(json.dumps({"manifest": {"files": []}}), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_e1_gate_spec(tmp_path)
    with pytest.raises(ConfigurationError):
        load_e1_gate_spec(tmp_path / "missing")


def test_planted_theory_values_pass_with_hand_derived_t() -> None:
    # m = 0.5: SE = 0.076 / sqrt(39) = 0.012170; t_lower = 0.105361 / SE = 8.657,
    # t_upper = -0.095310 / SE = -7.832. Both far past t(0.95, 39) = 1.6849.
    result = evaluate_e1_gate(_spec(), _passing_cells())
    cell = result.cells[0]
    assert cell.sex_ratio == 0.5 and cell.gated
    se = 0.076 / math.sqrt(39.0)
    assert cell.tost is not None
    assert cell.tost.standard_error == pytest.approx(se, rel=1e-12)
    assert cell.tost.t_lower == pytest.approx(-math.log(0.9) / se, rel=1e-9)
    assert cell.tost.t_upper == pytest.approx(-math.log(1.1) / se, rel=1e-9)
    assert cell.tost.ci_low == pytest.approx(math.log(2.0) - T95_39 * se, rel=1e-9)
    assert cell.equivalent and cell.excludes_null and cell.passed
    assert result.passed
    record = result.to_record()
    assert record["passed"] is True
    assert record == evaluate_e1_gate(_spec(), _passing_cells()).to_record()


def test_true_value_on_the_lower_bound_fails() -> None:
    # Mean exactly log 1.8: t_lower = 0, p_lower = 0.5. Equivalence cannot be shown.
    cells = _passing_cells()
    cells[(0.5, 200)] = _cell(math.log(1.8), 0.076)
    result = evaluate_e1_gate(_spec(), cells)
    cell = result.cells[0]
    assert cell.tost is not None and cell.tost.p_lower == pytest.approx(0.5, abs=1e-12)
    assert not cell.passed and not result.passed


def test_point_inside_but_interval_crossing_a_bound_fails() -> None:
    # Mean log 1.9 lies inside, but with d = 0.5 the 90% half-width is
    # 1.6849 * 0.5 / sqrt(39) = 0.1349 > log(1.9/1.8) = 0.0541, so the
    # interval crosses log 1.8. Noisy data must not pass.
    cells = _passing_cells()
    cells[(0.5, 200)] = _cell(math.log(1.9), 0.5)
    half = T95_39 * 0.5 / math.sqrt(39.0)
    assert half > math.log(1.9 / 1.8)
    assert not evaluate_e1_gate(_spec(), cells).passed


def test_interval_just_inside_passes_and_just_outside_fails() -> None:
    # Put the lower 90% limit 1e-6 above / below log 1.8 by choosing the centre.
    # This checks the gate has no slack and no bias on either side of the bound.
    d = 0.076
    half = T95_39 * d / math.sqrt(39.0)
    for offset, expected in ((1e-6, True), (-1e-6, False)):
        cells = _passing_cells()
        cells[(0.5, 200)] = _cell(math.log(1.8) + half + offset, d)
        assert evaluate_e1_gate(_spec(), cells).passed is expected
    for offset, expected in ((-1e-6, True), (1e-6, False)):
        cells = _passing_cells()
        cells[(0.5, 200)] = _cell(math.log(2.2) - half + offset, d)
        assert evaluate_e1_gate(_spec(), cells).passed is expected


def test_failure_at_either_sex_ratio_fails_the_gate() -> None:
    # PREREG section 3: failure at either sex ratio stops JR5 at phase 3.
    cells = _passing_cells()
    cells[(0.25, 200)] = _cell(math.log(1.6), 0.051, 0.25)
    result = evaluate_e1_gate(_spec(), cells)
    assert result.cells[0].passed and not result.cells[1].passed
    assert not result.passed


def test_null_exclusion_is_checked_separately() -> None:
    # The 95% interval excludes 1 for any passing E1 cell, so this branch is
    # checked by moving must_exclude inside the bounds. Half-width on the log
    # scale: t(0.975, 39) * 0.076 / sqrt(39) = 2.0227 * 0.012170 = 0.02462.
    # log(2 / 1.95) = 0.02532 > 0.02462, so 1.95 is excluded;
    # log(2 / 1.97) = 0.01511 < 0.02462, so 1.97 is not. Equivalence holds in both.
    base = _spec()
    for target, expected in ((1.95, True), (1.97, False)):
        spec = dataclasses.replace(base, must_exclude=target)
        cell = evaluate_e1_cell(spec, 0.5, 200, _cell(math.log(2.0), 0.076))
        assert cell.equivalent
        assert cell.excludes_null is expected
        assert cell.passed is expected


def test_exclusion_rule_and_cap() -> None:
    # Fixation before generation 3 excludes a population. The cap is 20% of
    # 40 = 8: 8 excluded is allowed, 9 is an instrument failure of the cell.
    spec = _spec()
    pops = _cell(math.log(2.0), 0.076)
    eight = [E1Population(p.seed, p.log_w, fixed_generation=2) if i < 8 else p for i, p in enumerate(pops)]
    cell = evaluate_e1_cell(spec, 0.5, 200, eight)
    assert len(cell.excluded_seeds) == 8 and not cell.exclusion_cap_exceeded
    # The 32 kept values are still balanced, so mean log 2 and the cell passes.
    assert cell.tost is not None and cell.tost.n == 32 and cell.passed
    nine = [E1Population(p.seed, p.log_w, fixed_generation=2) if i < 9 else p for i, p in enumerate(pops)]
    cell9 = evaluate_e1_cell(spec, 0.5, 200, nine)
    assert cell9.exclusion_cap_exceeded and not cell9.passed
    # Fixing at generation 3 or later stays in the fit and is only reported.
    late = [E1Population(p.seed, p.log_w, fixed_generation=3) if i < 20 else p for i, p in enumerate(pops)]
    cell_late = evaluate_e1_cell(spec, 0.5, 200, late)
    assert cell_late.excluded_seeds == () and len(cell_late.fixed_seeds) == 20 and cell_late.passed
    lost = [E1Population(p.seed, p.log_w, lost_generation=4) if i < 2 else p for i, p in enumerate(pops)]
    assert len(evaluate_e1_cell(spec, 0.5, 200, lost).lost_seeds) == 2


def test_n50_is_reported_but_does_not_gate() -> None:
    # PREREG: E1 at N = 50 is report-only. A failing N = 50 cell leaves the
    # gate as it is, and N = 50 alone cannot pass it.
    cells: dict[tuple[float, int], list[E1Population]] = dict(_passing_cells())
    cells[(0.5, 50)] = _cell(math.log(1.5), 0.158)
    result = evaluate_e1_gate(_spec(), cells)
    n50 = [c for c in result.cells if c.host_n == 50][0]
    assert not n50.gated and not n50.passed
    assert result.passed
    with pytest.raises(ConfigurationError):
        evaluate_e1_gate(_spec(), {(0.5, 50): _cell(math.log(2.0), 0.076), (0.25, 50): _cell(0.29, 0.05, 0.25)})


def test_missing_ratio_or_unregistered_ratio_raises() -> None:
    cells = _passing_cells()
    del cells[(0.25, 200)]
    with pytest.raises(ConfigurationError):
        evaluate_e1_gate(_spec(), cells)
    with pytest.raises(ConfigurationError):
        evaluate_e1_cell(_spec(), 0.4, 200, _cell(0.5, 0.05))
    with pytest.raises(ConfigurationError):
        evaluate_e1_cell(_spec(), 0.5, 100, _cell(0.5, 0.05))


def test_gate_module_holds_no_outcome_literals_and_no_randomness() -> None:
    # PREREG section 8: no verdict literal in the analysis code. The gate
    # returns booleans; typed outcomes belong to the verdict adapter.
    source = Path(jr5_e1_gate.__file__).read_text(encoding="utf-8")
    outcomes = _constants()["typed_outcomes"]
    names = outcomes if isinstance(outcomes, list) else list(outcomes)
    for name in [*names, "red_queen_proved"]:
        assert f'"{name}"' not in source and f"'{name}'" not in source
    assert "import random" not in source and "RNGManager" not in source
    assert "13101" not in source and "608ccdea" not in source


def test_required_pair_prereg_pass_and_prereg_fail() -> None:
    # Pass dataset, derived from the prereg margins and alpha = 0.05:
    # 40 populations per ratio at N = 200, log w = log(1/(1-m)) -/+ d.
    # m = 0.5, d = 0.076: SE = 0.076/sqrt(39) = 0.012170, 90% half-width
    #   1.684875 * 0.012170 = 0.020505, interval [log 2 - 0.0205, log 2 + 0.0205]
    #   = [1.9594, 2.0414], inside [1.8, 2.2]; 95% interval excludes 1.
    # m = 0.25, d = 0.051: SE = 0.008167, half-width 0.013760, interval
    #   [1.3151, 1.3518], inside [1.2, 1.4667].
    # This is condition (a) of RED_QUEEN_CLAIM_PATH.md, the gate input the
    # verdict adapter reads as record["passed"]. The flag itself is set only
    # by that adapter, from (a) to (e) together.
    passing = evaluate_e1_gate(_spec(), _passing_cells())
    ratio_ci = {c.sex_ratio: c.to_record()["ratio_ci"] for c in passing.cells}
    assert ratio_ci[0.5] == pytest.approx([1.95940, 2.04141], abs=1e-4)
    assert ratio_ci[0.25] == pytest.approx([1.31511, 1.35180], abs=1e-4)
    assert passing.to_record()["passed"] is True

    # Fail dataset: the same spread at m = 0.5 but centred on the realised
    # w = 1.75, 2.8% below the lower bound 1.8. The 90% interval
    # [1.7145, 1.7862] lies wholly below 1.8, so t_lower = log(1.75/1.8)/SE
    # = -2.315 and p_lower = P(T39 > -2.315) is about 0.987. m = 0.25 is
    # left passing to show that one failing ratio is enough.
    cells = _passing_cells()
    cells[(0.5, 200)] = _cell(math.log(1.75), 0.076)
    failing = evaluate_e1_gate(_spec(), cells)
    low = failing.cells[0]
    assert low.tost is not None
    assert low.tost.t_lower == pytest.approx(math.log(1.75 / 1.8) / (0.076 / math.sqrt(39.0)), rel=1e-9)
    assert low.tost.p_lower > 0.98
    assert failing.cells[1].passed
    assert failing.to_record()["passed"] is False


def test_cells_must_hold_exactly_the_preregistered_seed_block() -> None:
    # Basis: PREREG fixes 40 populations per cell on seed_split blocks
    # 13101-13140 (m = 0.5) and 13141-13180 (m = 0.25). Dropping, swapping or
    # adding a seed is selective inclusion and must be refused, at N = 200
    # and at the report-only N = 50 alike.
    spec = _spec()
    assert spec.seeds_for(0.5) == range(13101, 13141)
    assert spec.seeds_for(0.25) == range(13141, 13181)
    good = _cell(math.log(2.0), 0.076)
    shifted = [dataclasses.replace(good[0], seed=13141), *good[1:]]
    dup = [*good[:-1], dataclasses.replace(good[-1], seed=good[0].seed)]
    for host_n in (200, 50):
        assert evaluate_e1_cell(spec, 0.5, host_n, good).n_total == 40
        for bad in (good[:-1], shifted, dup, [*good, E1Population(13141, 0.7)], _cell(math.log(2.0), 0.076, 0.25)):
            with pytest.raises(ConfigurationError):
                evaluate_e1_cell(spec, 0.5, host_n, bad)


def test_excluded_population_may_lack_log_w_but_a_kept_one_may_not() -> None:
    # Basis: a population that fixes before generation 3 has no usable
    # frequency trajectory, so its fit may be undefined; it is excluded before
    # fitting. A kept population without a finite log w cannot enter a t test.
    spec = _spec()
    pops = _cell(math.log(2.0), 0.076)
    early = [
        E1Population(pops[0].seed, None, fixed_generation=1),
        E1Population(pops[1].seed, math.inf, fixed_generation=2),
        *pops[2:],
    ]
    cell = evaluate_e1_cell(spec, 0.5, 200, early)
    assert len(cell.excluded_seeds) == 2 and cell.tost is not None and cell.tost.n == 38
    for bad_w in (None, math.nan):
        kept = [E1Population(pops[0].seed, bad_w), *pops[1:]]
        with pytest.raises(ConfigurationError):
            evaluate_e1_cell(spec, 0.5, 200, kept)
        late = [E1Population(pops[0].seed, bad_w, fixed_generation=3), *pops[1:]]
        with pytest.raises(ConfigurationError):
            evaluate_e1_cell(spec, 0.5, 200, late)


def test_instrument_failure_both_ways() -> None:
    # Basis: PREREG.md line 15 - failure of the cost gate, or more than 20% of
    # an E1 cell excluded, is an instrument failure. A clean pass is not one; a
    # failing gate is; a cap breach is one even in the report-only N = 50 cell
    # and even while every gated cell passes.
    clean = evaluate_e1_gate(_spec(), _passing_cells())
    assert clean.passed and not clean.instrument_failure
    assert clean.to_record()["instrument_failure"] is False
    cells = _passing_cells()
    cells[(0.5, 200)] = _cell(math.log(1.75), 0.076)
    failed = evaluate_e1_gate(_spec(), cells)
    assert not failed.passed and failed.instrument_failure
    pops = _cell(math.log(2.0), 0.076)
    breach = [E1Population(p.seed, p.log_w, fixed_generation=0) if i < 9 else p for i, p in enumerate(pops)]
    with_n50 = {**_passing_cells(), (0.5, 50): breach}
    result = evaluate_e1_gate(_spec(), with_n50)
    assert result.passed and result.instrument_failure
    eight = [E1Population(p.seed, p.log_w, fixed_generation=0) if i < 8 else p for i, p in enumerate(pops)]
    assert not evaluate_e1_gate(_spec(), {**_passing_cells(), (0.5, 50): eight}).instrument_failure


def test_adapter_rows_carry_the_gated_cells_on_the_ratio_scale() -> None:
    # Basis: condition (a) of RED_QUEEN_CLAIM_PATH.md is stated on the ratio
    # scale; the verdict adapter reads one row per sex ratio at N = 200 with
    # the 90% and 95% intervals as exp of the log-scale t intervals.
    result = evaluate_e1_gate(_spec(), {**_passing_cells(), (0.5, 50): _cell(math.log(2.0), 0.1)})
    rows = result.adapter_e1()
    assert [r["sex_ratio"] for r in rows] == [0.5, 0.25]
    assert set(rows[0]) == {"sex_ratio", "n_populations", "n_excluded", "ci90", "ci95"}
    assert rows[0]["ci90"] == pytest.approx([1.95940, 2.04141], abs=1e-4)
    assert rows[0]["n_populations"] == 40 and rows[0]["n_excluded"] == 0
