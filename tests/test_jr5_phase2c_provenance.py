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
from tests import _jr5_deviation_attacks
from tests import _jr5_raw_evidence as raw
from tests.test_jr5_phase2c_verdict_adapter import bound_bundle, positive

ROOT = Path(__file__).resolve().parents[1]
_DEVIATIONS_TEXT = (ROOT / "src/codontrace/claimgate/data/jr5_deviations.md").read_text(encoding="utf-8")


def rehash(record: dict) -> None:
    record["digest"] = canonical_digest({k: v for k, v in record.items() if k != "digest"})


def test_same_verified_bytes_and_manifest_are_required() -> None:
    """A pinned digest authenticates the original bytes, not a tuned mapping or rehashed replacement."""
    constants = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_constants.json").read_bytes()
    record = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_record.json").read_bytes()
    assert verdict._verified_constants(constants, record, deviations_text=_DEVIATIONS_TEXT) == json.loads(constants)
    tuned = json.loads(constants)
    tuned["gate_e1"]["relative_margin"] = 0.9
    modified = json.dumps(tuned).encode()
    with pytest.raises(ConfigurationError, match="sha256"):
        verdict._verified_constants(modified, record, deviations_text=_DEVIATIONS_TEXT)
    swap = json.loads(record)
    manifest = swap["manifest"]
    manifest["files"] = [[p, hashlib.sha256(modified).hexdigest() if p.endswith("jr5_prereg_constants.json") else s]
                         for p, s in manifest["files"]]
    with pytest.raises(ConfigurationError, match="manifest|plan digest|sha256"):
        verdict._verified_constants(modified, json.dumps(swap).encode(), deviations_text=_DEVIATIONS_TEXT)
    manifest["digest"] = PlanManifest(tuple(map(tuple, manifest["files"])), manifest["title"]).digest
    with pytest.raises(ConfigurationError, match="manifest|plan digest|sha256"):
        verdict._verified_constants(modified, json.dumps(swap).encode(), deviations_text=_DEVIATIONS_TEXT)


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

        def read_text(self, encoding: str = "utf-8") -> str:
            return self.read_bytes().decode(encoding)

    class Package:
        def joinpath(self, name: str) -> Entry:
            return Entry(name)

    monkeypatch.setattr(verdict.resources, "files", lambda _: Package())
    assert verdict.jr5_constants()["budget"]["runs_total"] == 3760
    assert len(reads) == 3


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


def test_registering_a_conflicting_digest_contract_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """One class path can carry only one digest-field contract.

    Basis: ``register_noncritical_digest_class`` stores the digest-like
    public fields (``digest`` or a name containing ``_digest``) under the
    class's module and qualified name. Registering the same class again is a
    no-op, but a second class at the same path with other digest fields
    would silently change which fields the replay checks read, so it must be
    refused. The two probe classes share the path ``<this module>.Probe``:
    the first has fields (digest, run_digest), the second (digest,
    plan_digest). The registry is patched so the probes do not leak.
    Expected: first registration stores ("digest", "run_digest"); the repeat
    keeps it and lists the path once; the conflicting one raises
    ConfigurationError naming the conflict and leaves the stored contract.
    """
    from dataclasses import dataclass

    from codontrace.genesis import replay_integrity

    monkeypatch.setattr(replay_integrity, "_DIGEST_FIELDS_BY_CLASS", dict(replay_integrity._DIGEST_FIELDS_BY_CLASS))
    monkeypatch.setattr(
        replay_integrity, "NON_REPLAY_CRITICAL_DIGEST_CLASSES", replay_integrity.NON_REPLAY_CRITICAL_DIGEST_CLASSES
    )

    @dataclass(frozen=True)
    class Probe:
        digest: str
        run_digest: str
        note: str

    first = Probe
    path = f"{first.__module__}.{first.__qualname__}"
    replay_integrity.register_noncritical_digest_class(first)
    replay_integrity.register_noncritical_digest_class(first)
    assert replay_integrity._DIGEST_FIELDS_BY_CLASS[path] == ("digest", "run_digest")
    assert replay_integrity.NON_REPLAY_CRITICAL_DIGEST_CLASSES.count(path) == 1

    @dataclass(frozen=True)
    class Probe:  # type: ignore[no-redef]  # same path, other digest fields
        digest: str
        plan_digest: str

    assert f"{Probe.__module__}.{Probe.__qualname__}" == path
    with pytest.raises(ConfigurationError, match="Conflicting digest contract"):
        replay_integrity.register_noncritical_digest_class(Probe)
    assert replay_integrity._DIGEST_FIELDS_BY_CLASS[path] == ("digest", "run_digest")


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
    with pytest.raises(ConfigurationError, match="manifest|plan digest"):
        verdict._verified_constants(constants, json.dumps(record).encode(), deviations_text=_DEVIATIONS_TEXT)
    manifest = record["manifest"]
    manifest["digest"] = PlanManifest(tuple(map(tuple, manifest["files"])), manifest["title"]).digest
    with pytest.raises(ConfigurationError, match="manifest|plan digest"):
        verdict._verified_constants(constants, json.dumps(record).encode(), deviations_text=_DEVIATIONS_TEXT)


_CONSTANTS_RAW = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_constants.json").read_bytes()
_RECORD_RAW = (ROOT / "src/codontrace/claimgate/data/jr5_prereg_record.json").read_bytes()


def _record_listing(log_text: str) -> bytes:
    """The packaged record re-hashed over ``log_text``, as an editor of the log would refresh it."""

    record = json.loads(_RECORD_RAW)
    manifest = record["manifest"]
    sha = hashlib.sha256(log_text.encode("utf-8")).hexdigest()
    manifest["files"] = [
        [path, sha if path == "docs/prereg/jr5/DEVIATIONS.md" else digest] for path, digest in manifest["files"]
    ]
    manifest["digest"] = PlanManifest(tuple(map(tuple, manifest["files"])), manifest["title"]).digest
    return json.dumps(record).encode()


def test_claimgate_and_preregistration_plan_digest_checks_agree() -> None:
    """Claimgate keeps its own plan-digest and deviations-log checks so genesis
    cannot reach ``codontrace.preregistration`` through the known HP -> claimgate
    edges (import contracts). Both copies must therefore agree on the same inputs.

    Basis: ``plan_digest_from_files`` / ``verify_deviations_log`` (preregistration)
    and ``_verified_constants`` / ``_verify_deviations_log`` (claimgate, via
    ``canonical_digest`` over the locked file list) are two encodings of one
    schema with the same pins: lock digest 633aa9c8..., the sha256 of the
    lock-start entry and the checkpoints of the accepted log. On the packaged
    record both must accept and yield the code pin ``PREREG_RECORD_DIGEST``,
    and both must accept one well-formed appended entry.
    Expected: equal pins, equal plan digest, both accept.
    """

    from codontrace.preregistration import jr5_locked_plan as plan

    assert verdict._LOCK_START_DIGEST == plan.LOCK_START_DIGEST
    assert verdict._LOCK_START_ENTRY_SHA256 == plan.LOCK_START_ENTRY_SHA256
    assert verdict._ACCEPTED_LOG_CHECKPOINTS == plan.ACCEPTED_LOG_CHECKPOINTS
    assert verdict._DIGEST_LINE.pattern == plan.DIGEST_LINE.pattern
    assert verdict._deviations_log_entries(_DEVIATIONS_TEXT) == plan.deviations_log_entries(_DEVIATIONS_TEXT)
    record = json.loads(_RECORD_RAW)
    files = [(path, digest) for path, digest in record["manifest"]["files"]]
    plan_pre = plan.plan_digest_from_files(files, record["manifest"]["title"])
    assert plan_pre == verdict.PREREG_RECORD_DIGEST
    assert verdict._verified_constants(_CONSTANTS_RAW, _RECORD_RAW, deviations_text=_DEVIATIONS_TEXT) == json.loads(
        _CONSTANTS_RAW
    )
    plan.verify_deviations_log(_DEVIATIONS_TEXT, expected_plan_digest=plan_pre)
    verdict._verify_deviations_log(_DEVIATIONS_TEXT, expected_plan_digest=plan_pre)
    appended = _jr5_deviation_attacks.valid_append(_DEVIATIONS_TEXT)
    plan.verify_deviations_log(appended, expected_plan_digest=plan_pre)
    verdict._verify_deviations_log(appended, expected_plan_digest=plan_pre)
    assert verdict._verified_constants(
        _CONSTANTS_RAW, _record_listing(appended), deviations_text=appended
    ) == json.loads(_CONSTANTS_RAW)


@pytest.mark.parametrize("case", sorted(_jr5_deviation_attacks.ATTACKS))
def test_claimgate_and_preregistration_log_checks_refuse_the_same_edits(case: str) -> None:
    """Both log checks refuse every edit of the log other than a whole appended entry.

    Basis: the log is append-only (pinned lock-start entry, pinned
    checkpoints of the accepted log, whole appended entries, one digest line
    at a line start per entry, chain, last entry at the plan pin). Each case
    in ``tests/_jr5_deviation_attacks.py`` breaks one rule. The two copies
    run the same rules in the same order, so they must refuse with the same
    message; the claimgate loader is also fed a record re-hashed over the
    edited log, so the packaged-record check cannot be what refuses it.
    Expected: ConfigurationError with the message of the broken rule, from
    the preregistration check, the claimgate check and the claimgate loader.
    """

    from codontrace.preregistration.jr5_locked_plan import verify_deviations_log

    edit, message = _jr5_deviation_attacks.ATTACKS[case]
    text = edit(_DEVIATIONS_TEXT)
    for check in (verify_deviations_log, verdict._verify_deviations_log):
        with pytest.raises(ConfigurationError, match=message):
            check(text, expected_plan_digest=verdict.PREREG_RECORD_DIGEST)
    with pytest.raises(ConfigurationError, match=message):
        verdict._verified_constants(_CONSTANTS_RAW, _record_listing(text), deviations_text=text)


def test_packaged_log_must_match_its_record_entry() -> None:
    """A packaged log whose sha256 differs from the record's DEVIATIONS.md entry is refused.

    Basis: the record lists sha256(DEVIATIONS.md); that entry is the only tie
    between the shipped log and the shipped record. A valid appended entry
    passes every log rule, so with the unchanged record the only rule it
    breaks is this one (the record still lists the sha256 of the current log).
    Expected: ConfigurationError naming the record entry; with the record
    re-hashed over the new log it is accepted.
    """

    appended = _jr5_deviation_attacks.valid_append(_DEVIATIONS_TEXT)
    with pytest.raises(ConfigurationError, match="packaged DEVIATIONS.md does not match the record.json entry"):
        verdict._verified_constants(_CONSTANTS_RAW, _RECORD_RAW, deviations_text=appended)
    verdict._verified_constants(_CONSTANTS_RAW, _record_listing(appended), deviations_text=appended)


def test_record_declared_digest_must_be_the_digest_of_its_file_list() -> None:
    """A record whose declared manifest digest is not the canonical digest of its files is refused.

    Basis: ``manifest.digest`` is the canonical digest of the title and the
    full file list (DEVIATIONS.md included); the plan pin is computed from
    the files without it, so only this check ties the declared value to the
    list. Here the files are genuine and only the declared digest changes,
    to the plan pin itself (a plausible value that is not the full digest).
    Expected: ConfigurationError naming the declared digest.
    """

    record = json.loads(_RECORD_RAW)
    assert record["manifest"]["digest"] != verdict.PREREG_RECORD_DIGEST
    record["manifest"]["digest"] = verdict.PREREG_RECORD_DIGEST
    with pytest.raises(ConfigurationError, match="does not match its declared digest"):
        verdict._verified_constants(_CONSTANTS_RAW, json.dumps(record).encode(), deviations_text=_DEVIATIONS_TEXT)


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


def _packaged_resources(monkeypatch: pytest.MonkeyPatch, log_raw: bytes) -> None:
    """Serve the packaged constants, a record re-hashed over ``log_raw`` and ``log_raw`` as the log."""

    record = json.loads(_RECORD_RAW)
    manifest = record["manifest"]
    sha = hashlib.sha256(log_raw).hexdigest()
    manifest["files"] = [
        [path, sha if path == "docs/prereg/jr5/DEVIATIONS.md" else digest] for path, digest in manifest["files"]
    ]
    manifest["digest"] = PlanManifest(tuple(map(tuple, manifest["files"])), manifest["title"]).digest
    served = {
        verdict._CONSTANTS_RESOURCE: _CONSTANTS_RAW,
        verdict._RECORD_RESOURCE: json.dumps(record).encode(),
        verdict._DEVIATIONS_RESOURCE: log_raw,
    }

    class Entry:
        def __init__(self, name: str):
            self.name = name

        def read_bytes(self) -> bytes:
            return served[self.name]

        def read_text(self, encoding: str = "utf-8") -> str:
            # What a text-mode read of the file would return: universal newlines.
            return served[self.name].decode(encoding).replace("\r\n", "\n").replace("\r", "\n")

    class Package:
        def joinpath(self, name: str) -> Entry:
            return Entry(name)

    monkeypatch.setattr(verdict.resources, "files", lambda _: Package())


@pytest.mark.parametrize("case", sorted(_jr5_deviation_attacks.LINE_END_ATTACKS))
def test_both_log_readers_refuse_crlf_and_cr_bytes_alike(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """The two loaders give the same answer on a log whose line ends were rewritten.

    Basis: the checkpoints and the lock-start pin are sha256 values of the
    committed LF bytes. Both loaders decode the log bytes with no newline
    translation (the preregistration copy through read_deviations_log, the
    claimgate copy through the packaged resource bytes), so both see the CR
    bytes and both log checks refuse them with the same message. Each loader
    gets a record re-hashed over the edited bytes, so a record mismatch
    cannot be what refuses it. Before R44 the preregistration copy read the
    file in text mode, which turns CRLF and CR into LF, and accepted these
    bytes while claimgate refused them.
    Expected: ConfigurationError with the case's message from
    verify_jr5_record_at_root and from jr5_constants.
    """

    from codontrace.preregistration.jr5_locked_plan import verify_jr5_record_at_root
    from codontrace.preregistration.manifest import hash_plan
    from tests.test_jr5_phase3_e1_gate import RECORD, _clone_prereg

    edit, message = _jr5_deviation_attacks.LINE_END_ATTACKS[case]
    log_raw = edit((ROOT / "docs/prereg/jr5/DEVIATIONS.md").read_bytes())
    root = _clone_prereg(tmp_path)
    (root / "docs/prereg/jr5/DEVIATIONS.md").write_bytes(log_raw)
    record = json.loads(RECORD.read_bytes())
    fresh = hash_plan([path for path, _ in record["manifest"]["files"]], root=root, title=record["manifest"]["title"])
    (root / "docs/prereg/jr5/record.json").write_text(
        json.dumps({"manifest": fresh.to_dict()}, indent=2) + "\n", encoding="utf-8"
    )
    with pytest.raises(ConfigurationError, match=message):
        verify_jr5_record_at_root(root, locked_plan_digest=verdict.PREREG_RECORD_DIGEST)
    _packaged_resources(monkeypatch, log_raw)
    with pytest.raises(ConfigurationError, match=message):
        verdict.jr5_constants()


def test_both_log_readers_accept_the_committed_lf_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """On the committed LF log both loaders accept, and the pins are unchanged.

    Basis: the committed log has no CR byte, so decoding its bytes with or
    without newline translation gives the same text and the pinned
    checkpoints (sha256 of byte prefixes) still hold. The packaged log is
    byte-identical to docs/prereg/jr5/DEVIATIONS.md.
    Expected: no CR byte, equal packaged and repository bytes, every
    checkpoint equal to the sha256 of its prefix, verify_jr5_record_at_root
    returns the plan pin and jr5_constants returns the packaged constants.
    """

    from codontrace.preregistration.jr5_locked_plan import verify_jr5_record_at_root

    raw = (ROOT / "docs/prereg/jr5/DEVIATIONS.md").read_bytes()
    assert b"\r" not in raw and raw == _DEVIATIONS_TEXT.encode("utf-8")
    for size, digest in verdict._ACCEPTED_LOG_CHECKPOINTS:
        assert hashlib.sha256(raw[:size]).hexdigest() == digest
    _manifest, plan_digest = verify_jr5_record_at_root(ROOT, locked_plan_digest=verdict.PREREG_RECORD_DIGEST)
    assert plan_digest == verdict.PREREG_RECORD_DIGEST
    _packaged_resources(monkeypatch, raw)
    assert verdict.jr5_constants() == json.loads(_CONSTANTS_RAW)


def test_adapter_interval_on_a_constant_sample_at_a_registered_bound_is_degenerate() -> None:
    """The adapter's E1 interval rule and the gate's TOST agree on constant samples.

    Basis: the adapter rechecks E1 with its own t interval (_mean_sd and
    _t_interval) and calls the cell equivalent when the 90% interval lies
    strictly inside the bounds. For an exactly constant sample [v] * n the
    mean is v and the SD is 0, so the interval is [v, v], which is not
    strictly inside when v is a bound. A mean taken as fsum / n is one ulp
    off for some (v, n), which leaves a spread near 1e-16; before R44 that
    made the adapter's interval lie inside the bounds at 11 of the
    (bound, n) cases below (for example the m = 0.5 lower bound at n = 14).
    The gate's one_sample_tost must give the same decision. The paired
    contrast uses the same _mean_sd, so a constant non-zero contrast must
    take its zero-spread branch (two-sided p = 0).
    Expected: for the four registered log bounds and n = 2 to 60, interval
    (v, v), not inside, TOST not equivalent; seven copies of
    0.5877866649021191 (whose fsum / 7 is not the value) give mean and SD
    (value, 0.0), and as a paired contrast a two-sided p of 0.
    """

    from codontrace.campaigns.jr5_e1_gate import load_e1_gate_spec
    from codontrace.genesis.statistical_protocol import one_sample_tost

    spec = load_e1_gate_spec(ROOT)
    level = 1.0 - 2.0 * spec.alpha
    for m in (0.5, 0.25):
        lower, upper = spec.log_bounds(m)
        for v in (lower, upper):
            for n in range(2, 61):
                interval = verdict._t_interval([v] * n, level)
                assert (interval.lo, interval.hi) == (v, v), (m, v, n)
                assert not interval.inside(lower, upper), (m, v, n)
                assert one_sample_tost([v] * n, lower, upper, alpha=spec.alpha).equivalent is False
    value = 0.5877866649021191
    assert math.fsum([value] * 7) / 7 != value
    assert verdict._mean_sd([value] * 7) == (value, 0.0)
    assert verdict._Paired((value,) * 7, 1, 10).p_two_sided() == 0.0
