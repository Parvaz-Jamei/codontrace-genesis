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
from tests import _jr5_deviation_attacks

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
        (0.5, 50): _cell(math.log(2.0), 0.158),
        (0.25, 50): _cell(math.log(4.0 / 3.0), 0.107, 0.25),
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
            E1GateSpec._from_verified_mapping(
                {**_constants(), "gate_e1": block},
                constants_sha256=sha,
                prereg_manifest_sha256=_spec().prereg_manifest_sha256,
            )


def test_spec_requires_nested_block_and_every_per_ratio_key() -> None:
    # Basis: PREREG section 3 fixes bounds, theoretical cost and the seed block
    # per sex ratio; a gate that silently falls back to a top-level block or
    # skips a missing ratio key would test against unregistered settings.
    sha = _spec().constants_sha256
    with pytest.raises(ConfigurationError):
        E1GateSpec._from_verified_mapping(
            _constants()["gate_e1"], constants_sha256=sha, prereg_manifest_sha256=_spec().prereg_manifest_sha256
        )
    for key in ("equivalence_bounds", "theoretical_cost", "seed_split"):
        block = dict(_constants()["gate_e1"])
        block[key] = {k: v for k, v in block[key].items() if k != "0.25"}
        with pytest.raises(ConfigurationError):
            E1GateSpec._from_verified_mapping(
                {**_constants(), "gate_e1": block},
                constants_sha256=sha,
                prereg_manifest_sha256=_spec().prereg_manifest_sha256,
            )
    for key in ("log_margin", "populations_per_cell"):
        block = {k: v for k, v in _constants()["gate_e1"].items() if k != key}
        with pytest.raises(ConfigurationError):
            E1GateSpec._from_verified_mapping(
                {**_constants(), "gate_e1": block},
                constants_sha256=sha,
                prereg_manifest_sha256=_spec().prereg_manifest_sha256,
            )


def test_loader_checks_the_constants_sha_against_the_record(tmp_path: Path) -> None:
    # Basis: the prereg is locked by the sha256 of each file in record.json;
    # settings are only preregistered if their bytes hash to the pinned value.
    pinned = dict(json.loads(RECORD.read_text(encoding="utf-8"))["manifest"]["files"])
    sha = hashlib.sha256(CONSTANTS.read_bytes()).hexdigest()
    assert pinned["docs/prereg/jr5/jr5_prereg_constants.json"] == sha
    spec = _spec()
    assert spec.constants_sha256 == sha
    assert evaluate_e1_gate(spec, _passing_cells()).to_record()["constants_sha256"] == sha
    root = _clone_prereg(tmp_path)
    folder = root / "docs" / "prereg" / "jr5"
    # One changed byte (a trailing newline) breaks the pin, even with equal content.
    (folder / "jr5_prereg_constants.json").write_bytes(CONSTANTS.read_bytes() + b"\n")
    with pytest.raises(ConfigurationError):
        load_e1_gate_spec(root)
    shutil.copy(CONSTANTS, folder / "jr5_prereg_constants.json")
    assert load_e1_gate_spec(root) == spec
    (folder / "record.json").write_text(json.dumps({"manifest": {"files": []}}), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_e1_gate_spec(root)
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




def test_zero_spread_equivalent_gate_record_serializes() -> None:
    """Zero sample spread with mean at theory: infinite t, equivalent, content-addressable.

    Basis: every population has the same log w = log(1/(1-m)). Then SD = 0,
    SE = 0, and the one-sample TOST t statistics are +inf against the lower
    bound and -inf against the upper bound under the two one-sided
    equivalence tests. With the common value strictly inside the
    preregistered log bounds the one-sided p-values are both 0, so the cell
    is equivalent and, with the 95% interval degenerating to the point, also
    excludes log 1. The infinite t values are written as the tagged
    ``{"$float": "±inf"}`` form so ``to_record`` and its digest succeed
    without inventing a finite test statistic.
    """

    from codontrace.genesis.canonical import canonical_digest

    cells = {
        (0.5, 200): _cell(math.log(2.0), 0.0),
        (0.25, 200): _cell(math.log(4.0 / 3.0), 0.0, 0.25),
        (0.5, 50): _cell(math.log(2.0), 0.0),
        (0.25, 50): _cell(math.log(4.0 / 3.0), 0.0, 0.25),
    }
    result = evaluate_e1_gate(_spec(), cells)
    assert result.passed is True
    assert result.instrument_failure is False
    for cell in result.cells:
        assert cell.tost is not None
        assert cell.tost.standard_error == 0.0
        assert cell.tost.t_lower == math.inf
        assert cell.tost.t_upper == -math.inf
        assert cell.tost.p_lower == 0.0 and cell.tost.p_upper == 0.0
        assert cell.equivalent and cell.excludes_null and cell.passed
    record = result.to_record()
    gated = [c for c in record["cells"] if c["gated"]]
    assert gated
    for cell in gated:
        tost = cell["tost"]
        assert tost is not None
        assert tost["t_lower"] == {"$float": "inf"}
        assert tost["t_upper"] == {"$float": "-inf"}
        assert tost["equivalent"] is True
        assert tost["standard_error"] == 0.0
    body = {key: value for key, value in record.items() if key != "digest"}
    assert record["digest"] == canonical_digest(body)


def test_zero_spread_outside_bounds_fails_and_serializes() -> None:
    """Zero sample spread with mean above the upper bound: not equivalent, still serializable.

    Basis: every population has log w = log 3.0. Theory at m = 0.5 is log 2.0
    with upper bound log 2.2, so mean - upper > 0 and SE = 0 give t_upper =
    +inf and p_upper = 1. Equivalence fails (one-sided upper test does not
    reject). The tagged infinite t encoding still lets the gate record
    digest; the gated cell must report passed=False.
    """

    from codontrace.genesis.canonical import canonical_digest

    cells = {
        (0.5, 200): _cell(math.log(3.0), 0.0),
        (0.25, 200): _cell(math.log(4.0 / 3.0), 0.0, 0.25),
        (0.5, 50): _cell(math.log(2.0), 0.0),
        (0.25, 50): _cell(math.log(4.0 / 3.0), 0.0, 0.25),
    }
    result = evaluate_e1_gate(_spec(), cells)
    cell = next(c for c in result.cells if c.sex_ratio == 0.5 and c.host_n == 200)
    assert cell.tost is not None
    assert cell.tost.t_upper == math.inf
    assert cell.tost.p_upper == 1.0
    assert cell.equivalent is False
    assert cell.passed is False
    assert result.passed is False
    record = result.to_record()
    row = next(c for c in record["cells"] if c["sex_ratio"] == 0.5 and c["host_n"] == 200)
    assert row["tost"]["t_upper"] == {"$float": "inf"}
    assert row["tost"]["equivalent"] is False
    assert row["passed"] is False
    body = {key: value for key, value in record.items() if key != "digest"}
    assert record["digest"] == canonical_digest(body)


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
    ratio_ci = {c.sex_ratio: c.to_record()["ratio_ci"] for c in passing.cells if c.gated}
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
    repeated = [*good, good[0]]  # full block plus a repeat: same seed set, 41 rows
    for host_n in (200, 50):
        assert evaluate_e1_cell(spec, 0.5, host_n, good).n_total == 40
        for bad in (
            good[:-1],
            shifted,
            dup,
            repeated,
            [*good, E1Population(13141, 0.7)],
            _cell(math.log(2.0), 0.076, 0.25),
        ):
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
    # 95%: half-width t(0.975, 39) * 0.076 / sqrt(39) = 2.022691 * 0.012170 = 0.024616,
    # so [2 exp(-0.024616), 2 exp(0.024616)] = [1.95137, 2.04984].
    assert rows[0]["ci95"] == pytest.approx([1.95137, 2.04984], abs=1e-4)
    assert rows[0]["n_populations"] == 40 and rows[0]["n_excluded"] == 0


def _tuned_constants() -> dict[str, Any]:
    constants = _constants()
    gate = constants["gate_e1"]
    gate["relative_margin"] = 0.3
    gate["log_margin"] = {"low": math.log(0.7), "high": math.log(1.3)}
    gate["equivalence_bounds"] = {str(m): [0.7 / (1 - m), 1.3 / (1 - m)] for m in gate["sex_ratios"]}
    return constants


def test_public_decoder_hashes_the_bytes_it_parses() -> None:
    """A ±30% margin can be internally consistent but is not the locked ±10%.

    A genuine digest paired with a modified mapping proves nothing about the
    mapping. Expected: only the original byte payload can build the trusted
    spec; mapping input, edited bytes and even an extra newline are refused.
    """
    raw, record_raw = CONSTANTS.read_bytes(), RECORD.read_bytes()
    assert E1GateSpec.from_prereg_constants(raw, record_raw=record_raw) == _spec()
    tuned = _tuned_constants()
    with pytest.raises(ConfigurationError, match="raw bytes"):
        E1GateSpec.from_prereg_constants(tuned, record_raw=record_raw)  # type: ignore[arg-type]
    for edited in (json.dumps(tuned).encode(), raw + b"\n"):
        with pytest.raises(ConfigurationError, match="does not match its record.json sha256"):
            E1GateSpec.from_prereg_constants(edited, record_raw=record_raw)


@pytest.mark.parametrize("rehash", [False, True])
def test_loader_refuses_a_forged_record_and_consistent_constants(tmp_path: Path, rehash: bool) -> None:
    """A manifest copied with edited constants must not establish a new lock.

    The counterfeit constants consistently widen both ratio margins to ±30%.
    Their new hash replaces the constants entry. Expected: rejection whether
    the manifest repeats the old claimed digest or recomputes a consistent new
    one. Otherwise a post-hoc wider equivalence interval could pass the gate.
    """
    from codontrace.preregistration.manifest import PlanManifest

    raw = json.dumps(_tuned_constants()).encode()
    record = json.loads(RECORD.read_bytes())
    manifest = record["manifest"]
    manifest["files"] = [
        [name, hashlib.sha256(raw).hexdigest() if name == jr5_e1_gate.CONSTANTS_RELPATH else digest]
        for name, digest in manifest["files"]
    ]
    if rehash:
        manifest.pop("digest")
        record["manifest"] = PlanManifest.from_dict(manifest).to_dict()
    root = _clone_prereg(tmp_path)
    (root / "docs/prereg/jr5/record.json").write_text(json.dumps(record), encoding="utf-8")
    (root / "docs/prereg/jr5/jr5_prereg_constants.json").write_bytes(raw)
    with pytest.raises(ConfigurationError):
        load_e1_gate_spec(root)


@pytest.mark.parametrize("ratio,host_n", [(m, n) for m in (0.5, 0.25) for n in (200, 50)])
def test_gate_requires_every_reported_cell(ratio: float, host_n: int) -> None:
    """The prereg grid is 2 ratios × 2 sizes × 40 populations = 160.

    The N=50 cells do not gate on equivalence, but either may exceed the
    exclusion cap and cause instrument failure. Expected: omission of any
    cell is refused, including either report-only cell and both together.
    """
    cells = _passing_cells()
    del cells[(ratio, host_n)]
    with pytest.raises(ConfigurationError, match="prereg grid"):
        evaluate_e1_gate(_spec(), cells)
    only_gated = {key: rows for key, rows in _passing_cells().items() if key[1] == 200}
    with pytest.raises(ConfigurationError, match="prereg grid"):
        evaluate_e1_gate(_spec(), only_gated)


def test_modified_spec_cannot_stamp_a_gate_record_with_genuine_digests() -> None:
    """Hash labels cannot authorize settings changed after decoding.

    Keeping genuine digests while widening the margin would falsely stamp a
    post-hoc gate as preregistered. Expected: the public gate rejects a replaced
    spec while the unchanged complete 160-population positive still passes.
    """
    spec = _spec()
    with pytest.raises(ConfigurationError, match="verified prereg"):
        evaluate_e1_gate(dataclasses.replace(spec, relative_margin=0.3), _passing_cells())
    result = evaluate_e1_gate(spec, _passing_cells())
    assert result.passed and not result.instrument_failure
    assert sum(c.n_total for c in result.cells) == 160


def test_record_exposes_the_complete_verified_spec_and_actual_seeds() -> None:
    """A claim consumer must compare all rules, not merely a digest label.

    Expected: both manifest and constants digests, every numerical setting,
    both reported sizes and each cell's exact seed block are recorded. The
    complete positive remains a pass; each 40-seed block is present twice.
    """
    spec = _spec()
    record = evaluate_e1_gate(spec, _passing_cells()).to_record()
    assert record["schema"] == "jr5_e1_gate_v3"
    assert record["constants_sha256"] == spec.constants_sha256
    assert record["prereg_manifest_digest"] == jr5_e1_gate.LOCKED_PREREG_MANIFEST_DIGEST
    assert record["constants_sha256"] == jr5_e1_gate.LOCKED_PREREG_CONSTANTS_SHA256
    assert record["spec"] == spec.to_record()
    assert set(spec.to_record()) == {
        "constants_sha256",
        "prereg_manifest_digest",
        "test",
        "alpha",
        "ci_level",
        "relative_margin",
        "sex_ratios",
        "must_exclude",
        "must_exclude_ci_level",
        "early_fixation_generation",
        "exclusion_cap_fraction",
        "host_n_gate",
        "host_n_reported",
        "populations_per_cell",
        "seed_split",
    }
    for cell in record["cells"]:  # type: ignore[union-attr]
        assert cell["seeds"] == list(spec.seeds_for(cell["sex_ratio"]))
        assert cell["n_total"] == len(cell["seeds"]) == spec.populations_per_cell
    body = {k: v for k, v in record.items() if k != "digest"}
    assert record["digest"] == jr5_e1_gate.canonical_digest(body)


@pytest.mark.parametrize("ratio,host_n", [(m, n) for m in (0.5, 0.25) for n in (200, 50)])
def test_each_cell_requires_every_seed_once(ratio: float, host_n: int) -> None:
    """Each ratio has a fixed 40-seed block reused at both population sizes.
    Expected: removing a seed or replacing it by a duplicate is refused in
    all four cells; the complete, unedited block remains a valid input.
    """
    spec = _spec()
    rows = _passing_cells()[(ratio, host_n)]
    assert evaluate_e1_cell(spec, ratio, host_n, rows).n_total == 40
    for bad in (rows[:-1], [*rows[:-1], rows[0]]):
        with pytest.raises(ConfigurationError, match="exactly seeds"):
            evaluate_e1_cell(spec, ratio, host_n, bad)


@pytest.mark.parametrize("ratio,host_n", [(m, n) for m in (0.5, 0.25) for n in (200, 50)])
def test_cap_breach_in_each_cell_is_an_instrument_failure(ratio: float, host_n: int) -> None:
    """More than 20% of 40 excluded populations is a separate instrument
    failure: 8 is allowed, 9 is not. Expected: a nine-population cap breach
    counts at either ratio and either N, even when the N=200 gate passes.
    """
    cells = _passing_cells()
    rows = cells[(ratio, host_n)]
    cells[(ratio, host_n)] = [
        E1Population(row.seed, fixed_generation=1) if i < 9 else row for i, row in enumerate(rows)
    ]
    result = evaluate_e1_gate(_spec(), cells)
    assert result.instrument_failure
    assert result.passed is (host_n != 200)


def test_excluded_fit_can_be_omitted_entirely() -> None:
    """Fixation before generation 3 excludes a population before fitting.
    Expected: omitting log_w is permitted for that excluded row, leaving 39
    finite fits, but not for the same seed when it remains in the analysis.
    """
    rows = _cell(math.log(2.0), 0.076)
    early = [E1Population(rows[0].seed, fixed_generation=1), *rows[1:]]
    assert evaluate_e1_cell(_spec(), 0.5, 200, early).tost.n == 39  # type: ignore[union-attr]
    with pytest.raises(ConfigurationError, match="finite log_w"):
        evaluate_e1_cell(_spec(), 0.5, 200, [E1Population(rows[0].seed), *rows[1:]])


def test_code_pins_equal_the_digests_of_the_committed_prereg_bytes() -> None:
    """The two code pins are the digests of the files in this checkout, recomputed.

    Basis: the gate pins the plan digest (hash_plan over every manifest file
    except DEVIATIONS.md). record.json manifest.digest still covers
    DEVIATIONS.md and must recompute from its file list; each file entry is
    the sha256 of that file's bytes. DEVIATIONS.md names the same plan digest.
    Expected: pin == plan == last log entry; full manifest digest differs from
    the pin; constants sha matches the manifest entry and the constants pin.
    """
    import re

    from codontrace.preregistration.manifest import PlanManifest, hash_plan

    record = json.loads(RECORD.read_bytes())["manifest"]
    files = [(path, digest) for path, digest in record["files"]]
    recomputed = PlanManifest(tuple(files), record["title"]).digest
    assert recomputed == record["digest"]
    assert recomputed != jr5_e1_gate.LOCKED_PREREG_MANIFEST_DIGEST
    constants_sha = hashlib.sha256(CONSTANTS.read_bytes()).hexdigest()
    assert dict(files)[jr5_e1_gate.CONSTANTS_RELPATH] == constants_sha == jr5_e1_gate.LOCKED_PREREG_CONSTANTS_SHA256
    for path, digest in files:
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    log = "docs/prereg/jr5/DEVIATIONS.md"
    named = re.findall(r"^- Record digest: `[0-9a-f]{64}` -> `([0-9a-f]{64})`$", (ROOT / log).read_text("utf-8"), re.M)
    plan = hash_plan([p for p, _ in files if p != log], root=ROOT, title=record["title"]).digest
    assert named[-1] == plan == jr5_e1_gate.LOCKED_PREREG_MANIFEST_DIGEST == jr5_e1_gate.LOCKED_PREREG_PLAN_DIGEST


def test_loader_refuses_the_superseded_lock(tmp_path: Path) -> None:
    """The record and constants of the lock before the 2026-11-01 amendment are refused.

    Basis: main at 4400e07 holds the earlier lock (manifest a4f76d60...,
    constants 608ccdea...), genuine bytes that were trusted until the
    amendment. A gate that still accepted them could be fed the earlier
    record. The bytes are read with git show; a shallow clone without that
    commit skips, any other missing object fails.
    Expected: ConfigurationError naming the code-pinned lock.
    """
    import subprocess

    shallow = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"], capture_output=True, check=True, text=True
    )
    folder = tmp_path / "docs" / "prereg" / "jr5"
    folder.mkdir(parents=True)
    for name in ("record.json", "jr5_prereg_constants.json"):
        shown = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"4400e07:docs/prereg/jr5/{name}"], capture_output=True, check=False
        )
        if shown.returncode != 0 and shallow.stdout.strip() == "true":
            pytest.skip("shallow clone: 4400e07 is not in local history")
        assert shown.returncode == 0, shown.stderr
        (folder / name).write_bytes(shown.stdout)
    old = json.loads((folder / "record.json").read_bytes())["manifest"]
    assert old["digest"].startswith("a4f76d60")
    assert hashlib.sha256((folder / "jr5_prereg_constants.json").read_bytes()).hexdigest().startswith("608ccdea")
    with pytest.raises(ConfigurationError):
        E1GateSpec.from_prereg_constants(
            (folder / "jr5_prereg_constants.json").read_bytes(),
            record_raw=(folder / "record.json").read_bytes(),
        )


def _write_prereg(tmp_path: Path, record: dict[str, Any], constants_raw: bytes) -> Path:
    folder = tmp_path / "docs" / "prereg" / "jr5"
    folder.mkdir(parents=True)
    (folder / "record.json").write_text(json.dumps(record), encoding="utf-8")
    (folder / "jr5_prereg_constants.json").write_bytes(constants_raw)
    return tmp_path


def _clone_prereg(tmp_path: Path) -> Path:
    """Copy every file listed in record.json so load_e1_gate_spec can re-hash them."""

    record = json.loads(RECORD.read_bytes())
    for path, _digest in record["manifest"]["files"]:
        src = ROOT / path
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    # record.json is not in its own manifest, so it is copied separately.
    dest_rec = tmp_path / "docs/prereg/jr5/record.json"
    dest_rec.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RECORD, dest_rec)
    return tmp_path


def test_loader_recomputes_the_manifest_digest_instead_of_trusting_the_declared_one(tmp_path: Path) -> None:
    """A record that keeps the pinned digest but lists a different file hash is refused.

    Basis: manifest.digest is a function of the file list, so a declared
    digest that matches the pin proves nothing unless it is recomputed. Here
    only the PREREG.md entry changes, the constants bytes and their entry are
    genuine, and the declared digest is left at the pin.
    Expected: ConfigurationError from the recomputed-digest check, which runs
    before the spec's own pin check.
    """
    record = json.loads(RECORD.read_bytes())
    record["manifest"]["files"] = [
        [name, "0" * 64 if name.endswith("/PREREG.md") else digest] for name, digest in record["manifest"]["files"]
    ]
    assert record["manifest"]["digest"] == json.loads(RECORD.read_bytes())["manifest"]["digest"]
    with pytest.raises(ConfigurationError, match="record manifest content does not match"):
        E1GateSpec.from_prereg_constants(CONSTANTS.read_bytes(), record_raw=json.dumps(record).encode())


def test_constants_pin_holds_on_its_own(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The constants pin refuses edited constants even if the manifest pin named their manifest.

    Basis: the constants sha256 is pinned in code separately from the
    manifest digest, so a wrong manifest pin alone cannot admit other gate
    settings. The manifest pin is set to the digest of a manifest built for
    ±30% constants, which the manifest check then accepts.
    Expected: ConfigurationError from the loader's constants-entry check,
    before the spec's own pin check.
    """
    from codontrace.preregistration.jr5_locked_plan import plan_digest_from_files
    from codontrace.preregistration.manifest import PlanManifest

    raw = json.dumps(_tuned_constants()).encode()
    record = json.loads(RECORD.read_bytes())
    manifest = record["manifest"]
    manifest["files"] = [
        [name, hashlib.sha256(raw).hexdigest() if name == jr5_e1_gate.CONSTANTS_RELPATH else digest]
        for name, digest in manifest["files"]
    ]
    manifest.pop("digest")
    record["manifest"] = PlanManifest.from_dict(manifest).to_dict()
    forged_plan = plan_digest_from_files(
        [(p, h) for p, h in record["manifest"]["files"]], record["manifest"]["title"]
    )
    monkeypatch.setattr(jr5_e1_gate, "LOCKED_PREREG_MANIFEST_DIGEST", forged_plan)
    with pytest.raises(ConfigurationError, match="record.json constants entry does not match"):
        E1GateSpec.from_prereg_constants(raw, record_raw=json.dumps(record).encode())


@pytest.mark.parametrize(
    "field,value",
    [
        ("prereg_manifest_sha256", "a4f76d603a21a02d523fbdba86966dfe7df9faf41ba0d01813ae53f29be44daa"),
        ("prereg_manifest_sha256", "73bc5a83bbee6dfacee7f9a4f7eea2e27562434275ded2d8cc695c81e5ed4505"),
        ("constants_sha256", "608ccdea9f8d1efa51ceecec756c8732b0fe1804828ed5c3910396c2e625a78c"),
    ],
)
def test_spec_cannot_be_built_with_another_digest(field: str, value: str) -> None:
    """A spec copied with another digest label is refused at construction.

    Basis: a caller-supplied digest proves nothing unless it is checked when
    the object is built, not only in the loader. The values are the earlier
    lock, the full record.json manifest digest (covers DEVIATIONS.md; not the
    plan pin) and the earlier constants sha256.
    Expected: ConfigurationError naming the code pin.
    """
    with pytest.raises(ConfigurationError, match="code-pinned"):
        dataclasses.replace(_spec(), **{field: value})

def test_appending_a_valid_deviation_entry_keeps_the_gate_loading(tmp_path: Path) -> None:
    """A new DEVIATIONS.md entry that keeps the plan digest must not disable the gate.

    Basis: the pin is hash_plan over every manifest file except DEVIATIONS.md
    (577bd4ac...). Appending an entry whose digest line is
    577bd4ac... -> 577bd4ac..., then refreshing record.json with
    ``hash_plan`` over all listed paths (including the new log bytes), changes
    only the full manifest digest. Expected: load_e1_gate_spec succeeds and
    prereg_manifest_sha256 stays the plan pin.
    """

    from codontrace.preregistration.manifest import PlanManifest, hash_plan

    root = _clone_prereg(tmp_path)
    log = root / "docs/prereg/jr5/DEVIATIONS.md"
    pin = jr5_e1_gate.LOCKED_PREREG_MANIFEST_DIGEST
    log.write_text(
        log.read_text(encoding="utf-8")
        + "\n## 2099-01-01: synthetic log-only entry for the plan-pin test\n\n"
        + "- Reason: test-only append; locked plan files unchanged.\n"
        + f"- Record digest: `{pin}` -> `{pin}`\n"
        + "- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. "
        + "This is the author's declaration. What the repository shows at this entry: no JR5 run "
        + "script, campaign module or run output is committed (no path under `runs/` names JR5, "
        + "and the only JR5 script is the E1 power simulation, which runs no engine arm).\n",
        encoding="utf-8",
    )
    record = json.loads(RECORD.read_bytes())
    paths = [path for path, _ in record["manifest"]["files"]]
    fresh = hash_plan(paths, root=root, title=record["manifest"]["title"])
    assert fresh.digest != record["manifest"]["digest"]
    assert PlanManifest(
        tuple((p, h) for p, h in fresh.files if p != "docs/prereg/jr5/DEVIATIONS.md"),
        fresh.title,
    ).digest == pin
    (root / "docs/prereg/jr5/record.json").write_text(
        json.dumps({"manifest": fresh.to_dict()}, indent=2) + "\n",
        encoding="utf-8",
    )
    spec = load_e1_gate_spec(root)
    assert spec.prereg_manifest_sha256 == pin


def test_editing_a_locked_plan_file_refuses_the_gate(tmp_path: Path) -> None:
    """Changing PREREG.md bytes moves the plan digest and must refuse the loader.

    Basis: PREREG.md is in the locked plan. Appending one byte changes its
    sha256, so hash_plan without DEVIATIONS.md differs from 577bd4ac....
    Expected: ConfigurationError from the plan-pin check (fresh hashes or pin).
    """

    root = _clone_prereg(tmp_path)
    target = root / "docs/prereg/jr5/PREREG.md"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ConfigurationError, match="record.json does not match the fresh hashes|plan digest"):
        load_e1_gate_spec(root)


def _write_log_and_refresh_record(root: Path, text: str) -> None:
    """Write a DEVIATIONS.md and refresh record.json over it, as an editor of the log would."""

    from codontrace.preregistration.manifest import hash_plan

    (root / "docs/prereg/jr5/DEVIATIONS.md").write_text(text, encoding="utf-8")
    record = json.loads(RECORD.read_bytes())
    fresh = hash_plan([path for path, _ in record["manifest"]["files"]], root=root, title=record["manifest"]["title"])
    (root / "docs/prereg/jr5/record.json").write_text(
        json.dumps({"manifest": fresh.to_dict()}, indent=2) + "\n", encoding="utf-8"
    )


@pytest.mark.parametrize("case", sorted(_jr5_deviation_attacks.ATTACKS))
def test_edited_deviations_log_refuses_the_gate(tmp_path: Path, case: str) -> None:
    """Every edit of the log other than a whole appended entry refuses the loader.

    Basis: the log is append-only. The code pins the lock-start entry (old
    digest 633aa9c8... and the sha256 of its text) and checkpoints of the
    accepted log (byte length and sha256 of the text up to the end of an
    accepted entry), the way a transparency log is checked against a trusted
    tree size and root hash. Every entry has exactly one record-digest line at
    a line start, the lines chain, and the last names the plan pin. Each case
    in ``tests/_jr5_deviation_attacks.py`` breaks one of these rules, and
    record.json is refreshed over the edited log, so freshness cannot be what
    refuses it. The locked plan files are untouched, so the plan digest stays
    577bd4ac... in every case.
    Expected: ConfigurationError with the message of the broken rule.
    """

    edit, message = _jr5_deviation_attacks.ATTACKS[case]
    root = _clone_prereg(tmp_path)
    log = root / "docs/prereg/jr5/DEVIATIONS.md"
    _write_log_and_refresh_record(root, edit(log.read_text(encoding="utf-8")))
    with pytest.raises(ConfigurationError, match=message):
        load_e1_gate_spec(root)


def test_breaking_the_deviations_chain_refuses_the_gate(tmp_path: Path) -> None:
    """An appended entry whose old digest is not the previous new digest is refused.

    Basis: each entry's old digest must equal the previous entry's new digest.
    The accepted entries are pinned by checkpoints, so the chain rule is the
    one that guards appended entries: here the appended entry's old digest is
    bbbb... while the previous entry's new digest is 577bd4ac....
    Expected: ConfigurationError naming the chain.
    """

    edit, _ = _jr5_deviation_attacks.ATTACKS["chain_break_in_append"]
    root = _clone_prereg(tmp_path)
    log = root / "docs/prereg/jr5/DEVIATIONS.md"
    _write_log_and_refresh_record(root, edit(log.read_text(encoding="utf-8")))
    with pytest.raises(ConfigurationError, match="do not chain"):
        load_e1_gate_spec(root)


def test_log_pins_are_the_digests_of_the_committed_log() -> None:
    """The lock-start pin and every checkpoint are recomputed from the committed log.

    Basis: LOCK_START_ENTRY_SHA256 is the sha256 of the first entry's text
    (from its heading to the next heading) and LOCK_START_DIGEST its old
    digest. Each checkpoint is the byte length and sha256 of a prefix of the
    committed log that ends where the next entry's blank line starts, so a
    log can append after it. Checkpoints are oldest first and the main one
    (a01c950, three entries) is shorter than the last.
    Expected: each value equals the one computed here from the file bytes.
    """

    from codontrace.preregistration import jr5_locked_plan as plan

    raw = (ROOT / "docs/prereg/jr5/DEVIATIONS.md").read_bytes()
    text = raw.decode("utf-8")
    entries = plan.deviations_log_entries(text)
    assert hashlib.sha256(entries[0].encode()).hexdigest() == plan.LOCK_START_ENTRY_SHA256
    assert plan.DIGEST_LINE.findall(entries[0]) == [
        (plan.LOCK_START_DIGEST, "a4f76d603a21a02d523fbdba86966dfe7df9faf41ba0d01813ae53f29be44daa")
    ]
    sizes = [size for size, _ in plan.ACCEPTED_LOG_CHECKPOINTS]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)
    for size, digest in plan.ACCEPTED_LOG_CHECKPOINTS:
        assert hashlib.sha256(raw[:size]).hexdigest() == digest
        assert raw[size - 1 : size] == b"\n"
        assert raw[size:] == b"" or raw[size:].startswith(b"\n## ")
    assert sum(1 for e in entries if text.index(e) < sizes[0]) == 3


def test_stale_record_json_refuses_the_gate(tmp_path: Path) -> None:
    """A record.json whose listed DEVIATIONS hash does not match the file is refused.

    Basis: after copying the tree, only DEVIATIONS.md bytes change; record.json
    still names the old sha256. Expected: ConfigurationError that record.json
    does not match the fresh hashes.
    """

    root = _clone_prereg(tmp_path)
    log = root / "docs/prereg/jr5/DEVIATIONS.md"
    log.write_text(log.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="record.json does not match the fresh hashes"):
        load_e1_gate_spec(root)


def test_constant_samples_on_registered_bounds_follow_the_interval_rule() -> None:
    """A constant sample on a registered bound is never equivalent, for n = 2 to 60.

    Basis: for an exactly constant sample [v] * n the mean is v and se = 0, so
    every t interval is [v, v]. The TOST decision must equal strict inclusion
    of the (1 - 2 alpha) = 90% interval in (lower, upper), the duality that
    test_tost_decision_equals_interval_inclusion checks for samples with
    spread. With v on a bound that inclusion is false. The bounds are the four
    registered log bounds of the spec (m = 0.5 and 0.25, lower and upper), and
    n runs over 2 to 60. That range includes every n at which fsum([v] * n) / n
    is not v (for v the m = 0.5 lower bound these are n = 7, 14, 28, 55, 56),
    which is where a rounded mean would create a one-ulp spread and a finite t
    of sqrt(n - 1). Both paths that consume the sample are checked: the TOST
    (one_sample_tost) and the interval (one_sample_t_interval, at 90% and at
    the gate's must_exclude_ci_level).
    Expected: for every (m, bound, n): not equivalent, decision equal to
    strict 90% inclusion, the bound side has t = 0 and p = 1/2, both
    intervals are (v, v), and the non-round-tripping cases are present.
    """
    from codontrace.genesis.statistical_protocol import one_sample_t_interval, one_sample_tost

    spec = _spec()
    level = 1.0 - 2.0 * spec.alpha
    rounded_cases = []
    for m in (0.5, 0.25):
        lower, upper = spec.log_bounds(m)
        for v in (lower, upper):
            for n in range(2, 61):
                data = [v] * n
                if math.fsum(data) / n != v:
                    rounded_cases.append((m, v == lower, n))
                r = one_sample_tost(data, lower, upper, alpha=spec.alpha)
                interval = one_sample_t_interval(data, level)
                assert interval == (v, v) == (r.ci_low, r.ci_high), (m, v, n)
                assert one_sample_t_interval(data, spec.must_exclude_ci_level) == (v, v), (m, v, n)
                inside = lower < interval[0] and interval[1] < upper
                assert r.equivalent is inside is False, (m, v, n)
                t_on_bound, p_on_bound = (r.t_lower, r.p_lower) if v == lower else (r.t_upper, r.p_upper)
                assert t_on_bound == 0.0 and p_on_bound == 0.5, (m, v, n)
    assert (0.5, True, 7) in rounded_cases and len(rounded_cases) >= 10


@pytest.mark.parametrize("case", sorted(_jr5_deviation_attacks.LINE_END_ATTACKS))
def test_crlf_or_cr_log_bytes_refuse_the_gate(tmp_path: Path, case: str) -> None:
    """A log whose line ends were rewritten to CRLF or lone CR is refused.

    Basis: the checkpoints and the lock-start pin are sha256 values of the
    committed LF bytes. The loader decodes the file bytes without newline
    translation, so CRLF or CR bytes reach the check. With CRLF each digest
    line ends in CR and the end-of-line anchor finds none; with lone CR no
    heading starts a line, so there is no entry. record.json is refreshed
    over the new bytes, so freshness cannot be what refuses it. A text-mode
    read would translate the line ends to LF and accept the file.
    Expected: ConfigurationError (no digest line for CRLF, no entry for CR)
    from verify_jr5_record_at_root and from load_e1_gate_spec.
    """
    from codontrace.preregistration.jr5_locked_plan import verify_jr5_record_at_root
    from codontrace.preregistration.manifest import hash_plan

    edit, message = _jr5_deviation_attacks.LINE_END_ATTACKS[case]
    root = _clone_prereg(tmp_path)
    log = root / "docs/prereg/jr5/DEVIATIONS.md"
    log.write_bytes(edit(log.read_bytes()))
    record = json.loads(RECORD.read_bytes())
    fresh = hash_plan([path for path, _ in record["manifest"]["files"]], root=root, title=record["manifest"]["title"])
    (root / "docs/prereg/jr5/record.json").write_text(
        json.dumps({"manifest": fresh.to_dict()}, indent=2) + "\n", encoding="utf-8"
    )
    with pytest.raises(ConfigurationError, match=message):
        verify_jr5_record_at_root(root, locked_plan_digest=jr5_e1_gate.LOCKED_PREREG_MANIFEST_DIGEST)
    with pytest.raises(ConfigurationError, match=message):
        load_e1_gate_spec(root)


def test_committed_log_is_read_as_its_lf_bytes() -> None:
    """Reading the committed log keeps its bytes, and the pins still match them.

    Basis: read_deviations_log decodes the file bytes with no newline
    translation, so encoding the text again gives the file bytes. The
    committed log has no CR byte (.gitattributes sets eol=lf), so the change
    from a text-mode read leaves the checked text, and therefore every
    pinned value, as before: each checkpoint is the sha256 of a prefix of
    these bytes and the lock-start pin is the sha256 of the first entry.
    Expected: no CR byte, text.encode() equal to the bytes, every checkpoint
    and the lock-start pin equal to the values computed here, and the log
    check accepts the text at the plan pin.
    """
    from codontrace.preregistration import jr5_locked_plan as plan

    path = ROOT / "docs/prereg/jr5/DEVIATIONS.md"
    raw = path.read_bytes()
    text = plan.read_deviations_log(path)
    assert b"\r" not in raw and text.encode("utf-8") == raw
    for size, digest in plan.ACCEPTED_LOG_CHECKPOINTS:
        assert hashlib.sha256(raw[:size]).hexdigest() == digest
    entries = plan.deviations_log_entries(text)
    assert hashlib.sha256(entries[0].encode("utf-8")).hexdigest() == plan.LOCK_START_ENTRY_SHA256
    plan.verify_deviations_log(text, expected_plan_digest=jr5_e1_gate.LOCKED_PREREG_MANIFEST_DIGEST)
