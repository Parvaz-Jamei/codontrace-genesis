"""JR5 realised-w pilot runner (PREREG section 7).

No pilot seed runs here. Engine runs use smoke seeds 20011-20013 (outside
every registered and sealed block) at host N = 20 with a growth design.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import shutil
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


@pytest.fixture(scope="module")
def spec() -> P.RealisedWPilotSpec:
    return P.load_realised_w_pilot_spec(ROOT)


@pytest.fixture(scope="module")
def constants() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CONSTANTS.read_text(encoding="utf-8"))
    return data


def smoke_design(soft_k_multiple: float = 4.0) -> P.PopulationDesign:
    from codontrace.genesis import closed_loop_hp_arm01_selfing_hold as hold
    from codontrace.genesis.closed_loop_hp_arm01 import _INVASION_FOUNDERS

    return P.PopulationDesign(
        label="smoke-growth",
        soft_k_multiple=soft_k_multiple,
        world_size=12,
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
    "rel",
    [
        ".",
        "docs/prereg",
        "docs/prereg/jr5",
        "docs/prereg/jr5/out",
        "docs",
        "src/codontrace/claimgate/data",
        "src/codontrace/claimgate/data/x",
    ],
)
def test_output_guard_refuses_the_prereg_and_packaged_constants(rel: str) -> None:
    """Basis: the output may not be the repo root, be or lie in docs/prereg or
    src/codontrace/claimgate/data, or contain them (docs contains docs/prereg)."""

    with pytest.raises(ConfigurationError):
        P.check_output_dir(ROOT / rel, ROOT)


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
    assert end["rows_written"] == 5 and end["eta_seconds"] == 0.0 and math.isfinite(end["log_w"])
    lines = (out / "seeds" / f"seed-{SMOKE_SEED}.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5 and json.loads(lines[-1])["kind"] == "fit"
    assert gens[0]["asexual"] == 4 and gens[0]["census"] == 20
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        assert hashlib.sha256((out / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    assert manifest["body_digest"] == summary["body_digest"]
    assert manifest["run"]["design_digest"] == smoke_design().digest()
    assert not (out / "result.json").exists()


def test_rerun_and_resume_write_the_same_bytes(spec: P.RealisedWPilotSpec, tmp_path: Path) -> None:
    """Basis: RNGManager draws only from the run seed, so two fresh runs write identical seed
    files; resuming a complete run keeps the seed file (seed_kept) and the body digest; a
    killed run's partial file is kept as killed-1 and the seed re-run gives the same bytes."""

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
    run_smoke(c, spec)
    assert (c / name).read_bytes() == (a / name).read_bytes()
    assert (c / (name + ".killed-1")).read_bytes() == (a / name).read_bytes()
    assert "seed_rerun_same_seed" in [e["event"] for e in events(c)]


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

    def poisoned(arm: Any, generation: int, *a: Any) -> dict[str, Any]:
        row = real(arm, generation, *a)
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
