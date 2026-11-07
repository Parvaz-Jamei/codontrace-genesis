"""Raw-address, complete gate provenance, and independent statistical checks."""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from codontrace.claimgate import audit_bundle
from codontrace.claimgate import jr5_verdict as verdict
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.preregistration.manifest import PlanManifest
from codontrace.rng import RNGManager
from tests import _jr5_raw_evidence as raw
from tests.test_jr5_phase2c_verdict_adapter import bound_bundle, positive

ROOT = Path(__file__).resolve().parents[1]


def rehash(record: dict) -> None:
    record["digest"] = canonical_digest({k: v for k, v in record.items() if k != "digest"})


def test_same_verified_bytes_and_manifest_are_required() -> None:
    """A pinned digest authenticates the original bytes, not a tuned mapping or rehashed replacement."""
    constants = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_constants.json").read_bytes()
    record = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_record.json").read_bytes()
    assert verdict._verified_constants(constants, record) == json.loads(constants)
    tuned = json.loads(constants)
    tuned["gate_e1"]["relative_margin"] = 0.9
    modified = json.dumps(tuned).encode()
    with pytest.raises(ConfigurationError, match="sha256"):
        verdict._verified_constants(modified, record)
    swap = json.loads(record)
    manifest = swap["manifest"]
    manifest["files"] = [[p, hashlib.sha256(modified).hexdigest() if p.endswith("jr5_prereg_constants.json") else s]
                         for p, s in manifest["files"]]
    with pytest.raises(ConfigurationError, match="manifest"):
        verdict._verified_constants(modified, json.dumps(swap).encode())
    manifest["digest"] = PlanManifest(tuple(map(tuple, manifest["files"])), manifest["title"]).digest
    with pytest.raises(ConfigurationError, match="manifest"):
        verdict._verified_constants(modified, json.dumps(swap).encode())


def test_public_loader_reads_each_resource_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second read could parse different bytes; each resource must instead be read exactly once."""
    base = ROOT / "src/codontrace/claimgate"
    reads: dict[str, int] = {}

    class Entry:
        def __init__(self, name: str):
            self.name = name

        def read_bytes(self) -> bytes:
            reads[self.name] = reads.get(self.name, 0) + 1
            assert reads[self.name] == 1
            return (base / self.name).read_bytes()

    class Package:
        def joinpath(self, name: str) -> Entry:
            return Entry(name)

    monkeypatch.setattr(verdict.resources, "files", lambda _: Package())
    assert verdict.jr5_constants()["budget"]["runs_total"] == 3760
    assert len(reads) == 2


@pytest.mark.parametrize("field", ["test", "alpha", "ci_level", "relative_margin", "must_exclude",
    "must_exclude_ci_level", "exclusion_cap_fraction", "early_fixation_generation", "host_n_gate",
    "populations_per_cell", "sex_ratios", "host_n_reported", "seed_split", "constants_sha256", "prereg_manifest_digest"])
def test_gate_spec_cannot_be_retuned_with_genuine_top_hashes(field: str) -> None:
    """Every setting comes from the pinned bytes; rehashing a changed setting cannot preserve provenance."""
    ev = positive()
    rec = ev["e1_gate_record"]
    rec["spec"][field] = None
    rehash(rec)
    with pytest.raises(ConfigurationError, match="spec"):
        verdict.evaluate_jr5_verdict(ev)


@pytest.mark.parametrize("attack", ["missing_seeds", "wrong_seed", "duplicate_seed", "missing_cell", "extra_ratio",
                                     "duplicate_cell", "wrong_manifest", "mean", "ratio_interval", "n_total_bool"])
def test_rehashed_gate_records_must_match_all_raw_cells(attack: str) -> None:
    """All four registered cells, exact seed blocks, and recomputed fit summaries are required, not just pass flags."""
    ev = positive()
    rec = ev["e1_gate_record"]
    cell = rec["cells"][0]
    if attack == "missing_seeds":
        del cell["seeds"]
    elif attack == "wrong_seed":
        cell["seeds"][0] += 1000
    elif attack == "duplicate_seed":
        cell["seeds"][0] = cell["seeds"][1]
    elif attack == "missing_cell":
        rec["cells"].pop()
    elif attack == "extra_ratio":
        cell["sex_ratio"] = 0.1
    elif attack == "duplicate_cell":
        rec["cells"].append(deepcopy(cell))
    elif attack == "wrong_manifest":
        rec["prereg_manifest_digest"] = "0" * 64
    elif attack == "mean":
        cell["tost"]["mean"] += 0.01
    elif attack == "ratio_interval":
        cell["ratio_ci"][0] += 0.01
    else:
        cell["n_total"] = True
    rehash(rec)
    with pytest.raises(ConfigurationError):
        verdict.evaluate_jr5_verdict(ev)


def test_constructed_or_mutated_evidence_is_revalidated() -> None:
    """Dataclass construction and mutable nested mappings cannot replace byte-address and complete-grid checks."""
    ev = verdict.Jr5Evidence.from_dict(positive())
    for invalid in (replace(ev, prereg_record_digest="0" * 64), replace(ev, runs=ev.runs[:-1])):
        with pytest.raises(ConfigurationError):
            verdict.evaluate_jr5_verdict(invalid)
    ev.runs[0].raw["data"]["uniparental_counts"][0] += 1
    with pytest.raises(ConfigurationError, match="address"):
        verdict.evaluate_jr5_verdict(ev)


@pytest.mark.parametrize("host_n", [50, 200])
def test_exclusion_cap_breach_uses_all_registered_cells(host_n: int) -> None:
    """Nine exclusions exceed 0.2*40=8; N50 preserves the gated pass, N200 cannot, and both instrument-fail."""
    ev, _ = raw.build(e1_early_fixed={(0.5, host_n): 9})
    record = ev["e1_gate_record"]
    assert record["passed"] is (host_n == 50)
    assert record["instrument_failure"] is True
    result = verdict.evaluate_jr5_verdict(ev)
    assert not result.conditions["a"] and not result.red_queen_proved


def test_registered_window_times_cannot_be_swapped() -> None:
    """The lock fixes horizon 70 and primary lag 3, so the paired window is [67,70], not [66,70]."""
    lock = (ROOT / "runs/rq-mechanism-v2/PHASE6_CONFIRM_LOCK.md").read_text()
    assert "Primary lag: 3." in lock and "Horizon: 70 generations." in lock
    assert verdict.E4_WINDOW_GENERATIONS == (70 - 3, 70)
    ev = positive()
    run = next(r for r in ev["runs"] if "e4" in r["data"])
    run["data"]["e4_window"] = [66, 70]
    raw.readdress(run)
    with pytest.raises(ConfigurationError, match="window"):
        verdict.evaluate_jr5_verdict(ev)


@pytest.mark.parametrize("part", ["arms", "outcomes", "comparisons", "config_digest", "replay", "artifacts"])
def test_bundle_projection_cannot_carry_unrelated_results(part: str) -> None:
    """A valid verdict binds exact arm addresses, vectors, contrasts and replay artifacts; replacing any one keeps the ban."""
    ev = positive()
    payload = bound_bundle(ev)
    unrelated = json.loads((ROOT / "tests/fixtures/claimgate/level2_difference.json").read_text())
    payload[part] = unrelated[part]
    report = audit_bundle(payload)
    assert report.achieved_level <= 1
    assert any("red_queen_proved" in s for s in report.warnings)


def test_bias_reduced_slopes_match_registered_score_solver() -> None:
    """The registered modified-score solution, not a half-count regression approximation, determines each slope."""
    ev = positive()
    for run in ev["runs"]:
        if run["experiment"] == "e1":
            counts, n = run["data"]["uniparental_counts"], run["host_n"]
            fitted = verdict._firth_logit_slope(counts, n, verdict.jr5_constants()["gate_e1"]["fit"])
            assert fitted == pytest.approx(raw._slope(tuple(counts), n), abs=2e-10)


def test_paired_tests_and_rank_trend_match_independent_distributions() -> None:
    """With differences d, t=mean(d)/(SD(d)/sqrt(n)); average-rank correlation uses its n-2 t tail."""
    rng = np.random.default_rng(20261107)
    for _ in range(100):
        a = rng.normal(size=60)
        b = rng.normal(size=60)
        paired = verdict._Paired(tuple(a - b), 12345, 10000)
        assert paired.p_two_sided() == pytest.approx(float(stats.ttest_rel(a, b).pvalue), abs=2e-12)
        expected = stats.t.interval(0.95, 59, loc=np.mean(a - b), scale=stats.sem(a - b))
        actual = paired.ci(0.95)
        assert [actual.lo, actual.hi] == pytest.approx(expected, abs=2e-12)
        x = rng.integers(0, 4, size=180).tolist()
        y = rng.normal(size=180).tolist()
        rho, p = verdict._spearman_greater(x, y)
        ref = stats.spearmanr(x, y, alternative="greater")
        assert rho == pytest.approx(float(ref.statistic), abs=2e-14)
        assert p == pytest.approx(float(ref.pvalue), abs=2e-12)
    x = list(range(100))
    y = x.copy()
    y[0], y[1] = y[1], y[0]
    _, tail = verdict._spearman_greater(x, y)
    expected_tail = float(stats.spearmanr(x, y, alternative="greater").pvalue)
    assert 0 < tail < 1e-100
    assert tail == pytest.approx(expected_tail, rel=1e-8, abs=0)


def test_registered_resample_stream_and_adjusted_quantiles() -> None:
    """Use 10000 paired draws at seed12345; bias and jackknife acceleration adjust each two-sided tail before quantiles."""
    values = np.random.default_rng(20261107).lognormal(size=60)
    rng = RNGManager(seed=12345, namespace="bootstrap_paired")
    draws = np.asarray([[values[rng.randrange(60)] for _ in range(60)] for _ in range(10000)])
    means = draws.mean(axis=1)
    theta = values.mean()
    z0 = float(stats.norm.ppf(np.count_nonzero(means < theta) / 10000))
    jack = np.asarray([np.delete(values, i).mean() for i in range(60)])
    differences = jack.mean() - jack
    acceleration = float(np.sum(differences ** 3) / (6 * np.sum(differences ** 2) ** 1.5))
    paired = verdict._Paired(tuple(values), 12345, 10000)
    for level in (0.9875, 1 - 0.05 / 3, 0.975, 0.95):
        tails = np.asarray([(1 - level) / 2, (1 + level) / 2])
        z = stats.norm.ppf(tails)
        adjusted = stats.norm.cdf(z0 + (z0 + z) / (1 - acceleration * (z0 + z)))
        expected = np.quantile(means, adjusted)
        interval = paired.bca(level)
        assert [interval.lo, interval.hi] == pytest.approx(expected, abs=2e-7)


def test_digest_contracts_are_registered_from_the_consumer() -> None:
    """Evidence and verdict expose reference digests, while raw body addresses are verified within run envelopes."""
    from codontrace.genesis import replay_integrity
    for cls in (verdict.Jr5Evidence, verdict.Jr5Verdict):
        path = f"{cls.__module__}.{cls.__qualname__}"
        assert path in replay_integrity.NON_REPLAY_CRITICAL_DIGEST_CLASSES
        assert replay_integrity._DIGEST_FIELDS_BY_CLASS[path] == replay_integrity.public_dataclass_digest_fields(cls)
    source = (ROOT / "src/codontrace/genesis/replay_integrity.py").read_text()
    assert "jr5_verdict" not in source


@pytest.mark.parametrize(("field", "value", "expected"), [
    ("resumed_body_sha256", "0" * 64, False),
    ("atp_ledger_residual", 1e-9, True),
    ("atp_ledger_residual", -1e-9, True),
    ("atp_ledger_residual", -2e-9, False),
])
def test_replay_body_equality_and_closed_residual_boundary(field: str, value: object, expected: bool) -> None:
    """Replay bodies must match, while the absolute residual threshold is closed at +/-1e-9."""
    ev = positive()
    run = ev["runs"][123]
    run["replay"][field] = value
    raw.readdress(run)
    result = verdict.evaluate_jr5_verdict(ev)
    assert result.conditions["e"] is expected
    assert result.red_queen_proved is expected


def test_one_bit_raw_edit_changes_the_content_address() -> None:
    """The exact JSON float is addressed: even a one-ulp edit without a fresh hash must be refused."""
    ev = positive()
    run = next(r for r in ev["runs"] if r["experiment"] == "e2")
    before = run["sha256"]
    value = run["data"]["terminal_uniparental_frequency"]
    run["data"]["terminal_uniparental_frequency"] = math.nextafter(value, math.inf)
    assert verdict.run_record_sha256(run) != before
    with pytest.raises(ConfigurationError, match="address"):
        verdict.evaluate_jr5_verdict(ev)


def test_a_low_virulence_e2_effect_prevents_a_load_only_outcome() -> None:
    """'E2 not significant' means all four family members: one strong low-virulence effect prevents load-only attribution."""
    effects = {(200, "high"): 0.0, (50, "high"): 0.0, (200, "low"): -0.25, (50, "low"): 0.0}
    ev, _ = raw.build(e2_effect=effects, load_effect=0.10, load_slope=4.0)
    result = verdict.evaluate_jr5_verdict(ev)
    assert result.outcome == "none" and not result.red_queen_proved


def test_non_significance_alone_never_rules_out_an_alternative() -> None:
    """At mean zero and SD0.5, the 90% half-width is about0.108>0.10 and the 95% interval spans zero: not ruled out."""
    values = tuple(0.5 * z for z in raw.scores("uncertain"))
    contrast = verdict._Paired(values, 12345, 10000)
    assert contrast.p_two_sided() > 0.9
    assert not verdict._ruled_out(contrast, 0.10, -1, 0.90, 0.95)


def test_a_genuine_constants_hash_does_not_authenticate_an_edited_manifest() -> None:
    """Changing only the manifest title leaves constants genuine but breaks the code-pinned canonical manifest digest."""
    constants = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_constants.json").read_bytes()
    original = json.loads((ROOT / "src/codontrace/claimgate/data/jr5_prereg_record.json").read_bytes())
    record = deepcopy(original)
    record["manifest"]["title"] += " changed"
    with pytest.raises(ConfigurationError, match="manifest"):
        verdict._verified_constants(constants, json.dumps(record).encode())
    manifest = record["manifest"]
    manifest["digest"] = PlanManifest(tuple(map(tuple, manifest["files"])), manifest["title"]).digest
    with pytest.raises(ConfigurationError, match="manifest"):
        verdict._verified_constants(constants, json.dumps(record).encode())


@pytest.mark.parametrize("fields", [("expected_digest", "replayed_digest"), ("one_shot_body_sha256", "resumed_body_sha256")])
def test_matching_placeholder_replay_strings_are_not_digests(fields: tuple[str, str]) -> None:
    """Equality of two placeholder strings is not replay evidence: both digest and body addresses require 64 hex characters."""
    ev = positive()
    run = ev["runs"][0]
    for field in fields:
        run["replay"][field] = "not-a-digest"
    raw.readdress(run)
    with pytest.raises(ConfigurationError, match="sha256"):
        verdict.evaluate_jr5_verdict(ev)


def test_gate_digest_is_checked_even_when_all_statistics_match() -> None:
    """A valid raw fit fixes every field; a different declared record digest still breaks its canonical content address."""
    ev = positive()
    ev["e1_gate_record"]["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest"):
        verdict.evaluate_jr5_verdict(ev)


def test_auditor_fails_closed_on_a_forged_verdict() -> None:
    """Positive raw arms do not authorize a forged verdict: a mismatched evidence digest must keep the global ban."""
    payload = bound_bundle(positive())
    payload["jr5_verdict"]["evidence_digest"] = "jr5-evidence:" + "0" * 64
    report = audit_bundle(payload)
    assert report.achieved_level <= 1
    assert any("red_queen_proved" in warning for warning in report.warnings)


def test_condition_c_keeps_its_registered_one_sided_level() -> None:
    """Left-skewed differences have one-sided p=.034 and a negative 95% resampling interval: alpha.025 must not reject."""
    n = 60
    w = [math.log(1 - (i + 0.5) / n) for i in range(n)]
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in w) / (n - 1))
    deltas = [-0.015 + 0.0625 * (x - mean) / sd for x in w]
    paired = verdict._Paired(tuple(deltas), 12345, 10000)
    assert 0.025 < paired.p_two_sided() / 2 < 0.05
    assert paired.bca(0.95).side() == -1
    ev, _ = raw.build(e2_deltas={(200, "high"): deltas}, frozen_minus_fixed=0.10)
    assert verdict.evaluate_jr5_verdict(ev).conditions["c"] is False


def test_step_down_rejection_requires_both_family_level_and_stop() -> None:
    """Four p=.02 values fail the first .05/4=.0125 threshold; later thresholds cannot restart rejection."""
    class Contrast:
        estimate = -0.1

        def p_two_sided(self) -> float:
            return 0.02

        def bca(self, level: float) -> verdict.Interval:
            return verdict.Interval(-0.2, -0.01)

    k = verdict.jr5_constants()
    family = {name: Contrast() for name in k["multiplicity"]["primary_family"]}
    calls = verdict._holm_calls(family, k)
    assert not any(call.significant for call in calls.values())


def test_registered_resampling_settings_reach_paired_contrasts() -> None:
    """Sorted shared seeds define paired differences; the registered stream uses exactly10000 resamples and seed12345."""
    boot = verdict.jr5_constants()["e2"]["bootstrap"]
    a, b = {3: 0.7, 1: 0.4, 2: 0.6}, {2: 0.3, 3: 0.2, 1: 0.1}
    contrast = verdict._paired(a, b, boot)
    assert contrast.deltas == pytest.approx((0.3, 0.3, 0.5))
    assert contrast.resamples == 10000 and contrast.bootstrap_seed == 12345


def test_fixation_at_the_cutoff_is_kept_and_loss_is_reported_not_excluded() -> None:
    """The exclusion rule is fixed_generation<3, not <=3; loss is recorded separately and remains among the40 fitted seeds."""
    ev = positive()
    boundary = next(r for r in ev["runs"] if r["experiment"] == "e1" and r["host_n"] == 200 and r["cell"]["sex_ratio"] == 0.5)
    boundary["data"]["uniparental_counts"] = [40, 70, 120, 200, 200, 200]
    raw.readdress(boundary)
    loss = next(r for r in ev["runs"] if r["experiment"] == "e1" and r["host_n"] == 50 and r["cell"]["sex_ratio"] == 0.5)
    loss["data"]["uniparental_counts"] = [10, 1, 0, 0, 0, 0]
    raw.readdress(loss)
    ev["e1_gate_record"] = raw.gate_record(ev["runs"])
    for cell in ev["e1_gate_record"]["cells"]:
        assert cell["n_used"] == 40 and cell["excluded_seeds"] == []
    assert verdict.evaluate_jr5_verdict(ev).conditions["a"] is True


@pytest.mark.parametrize("step", [1, 2])
def test_resampling_interval_follows_the_actual_family_step(step: int) -> None:
    """Right-skewed mean-.022, SD.0625 gives p=.0084:95% excludes0, but step1's98.75% and step2's98.333% include0."""
    n = 60
    w = [-math.log(1 - (i + 0.5) / n) for i in range(n)]
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in w) / (n - 1))
    deltas = tuple(-0.022 + 0.0625 * (x - mean) / sd for x in w)
    target = verdict._Paired(deltas, 12345, 10000)
    zero = verdict._Paired(tuple(raw.scores("retained")), 12345, 10000)
    strong = verdict._Paired(tuple(-0.25 + 0.1 * z for z in raw.scores("rejected")), 12345, 10000)
    k = verdict.jr5_constants()
    family = {name: zero for name in k["multiplicity"]["primary_family"]}
    family["e2_N200_high"] = target
    if step == 2:
        family["e2_N50_high"] = strong
    level = k["e2"]["bootstrap"]["ci_level_by_holm_step"][step - 1]
    assert target.p_two_sided() < 0.05 / (5 - step)
    assert target.bca(level).side() == 0 and target.bca(0.95).side() == -1
    call = verdict._holm_calls(family, k)["e2_N200_high"]
    assert not call.significant and not call.agree


def test_gate_audit_seed_lists_are_sets_not_population_input_order() -> None:
    """The gate sorts its all-seed vector but may report excluded/fixed/lost lists in population input order; memberships must agree."""
    ev, _ = raw.build(e1_early_fixed={(0.5, 50): 9})
    record = ev["e1_gate_record"]
    for cell in record["cells"]:
        for name in ("excluded_seeds", "fixed_seeds", "lost_seeds"):
            cell[name].reverse()
    rehash(record)
    result = verdict.evaluate_jr5_verdict(ev)
    assert result.conditions["a"] is False and result.outcome == "instrument_fail"


def test_boolean_cell_levels_cannot_alias_registered_numeric_zero() -> None:
    """Although False==0.0 in mapping keys, a registered numeric mutation rate is not a JSON boolean."""
    ev = positive()
    run = next(r for r in ev["runs"] if r["experiment"] == "mutation_load" and r["cell"]["mutation"] == 0.0)
    run["cell"]["mutation"] = False
    raw.readdress(run)
    with pytest.raises(ConfigurationError, match="cell"):
        verdict.evaluate_jr5_verdict(ev)


def test_a_near_null_cost_is_reported_as_an_instrument_failure() -> None:
    """Removing log(1/(1-m)) centres fitted cost near1; its95% interval includes1 and its90% interval misses registered cost bounds."""
    ev, _ = raw.build(e1_log_shift={0.5: -math.log(2.0), 0.25: -math.log(4 / 3)})
    assert all(not c["excludes_null"] for c in ev["e1_gate_record"]["cells"] if c["gated"])
    result = verdict.evaluate_jr5_verdict(ev)
    assert not result.conditions["a"] and result.outcome == "instrument_fail"
