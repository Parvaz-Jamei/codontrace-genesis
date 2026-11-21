"""JR5 realised-w pilot runner (PREREG section 7).

No pilot seed runs here. Engine runs use smoke seeds 20011-20013 (outside
every registered and sealed block) at host N = 20 with a growth design, and
the post-gate pilot path runs on a synthetic unregistered block 30001-30003
with a stubbed fit. An autouse fixture refuses any engine boot on a
registered or sealed seed, so a broken guard cannot boot one. No test reads
or prints a smoke w estimate: blinding tests assert absence only and report
offending paths, never values.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import math
import re
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from codontrace.campaigns import jr5_realised_w_pilot as P
from codontrace.campaigns.jr5_e1_gate import E1Population, evaluate_e1_cell, evaluate_e1_pilot_cell
from codontrace.errors import ConfigurationError

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = ROOT / "docs/prereg/jr5/jr5_prereg_constants.json"
SMOKE_SEED = 20011
SMOKE_N = 20
SMOKE_T = 3


def _registered_or_sealed(seed: object) -> bool:
    """Every seed of the registered blocks and sealed ranges, read from the constants."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        return False
    seeds = json.loads(CONSTANTS.read_text(encoding="utf-8"))["seeds"]
    blocks = [v for k, v in seeds.items() if k.endswith("_block")] + list(seeds["sealed_ranges"])
    return any(first <= seed <= last for first, last in blocks)


@pytest.fixture(autouse=True)
def no_engine_boot_on_registered_seeds(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Test safety net: the engine harness refuses to boot on any registered or sealed seed."""

    from codontrace.genesis import closed_loop_hp_arm01 as arm_module

    original = arm_module.LifeLoopEcologyArm.boot

    def guarded_boot(*args: Any, **kwargs: Any) -> Any:
        if _registered_or_sealed(kwargs.get("seed")):
            raise RuntimeError(f"test safety net: engine boot refused on registered seed {kwargs.get('seed')}")
        return original(*args, **kwargs)

    monkeypatch.setattr(arm_module.LifeLoopEcologyArm, "boot", guarded_boot)
    yield


@pytest.fixture(scope="module")
def spec() -> P.RealisedWPilotSpec:
    return P.load_realised_w_pilot_spec(ROOT)


@pytest.fixture(scope="module")
def constants() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CONSTANTS.read_text(encoding="utf-8"))
    return data


def smoke_design(soft_k_multiple: float = 4.0, generation_model: str = "engine_overlapping") -> P.PopulationDesign:
    from codontrace.genesis import closed_loop_hp_arm01_selfing_hold as hold
    from codontrace.genesis.closed_loop_hp_arm01 import _INVASION_FOUNDERS

    return P.PopulationDesign(
        label="smoke-growth",
        generation_model=generation_model,
        soft_k_multiple=soft_k_multiple,
        world_size=12,
        enable_max_age_death=False,
        max_age_ticks=None,
        birth_atp=hold.HOLD_BIRTH_ATP,
        basal_runtime_atp_cost=hold.HOLD_BASAL_ATP_COST,
        passage_refill_mode=hold.HOLD_PASSAGE_REFILL_MODE,
        resource_bolus_amount=hold.HOLD_RESOURCE_BOLUS_AMOUNT,
        food_patches=hold.HOLD_FOOD_PATCHES,
        founder_spatial_policy=hold.HOLD_FOUNDER_SPATIAL_POLICY,
        mating_locus_lock=True,
        mate_search_radius=1,
        outcross_mates_per_generation_cap=1,
        chamber_max_birth_wait_ticks=2,
        chamber_timeout_policy="fail",
        founder_windows=tuple(w for _, w in _INVASION_FOUNDERS),
    )


def discrete_design(**change: Any) -> P.PopulationDesign:
    """The discrete census model with the locked mate settings (global search, no cap, chamber wait
    2, timeout fail), soft K 3N, max-age death after 2 ticks, on a world of 12 (144 >= 3 * 20)."""

    base = dataclasses.replace(
        smoke_design(3.0),
        label="smoke-discrete",
        generation_model=P.DISCRETE_UNIFORM_CENSUS,
        enable_max_age_death=True,
        max_age_ticks=2,
        mate_search_radius=None,
        outcross_mates_per_generation_cap=None,
    )
    return dataclasses.replace(base, **change)


def run_smoke(out: Path, spec: P.RealisedWPilotSpec, **kw: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "mode": P.MODE_SMOKE,
        "seeds": [SMOKE_SEED],
        "design": smoke_design(),
        "host_n": SMOKE_N,
        "horizon": SMOKE_T,
        "root": ROOT,
        "spec": spec,
    }
    args.update(kw)
    return P.run_pilot(out, **args)


def events(out: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (out / "progress.log").read_text(encoding="utf-8").splitlines()]


# ------------------------------------------------------------------ spec


def test_spec_reads_every_pilot_setting_from_the_locked_constants(
    spec: P.RealisedWPilotSpec, constants: dict[str, Any]
) -> None:
    """Basis: constants realised_w_pilot = block 13201-13240, 40 populations, m 0.5, N 200,
    T 5 = gate_e1.generations["0.5"], bounds [1.8, 2.2] = gate_e1.equivalence_bounds["0.5"],
    ci 0.9 = 1 - 2*alpha(0.05), founder share 0.2, fit tol 1e-10 / 100 iterations, ledger
    residual = validity.atp_ledger_max_residual, engine config = host_mating_arm_modes.engine_config."""

    pilot, g = constants["realised_w_pilot"], constants["gate_e1"]
    assert spec.seed_block == tuple(pilot["seed_block"]) == (13201, 13240)
    assert list(spec.seeds) == list(range(13201, 13241))
    assert spec.populations == pilot["populations"] == g["populations_per_cell"] == 40
    assert spec.sex_ratio == pilot["sex_ratio"] == 0.5
    assert spec.host_n == pilot["host_n"] == g["host_n_gate"] == 200
    assert spec.horizon == pilot["horizon"] == g["generations"]["0.5"] == 5
    assert spec.bounds == tuple(pilot["bounds"]) == tuple(g["equivalence_bounds"]["0.5"]) == (1.8, 2.2)
    assert spec.ci_level == pilot["ci_level"] == 1 - 2 * g["alpha"]
    assert spec.founder_share == g["founder_uniparental_frequency"] == 0.2
    assert (spec.fit_tol, spec.fit_max_iter) == (g["fit"]["tol"], g["fit"]["max_iter"]) == (1e-10, 100)
    assert spec.fit_implementation == g["fit"]["implementation"]
    assert spec.max_ledger_residual == constants["validity"]["atp_ledger_max_residual"]
    assert dict(spec.engine_config) == constants["host_mating_arm_modes"]["engine_config"]
    assert spec.max_reruns_after_fix == pilot["max_reruns_after_fix"] == 1
    assert spec.gate.constants_sha256 == hashlib.sha256(CONSTANTS.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("realised_w_pilot", "horizon"), 6, "horizon"),
        (("realised_w_pilot", "bounds"), [1.7, 2.2], "bounds"),
        (("realised_w_pilot", "populations"), 39, "populations"),
        (("realised_w_pilot", "host_n"), 50, "host_n"),
        (("realised_w_pilot", "ci_level"), 0.95, "ci_level"),
        (("realised_w_pilot", "estimator"), "plain_mle", "estimator"),
        (("realised_w_pilot", "fit"), "plain", "estimator"),
        (("realised_w_pilot", "outcross_mating_fee_atp"), 0.5, "fee_atp"),
        (("realised_w_pilot", "diploid_meiosis"), False, "diploid_meiosis"),
        (("realised_w_pilot", "confirmatory"), True, "non-confirmatory"),
        (("realised_w_pilot", "seed_block"), [13202, 13241], "disagrees"),
        (("seeds", "realised_w_pilot_block"), [13202, 13241], "disagrees"),
        (
            ("host_mating_arm_modes", "engine_config", "closed_loop_hp_life", "outcross_runtime_atp"),
            0.1,
            "outcross_runtime_atp",
        ),
        (
            ("host_mating_arm_modes", "engine_config", "sexual_recombination", "diploid_meiosis"),
            False,
            "diploid_meiosis",
        ),
        (("gate_e1", "fit", "on_no_convergence"), "drop", "no convergence"),
    ],
)
def test_spec_refuses_a_pilot_number_that_disagrees_with_e1(
    spec: P.RealisedWPilotSpec, constants: dict[str, Any], path: tuple[str, ...], value: Any, message: str
) -> None:
    """Basis: section 7 fixes the pilot to the E1 instrument (T 5, bounds [1.8, 2.2], 40
    populations, N 200, 90% level, bias-reduced estimator, fee 0.0, diploid meiosis); any
    other value in the decoded constants is refused, never used."""

    data = copy.deepcopy(constants)
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(ConfigurationError, match=message):
        P.spec_from_constants(spec.gate, data)


@pytest.mark.parametrize(
    ("block", "name"),
    [([13050, 13089], "confirmatory_block"), ([13101, 13140], "e1_calibration_block"), ([13901, 13940], "pilot_block")],
)
def test_spec_refuses_a_pilot_block_overlapping_another_block(
    spec: P.RealisedWPilotSpec, constants: dict[str, Any], block: list[int], name: str
) -> None:
    """Basis: blocks confirmatory 13001-13060, E1 13101-13180, horizon pilot 13901-13930;
    each 40-seed block here shares at least one seed with the named block."""

    data = copy.deepcopy(constants)
    data["realised_w_pilot"]["seed_block"] = block
    data["seeds"]["realised_w_pilot_block"] = block
    with pytest.raises(ConfigurationError, match=name):
        P.spec_from_constants(spec.gate, data)


def test_spec_refuses_a_pilot_block_inside_a_sealed_range(
    spec: P.RealisedWPilotSpec, constants: dict[str, Any]
) -> None:
    """Basis: sealed range 12001-12240; block 12201-12240 lies inside it."""

    data = copy.deepcopy(constants)
    data["realised_w_pilot"]["seed_block"] = [12201, 12240]
    data["seeds"]["realised_w_pilot_block"] = [12201, 12240]
    with pytest.raises(ConfigurationError, match="sealed range 12001-12240"):
        P.spec_from_constants(spec.gate, data)


# ------------------------------------------------------------ seed guards


def test_pilot_seed_guard_accepts_only_the_registered_block(spec: P.RealisedWPilotSpec) -> None:
    """Basis: block 13201-13240 = 40 seeds; 13200 and 13241 are its neighbours, 13101 is E1,
    True is not a seed, a repeat is refused."""

    assert P.check_pilot_seeds(spec, list(range(13201, 13241))) == tuple(range(13201, 13241))
    for bad in ([13200], [13241], [13101], [True], [13201, 13201], []):
        with pytest.raises(ConfigurationError):
            P.check_pilot_seeds(spec, bad)


@pytest.mark.parametrize(
    "seed", [13201, 13240, 13220, 13001, 13060, 13101, 13180, 13901, 13930, 0, 149, 9300, 12240, 90002, -1]
)
def test_smoke_seed_guard_refuses_every_registered_and_sealed_seed(spec: P.RealisedWPilotSpec, seed: int) -> None:
    """Basis: realised-w 13201-13240, confirmatory 13001-13060, E1 13101-13180, horizon pilot
    13901-13930 and sealed ranges (0-149, 9300-9899, 12001-12240, 90001-90003) are refused;
    a negative seed is not a seed."""

    with pytest.raises(ConfigurationError):
        P.check_smoke_seeds(spec, [seed])


def test_smoke_seed_guard_accepts_an_unregistered_seed(spec: P.RealisedWPilotSpec) -> None:
    """Basis: 20011-20013 lie outside every block and sealed range of the constants."""

    assert P.check_smoke_seeds(spec, [20011, 20012, 20013]) == (20011, 20012, 20013)
    with pytest.raises(ConfigurationError, match="repeat"):
        P.check_smoke_seeds(spec, [20011, 20011])


# ----------------------------------------------------------- output guard


@pytest.mark.parametrize(
    ("rel", "message"),
    [
        ("docs/prereg/jr5", "contain docs/prereg/jr5"),
        ("docs/prereg/jr5/out", "contain docs/prereg/jr5"),
        ("docs/prereg", "contain docs/prereg/jr5"),
        ("docs", "contain docs/prereg/jr5"),
        ("src", "contain src"),
        ("src/codontrace/claimgate/data", "contain src"),
        ("src/codontrace/preregistration", "contain src"),
        ("tests/out", "contain tests"),
    ],
)
def test_output_guard_refuses_the_prereg_source_and_test_trees(rel: str, message: str) -> None:
    """Basis: the output may not be docs/prereg/jr5 (equal), lie inside it (docs/prereg/jr5/out),
    or contain it (docs/prereg, docs); the same holds for src (packaged constants under
    src/codontrace/claimgate/data, the prereg code under src/codontrace/preregistration) and
    tests. The message names the protected folder."""

    with pytest.raises(ConfigurationError, match=message):
        P.check_output_dir(ROOT / rel, ROOT)


def test_output_guard_refuses_a_directory_holding_a_locked_file(tmp_path: Path) -> None:
    """Basis: a root whose record.json lists data/locked.txt as a plan file: data (which holds
    it) is refused by the record check; data/other (which does not) is accepted."""

    (tmp_path / "docs/prereg/jr5").mkdir(parents=True)
    record = {"manifest": {"files": [["data/locked.txt", "0" * 64]]}}
    (tmp_path / "docs/prereg/jr5/record.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="locked file data/locked.txt"):
        P.check_output_dir(tmp_path / "data", tmp_path)
    with pytest.raises(ConfigurationError, match="locked file data/locked.txt"):
        P.check_output_dir(tmp_path / "data/locked.txt", tmp_path)
    assert P.check_output_dir(tmp_path / "other", tmp_path) == (tmp_path / "other").resolve()


def test_output_guard_names_the_repository_root(tmp_path: Path) -> None:
    """Basis: the root is refused with its own message before the protected-folder check."""

    with pytest.raises(ConfigurationError, match="repository root"):
        P.check_output_dir(ROOT, ROOT)


def test_output_guard_accepts_a_scratch_directory_and_refuses_a_file(tmp_path: Path) -> None:
    """Basis: tmp_path is outside the repo; an existing regular file is not a directory."""

    assert P.check_output_dir(tmp_path / "out", ROOT) == (tmp_path / "out").resolve()
    f = tmp_path / "file"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not a directory"):
        P.check_output_dir(f, ROOT)


# ------------------------------------------------------------------ fit


def test_fit_pin_is_the_sha256_of_the_registered_file(spec: P.RealisedWPilotSpec) -> None:
    """Basis: FIT_IMPLEMENTATION_SHA256 = sha256(tests/_jr5_e1_fit.py); load_fit returns the
    module with TOL 1e-10 and MAX_ITER 100 (gate_e1.fit)."""

    raw = (ROOT / spec.fit_implementation).read_bytes()
    assert P.FIT_IMPLEMENTATION_SHA256 == hashlib.sha256(raw).hexdigest()
    module, digest = P.load_fit(spec, ROOT)
    assert digest == P.FIT_IMPLEMENTATION_SHA256
    assert (module.TOL, module.MAX_ITER) == (1e-10, 100)


def test_fit_pin_refuses_a_changed_file(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: one appended byte changes the sha256, so the estimator file is refused."""

    target = tmp_path / spec.fit_implementation
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / spec.fit_implementation).read_bytes() + b"\n")
    with pytest.raises(ConfigurationError, match="pinned sha256"):
        P.load_fit(spec, tmp_path)


def _rows(asexual: list[int], census: list[int]) -> list[dict[str, Any]]:
    return [{"generation": g, "asexual": a, "census": c} for g, (a, c) in enumerate(zip(asexual, census, strict=True))]


def test_fit_population_is_the_registered_bias_reduced_fit(spec: P.RealisedWPilotSpec) -> None:
    """Basis: exact WF expectations at w = 2 from p0 0.2 and N 200: logit p_t = log(0.25) + t log 2,
    so p = 0.2, 1/3, 1/2, 2/3, 0.8, 8/9 and k = 200 p. The runner's slope is fit_logit(...,
    bias_reduced=True) bit for bit; the plain MLE of exact expectations is log 2 (1e-9) and
    the bias-reduced slope lies within 0.01 of it."""

    module, _ = P.load_fit(spec, ROOT)
    p = [1.0 / (1.0 + math.exp(-(math.log(0.25) + t * math.log(2.0)))) for t in range(6)]
    k = np.array([200.0 * v for v in p])
    n = np.full(6, 200.0)
    x = np.arange(6, dtype=float)
    rows = [{"generation": t, "asexual": float(k[t]), "census": 200.0} for t in range(6)]
    log_w, fixed, lost, converged = P.fit_population(module, spec, rows)
    direct = module.fit_logit(k, n, x, bias_reduced=True, tol=1e-10, max_iter=100)
    assert log_w == float(direct[1])
    assert (fixed, lost, converged) == (None, None, True)
    assert abs(float(module.fit_logit(k, n, x, bias_reduced=False)[1]) - math.log(2.0)) < 1e-9
    assert log_w is not None and abs(log_w - math.log(2.0)) < 0.01


def test_fit_population_reports_fixation_and_loss_generations(spec: P.RealisedWPilotSpec) -> None:
    """Basis: counts 4, 10, 20, 20 of 20 first equal the census at generation 2; counts
    4, 1, 0, 0 first reach 0 at generation 2."""

    module, _ = P.load_fit(spec, ROOT)
    fixed = P.fit_population(module, spec, _rows([4, 10, 20, 20], [20, 20, 20, 20]))
    lost = P.fit_population(module, spec, _rows([4, 1, 0, 0], [20, 20, 20, 20]))
    assert fixed[1:3] == (2, None)
    assert lost[1:3] == (None, 2)


class _NoConvergence:
    TOL = 1e-10
    MAX_ITER = 100

    @staticmethod
    def fit_logit(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("fit did not converge")


def test_non_convergence_raises_for_a_kept_population_and_is_none_for_an_excluded_one(
    spec: P.RealisedWPilotSpec,
) -> None:
    """Basis: gate_e1.fit.on_no_convergence = raise; fixation at generation 1 < 3
    (early_fixation_generation) excludes the population, so its slope is not used (None)."""

    module: Any = _NoConvergence
    with pytest.raises(RuntimeError):
        P.fit_population(module, spec, _rows([4, 6, 8, 10], [20, 20, 20, 20]))
    assert P.fit_population(module, spec, _rows([4, 20, 20, 20], [20, 20, 20, 20])) == (None, 1, None, False)


# -------------------------------------------------------------- decision


def _alternating(center: float, half: float = 0.05) -> list[float]:
    return [center + (half if i % 2 == 0 else -half) for i in range(40)]


def test_pilot_cell_is_the_e1_cell_rule_on_the_pilot_block(spec: P.RealisedWPilotSpec) -> None:
    """Basis: the same 40 log w (log 2 +/- 0.05) on the E1 block 13101-13140 and on the pilot
    block 13201-13240 give the same TOST record: mean log 2, sd 0.05*sqrt(40/39) = 0.05064,
    se 0.008006, half width 1.6849*se = 0.01349, ci90 [0.6796, 0.7066] inside
    [log 1.8, log 2.2] = [0.5878, 0.7885]; passed."""

    values = _alternating(math.log(2.0))
    e1 = evaluate_e1_cell(spec.gate, 0.5, 200, [E1Population(seed=13101 + i, log_w=v) for i, v in enumerate(values)])
    pops = [E1Population(seed=13201 + i, log_w=v) for i, v in enumerate(values)]
    cell, passed = P.pilot_decision(spec, pops)
    assert cell.tost is not None and e1.tost is not None
    assert cell.tost.to_record() == e1.tost.to_record()
    assert cell.exclusion_interval == e1.exclusion_interval
    assert passed is True and cell.passed is e1.passed is True
    assert cell.tost.ci_low == pytest.approx(0.6796, abs=2e-4)
    assert cell.tost.ci_high == pytest.approx(0.7066, abs=2e-4)


def test_pilot_fails_when_the_interval_leaves_the_bounds(spec: P.RealisedWPilotSpec) -> None:
    """Basis: centre log 1.75 = 0.5596 with half width 0.0135 gives ci90 upper 0.5731 < log 1.8
    = 0.5878, so not equivalent and the pilot fails."""

    pops = [E1Population(seed=13201 + i, log_w=v) for i, v in enumerate(_alternating(math.log(1.75)))]
    cell, passed = P.pilot_decision(spec, pops)
    assert cell.equivalent is False and passed is False


@pytest.mark.parametrize(("n_fixed", "cap_exceeded"), [(8, False), (9, True)])
def test_pilot_exclusion_cap_is_the_e1_cap(spec: P.RealisedWPilotSpec, n_fixed: int, cap_exceeded: bool) -> None:
    """Basis: cap 0.2 of 40 = 8; fixation at generation 1 < 3 excludes a population; 8 excluded
    is at the cap (pass, 32 kept values log 2 +/- 0.05 are equivalent), 9 exceeds it (fail)."""

    values = _alternating(math.log(2.0))
    pops = [
        E1Population(seed=13201 + i, log_w=None, fixed_generation=1)
        if i < n_fixed
        else E1Population(seed=13201 + i, log_w=v)
        for i, v in enumerate(values)
    ]
    cell, passed = P.pilot_decision(spec, pops)
    assert cell.exclusion_cap_exceeded is cap_exceeded
    assert passed is (not cap_exceeded)


def test_pilot_cell_refuses_e1_seeds_and_a_block_overlapping_e1(spec: P.RealisedWPilotSpec) -> None:
    """Basis: the pilot cell expects seeds 13201-13240; E1 seeds 13101-13140 are refused, and a
    block 13130-13169 shares seeds with the E1 block 13101-13140."""

    values = _alternating(math.log(2.0))
    with pytest.raises(ConfigurationError):
        P.pilot_decision(spec, [E1Population(seed=13101 + i, log_w=v) for i, v in enumerate(values)])
    pops = [E1Population(seed=13130 + i, log_w=v) for i, v in enumerate(values)]
    with pytest.raises(ConfigurationError, match="overlaps an E1 calibration block"):
        evaluate_e1_pilot_cell(spec.gate, 0.5, 200, pops, (13130, 13169))


# ------------------------------------------------------------- invariants


def _row(**kw: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": "generation",
        "generation": 1,
        "census": 36,
        "asexual": 8,
        "counts": {"asexual": 8, "hermaphrodite": 15, "male": 13},
        "births": 16,
        "genome_lengths": [24],
        "genome_length_founders": 24,
        "ledger_residual": 0.0,
        "outcross_fee_atp": 0.0,
    }
    row.update(kw)
    return row


_PREV = _row(generation=0, census=20, asexual=4, births=0, counts={"asexual": 4, "hermaphrodite": 8, "male": 8})


def test_check_row_passes_a_valid_generation(spec: P.RealisedWPilotSpec) -> None:
    """Basis: generation 1 from 4 of 20 to 8 of 36 with 16 births, soft K 80: every invariant holds."""

    assert P.check_row(_row(), _PREV, spec, 80)[-1] == "loss_absorbing"
    assert "founder_share" in P.check_row(_PREV, None, spec, 80)


@pytest.mark.parametrize(
    ("change", "name"),
    [
        ({"ledger_residual": float("nan")}, "finite"),
        ({"census": float("inf")}, "finite"),
        ({"asexual": 37}, "asexual_within_census"),
        ({"census": 81, "counts": {"asexual": 8, "male": 73}}, "census_within_soft_k"),
        ({"counts": {"asexual": 8, "male": 27}}, "counts_sum_to_census"),
        ({"genome_lengths": [24, 25]}, "genome_length_conserved"),
        ({"ledger_residual": 1e-6}, "ledger_residual"),
        ({"outcross_fee_atp": 0.25}, "outcross_fee_zero"),
        ({"generation": 2}, "generation_step"),
        ({"births": 0}, "births_present"),
    ],
)
def test_check_row_stops_at_the_first_broken_invariant(
    spec: P.RealisedWPilotSpec, change: dict[str, Any], name: str
) -> None:
    """Basis: each change breaks exactly the named invariant (residual limit 1e-9, fee 0.0,
    soft K 80, census 36); the error names it."""

    with pytest.raises(P.PilotInvariantError, match=name):
        P.check_row(_row(**change), _PREV, spec, 80)


def test_check_row_founder_share_and_absorbing_states(spec: P.RealisedWPilotSpec) -> None:
    """Basis: founders need 0.2 * 20 = 4 asexual; a fixed line (20 of 20) must stay fixed; a
    lost line (0) must stay lost."""

    with pytest.raises(P.PilotInvariantError, match="founder_share"):
        P.check_row(_row(generation=0, census=20, asexual=5, counts={"asexual": 5, "male": 15}), None, spec, 80)
    fixed = _row(generation=0, census=20, asexual=20, counts={"asexual": 20})
    with pytest.raises(P.PilotInvariantError, match="fixation_absorbing"):
        P.check_row(_row(), fixed, spec, 80)
    lost = _row(generation=0, census=20, asexual=0, counts={"male": 20})
    with pytest.raises(P.PilotInvariantError, match="loss_absorbing"):
        P.check_row(_row(), lost, spec, 80)


# ---------------------------------------------------------------- engine


def test_population_carries_the_section4_config_and_the_founder_share(spec: P.RealisedWPilotSpec) -> None:
    """Basis: section-4 engine config (sexual_recombination, closed_loop_hp_life) is applied as
    locked with sex ratio 0.5; 20 founders on the outcross locus, every 5th (1/0.2) asexual,
    so founders 0, 5, 10, 15 = 4 = 0.2 * 20."""

    from codontrace.genesis.host_parasite_life_plugin import hp_life_config

    arm = P.build_population(spec, smoke_design(), SMOKE_SEED, SMOKE_N)
    cfg = arm.runner.configs
    sexual = spec.engine_config["sexual_recombination"]
    life = spec.engine_config["closed_loop_hp_life"]
    for key in (
        "enabled",
        "mating_types_enabled",
        "sex_assignment",
        "pairing_policy",
        "two_fold_cost_sex",
        "hermaphrodite_selfing",
        "diploid_meiosis",
    ):
        assert getattr(cfg.sexual_recombination, key) == sexual[key]
    assert cfg.sexual_recombination.sex_ratio == 0.5
    assert list(cfg.sexual_recombination.mating_type_set) == spec.engine_config["mating_type_set"]["obligate_outcross"]
    hp = hp_life_config(cfg.closed_loop_hp_life)
    assert (hp.outcross_enabled, hp.outcross_runtime_atp, hp.selfing_birth_atp_endowment) == (
        life["outcross_enabled"],
        life["outcross_runtime_atp"],
        life["selfing_birth_atp_endowment"],
    )
    orgs = arm.runner.population.organisms
    assert len(orgs) == 20
    assert [i for i, o in enumerate(orgs) if o.asexual_lineage] == [0, 5, 10, 15]


class _BrokenLedger:
    @staticmethod
    def check() -> None:
        raise RuntimeError("residual 1e-3")


@pytest.mark.parametrize(
    ("ledger", "message"), [(None, "no world ATP ledger"), (_BrokenLedger(), "ledger check failed")]
)
def test_census_refuses_a_missing_or_failing_world_ledger(
    spec: P.RealisedWPilotSpec, ledger: Any, message: str
) -> None:
    """Basis: the ledger residual invariant needs the world ATP ledger; without one, or when
    its own check fails, the census row is refused rather than reported as residual 0."""

    arm = P.build_population(spec, smoke_design(), SMOKE_SEED, SMOKE_N)
    arm.runner.atp_ledger = ledger
    with pytest.raises(P.PilotInvariantError, match=message):
        P.census_row(arm, 0, set(), 24, SMOKE_SEED)


def test_founders_at_soft_k_give_no_births_and_the_runner_stops(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: with founders = soft K (multiple 1.0) the harness places no offspring, so the
    asexual share cannot change; births_present breaks at generation 1 and the run stops with
    a traceback in the progress log and the partial rows kept as failed-1."""

    out = tmp_path / "k1"
    with pytest.raises(P.PilotInvariantError, match="births_present"):
        run_smoke(out, spec, design=smoke_design(1.0))
    ev = events(out)
    assert ev[-1]["event"] == "failed" and "births_present" in ev[-1]["traceback"]
    assert (out / "seeds" / f"seed-{SMOKE_SEED}.jsonl.failed-1").is_file()
    assert not (out / "seeds" / f"seed-{SMOKE_SEED}.jsonl").exists()
    assert (out / "manifest.json").is_file()


def test_smoke_run_logs_progress_and_writes_a_manifest_with_digests(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: T 3 gives generation rows 0..3 plus one fit row = 5 rows; progress has start,
    seed_start, 4 generation events with invariant lists, seed_end (rows 5, ETA 0 for the last
    seed) and done; the manifest sha256 of each file equals the file's sha256; smoke writes no
    result.json."""

    out = tmp_path / "run"
    summary = run_smoke(out, spec)
    assert summary["decision_written"] is False and summary["seeds_done"] == 1
    ev = events(out)
    kinds = [e["event"] for e in ev]
    assert kinds == ["start", "seed_start", "generation", "generation", "generation", "generation", "seed_end", "done"]
    gens = [e for e in ev if e["event"] == "generation"]
    assert [g["generation"] for g in gens] == [0, 1, 2, 3]
    assert gens[0]["invariants_ok"][-1] == "founder_share" and gens[1]["invariants_ok"][-1] == "loss_absorbing"
    end = ev[-2]
    assert end["rows_written"] == 5 and end["eta_seconds"] == 0.0 and "log_w" not in end
    lines = (out / "seeds" / f"seed-{SMOKE_SEED}.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5 and json.loads(lines[-1])["kind"] == "fit"
    assert set(gens[0]) == {"ts", "event", "seed", "generation", "births", "invariants_ok"}
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        assert hashlib.sha256((out / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    assert manifest["body_digest"] == summary["body_digest"]
    assert manifest["run"]["design_digest"] == smoke_design().digest()
    assert not (out / "result.json").exists()


def test_rerun_and_resume_write_the_same_bytes(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: RNGManager draws only from the run seed, so two fresh runs write identical seed
    files; resuming a complete run keeps the seed file (seed_kept) and the body digest; a
    killed run's partial file is kept as killed-1 and the seed re-run gives the same bytes; the
    killed copy is kept and listed but is not part of the body, so the killed-then-resumed run has
    the one-shot run's body digest (PREREG section 8, R50-L4b)."""

    a, b = tmp_path / "a", tmp_path / "b"
    first = run_smoke(a, spec)
    run_smoke(b, spec)
    name = f"seeds/seed-{SMOKE_SEED}.jsonl"
    assert (a / name).read_bytes() == (b / name).read_bytes()
    again = run_smoke(a, spec)
    assert again["body_digest"] == first["body_digest"]
    assert "seed_kept" in [e["event"] for e in events(a)]
    c = tmp_path / "c"
    shutil.copytree(a, c)
    (c / name).rename(c / (name + ".partial"))
    resumed = run_smoke(c, spec)
    assert (c / name).read_bytes() == (a / name).read_bytes()
    assert (c / (name + ".killed-1")).read_bytes() == (a / name).read_bytes()
    assert "seed_rerun_same_seed" in [e["event"] for e in events(c)]
    assert resumed["body_digest"] == first["body_digest"]


def test_resume_refuses_a_different_configuration(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: run.json fixes the horizon at 3; a resume at horizon 2 is a different run."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    with pytest.raises(ConfigurationError, match="different configuration"):
        run_smoke(out, spec, horizon=2)


def test_nan_in_a_census_row_stops_the_run(
    spec: P.RealisedWPilotSpec, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Basis: a NaN ledger residual at generation 2 breaks the finite invariant; the run
    stops there with generation rows 0 and 1 written and no fit row."""

    real = P.census_row

    def poisoned(arm: Any, generation: int, *a: Any, **kw: Any) -> dict[str, Any]:
        row = real(arm, generation, *a, **kw)
        if generation == 2:
            row["ledger_residual"] = float("nan")
        return row

    monkeypatch.setattr(P, "census_row", poisoned)
    out = tmp_path / "nan"
    with pytest.raises(P.PilotInvariantError, match="finite"):
        run_smoke(out, spec)
    kept = (out / "seeds" / f"seed-{SMOKE_SEED}.jsonl.failed-1").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["generation"] for line in kept] == [0, 1]


def test_smoke_mode_refuses_pilot_seeds_and_the_pilot_host_n(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: smoke seeds may not touch 13201-13240; smoke host N must be below 200."""

    with pytest.raises(ConfigurationError, match="realised_w_pilot"):
        run_smoke(tmp_path / "x", spec, seeds=[13201])
    with pytest.raises(ConfigurationError, match="below the pilot host N"):
        run_smoke(tmp_path / "y", spec, host_n=200)
    assert not (tmp_path / "x").exists() and not (tmp_path / "y").exists()


def test_pilot_mode_refuses_while_the_design_is_undecided(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: PILOT_POPULATION_DESIGN is None until the demography is decided, so pilot mode
    refuses before writing anything; it also refuses any design, N or T override."""

    assert P.PILOT_POPULATION_DESIGN is None
    with pytest.raises(ConfigurationError, match="not decided"):
        P.run_pilot(tmp_path / "p", root=ROOT, spec=spec)
    with pytest.raises(ConfigurationError, match="override"):
        P.run_pilot(tmp_path / "p", root=ROOT, spec=spec, design=smoke_design())
    assert not (tmp_path / "p").exists()


def test_cli_dry_run_writes_nothing_and_pilot_cli_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Basis: dry run prints the configuration (seeds 13201..13240 = 40, runnable false while
    the design is None) and creates no directory; the pilot run exits 2 with the refusal."""

    out = tmp_path / "dry"
    assert P.main(["--out", str(out), "--root", str(ROOT), "--dry-run"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["seeds"] == [13201, 13240, 40] and shown["runnable"] is False
    assert shown["design_pin"].startswith("refused: no DEVIATIONS.md entry names")
    assert shown["fit_sha256"] == P.FIT_IMPLEMENTATION_SHA256
    assert not out.exists()
    assert P.main(["--out", str(out), "--root", str(ROOT)]) == 2
    assert "not decided" in capsys.readouterr().err
    assert not out.exists()


def test_cli_smoke_run_with_a_design_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Basis: the design JSON round-trips to the same PopulationDesign (same digest); the smoke
    run writes one seed file and prints its summary."""

    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(smoke_design().to_record()), encoding="utf-8")
    out = tmp_path / "cli"
    argv = ["--out", str(out), "--root", str(ROOT), "--mode", "smoke", "--seeds", str(SMOKE_SEED)]
    argv += ["--host-n", str(SMOKE_N), "--horizon", str(SMOKE_T), "--design-json", str(design_path)]
    assert P.main(argv) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["seeds_done"] == 1
    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert run["design_digest"] == smoke_design().digest()


# ------------------------------------------------------------ blinding (M1a)


# Keys that would carry the asexual or census series (or counts by type) in smoke outputs.
_SERIES_KEYS = frozenset(
    {"asexual", "census", "counts", "fixed_generation", "lost_generation", "generations", "thinned"}
)
_TYPE_KEYS = frozenset({"male", "female", "hermaphrodite"})
# A count named next to a number in free text, or a printed dict of counts.
_COUNT_TEXT = re.compile(r"(asexual|census|counts|male|female|hermaphrodite|offspring|of)\W{0,4}[0-9]|\{'")


def _series_leaks(value: Any, where: str) -> list[str]:
    """Paths (never values) of every series or count key, and every numeric log_w, inside a JSON value."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SERIES_KEYS or key in _TYPE_KEYS:
                found.append(f"{where}.{key}")
            if key == "log_w" and isinstance(item, (int, float)) and not isinstance(item, bool):
                found.append(f"{where}.{key}")
            found.extend(_series_leaks(item, f"{where}.{key}"))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            found.extend(_series_leaks(item, f"{where}[{i}]"))
    return found


def _text_leaks(text: str, where: str) -> list[str]:
    """Lines of error text naming a count next to a number. Traceback source lines (indented 4)
    are the module's fixed code, not run values, and are skipped."""

    return [
        f"{where}:{n + 1}"
        for n, line in enumerate(text.splitlines())
        if not line.startswith("    ") and _COUNT_TEXT.search(line)
    ]


def _leaks(out: Path) -> list[str]:
    """Every file under a smoke output directory: JSON keys, CSV header, and free text (errors,
    tracebacks) of the progress log. Reports paths only."""

    leaks: list[str] = []
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        rel = path.relative_to(out).as_posix()
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".csv":
            header = set(text.splitlines()[0].split(","))
            leaks.extend(f"{rel}: column {c}" for c in sorted(header & (_SERIES_KEYS | {"log_w"})))
            continue
        if path.suffix == ".json":
            leaks.extend(_series_leaks(json.loads(text), rel))
            continue
        for n, line in enumerate(text.splitlines()):
            record = json.loads(line)
            leaks.extend(_series_leaks(record, f"{rel}:{n + 1}"))
            for key in ("error", "traceback"):
                if isinstance(record.get(key), str):
                    leaks.extend(_text_leaks(record[key], f"{rel}:{n + 1}.{key}"))
    return leaks


@pytest.mark.parametrize("design", ["overlapping", "discrete"])
def test_smoke_outputs_hold_no_series_or_estimate(
    spec: P.RealisedWPilotSpec, tmp_path: Path, capsys: pytest.CaptureFixture[str], design: str
) -> None:
    """Basis: smoke mode is blind (R50-M1a, R51-M1a): w can be fitted from the per-generation
    asexual count out of the census, so no smoke file may hold that series. Seed rows keep only
    pooled checks (births, genome lengths, ledger, fee, discrete-step checks); the fit row has
    log_w null and no arrays, fixation or loss generation; progress lines, populations.csv,
    run.json, manifest.json and the CLI's stdout carry none either. Failures list paths only."""

    chosen = smoke_design() if design == "overlapping" else discrete_design()
    out = tmp_path / "blind"
    run_smoke(out, spec, seeds=[20011, 20012], design=chosen, horizon=2)
    assert _leaks(out) == []
    rows = [json.loads(x) for x in (out / "seeds/seed-20011.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(r["blinded"] is True for r in rows)
    assert set(rows[0]) <= set(P.SMOKE_ROW_KEYS) | {"blinded"}
    assert set(rows[-1]) == {"kind", "seed", "log_w", "blinded", "converged", "population_lost_generation"}
    assert rows[-1]["log_w"] is None
    header = (out / "populations.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == "seed,converged,population_lost_generation"
    assert json.loads((out / "run.json").read_text(encoding="utf-8"))["blinded"] is True
    assert not (out / "result.json").exists()
    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(chosen.to_record()), encoding="utf-8")
    argv = ["--out", str(tmp_path / "cli"), "--root", str(ROOT), "--mode", "smoke", "--seeds", "20013"]
    assert P.main([*argv, "--host-n", "20", "--horizon", "2", "--design-json", str(design_path)]) == 0
    captured = capsys.readouterr()
    assert _series_leaks(json.loads(captured.out), "stdout") == [] and captured.err == ""
    assert _leaks(tmp_path / "cli") == []


def test_a_failing_smoke_run_names_the_invariant_but_no_count(
    spec: P.RealisedWPilotSpec, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Basis: the failure path is blind too (R51-M1a channel 4). With the asexual count set above
    the census at generation 1 the run stops at asexual_within_census; the exception, the
    progress log's failed event (error and traceback), the kept failed-1 rows and the CLI's
    stderr name the invariant and the generation but no count, census or counts dict."""

    real = P.census_row

    def poisoned(arm: Any, generation: int, *a: Any, **kw: Any) -> dict[str, Any]:
        row = real(arm, generation, *a, **kw)
        if generation == 1:
            row["asexual"] = row["census"] + 1
        return row

    monkeypatch.setattr(P, "census_row", poisoned)
    out = tmp_path / "fail"
    with pytest.raises(P.PilotInvariantError) as info:
        run_smoke(out, spec)
    assert str(info.value) == "invariant asexual_within_census broke at generation 1 (details withheld: blind run)"
    assert events(out)[-1]["event"] == "failed"
    assert (out / "seeds" / f"seed-{SMOKE_SEED}.jsonl.failed-1").is_file()
    assert _leaks(out) == []
    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(smoke_design().to_record()), encoding="utf-8")
    argv = ["--out", str(tmp_path / "cli"), "--root", str(ROOT), "--mode", "smoke", "--seeds", str(SMOKE_SEED)]
    assert P.main([*argv, "--host-n", "20", "--horizon", "2", "--design-json", str(design_path)]) == 2
    err = capsys.readouterr().err
    assert "asexual_within_census" in err and _text_leaks(err, "stderr") == []
    assert _leaks(tmp_path / "cli") == []


# ------------------------------------------------- design pin (M1b) fixture

LOCKED_PLAN = "577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382"


def _entry(design_digest: str | None, *, old: str = LOCKED_PLAN, pre_pilot: bool = True, extra: str = "") -> str:
    lines = [
        "",
        "## 2026-11-15: realised-w pilot population design (test fixture)",
        "",
        "- Reason: test fixture for the runner's design pin; never part of the real log.",
    ]
    if design_digest is not None:
        lines.append(f"- Realised-w pilot population design: `{design_digest}`")
    if extra:
        lines.append(extra)
    if pre_pilot:
        lines.append(P.PRE_PILOT_LINE)
    lines += ["- Files: DEVIATIONS.md (this entry), record.json.", f"- Record digest: `{old}` -> `{LOCKED_PLAN}`", ""]
    return "\n".join(lines)


def make_root(tmp_path: Path, appended: str | None) -> Path:
    """A copy of the locked prereg folder and the fit file, with ``appended`` added to the log
    and record.json refreshed (file hashes and manifest digest), as a reviewed entry would be."""

    from codontrace.preregistration.manifest import PlanManifest, hash_plan

    root = tmp_path / "root"
    shutil.copytree(ROOT / "docs/prereg/jr5", root / "docs/prereg/jr5")
    (root / "tests").mkdir()
    shutil.copy2(ROOT / "tests/_jr5_e1_fit.py", root / "tests/_jr5_e1_fit.py")
    if appended is not None:
        with (root / "docs/prereg/jr5/DEVIATIONS.md").open("ab") as fh:
            fh.write(appended.encode("utf-8"))
    record_path = root / "docs/prereg/jr5/record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    title = record["manifest"]["title"]
    fresh = hash_plan([f for f, _ in record["manifest"]["files"]], root=root, title=title)
    record["manifest"]["files"] = [list(f) for f in fresh.files]
    record["manifest"]["digest"] = PlanManifest(fresh.files, title).digest
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return root


def test_the_real_log_names_no_pilot_design() -> None:
    """Basis: DEVIATIONS.md at this commit has seven entries and no design line (the
    2026-11-21 pilot-runner entry records exposures but fixes no design), so the pin check
    refuses and no pilot can run."""

    text = (ROOT / P.DEVIATIONS_RELPATH).read_text(encoding="utf-8")
    assert len(P.deviations_log_entries(text)) == 7
    assert not P.DESIGN_DIGEST_LINE.findall(text)
    with pytest.raises(ConfigurationError, match="no DEVIATIONS.md entry names a pilot population design"):
        P.verified_pilot_design_digest(ROOT)


def test_design_pin_accepts_a_verified_pre_pilot_entry(tmp_path: Path) -> None:
    """Basis: one appended entry chaining 577bd4ac -> 577bd4ac, naming the smoke design digest and
    declaring no pilot seed ran before it: the verified log yields that digest and its heading."""

    digest = smoke_design().digest()
    root = make_root(tmp_path, _entry(digest))
    pinned, heading = P.verified_pilot_design_digest(root)
    assert pinned == digest and heading.startswith("## 2026-11-15: realised-w pilot population design")


def test_design_pin_takes_the_latest_design_line(tmp_path: Path) -> None:
    """Basis: two appended entries name designs A then B; the latest (B) is the pinned design."""

    a, b = smoke_design().digest(), smoke_design(soft_k_multiple=2.0).digest()
    root = make_root(tmp_path, _entry(a) + _entry(b))
    assert P.verified_pilot_design_digest(root)[0] == b != a


@pytest.mark.parametrize(
    ("appended", "message"),
    [
        (lambda d: _entry(None), "no DEVIATIONS.md entry names"),
        (lambda d: _entry(d, pre_pilot=False), "no pilot seed ran before it"),
        (lambda d: _entry(d, extra=f"- Realised-w pilot population design: `{d}`"), "more than one"),
        (lambda d: _entry(d, old="0" * 64), "do not chain"),
    ],
    ids=["no-design-line", "no-pre-pilot-line", "two-design-lines", "broken-chain"],
)
def test_design_pin_refuses_an_entry_that_does_not_pin(tmp_path: Path, appended: Any, message: str) -> None:
    """Basis: the pin needs a design line, the no-pilot-seed declaration and exactly one design per
    entry; an entry whose old digest (0...0) is not the previous new digest (577bd4ac) breaks
    the chain that the locked-plan verification checks."""

    root = make_root(tmp_path, appended(smoke_design().digest()))
    with pytest.raises(ConfigurationError, match=message):
        P.verified_pilot_design_digest(root)


def test_design_pin_refuses_a_log_changed_after_the_record(tmp_path: Path) -> None:
    """Basis: record.json lists the sha256 of DEVIATIONS.md; one byte appended after the record was
    refreshed makes the fresh hash differ, so the log is refused before it is parsed."""

    root = make_root(tmp_path, _entry(smoke_design().digest()))
    with (root / "docs/prereg/jr5/DEVIATIONS.md").open("ab") as fh:
        fh.write(b"\n")
    with pytest.raises(ConfigurationError):
        P.verified_pilot_design_digest(root)


def test_design_pin_refuses_bytes_other_than_the_verified_ones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Basis: if the bytes read for parsing are not the bytes record.json lists (a change between
    the verification and the read), the pin is refused."""

    root = make_root(tmp_path, _entry(smoke_design().digest()))
    real = P.read_deviations_log
    monkeypatch.setattr(P, "read_deviations_log", lambda path: real(path) + "\n")
    with pytest.raises(ConfigurationError, match="changed after record.json was verified"):
        P.verified_pilot_design_digest(root)


def test_design_pin_runs_the_log_verification_on_the_parsed_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Basis: the parsed text itself goes through verify_deviations_log (checkpoints, chain, plan
    digest); a verifier that refuses it stops the pin."""

    root = make_root(tmp_path, _entry(smoke_design().digest()))

    def refuse(text: str, *, expected_plan_digest: str) -> None:
        raise ConfigurationError("verifier refused")

    monkeypatch.setattr(P, "verify_deviations_log", refuse)
    with pytest.raises(ConfigurationError, match="verifier refused"):
        P.verified_pilot_design_digest(root)


def _unchecked(design: P.PopulationDesign, name: str, value: Any) -> P.PopulationDesign:
    """A copy with one field set, bypassing validation (the digest must cover even refused values)."""

    other = copy.copy(design)
    object.__setattr__(other, name, value)
    return other


def test_design_digest_covers_every_field() -> None:
    """Basis: the digest is a canonical sha256 over every PopulationDesign field (label, generation
    model, the two max-age fields and the 14 harness fields); changing any one field changes it."""

    base = discrete_design()
    record = base.to_record()
    assert set(record) == {f.name for f in dataclasses.fields(P.PopulationDesign)} and len(record) == 18
    assert (record["enable_max_age_death"], record["max_age_ticks"]) == (True, 2)
    changes: dict[str, Any] = {
        "label": "other",
        "generation_model": "resample_to_census",
        "soft_k_multiple": 5.0,
        "world_size": 13,
        "enable_max_age_death": False,
        "max_age_ticks": 3,
        "birth_atp": base.birth_atp + 1.0,
        "basal_runtime_atp_cost": base.basal_runtime_atp_cost + 0.5,
        "passage_refill_mode": base.passage_refill_mode + "-x",
        "resource_bolus_amount": base.resource_bolus_amount + 1.0,
        "food_patches": ((0, 0),),
        "founder_spatial_policy": base.founder_spatial_policy + "-x",
        "mating_locus_lock": False,
        "mate_search_radius": 2,
        "outcross_mates_per_generation_cap": 2,
        "chamber_max_birth_wait_ticks": 3,
        "chamber_timeout_policy": "other",
        "founder_windows": ("x",),
    }
    assert set(changes) == set(record)
    for name, value in changes.items():
        assert _unchecked(base, name, value).digest() != base.digest(), name


def test_design_refuses_an_unknown_or_unwired_generation_model(spec: P.RealisedWPilotSpec) -> None:
    """Basis: generation_model must be one of the five named models; engine_overlapping and
    discrete_uniform_census are wired, the other three are refused before any engine boot."""

    with pytest.raises(ConfigurationError, match="generation_model must be one of"):
        smoke_design(generation_model="wright_fisher")
    unwired = [m for m in P.GENERATION_MODELS if m not in ("engine_overlapping", P.DISCRETE_UNIFORM_CENSUS)]
    assert len(unwired) == 3 and len(P.GENERATION_MODELS) == 5
    for model in unwired:
        with pytest.raises(ConfigurationError, match="is not wired"):
            P.build_population(spec, smoke_design(generation_model=model), SMOKE_SEED, SMOKE_N)


# ------------------------------------------------- pilot path after the gate (L2)


def _synthetic_pilot_spec(root: Path) -> P.RealisedWPilotSpec:
    """The registered spec with a synthetic unregistered block 30001-30003, N 20, T 3, and N 20
    added to the gate's reported host N so the E1 cell rule accepts the cell."""

    real = P.load_realised_w_pilot_spec(root)
    gate = dataclasses.replace(real.gate, host_n_reported=(*real.gate.host_n_reported, 20))
    return dataclasses.replace(real, gate=gate, seed_block=(30001, 30003), populations=3, host_n=20, horizon=3)


@pytest.fixture
def pilot_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, P.RealisedWPilotSpec]:
    """Pinned smoke design as PILOT_POPULATION_DESIGN, a root whose log pins it, and a fit stub
    returning log 2 for every population, so no engine w is estimated or written."""

    design = smoke_design()
    root = make_root(tmp_path, _entry(design.digest()))
    monkeypatch.setattr(P, "PILOT_POPULATION_DESIGN", design)
    monkeypatch.setattr(P, "fit_population", lambda module, spec, rows: (math.log(2.0), None, None, True))
    return root, _synthetic_pilot_spec(root)


def test_pilot_path_writes_the_decision_after_the_last_seed(
    pilot_env: tuple[Path, P.RealisedWPilotSpec], tmp_path: Path
) -> None:
    """Basis: block 30001-30003 at N 20, T 3, with the fit stubbed to log 2 for all three: a
    constant sample has zero spread, so the 90% and 95% intervals are [log 2, log 2], inside
    [log 1.8, log 2.2] and excluding 0; the cell passes. run.json carries N 20 and T 3; the
    decision is written once, after seed 30003."""

    root, spec = pilot_env
    out = tmp_path / "pilot"
    summary = P.run_pilot(out, root=root, spec=spec)
    assert summary["decision_written"] is True and summary["pilot_passed"] is True
    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert (run["host_n"], run["horizon"], run["seeds"], run["blinded"]) == (20, 3, [30001, 30002, 30003], False)
    kinds = [e["event"] for e in events(out)]
    assert kinds.index("decision") > max(i for i, k in enumerate(kinds) if k == "seed_end")
    assert kinds.count("seed_end") == 3 and kinds.count("decision") == 1
    result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert result["design_digest"] == smoke_design().digest() and result["pilot_passed"] is True
    assert result["cell"]["seeds"] == [30001, 30002, 30003] and result["confirmatory"] is False
    rows = (out / "seeds/seed-30003.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 5 and json.loads(rows[-1])["blinded"] is False


def test_pilot_path_writes_no_decision_for_part_of_the_block(
    pilot_env: tuple[Path, P.RealisedWPilotSpec], tmp_path: Path
) -> None:
    """Basis: seeds 30001-30002 are 2 of the 3 block seeds; the decision needs every seed, so no
    result.json is written."""

    root, spec = pilot_env
    out = tmp_path / "part"
    summary = P.run_pilot(out, root=root, spec=spec, seeds=[30001, 30002])
    assert summary["decision_written"] is False and not (out / "result.json").exists()
    assert "decision" not in [e["event"] for e in events(out)]


def test_pilot_path_refuses_a_design_the_log_does_not_pin(
    pilot_env: tuple[Path, P.RealisedWPilotSpec], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Basis: the log pins the smoke design (soft K multiple 4); a design with multiple 2 has
    another digest, so pilot mode refuses before writing anything."""

    root, spec = pilot_env
    monkeypatch.setattr(P, "PILOT_POPULATION_DESIGN", smoke_design(soft_k_multiple=2.0))
    with pytest.raises(ConfigurationError, match="not the one the DEVIATIONS.md entry pins"):
        P.run_pilot(tmp_path / "x", root=root, spec=spec)
    assert not (tmp_path / "x").exists()


def test_pilot_path_refuses_when_the_log_names_no_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Basis: the real log names no design, so even a set PILOT_POPULATION_DESIGN cannot run."""

    monkeypatch.setattr(P, "PILOT_POPULATION_DESIGN", smoke_design())
    with pytest.raises(ConfigurationError, match="no DEVIATIONS.md entry names"):
        P.run_pilot(tmp_path / "x", root=ROOT, spec=_synthetic_pilot_spec(ROOT))
    assert not (tmp_path / "x").exists()


# ------------------------------------------------------------ boot guard (L6)


@pytest.mark.parametrize(("mode", "seed"), [(P.MODE_SMOKE, 13201), (P.MODE_SMOKE, 13901), (P.MODE_PILOT, 20011)])
def test_engine_boot_is_guarded_again_before_each_seed(spec: P.RealisedWPilotSpec, mode: str, seed: int) -> None:
    """Basis: immediately before an engine boot the seed is checked again for its mode: a smoke
    run refuses the realised-w and horizon pilot seeds 13201 and 13901, a pilot run refuses
    20011 (outside 13201-13240). The refusal is a ConfigurationError, not the test safety net's
    RuntimeError, so no boot was attempted."""

    with pytest.raises(ConfigurationError):
        P._run_seed(spec, smoke_design(), seed, SMOKE_N, SMOKE_T, None, lambda row, checked: None, mode)  # type: ignore[arg-type]


def test_boot_guard_refuses_an_unknown_mode(spec: P.RealisedWPilotSpec) -> None:
    """Basis: only pilot and smoke modes exist; any other mode is refused before a boot."""

    with pytest.raises(ConfigurationError, match="mode must be"):
        P._guard_boot(spec, "probe", SMOKE_SEED)


def test_the_safety_net_refuses_registered_seeds() -> None:
    """Basis: the test fixture reads every block and sealed range from the constants; 13201
    (realised-w), 13930 (horizon pilot) and 12240 (sealed) are refused at boot, 20011 is not."""

    from codontrace.genesis.closed_loop_hp_arm01 import LifeLoopEcologyArm

    for seed in (13201, 13930, 12240):
        with pytest.raises(RuntimeError, match="test safety net"):
            LifeLoopEcologyArm.boot(arm="avirulent", seed=seed)
    assert not _registered_or_sealed(20011)


# ------------------------------------------------------- resume checks (L1, L3, L4)


def _seed_file(out: Path) -> Path:
    return out / "seeds" / f"seed-{SMOKE_SEED}.jsonl"


def _rewrite_seed_file(out: Path, edit: Any, *, drop_manifest: bool = True) -> None:
    path = _seed_file(out)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records = edit(records)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    if drop_manifest:
        (out / "manifest.json").unlink()


@pytest.mark.parametrize(
    ("edit", "error", "message"),
    [
        (lambda r: r[:-1], ConfigurationError, "without its fit row"),
        (lambda r: [*r[:-1], {**r[-1], "seed": 30002}], ConfigurationError, "fit row of another seed"),
        (lambda r: [*r[:-1], {**r[-1], "converged": not r[-1]["converged"]}], ConfigurationError, "does not match"),
        (lambda r: [*r[:-1], {**r[-1], "census": [0, 0, 0, 0]}], ConfigurationError, "does not match"),
        (lambda r: [r[0], {**r[1], "ledger_residual": 5.0}, *r[2:]], P.PilotInvariantError, "ledger_residual"),
        (lambda r: [r[0], r[2], r[1], *r[3:]], ConfigurationError, "generations 0 to 3"),
    ],
    ids=["no-fit-row", "other-seed", "edited-fit", "edited-census", "bad-row", "reordered"],
)
def test_resume_refuses_a_kept_pilot_seed_file_that_would_not_be_written_again(
    pilot_env: tuple[Path, P.RealisedWPilotSpec], tmp_path: Path, edit: Any, error: type[Exception], message: str
) -> None:
    """Basis: a kept pilot file is re-verified on resume (R50-L4): it needs a fit row for this
    seed, generations 0..3 in order, rows that pass the invariants again (ledger residual 5.0 >
    1e-9) and a fit row equal to the one recomputed from its rows. Synthetic block 30001-30003,
    fit stubbed; the manifest is removed first so the content checks, not the sha check, refuse."""

    root, pspec = pilot_env
    out = tmp_path / "pilot"
    P.run_pilot(out, root=root, spec=pspec, seeds=[30001])
    path = out / "seeds" / "seed-30001.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in edit(records)), encoding="utf-8")
    (out / "manifest.json").unlink()
    with pytest.raises(error, match=message):
        P.run_pilot(out, root=root, spec=pspec, seeds=[30001])


@pytest.mark.parametrize(
    "edit",
    [lambda r: r[:-1], lambda r: [r[0], {**r[1], "births": r[1]["births"] + 1}, *r[2:]], lambda r: [*r, r[-1]]],
    ids=["no-fit-row", "edited-births", "extra-row"],
)
def test_resume_reruns_a_kept_smoke_seed_and_refuses_other_bytes(
    spec: P.RealisedWPilotSpec, tmp_path: Path, edit: Any
) -> None:
    """Basis: a smoke file holds no census series to re-check, so a kept smoke seed is run again in
    memory (same seed, same draws) and must give the same bytes; an unedited file is kept
    (seed_kept), and any edit is refused without the manifest's help."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    (out / "manifest.json").unlink()
    run_smoke(out, spec)
    assert "seed_kept" in [e["event"] for e in events(out)]
    _rewrite_seed_file(out, edit)
    with pytest.raises(ConfigurationError, match="differs from a re-run of its seed"):
        run_smoke(out, spec)


def test_resume_refuses_a_kept_file_that_differs_from_the_manifest(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: the previous manifest lists the seed file's sha256; any byte change (here one more
    trailing newline) makes it differ, so the file is refused."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    with _seed_file(out).open("a", encoding="utf-8") as fh:
        fh.write("\n")
    with pytest.raises(ConfigurationError, match="differs from the previous manifest"):
        run_smoke(out, spec)


@pytest.mark.parametrize(
    "change",
    [{"design": "k2"}, {"seeds": [SMOKE_SEED, 20012]}, {"host_n": 10}],
    ids=["design", "seeds", "host-n"],
)
def test_resume_refuses_another_design_seed_list_or_host_n(
    spec: P.RealisedWPilotSpec, tmp_path: Path, change: dict[str, Any]
) -> None:
    """Basis: run.json fixes design (multiple 4), seeds [20011] and host N 20; a resume with
    multiple 2, seeds [20011, 20012] or N 10 is another configuration."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    kw = {"design": smoke_design(soft_k_multiple=2.0)} if change.get("design") else dict(change)
    with pytest.raises(ConfigurationError, match="different configuration"):
        run_smoke(out, spec, **kw)


@pytest.mark.parametrize("damage", ["truncate", "not-object"])
def test_resume_refuses_an_unreadable_run_json(spec: P.RealisedWPilotSpec, tmp_path: Path, damage: str) -> None:
    """Basis: a truncated run.json is not JSON and a JSON list is not a run record; both are
    refused with ConfigurationError (CLI exit 2), not a raw JSONDecodeError (R50-L3)."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    raw = (out / "run.json").read_bytes()
    (out / "run.json").write_bytes(raw[: len(raw) // 2] if damage == "truncate" else b"[]")
    with pytest.raises(ConfigurationError, match="run.json"):
        run_smoke(out, spec)


@pytest.mark.parametrize("damage", [b"{", b"{}", b'{"files": [{"path": 1}]}'])
def test_resume_refuses_an_unreadable_previous_manifest(
    spec: P.RealisedWPilotSpec, tmp_path: Path, damage: bytes
) -> None:
    """Basis: a previous manifest that is not JSON, has no file list, or lists an entry without a
    path and sha256 cannot vouch for kept files, so the resume is refused."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    (out / "manifest.json").write_bytes(damage)
    with pytest.raises(ConfigurationError, match="manifest.json"):
        run_smoke(out, spec)


def test_outputs_are_replaced_atomically(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: run.json, populations.csv and manifest.json are written to <name>.tmp and renamed
    with os.replace; after the run no .tmp file is left and each final file parses."""

    out = tmp_path / "run"
    run_smoke(out, spec)
    assert not list(out.rglob("*.tmp"))
    for name in ("run.json", "manifest.json"):
        json.loads((out / name).read_text(encoding="utf-8"))
    assert (out / "populations.csv").read_text(encoding="utf-8").count("\n") == 2


def test_atomic_write_leaves_the_old_file_when_the_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Basis: the new bytes go to a temporary file first; if the rename fails the old file keeps its
    bytes (b"old"), so a crash never leaves a half-written run.json."""

    target = tmp_path / "run.json"
    target.write_bytes(b"old")

    def fail(*_a: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(P.os, "replace", fail)
    with pytest.raises(OSError):
        P._atomic_write(target, b"new")
    assert target.read_bytes() == b"old"


def test_fit_tolerance_cross_check_refuses_a_retuned_copy(
    spec: P.RealisedWPilotSpec, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Basis: gate_e1.fit says TOL 1e-10, MAX_ITER 100; a copy with TOL 1e-8 (sha pin moved to the
    copy so only the cross-check can refuse) or MAX_ITER 50 is refused."""

    for old, new in (("TOL = 1e-10", "TOL = 1e-8"), ("MAX_ITER = 100", "MAX_ITER = 50")):
        target = tmp_path / old.split()[0] / spec.fit_implementation
        target.parent.mkdir(parents=True)
        text = (ROOT / spec.fit_implementation).read_text(encoding="utf-8").replace(old, new)
        target.write_text(text, encoding="utf-8")
        monkeypatch.setattr(P, "FIT_IMPLEMENTATION_SHA256", hashlib.sha256(text.encode("utf-8")).hexdigest())
        with pytest.raises(ConfigurationError, match="tolerance or iteration cap"):
            P.load_fit(spec, tmp_path / old.split()[0])


@pytest.mark.parametrize(("counts", "expected"), [([4, 10, 20, 20], "excluded"), ([4, 6, 10, 20], "raises")])
def test_non_convergence_exclusion_boundary(spec: P.RealisedWPilotSpec, counts: list[int], expected: str) -> None:
    """Basis: early_fixation_generation = 3 and the rule excludes fixation before 3: fixation at
    generation 2 is excluded (None), fixation at generation 3 is kept, so a non-converging fit
    raises."""

    module: Any = _NoConvergence
    rows = _rows(counts, [20, 20, 20, 20])
    if expected == "excluded":
        assert P.fit_population(module, spec, rows) == (None, 2, None, False)
    else:
        with pytest.raises(RuntimeError):
            P.fit_population(module, spec, rows)


def test_on_fail_must_be_text(spec: P.RealisedWPilotSpec, constants: dict[str, Any]) -> None:
    """Basis: realised_w_pilot.on_fail is the registered failure rule string; a missing or
    non-string value is refused rather than recorded as "None"."""

    for value in (None, 1, ""):
        data = copy.deepcopy(constants)
        data["realised_w_pilot"]["on_fail"] = value
        with pytest.raises(ConfigurationError, match="on_fail"):
            P.spec_from_constants(spec.gate, data)


def test_cli_dry_run_reports_a_pinned_design_as_runnable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Basis: with the smoke design set as the pilot design and a root whose log pins its digest,
    the dry run shows that digest as the pin and runnable true; with a design the log does not
    pin (multiple 2), runnable is false. Nothing runs and nothing is written."""

    design = smoke_design()
    root = make_root(tmp_path, _entry(design.digest()))
    out = tmp_path / "dry"
    monkeypatch.setattr(P, "PILOT_POPULATION_DESIGN", design)
    assert P.main(["--out", str(out), "--root", str(root), "--dry-run"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["design_pin"] == design.digest() and shown["runnable"] is True
    monkeypatch.setattr(P, "PILOT_POPULATION_DESIGN", smoke_design(soft_k_multiple=2.0))
    assert P.main(["--out", str(out), "--root", str(root), "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["runnable"] is False
    assert not out.exists()


# ------------------------------------------------ discrete census model (package 2)


def _ids(arm: Any) -> set[str]:
    return {o.id for o in arm.runner.population.organisms}


def test_discrete_step_removes_exactly_the_parents_and_keeps_every_newborn(spec: P.RealisedWPilotSpec) -> None:
    """Basis: discrete generations (section 7 power model, Wright-Fisher at census N) need every
    organism alive at the start of a step to die during it and every offspring of the step to
    survive it. With max-age death on (2 ticks, set after boot) no founder id is alive after one
    step and every id born in the step is alive; with the same harness and max-age off the
    founders all survive, so the deaths are the max-age rule's. Ids and census only."""

    arm = P.build_population(spec, discrete_design(), SMOKE_SEED, SMOKE_N)
    monitoring = arm.runner.configs.death_monitoring
    assert (monitoring.enable_max_age_death, monitoring.max_age_ticks) == (True, 2)
    founders = _ids(arm)
    step = P._discrete_step(arm, 1, SMOKE_N, SMOKE_SEED)
    alive = _ids(arm)
    born = {r.organism_id for r in arm.runner.population.lineage} - founders
    assert alive and not (alive & founders) and alive == born
    assert step == {
        "births": len(born),
        "parents_survived": 0,
        "newborns_removed": 0,
        "capacity_refusals": 0,
        "thinned": max(0, len(born) - SMOKE_N),
    }
    overlapping = P.build_population(spec, smoke_design(3.0), SMOKE_SEED, SMOKE_N)
    assert overlapping.runner.configs.death_monitoring.enable_max_age_death is False
    start = _ids(overlapping)
    overlapping.run_generations(1)
    assert start <= _ids(overlapping)


class _Org:
    def __init__(self, ident: str) -> None:
        self.id = ident


def test_thinning_keeps_n_uniformly_without_replacement() -> None:
    """Basis: the census draws N of M offspring without replacement, each with probability N/M:
    10 offspring, N 4, generations 1..2000 give each id kept 800 times in expectation (sd 21.9);
    every count lies within 5 sd. Each draw is 4 distinct ids of the 10, in the engine's order, and
    is the RNGManager fork jr5/e1/census/<g> shuffle of the sorted ids (same seed and generation,
    same draw)."""

    from codontrace.rng import RNGManager

    orgs = [_Org(f"o{i}") for i in (3, 1, 4, 0, 5, 9, 2, 6, 8, 7)]
    kept_count = dict.fromkeys((o.id for o in orgs), 0)
    for generation in range(1, 2001):
        kept = P.thin_to_census(orgs, 4, SMOKE_SEED, generation)
        ids = [o.id for o in kept]
        assert len(ids) == len(set(ids)) == 4
        assert ids == [o.id for o in orgs if o.id in set(ids)]
        for i in ids:
            kept_count[i] += 1
    assert all(abs(n - 800) <= 5 * 21.9 for n in kept_count.values())
    order = sorted(o.id for o in orgs)
    RNGManager(seed=SMOKE_SEED).fork("jr5/e1/census/7").shuffle(order)
    assert {o.id for o in P.thin_to_census(orgs, 4, SMOKE_SEED, 7)} == set(order[:4])
    assert P.thin_to_census(orgs, 4, SMOKE_SEED, 7) == P.thin_to_census(orgs, 4, SMOKE_SEED, 7)


def test_short_census_keeps_every_offspring_and_none_is_empty() -> None:
    """Basis: with N or fewer offspring all are kept (a short census is recorded, never filled by
    copies); with no offspring nothing is kept."""

    orgs = [_Org("b"), _Org("a"), _Org("c")]
    assert P.thin_to_census(orgs, 3, SMOKE_SEED, 1) == tuple(orgs)
    assert P.thin_to_census(orgs, 4, SMOKE_SEED, 1) == tuple(orgs)
    assert P.thin_to_census([], 4, SMOKE_SEED, 1) == ()


def test_census_thinning_on_the_engine_keeps_the_atp_ledger_exact(spec: P.RealisedWPilotSpec) -> None:
    """Basis: thinning to N 8 removes births - 8 organisms; their accounts are closed at once (the
    ledger's open agents, by organism id, are exactly the kept ids) with their ATP (newborn endowments, > 0) in the
    census sink, so the world ledger check passes and its residual is 0; the census row's own check
    census = min(births, N) and thinned = births - census holds."""

    arm = P.build_population(spec, discrete_design(), SMOKE_SEED, SMOKE_N)
    step = P._discrete_step(arm, 1, 8, SMOKE_SEED)
    census = len(arm.runner.population.organisms)
    assert step["births"] > 8 and census == 8 and step["thinned"] == step["births"] - 8
    assert P._ledger_residual(arm) == 0.0
    ledger = arm.runner.atp_ledger
    assert {a.split("/")[0] for a in ledger.open_agents} == _ids(arm)
    assert ledger.balance(P.CENSUS_THINNING_SINK) > 0


def test_a_capacity_refusal_stops_the_run(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: a birth refused at the soft carrying capacity means the cap, not the census draw,
    chose which offspring exist (an id-order bias). With soft K = N (multiple 1.0) the founders
    fill the cap and a birth is refused in generation 1, so the run stops at no_capacity_refusal,
    with no count in the message (smoke)."""

    with pytest.raises(P.PilotInvariantError, match=r"no_capacity_refusal broke at generation 1 \(details withheld"):
        run_smoke(tmp_path / "k1", spec, design=discrete_design(soft_k_multiple=1.0))


def test_capacity_refusals_counts_only_capacity_reasons() -> None:
    """Basis: only max_population_reached and population_capacity_reached are capacity refusals; a
    missing mate is not."""

    class _Event:
        def __init__(self, reason: str | None) -> None:
            self.world_delta = {"reproduction_blocked_reason": reason}

    class _Trace:
        events = (_Event("max_population_reached"), _Event("no_viable_mate"), _Event(None))

    class _Trace2:
        events = (_Event("population_capacity_reached"),)

    class _Result:
        traces = (_Trace(), _Trace2())

    assert P.capacity_refusals(_Result()) == 2


def _lost_at_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make generation 2 of the discrete model end with no offspring (every organism gone, no
    births), as a population that fails to reproduce would."""

    real = P._discrete_step

    def step(arm: Any, generation: int, host_n: int, seed: int) -> dict[str, int]:
        if generation < 2:
            return real(arm, generation, host_n, seed)
        arm.runner.population = dataclasses.replace(arm.runner.population, organisms=())
        return {"births": 0, "parents_survived": 0, "newborns_removed": 0, "capacity_refusals": 0, "thinned": 0}

    monkeypatch.setattr(P, "_discrete_step", step)


def test_a_population_with_no_offspring_is_lost_and_not_fitted(
    spec: P.RealisedWPilotSpec, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Basis: zero offspring ends the population; it is not a fit input and is never refilled by
    copies. The seed file holds rows 0..1, a population_lost record at 2 and a fit row with no
    estimate and population_lost_generation 2; the summary counts one lost population; a resume
    re-runs the seed and keeps it."""

    _lost_at_two(monkeypatch)
    out = tmp_path / "lost"
    summary = run_smoke(out, spec, design=discrete_design())
    records = [json.loads(x) for x in _seed_file(out).read_text(encoding="utf-8").splitlines()]
    assert [r["kind"] for r in records] == ["generation", "generation", "population_lost", "fit"]
    assert records[-1]["population_lost_generation"] == 2 and records[-1]["converged"] is False
    assert summary["populations_lost"] == 1
    assert "population_lost" in [e["event"] for e in events(out)]
    run_smoke(out, spec, design=discrete_design())
    assert "seed_kept" in [e["event"] for e in events(out)]


@pytest.fixture
def discrete_pilot_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, P.RealisedWPilotSpec]:
    """The discrete design pinned in a test root's log and set as PILOT_POPULATION_DESIGN for the
    synthetic block 30001-30003 (N 20, T 3), with the fit stubbed to log 2."""

    design = discrete_design()
    root = make_root(tmp_path, _entry(design.digest()))
    monkeypatch.setattr(P, "PILOT_POPULATION_DESIGN", design)
    monkeypatch.setattr(P, "fit_population", lambda module, spec, rows: (math.log(2.0), None, None, True))
    return root, _synthetic_pilot_spec(root)


def test_pilot_path_runs_the_discrete_model_and_keeps_the_rows_on_resume(
    discrete_pilot_env: tuple[Path, P.RealisedWPilotSpec], tmp_path: Path
) -> None:
    """Basis: in pilot mode (synthetic block, stubbed fit) each discrete row carries the step
    checks (no parent survived, no newborn removed, no capacity refusal, census = min(births, N));
    the decision is written after the last seed; a resume without the manifest re-checks the kept
    rows and keeps them."""

    root, pspec = discrete_pilot_env
    out = tmp_path / "pilot"
    summary = P.run_pilot(out, root=root, spec=pspec)
    assert summary["decision_written"] is True
    rows = [json.loads(x) for x in (out / "seeds/seed-30001.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows[1:-1]:
        assert (row["parents_survived"], row["newborns_removed"], row["capacity_refusals"]) == (0, 0, 0)
        assert row["census"] == min(row["births"], 20)
    (out / "manifest.json").unlink()
    P.run_pilot(out, root=root, spec=pspec)
    assert [e["event"] for e in events(out)].count("seed_kept") == 3


def test_pilot_path_writes_no_decision_when_a_population_is_lost(
    discrete_pilot_env: tuple[Path, P.RealisedWPilotSpec], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Basis: a lost population is not a fit input and the E1 cell rule needs every seed of the
    block, so no decision is written (no_decision event); a resume re-checks the kept file with
    its population_lost record and keeps it."""

    _lost_at_two(monkeypatch)
    root, pspec = discrete_pilot_env
    out = tmp_path / "pilot"
    summary = P.run_pilot(out, root=root, spec=pspec)
    assert summary["decision_written"] is False and summary["populations_lost"] == 3
    assert not (out / "result.json").exists() and "no_decision" in [e["event"] for e in events(out)]
    (out / "manifest.json").unlink()
    P.run_pilot(out, root=root, spec=pspec)
    assert [e["event"] for e in events(out)].count("seed_kept") == 3


def _discrete_row(**kw: Any) -> dict[str, Any]:
    row = _row(census=20, births=26, parents_survived=0, newborns_removed=0, capacity_refusals=0, thinned=6)
    row["counts"] = {"asexual": 8, "hermaphrodite": 6, "male": 6}
    row.update(kw)
    return row


@pytest.mark.parametrize(
    ("change", "name"),
    [
        ({"parents_survived": 1}, "parents_removed"),
        ({"newborns_removed": 1}, "newborns_kept"),
        ({"capacity_refusals": 1}, "no_capacity_refusal"),
        ({"thinned": 5}, "census_is_thinned_offspring"),
        ({"births": 19}, "census_is_thinned_offspring"),
    ],
)
def test_check_row_discrete_step_invariants(spec: P.RealisedWPilotSpec, change: dict[str, Any], name: str) -> None:
    """Basis: a discrete row of N 20 with 26 births keeps 20 and thins 6, with no parent left, no
    newborn removed and no refusal; each change breaks the named check. Blinded, the message
    names the check and generation only."""

    assert P.check_row(_discrete_row(), _PREV, spec, 60, host_n=20)[-1] == "loss_absorbing"
    with pytest.raises(P.PilotInvariantError, match=name):
        P.check_row(_discrete_row(**change), _PREV, spec, 60, host_n=20)
    with pytest.raises(P.PilotInvariantError) as info:
        P.check_row(_discrete_row(**change), _PREV, spec, 60, host_n=20, blinded=True)
    assert str(info.value) == f"invariant {name} broke at generation 1 (details withheld: blind run)"
    with pytest.raises(ConfigurationError, match="host N"):
        P.check_row(_discrete_row(), _PREV, spec, 60)


def test_chamber_timeout_policy_is_derived_from_the_registered_rule(
    spec: P.RealisedWPilotSpec, constants: dict[str, Any]
) -> None:
    """Basis: the registered unmated_outcrosser rule is refused_no_selfing_at_timeout, so an unmated
    outcrosser's chamber slot fails; asexual_fallback would turn it into a copy and remove the cost
    of males. The discrete design refuses any other policy, every design is refused at build, and
    an unknown registered rule is refused."""

    assert spec.engine_config["unmated_outcrosser"] == "refused_no_selfing_at_timeout"
    assert P.required_chamber_timeout_policy(spec) == "fail"
    with pytest.raises(ConfigurationError, match="chamber_timeout_policy 'fail'"):
        discrete_design(chamber_timeout_policy="asexual_fallback")
    other = dataclasses.replace(smoke_design(), chamber_timeout_policy="asexual_fallback")
    with pytest.raises(ConfigurationError, match="unmated_outcrosser rule requires"):
        P.build_population(spec, other, SMOKE_SEED, SMOKE_N)
    engine = {**spec.engine_config, "unmated_outcrosser": "asexual_copy_at_timeout"}
    with pytest.raises(ConfigurationError, match="has no chamber timeout policy"):
        P.required_chamber_timeout_policy(dataclasses.replace(spec, engine_config=engine))


def test_discrete_world_must_hold_three_n(spec: P.RealisedWPilotSpec) -> None:
    """Basis: soft K is 3N transient room, so the world needs side >= ceil(sqrt(3N)): at N 20 that
    is 8 (64 >= 60); 7 (49 cells) is refused. The pilot's 29 meets ceil(sqrt(600)) = 25."""

    with pytest.raises(ConfigurationError, match="ceil"):
        P.build_population(spec, discrete_design(world_size=7), SMOKE_SEED, SMOKE_N)
    assert P.build_population(spec, discrete_design(world_size=8), SMOKE_SEED, SMOKE_N) is not None
    assert 29**2 >= 3 * 200 > 24**2


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"enable_max_age_death": False}, "needs enable_max_age_death"),
        ({"max_age_ticks": None}, "needs max_age_ticks"),
        ({"max_age_ticks": 0}, "positive integer"),
        ({"generation_model": "engine_overlapping"}, "part of discrete_uniform_census only"),
    ],
)
def test_max_age_fields_are_validated(change: dict[str, Any], message: str) -> None:
    """Basis: the discrete model removes parents by max-age death, so it needs the rule on with a
    positive age; another model may not switch it on."""

    with pytest.raises(ConfigurationError, match=message):
        discrete_design(**change)


@pytest.mark.parametrize(("mode", "seed"), [(P.MODE_SMOKE, 13201), (P.MODE_SMOKE, 12240), (P.MODE_PILOT, 20011)])
def test_build_population_guards_the_seed_itself(spec: P.RealisedWPilotSpec, mode: str, seed: int) -> None:
    """Basis (R50-L6): the public build_population checks the seed for its mode (smoke by default)
    before booting, so a direct caller cannot boot a registered or sealed seed; the refusal is a
    ConfigurationError, not the test safety net's RuntimeError."""

    with pytest.raises(ConfigurationError):
        P.build_population(spec, smoke_design(), seed, SMOKE_N, mode=mode)
    with pytest.raises(ConfigurationError):
        P.build_population(spec, smoke_design(), 13201, SMOKE_N)


@pytest.mark.parametrize(
    "bad",
    ["a" * 63, "a" * 65, "A" * 64, "g" * 64],
    ids=["63-hex", "65-hex", "upper-case", "not-hex"],
)
def test_design_pin_refuses_a_malformed_design_line_after_a_valid_one(tmp_path: Path, bad: str) -> None:
    """Basis (R51 D08): a design digest is exactly 64 lower-case hex characters. A later entry
    whose design line is malformed must be refused, not skipped: skipping it would leave the
    earlier entry's design in force although the log's last word on the design is unreadable."""

    good = smoke_design().digest()
    later = _entry(None, extra=f"- Realised-w pilot population design: `jr5_e1_population_design:{bad}`")
    later = later.replace("(test fixture)", "(test fixture, later)")
    root = make_root(tmp_path, _entry(good) + later)
    with pytest.raises(ConfigurationError, match="design line is malformed"):
        P.verified_pilot_design_digest(root)


def test_design_pin_refuses_a_changed_locked_file_other_than_the_log(tmp_path: Path) -> None:
    """Basis (R51 L3): record.json lists every plan file's sha256, not only DEVIATIONS.md. With a
    valid pinned entry and the record refreshed, one byte appended to REFERENCES.md (listed, and
    not the log) makes its fresh hash differ from the listing, so the pin is refused before the
    log is read."""

    root = make_root(tmp_path, _entry(smoke_design().digest()))
    assert P.verified_pilot_design_digest(root)[0] == smoke_design().digest()
    with (root / "docs/prereg/jr5/REFERENCES.md").open("ab") as fh:
        fh.write(b"\n")
    with pytest.raises(ConfigurationError, match="does not match the fresh hashes of its plan files"):
        P.verified_pilot_design_digest(root)
