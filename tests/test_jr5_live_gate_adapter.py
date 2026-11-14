"""Actual cost-gate producer records consumed by the raw adapter and auditor."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest

from codontrace.campaigns.jr5_e1_gate import (
    E1GateResult,
    E1Population,
    evaluate_e1_gate,
    load_e1_gate_spec,
)
from codontrace.claimgate import audit_bundle
from codontrace.claimgate.jr5_verdict import (
    PREREG_RECORD_DIGEST,
    assert_jr5_red_queen_claim_allowed,
    evaluate_jr5_verdict,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from tests import _jr5_raw_evidence as raw
from tests.test_jr5_phase2c_verdict_adapter import bound_bundle


def actual_evidence(evidence: dict[str, Any] | None = None, **plan: Any) -> tuple[dict[str, Any], E1GateResult]:
    """Fit each raw count trajectory; the actual gate alone serializes the consumer record."""
    if evidence is None:
        evidence, _ = raw.build(**plan)
    del evidence["e1_gate_record"]
    spec = load_e1_gate_spec()
    cells: dict[tuple[float, int], list[E1Population]] = {}
    for run in evidence["runs"]:
        if run["experiment"] != "e1":
            continue
        n = run["host_n"]
        counts = run["data"]["uniparental_counts"]
        fixed = next((t for t, count in enumerate(counts) if count == n), None)
        lost = next((t for t, count in enumerate(counts) if count == 0), None)
        excluded = fixed is not None and fixed < spec.early_fixation_generation
        population = E1Population(
            seed=run["seed"],
            log_w=None if excluded else raw._slope(tuple(counts), n),
            fixed_generation=fixed,
            lost_generation=lost,
        )
        key = (float(run["cell"]["sex_ratio"]), n)
        cells.setdefault(key, []).append(population)
    result = evaluate_e1_gate(spec, cells)
    evidence["e1_gate_record"] = result.to_record()
    return evidence, result


@pytest.mark.parametrize(("plan", "gate_pass", "instrument_failure", "proved"), [
    ({}, True, False, True),
    ({"e2_effect": {(200, "high"): 0.0, (50, "high"): 0.0,
                    (200, "low"): 0.0, (50, "low"): 0.0}}, True, False, False),
    ({"e1_log_shift": {0.5: 0.15, 0.25: 0.0}}, False, True, False),
    ({"e1_early_fixed": {(0.5, 50): 9}}, True, True, False),
], ids=["qualifying", "no_invasion", "failed_cost", "report_only_cap"])
def test_actual_producer_adapter_and_auditor_end_to_end(
    plan: dict[str, Any], gate_pass: bool, instrument_failure: bool, proved: bool,
) -> None:
    """Theoretical E1 cost and -.25 invasion qualify; zero invasion, cost2*exp(.15)>2.2, or9>0.2*40 exclusions cannot."""
    evidence, result = actual_evidence(**plan)
    assert isinstance(result, E1GateResult)
    assert result.passed is gate_pass and result.instrument_failure is instrument_failure
    record = result.to_record()
    assert evidence["e1_gate_record"] == record
    assert result.spec.prereg_manifest_sha256 == PREREG_RECORD_DIGEST
    assert record["prereg_manifest_digest"] == record["spec"]["prereg_manifest_digest"] == PREREG_RECORD_DIGEST
    verdict = evaluate_jr5_verdict(evidence)
    assert verdict.red_queen_proved is proved
    payload = bound_bundle(evidence)
    assert payload["jr5_evidence"]["e1_gate_record"] == result.to_record()
    report = audit_bundle(payload)
    if proved:
        assert assert_jr5_red_queen_claim_allowed(verdict.to_dict(), evidence) == "red_queen_proved"
        assert report.achieved_level >= 2
        assert not any("forbidden_claim:red_queen_proved" in warning for warning in report.warnings)
    else:
        with pytest.raises(ConfigurationError):
            assert_jr5_red_queen_claim_allowed(verdict.to_dict(), evidence)
        assert report.achieved_level <= 1
        assert any("red_queen_proved" in warning for warning in report.warnings)


@pytest.mark.parametrize("attack", ["settings", "missing_manifest", "wrong_manifest", "missing_constants",
                                     "wrong_constants", "missing_seed", "spec_manifest"])
def test_actual_record_rejects_rehashed_settings_and_provenance_forgery(attack: str) -> None:
    """A genuine producer record binds all settings, both digests and every seed; rehashing any alteration cannot authenticate it."""
    evidence, result = actual_evidence()
    record = evidence["e1_gate_record"]
    assert record == result.to_record()
    if attack == "settings":
        record["spec"]["relative_margin"] = 0.9
    elif attack == "missing_manifest":
        del record["prereg_manifest_digest"]
    elif attack == "wrong_manifest":
        record["prereg_manifest_digest"] = "0" * 64
    elif attack == "missing_constants":
        del record["constants_sha256"]
    elif attack == "wrong_constants":
        record["constants_sha256"] = "0" * 64
    elif attack == "missing_seed":
        record["cells"][0]["seeds"].pop()
    else:
        record["spec"]["prereg_manifest_digest"] = "0" * 64
    record["digest"] = canonical_digest({k: v for k, v in record.items() if k != "digest"})
    with pytest.raises(ConfigurationError):
        evaluate_jr5_verdict(evidence)


def test_actual_producer_rejects_retuned_spec() -> None:
    """Replacing the registered10% margin with90% is not the trusted spec, even when its original digest strings are retained."""
    spec = load_e1_gate_spec()
    forged = replace(spec, relative_margin=0.9)
    with pytest.raises(ConfigurationError, match="spec"):
        evaluate_e1_gate(forged, {})


def _zero_spread_e1_evidence() -> dict[str, Any]:
    """Raw evidence whose E1 populations in each cell all carry the first population's counts."""

    evidence, _ = raw.build()
    first: dict[tuple[float, int], list[int]] = {}
    for run in evidence["runs"]:
        if run["experiment"] != "e1":
            continue
        key = (float(run["cell"]["sex_ratio"]), int(run["host_n"]))
        counts = first.setdefault(key, list(run["data"]["uniparental_counts"]))
        run["data"]["uniparental_counts"] = list(counts)
        raw.readdress(run)
    return evidence


def test_zero_spread_actual_gate_record_round_trips() -> None:
    """Zero E1 spread from raw counts: the producer writes tagged infinite t and the adapter agrees.

    Basis: every E1 population of a cell is given the same raw count
    trajectory (that of the cell's first seed, which is not excluded), so the
    bias-reduced slope fit returns the same log w for each of them. In the
    two gated cells (N = 200, m = 0.5 and 0.25) the sample SD is then exactly
    0 (``math.fsum`` of 40 equal values divided by 40 returns that value for
    these two floats; checked below). With SE = 0 the one-sided statistics
    are +inf (mean above the lower bound) and -inf (mean below the upper
    bound) when the common log w lies strictly inside the TOST margin, which
    holds here: the first seeds give log w 0.6954 inside (0.5878, 0.7885)
    for m = 0.5 and 0.3493 inside (0.1823, 0.3830) for m = 0.25. The
    report-only N = 50 cells are compared by the adapter as well. The producer
    (``evaluate_e1_gate``) writes {"$float": "inf"} and {"$float": "-inf"}.
    The adapter (``evaluate_jr5_verdict``) refits the raw counts, rebuilds
    each cell's TOST record with ``_tost_record`` and compares it to the
    producer record field by field; a finite stand-in for an infinite t on
    either side would not match and would raise ConfigurationError.
    Expected: gate passed; both gated cells have SD 0, t_lower +inf and
    t_upper -inf in the record; the verdict accepts the record and proves the claim, as
    for the planted positive.
    """

    evidence, result = actual_evidence(_zero_spread_e1_evidence())
    record = result.to_record()
    assert result.passed is True and result.instrument_failure is False
    gated = [cell for cell in record["cells"] if cell["gated"]]
    assert sorted((cell["sex_ratio"], cell["host_n"]) for cell in gated) == [(0.25, 200), (0.5, 200)]
    for cell in gated:
        tost = cell["tost"]
        assert tost["sd"] == 0.0
        assert tost["t_lower"] == {"$float": "inf"} and tost["t_upper"] == {"$float": "-inf"}
        assert tost["equivalent"] is True
    verdict = evaluate_jr5_verdict(evidence)
    assert verdict.conditions["a"] is True
    assert verdict.outcome == "rq_consistent" and verdict.red_queen_proved is True


@pytest.mark.parametrize("n_low", [200, 50], ids=["live_N200_low", "live_N50_low"])
def test_actual_producer_low_disagreement_never_proves(n_low: int) -> None:
    """End-to-end: producer gate + raw adapter + claim path refuse a low-virulence disagreement.

    Derived: the same -0.022 + 0.0625*z deltas give p = 0.008413 with 97.5% BCa
    [-0.036858813, 0.000316853] (agree=False). High contrasts remain at the
    qualifying -0.25 planting. The live E1 producer still passes; the verdict
    must be inconclusive and the auditor must not grant red_queen_proved.
    """

    import math

    n = 60
    w = [-math.log(1.0 - (i + 0.5) / n) for i in range(n)]
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in w) / (n - 1))
    deltas = [-0.022 + 0.0625 * (x - mean) / sd for x in w]
    evidence, result = actual_evidence(e2_deltas={(n_low, "low"): deltas})
    assert result.passed is True
    verdict = evaluate_jr5_verdict(evidence)
    assert verdict.outcome == "inconclusive"
    assert verdict.red_queen_proved is False
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(verdict.to_dict(), evidence)
    report = audit_bundle(bound_bundle(evidence))
    assert report.achieved_level < 2


# R46: the E1 decision has one source, the gate's TOST p-rule.
# The tester's scan (n slopes c + (i - (n - 1) / 2) * 0.016, c stepped one
# float at a time across the m = 0.5 lower bound) found samples where the
# adapter's old interval rule (power.t_ppf, 1443 ulp below to 1366 ulp above
# the exact 0.95 quantile at the E1 dfs) and the gate's rule (student_t_sf,
# 102 ulp below to 73 ulp above) split. scipy's t.ppf, within 2.6 ulp of the
# exact quantile at these dfs (60-digit reference), is the cross-check for
# "exactly equivalent" below; every t used is at least 7 ulp from it.

_DF37_EXACT_AND_GATE_EQUIVALENT = 0.6364498853178189  # n = 38: t_lower 13.1 ulp past exact q; t_ppf +1366
_DF39_EXACT_EQUIVALENT_GATE_NOT = 0.6376164490249974  # n = 40: t_lower +4.4 ulp; sf threshold +73.4
_DF39_NEITHER_EQUIVALENT = 0.6376164490249973  # n = 40: t_lower -12.6 ulp; t_ppf -494 (old rule: inside)


def _r46_slopes(c: float, n: int) -> list[float]:
    return [c + (i - (n - 1) / 2) * 0.016 for i in range(n)]


def _r46_evidence(monkeypatch: pytest.MonkeyPatch, slopes: list[float]) -> tuple[dict[str, Any], E1GateResult]:
    """Valid positive grid whose gated m = 0.5 cell fits to ``slopes``, with the actual gate's record.

    40 - len(slopes) populations of that cell fix at generation 1 (excluded,
    within the cap of 8). The adapter's fit is replaced for that cell only
    (host N 200, 6 counts) and returns ``slopes`` in seed order, as the gate
    receives them.
    """
    import itertools

    from codontrace.claimgate import jr5_verdict

    excluded = 40 - len(slopes)
    evidence, _ = raw.build(e1_early_fixed={(0.5, 200): excluded} if excluded else {})
    del evidence["e1_gate_record"]
    spec = load_e1_gate_spec()
    cells: dict[tuple[float, int], list[E1Population]] = {}
    for run in sorted(evidence["runs"], key=lambda r: r["seed"]):
        if run["experiment"] != "e1":
            continue
        n = run["host_n"]
        counts = run["data"]["uniparental_counts"]
        fixed = next((t for t, count in enumerate(counts) if count == n), None)
        lost = next((t for t, count in enumerate(counts) if count == 0), None)
        key = (float(run["cell"]["sex_ratio"]), n)
        pops = cells.setdefault(key, [])
        if fixed is not None and fixed < spec.early_fixation_generation:
            log_w = None
        elif key == (0.5, 200):
            log_w = slopes[sum(p.log_w is not None for p in pops)]
        else:
            log_w = raw._slope(tuple(counts), n)
        pops.append(E1Population(seed=run["seed"], log_w=log_w, fixed_generation=fixed, lost_generation=lost))
    result = evaluate_e1_gate(spec, cells)
    evidence["e1_gate_record"] = result.to_record()
    real = jr5_verdict._firth_logit_slope
    crafted = itertools.cycle(slopes)
    monkeypatch.setattr(
        jr5_verdict,
        "_firth_logit_slope",
        lambda counts, host_n, fit: next(crafted) if host_n == 200 and len(counts) == 6 else real(counts, host_n, fit),
    )
    return evidence, result


def _gated_half(record: dict[str, Any]) -> dict[str, Any]:
    return next(c for c in record["cells"] if c["sex_ratio"] == 0.5 and c["host_n"] == 200)


def test_df37_sample_the_gate_calls_equivalent_proves_the_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    """A df 37 cell inside the margin by the gate's rule is accepted, not refused by a second rule.

    Basis: 38 used slopes c + (i - 18.5) * 0.016 with c = 0.6364498853178189
    at the m = 0.5 bounds (log 1.8, log 2.2). Float moments hold; t_lower =
    1.6870936195962665, 15 ulp above scipy's 0.95 quantile at df 37
    (1.6870936195962631, 1.9 ulp below exact) and 13.1 ulp above the exact
    quantile, so the exact TOST rejects the lower null; t_upper is far below -q. The gate's p-rule (student_t_sf <
    0.05) agrees: p_lower = 0.04999999999999927. The old adapter rule, the
    90% interval with power.t_ppf = 1.687093619596567 (about 1366 ulp above
    exact), put the lower end below log 1.8, called the cell not
    equivalent, and so refused the honest gate record and blocked a valid
    positive. With equivalent = tost.equivalent both copies say equivalent.
    The reported 90% interval uses the gate's quantile, so its ends equal
    the gate's tost ci_low / ci_high and the 95% interval equals the gate's
    exclusion interval, float for float.
    Expected: gate passed; the t_ppf interval rule says not inside; the
    verdict is rq_consistent with red_queen_proved True; adapter cell equal
    to the gate's cell in equivalent, passed, ratio_ci and the 95% interval.
    """
    from scipy import stats

    from codontrace.claimgate import jr5_verdict

    slopes = _r46_slopes(_DF37_EXACT_AND_GATE_EQUIVALENT, 38)
    evidence, result = _r46_evidence(monkeypatch, slopes)
    cell = _gated_half(result.to_record())
    lo, hi = cell["log_bounds"]
    assert cell["n_used"] == 38 and cell["tost"]["df"] == 37
    assert cell["tost"]["t_lower"] > float(stats.t.ppf(0.95, 37))
    assert cell["tost"]["p_lower"] < 0.05 and cell["equivalent"] is True and result.passed is True
    assert not jr5_verdict._t_interval(slopes, 0.9, (lo, hi)).inside(lo, hi)
    verdict = evaluate_jr5_verdict(evidence)
    assert verdict.outcome == "rq_consistent" and verdict.red_queen_proved is True
    _gp, _br, cells = jr5_verdict._e1(
        jr5_verdict._Values(jr5_verdict.Jr5Evidence.from_dict(evidence)), jr5_verdict.jr5_constants()
    )
    mine = next(c for c in cells if c["sex_ratio"] == 0.5 and c["host_n"] == 200)
    assert mine["equivalent"] is True and mine["passed"] is True
    assert mine["ratio_ci"] == cell["ratio_ci"]
    assert mine["exclusion_interval_log"] == cell["exclusion_interval_log"]


def test_df39_sample_at_the_gate_accuracy_limit_is_not_equivalent_in_both_copies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At df 39 a cell the exact TOST calls equivalent but the gate's p-rule does not: both copies say no.

    Basis: 40 slopes c + (i - 19.5) * 0.016, c = 0.6376164490249974, m = 0.5.
    t_lower = 1.6848751217112263 is 7 ulp above scipy's 0.95 quantile at
    df 39 (1.6848751217112248, 2.6 ulp below exact) and 4.4 ulp above the
    exact quantile, so the exact TOST rejects. The gate's threshold, the smallest float t with
    student_t_sf(t, 39) < 0.05, is 73.4 ulp above the exact quantile, so
    p_lower = 0.05000000000000193 and the gate says not equivalent. That is
    the documented accuracy limit of student_t_sf (a band of a few ulp of
    the mean), not a split: the adapter takes the same decision, so the
    honest record is accepted and E1 fails. The old t_ppf interval
    (t_ppf = 1.6848751217111158, about 494 ulp below exact) said inside,
    disagreed with the record and refused it.
    Expected: gate not passed (instrument failure); the t_ppf interval rule
    says inside; the verdict is instrument_fail with red_queen_proved False,
    no ConfigurationError; adapter cell not equivalent, like the gate's.
    """
    from scipy import stats

    from codontrace.claimgate import jr5_verdict

    slopes = _r46_slopes(_DF39_EXACT_EQUIVALENT_GATE_NOT, 40)
    evidence, result = _r46_evidence(monkeypatch, slopes)
    cell = _gated_half(result.to_record())
    lo, hi = cell["log_bounds"]
    assert cell["tost"]["t_lower"] > float(stats.t.ppf(0.95, 39))
    assert cell["tost"]["p_lower"] >= 0.05 and cell["equivalent"] is False
    assert result.passed is False and result.instrument_failure is True
    assert jr5_verdict._t_interval(slopes, 0.9, (lo, hi)).inside(lo, hi)
    verdict = evaluate_jr5_verdict(evidence)
    assert verdict.outcome == "instrument_fail" and verdict.red_queen_proved is False
    assert verdict.conditions["a"] is False
    _gp, _br, cells = jr5_verdict._e1(
        jr5_verdict._Values(jr5_verdict.Jr5Evidence.from_dict(evidence)), jr5_verdict.jr5_constants()
    )
    mine = next(c for c in cells if c["sex_ratio"] == 0.5 and c["host_n"] == 200)
    assert mine["equivalent"] is False and mine["tost"]["equivalent"] is False


def test_df39_record_copied_from_an_interval_rule_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rehashed record whose cell says equivalent while its own TOST says not is refused.

    Basis: 40 slopes c + (i - 19.5) * 0.016, c = 0.6376164490249973, m = 0.5.
    t_lower = 1.6848751217112226 is 10 ulp below scipy's 0.95 quantile at
    df 39 (12.6 ulp below exact), so the exact TOST does not reject and
    the gate agrees (p_lower = 0.050000000000001765). The old adapter
    interval with t_ppf (about 494 ulp too small) said inside. A record
    whose gated cell carries that interval decision (equivalent and passed
    True, record passed, no instrument failure, digest recomputed) next to
    the gate's TOST is not a gate record: the gate defines equivalent as
    tost.equivalent. Accepting it gave rq_consistent with red_queen_proved
    True against the exact answer.
    Expected: honest record gives instrument_fail; the edited, rehashed
    record raises ConfigurationError ("equivalent does not follow its TOST
    record"), so red_queen_proved is never reached.
    """
    from scipy import stats

    from codontrace.claimgate import jr5_verdict

    slopes = _r46_slopes(_DF39_NEITHER_EQUIVALENT, 40)
    evidence, result = _r46_evidence(monkeypatch, slopes)
    record = result.to_record()
    cell = _gated_half(record)
    lo, hi = cell["log_bounds"]
    assert cell["tost"]["t_lower"] < float(stats.t.ppf(0.95, 39))
    assert cell["tost"]["equivalent"] is False and cell["equivalent"] is False
    assert jr5_verdict._t_interval(slopes, 0.9, (lo, hi)).inside(lo, hi)
    assert evaluate_jr5_verdict(evidence).outcome == "instrument_fail"
    forged = deepcopy(record)
    del forged["digest"]
    forged_cell = _gated_half(forged)
    forged_cell["equivalent"] = forged_cell["passed"] = True
    forged["passed"], forged["instrument_failure"] = True, False
    forged["digest"] = canonical_digest(forged)
    evidence["e1_gate_record"] = forged
    with pytest.raises(ConfigurationError, match="equivalent does not follow its TOST record"):
        evaluate_jr5_verdict(evidence)


@pytest.mark.parametrize(
    "edit",
    [
        "equivalent_without_tost_rejection",
        "passed_without_equivalence",
        "passed_over_the_cap",
        "equivalent_without_tost",
    ],
)
def test_record_check_refuses_a_cell_inconsistent_with_its_own_tost(edit: str) -> None:
    """The record check ties each cell to its own TOST even when the recomputation carries the same cell.

    Basis: the gate writes equivalent = (tost is not None and
    tost.equivalent) and passed = equivalent and excludes_null and not
    exclusion_cap_exceeded (campaigns.jr5_e1_gate.E1CellResult). Here the
    expected cells handed to _check_e1_gate_record carry the same edit as
    the record, so the field-by-field comparison alone would accept; only
    the per-cell consistency rule can refuse. Edits on the gated m = 0.5
    cell of the valid positive dataset (tost.equivalent True, excludes_null
    True, cap not exceeded): tost.equivalent set False with equivalent left
    True; equivalent False with passed left True; exclusion_cap_exceeded
    True with passed left True; tost removed with equivalent left True.
    Expected: ConfigurationError for every edit, naming the cell's
    equivalent or passed field.
    """
    from codontrace.claimgate import jr5_verdict

    evidence, _ = raw.build()
    k = jr5_verdict.jr5_constants()
    gated_pass, breach, cells = jr5_verdict._e1(jr5_verdict._Values(jr5_verdict.Jr5Evidence.from_dict(evidence)), k)
    cell = next(c for c in cells if c["sex_ratio"] == 0.5 and c["host_n"] == 200)
    assert cell["tost"]["equivalent"] is cell["equivalent"] is cell["passed"] is True
    if edit == "equivalent_without_tost_rejection":
        cell["tost"] = dict(cell["tost"], equivalent=False)
    elif edit == "passed_without_equivalence":
        cell["equivalent"] = False
    elif edit == "passed_over_the_cap":
        cell["exclusion_cap_exceeded"] = True
    else:
        cell["tost"] = None
    record = deepcopy(evidence["e1_gate_record"])
    del record["digest"]
    record["cells"] = deepcopy(cells)
    record["digest"] = canonical_digest(record)
    instrument_failure = not gated_pass or breach
    with pytest.raises(ConfigurationError, match="(equivalent|passed) does not follow"):
        jr5_verdict._check_e1_gate_record(record, gated_pass, instrument_failure, cells, k)
