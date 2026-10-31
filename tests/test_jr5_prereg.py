"""JR5 phase 1: the prereg record matches its files and the seed blocks are clean."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.claimgate.domain import HOST_PARASITE
from codontrace.errors import ConfigurationError
from codontrace.preregistration import PreregistrationRecord
from codontrace.preregistration.manifest import hash_plan

ROOT = Path(__file__).resolve().parents[1]
PREREG_DIR = ROOT / "docs" / "prereg" / "jr5"


def _constants() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((PREREG_DIR / "jr5_prereg_constants.json").read_text(encoding="utf-8"))
    return data


def _record() -> PreregistrationRecord:
    return PreregistrationRecord.from_json((PREREG_DIR / "record.json").read_text(encoding="utf-8"))


def _block(pair: list[int]) -> set[int]:
    lo, hi = pair
    assert lo <= hi
    return set(range(lo, hi + 1))


def test_record_matches_files() -> None:
    rec = _record()
    paths = [p for p, _ in rec.manifest.files]
    fresh = hash_plan(paths, root=ROOT, title=rec.manifest.title)
    assert fresh.files == rec.manifest.files
    assert fresh.digest == rec.manifest.digest


def test_record_covers_constants_and_docs() -> None:
    paths = {p for p, _ in _record().manifest.files}
    for name in (
        "PREREG.md",
        "MATING_TYPES_DESIGN_NOTE.md",
        "SUMMARY_SHA256_NOTE.md",
        "REFERENCES.md",
        "RED_QUEEN_CLAIM_PATH.md",
        "jr5_prereg_constants.json",
    ):
        assert f"docs/prereg/jr5/{name}" in paths


def test_constants_well_formed() -> None:
    c = _constants()
    assert c["schema"] == "codontrace_jr5_prereg_constants_v1"
    assert len(c["base_commit"]) == 40
    assert set(c["typed_outcomes"]) == {
        "rq_consistent",
        "load_consistent",
        "diversity_without_rqd",
        "none",
        "inconclusive",
        "instrument_fail",
    }
    gated = c["gated_claim_flags"]["red_queen_proved"]
    assert gated["default"] is False
    assert len(gated["conditions"]) == 5
    assert (ROOT / gated["doc"]).is_file()
    assert c["host_n"]["primary"] == 200
    assert c["host_n"]["sensitivity"] == 50
    assert c["multiplicity"]["method"] == "holm"


def test_gate_bounds_follow_margin() -> None:
    gate = _constants()["gate_e1"]
    margin = gate["relative_margin"]
    assert gate["alpha"] == 0.05
    assert math.isclose(gate["ci_level"], 1 - 2 * gate["alpha"])
    for s in gate["sex_ratios"]:
        theory = 1.0 / (1.0 - s)
        assert math.isclose(gate["theoretical_cost"][str(s)], theory)
        lo, hi = gate["equivalence_bounds"][str(s)]
        assert math.isclose(lo, (1 - margin) * theory)
        assert math.isclose(hi, (1 + margin) * theory)
        assert lo > gate["must_exclude"]


def test_seed_blocks_do_not_touch_sealed() -> None:
    seeds = _constants()["seeds"]
    sealed: set[int] = set()
    for pair in seeds["sealed_ranges"]:
        sealed |= _block(pair)
    blocks = [_block(seeds[k]) for k in ("confirmatory_block", "e1_calibration_block", "pilot_block")]
    for block in blocks:
        assert not block & sealed
        assert min(block) >= 13001
    for i, a in enumerate(blocks):
        for b in blocks[i + 1 :]:
            assert not a & b


@pytest.mark.parametrize(
    "sealed",
    [
        0,
        101,
        508,
        701,
        708,
        1000,
        1009,
        8000,
        9001,
        9201,
        9224,
        9901,
        9922,
        9120,
        9601,
        9712,
        9807,
        10001,
        10576,
        11001,
        11384,
        12001,
        12240,
    ],
)
def test_known_sealed_seeds_listed(sealed: int) -> None:
    ranges = _constants()["seeds"]["sealed_ranges"]
    assert any(lo <= sealed <= hi for lo, hi in ranges)


def test_seed_counts_cover_design() -> None:
    c = _constants()
    conf = _block(c["seeds"]["confirmatory_block"])
    assert len(conf) >= c["e2"]["seeds_per_cell"]
    calib = _block(c["seeds"]["e1_calibration_block"])
    assert len(calib) >= c["gate_e1"]["populations_per_cell"] * len(c["gate_e1"]["sex_ratios"])


CLAIM_PATH_SHA256 = "f90b8b1c8bf102814546930a06f295178939ef6c1b14b2042dc51cf2be8a49dc"
RANGE_RE = re.compile(r"`(\d+)\s*(?:\u2013|-|\u2026|\.\.\.)\s*(\d+)`")


def _prereg_text() -> str:
    return (PREREG_DIR / "PREREG.md").read_text(encoding="utf-8")


def _doc_seed_blocks(path: Path) -> list[tuple[int, int]]:
    """Backticked ranges on table rows and on lines that mention seeds."""
    out: list[tuple[int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not (line.lstrip().startswith("|") or "seed" in line.lower()):
            continue
        for lo, hi in RANGE_RE.findall(line):
            out.append((int(lo), int(hi)))
    return out


def test_gate_still_blocks_red_queen_proved_today() -> None:
    assert "red_queen_proved" in HOST_PARASITE.blocked_claims
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("red_queen_proved")


def test_prereg_seed_tables_do_not_overlap_across_preregs() -> None:
    docs = sorted((ROOT / "docs").rglob("*PREREG*.md"))
    blocks = {d.relative_to(ROOT).as_posix(): _doc_seed_blocks(d) for d in docs}
    assert set(blocks["docs/campaigns/rq_redesign_20260928/PREREG_V2.md"]) >= {
        (9001, 9096),
        (9101, 9120),
        (10001, 10576),
        (11001, 11384),
        (12001, 12240),
    }
    seeds = _constants()["seeds"]
    jr5 = {tuple(seeds[k]) for k in ("confirmatory_block", "e1_calibration_block", "pilot_block")}
    assert set(blocks["docs/prereg/jr5/PREREG.md"]) == jr5
    assert any(n.startswith("docs/handoff/") and "_PREREG_" in n for n in blocks)
    assert any(n.startswith("docs/HARD_EXPERIMENT_0") and "_PREREG" in n for n in blocks)
    names = sorted(blocks)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            for lo1, hi1 in blocks[a]:
                for lo2, hi2 in blocks[b]:
                    assert hi1 < lo2 or hi2 < lo1, (a, (lo1, hi1), b, (lo2, hi2))


def test_runs_total_rebuilds_from_grid() -> None:
    c = _constants()
    grid = c["grid"]
    total = sum(math.prod(cell.values()) for cell in grid.values())
    assert total == c["budget"]["runs_total"] == 3760
    assert math.prod(grid["e1"].values()) == c["budget"]["runs_e1"]
    alt = c["alternative_arms"]
    assert grid["mutation_load"]["seeds"] == alt["mutation_load"]["seeds_per_cell"]
    assert grid["mutation_load"]["mutation"] == len(alt["mutation_load"]["host_mutation_grid"])
    for name in ("uniform_tax", "recombination_off", "migration_on", "sex_ratio_0.25", "mutation_load"):
        assert grid[name]["host_n"] == len(alt[name]["host_n"])
    assert grid["e2"]["parasite_arms"] == len(c["parasite_arms"])
    long_runs = total - c["budget"]["runs_e1"]
    assert c["budget"]["runs_h100_N200"] + c["budget"]["runs_h100_N50"] == long_runs
    spg = c["timing_basis"]["seconds_per_generation"]
    h = c["horizon"]["floor"]
    gens = sum(c["gate_e1"]["generations"].values()) * grid["e1"]["seeds"]
    secs = c["budget"]["runs_h100_N200"] * h * spg["200"] + c["budget"]["runs_h100_N50"] * h * spg["50"]
    secs += gens * (spg["200"] + spg["50"])
    assert math.isclose(c["budget"]["cpu_hours_estimate"], secs / 3600, abs_tol=0.05)


def test_e1_horizon_keeps_p_below_cap_at_upper_bound() -> None:
    gate = _constants()["gate_e1"]
    p0 = gate["founder_uniparental_frequency"]
    cap = gate["horizon_max_expected_p"]
    for s in gate["sex_ratios"]:
        t = gate["generations"][str(s)]
        hi = gate["equivalence_bounds"][str(s)][1]

        def p_at(g: int, hi: float = hi) -> float:
            return 1.0 / (1.0 + math.exp(-(math.log(p0 / (1 - p0)) + g * math.log(hi))))

        assert p_at(t) < cap <= p_at(t + 1)
    lo, hi = gate["log_margin"]["low"], gate["log_margin"]["high"]
    assert math.isclose(lo, math.log(1 - gate["relative_margin"]))
    assert math.isclose(hi, math.log(1 + gate["relative_margin"]))
    assert gate["must_exclude_ci_level"] == 0.95
    assert gate["founder"] == "all_female_asexual"


def test_prereg_text_matches_json() -> None:
    c = _constants()
    text = _prereg_text()
    gate = c["gate_e1"]
    for s in gate["sex_ratios"]:
        lo, hi = gate["equivalence_bounds"][str(s)]
        assert f"inside [{lo:g}, {round(hi, 4):g}]" in text
        assert f"T = {gate['generations'][str(s)]}" in text
    assert f"TOST at alpha {gate['alpha']:g}" in text
    assert f"{gate['log_margin']['low']:.4f} / +{gate['log_margin']['high']:.4f}" in text.replace("\u2212", "-")
    assert f"at most {gate['exclusion_cap_fraction']:.0%}" in text
    seeds = c["seeds"]
    for k in ("confirmatory_block", "e1_calibration_block", "pilot_block"):
        lo, hi = seeds[k]
        assert f"`{lo}\u2013{hi}`" in text
    for lo, hi in seeds["sealed_ranges"]:
        assert f"{lo}-{hi}" in text
    boot = c["e2"]["bootstrap"]
    assert boot["method"] == "bca"
    assert f"BCa bootstrap interval ({boot['resamples']:,} resamples of seeds, bootstrap seed {boot['seed']})" in text
    assert f"{c['budget']['runs_total']:,} runs" in text
    assert len(c["multiplicity"]["primary_family"]) == 4
    assert "Holm across four E2 tests" in text
    assert f"{c['alternative_arms']['mutation_load']['seeds_per_cell']} seeds per cell" in text


def test_forbidden_claim_flags_pinned() -> None:
    c = _constants()
    assert c["forbidden_claim_flags"] == []
    assert c["claim_ceiling"] == "runtime_observation"


def test_holm_family_pinned() -> None:
    m = _constants()["multiplicity"]
    assert m["primary_family"] == ["e2_N200_high", "e2_N200_low", "e2_N50_high", "e2_N50_low"]
    assert m["family_alpha"] == 0.05
    assert m["e1_is_gate_not_claim"] is True


def test_claim_path_doc_pinned() -> None:
    data = (PREREG_DIR / "RED_QUEEN_CLAIM_PATH.md").read_bytes()
    assert hashlib.sha256(data).hexdigest() == CLAIM_PATH_SHA256


def test_bca_level_follows_holm_step_in_text_and_json() -> None:
    c = _constants()
    boot = c["e2"]["bootstrap"]
    family = c["multiplicity"]["primary_family"]
    alpha = c["multiplicity"]["family_alpha"]
    levels = [1 - alpha / (len(family) - i) for i in range(len(family))]
    assert boot["ci_level_rule"] == "bca_at_one_minus_holm_adjusted_alpha_of_step"
    assert all(math.isclose(a, b) for a, b in zip(boot["ci_level_by_holm_step"], levels, strict=True))
    first = f"{levels[0]:.2%}"
    claim = (PREREG_DIR / "RED_QUEEN_CLAIM_PATH.md").read_text(encoding="utf-8")
    for text in (_prereg_text(), claim):
        assert f"{first} at step 1" in text
    assert "bootstrap 95% interval (" not in claim
    assert boot["condition_c_ci_level"] == 0.95
    assert (
        "two-sided 95% intervals (10,000 resamples, seed 12345), the level that matches one-sided alpha 0.025" in claim
    )


def test_e1_estimator_is_bias_reduced() -> None:
    c = _constants()
    assert "bias_reduced" in c["gate_e1"]["estimator"]
    assert "a bias-reduced binomial GLM" in _prereg_text()
    assert c["power"]["e1"]["recheck_sd_N50_0.25"] == 0.127


# Reserved blocks listed by an earlier prereg that overlap another prereg's own
# block. Both are legacy and outside every JR5 block; they are kept, not reused.
LEGACY_OVERLAPS = {
    ("docs/campaigns/rq_redesign_20260928/PREREG_V2.md", (1000, 1009)): (
        "docs/experiments/2026-09-29/causal_tape/PREREG.md",
        (1000, 1299),
    ),
}
ANY_RANGE_RE = re.compile(r"(?<![\d.])(\d{1,6})\s*(?:-|\u2013|\u2026|\.\.\.?)\s*(\d{1,6})(?![\d.])")


def test_legacy_overlap_allow_list_is_real() -> None:
    for (doc_a, block_a), (doc_b, block_b) in LEGACY_OVERLAPS.items():
        text_a = (ROOT / doc_a).read_text(encoding="utf-8")
        assert f"`{block_a[0]}\u2013{block_a[1]}`" in text_a
        assert block_b in _doc_seed_blocks(ROOT / doc_b)
        assert block_b[0] <= block_a[0] <= block_a[1] <= block_b[1]
        sealed = _constants()["seeds"]["sealed_ranges"]
        assert list(block_a) in sealed and list(block_b) in sealed


def test_jr5_blocks_clear_every_plain_range_in_prereg_docs() -> None:
    """Any number range on any line of another prereg, backticked or not."""
    seeds = _constants()["seeds"]
    jr5 = [seeds[k] for k in ("confirmatory_block", "e1_calibration_block", "pilot_block")]
    for doc in sorted((ROOT / "docs").rglob("*PREREG*.md")):
        if doc.parent == PREREG_DIR:
            continue
        for lo_s, hi_s in ANY_RANGE_RE.findall(doc.read_text(encoding="utf-8")):
            lo, hi = int(lo_s), int(hi_s)
            if lo >= hi:
                continue
            for a, b in jr5:
                assert hi < a or b < lo, (doc, lo, hi)


def test_e1_fit_pinned() -> None:
    from tests import _jr5_e1_fit as fit_mod

    fit = _constants()["gate_e1"]["fit"]
    assert fit["implementation"] == "tests/_jr5_e1_fit.py"
    assert fit["tol"] == fit_mod.TOL
    assert fit["max_iter"] == fit_mod.MAX_ITER
    assert fit["method"] == "penalised_likelihood_plus_half_log_det_fisher_information"


@pytest.mark.parametrize(("k0", "k1"), [(3.0, 11.0), (0.0, 7.0), (12.0, 20.0)])
def test_bias_reduced_fit_matches_half_count_rule(k0: float, k1: float) -> None:
    """With two groups the model is saturated; the penalised fit then equals
    the empirical logits after adding 1/2 to every count (exact, known result)."""
    np = pytest.importorskip("numpy")
    from tests._jr5_e1_fit import fit_logit

    n = np.array([20.0, 20.0])
    k = np.array([k0, k1])
    beta = fit_logit(k, n, np.array([0.0, 1.0]), bias_reduced=True)
    logit = np.log((k + 0.5) / (n - k + 0.5))
    assert math.isclose(beta[0], logit[0], abs_tol=1e-8)
    assert math.isclose(beta[1], logit[1] - logit[0], abs_tol=1e-8)


def test_plain_fit_matches_statsmodels() -> None:
    np = pytest.importorskip("numpy")
    sm = pytest.importorskip("statsmodels.api")
    from tests._jr5_e1_fit import fit_logit

    x = np.arange(6.0)
    n = np.full(6, 200.0)
    k = np.array([40.0, 66.0, 100.0, 133.0, 160.0, 181.0])
    ours = fit_logit(k, n, x, bias_reduced=False)
    ref = sm.GLM(np.column_stack([k, n - k]), sm.add_constant(x), family=sm.families.Binomial()).fit()
    assert np.allclose(ours, ref.params, atol=1e-8)
