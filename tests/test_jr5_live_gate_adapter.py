"""Actual cost-gate producer records consumed by the raw adapter and auditor."""
from __future__ import annotations

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

