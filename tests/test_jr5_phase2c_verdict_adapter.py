"""JR5 phase 2c: the verdict is recomputed from raw per-seed records.

The evidence is the full prereg run grid (3,760 runs) built by
``tests/_jr5_raw_evidence.py``. Each arm's values have an exact planted mean
and SD (fixed normal scores, no random draw), so every expected outcome below
follows from a preregistered bound and not from the verdict code:

- E1 TOST: theory 1/(1 - m) is 2.0 at m = 0.5 and 4/3 at m = 0.25, bounds +-10%
  ([1.8, 2.2], [1.2, 1.4667]); the 90% t interval of log w over 40 populations
  must lie inside and the 95% interval must exclude log 1 = 0. At the
  bias-reduced SD 0.076 the 90% half-width is about 1.685 * 0.076 / sqrt(40)
  = 0.020, far inside log(2.2/2) = 0.095. Cap: at most 0.2 * 40 = 8 populations
  fixed before generation 3, in every E1 cell.
- E2 Holm over four tests at family alpha 0.05: step k at 0.05 / (5 - k)
  (0.0125, 0.01667, 0.025, 0.05), BCa at 98.75 / 98.333 / 97.5 / 95%,
  10,000 resamples, seed 12345. A planted difference of -0.25 with SD 0.10
  over 60 seeds gives t of about -19, far past every step.
- Condition (c): one-sided 0.025 plus the two-sided 95% BCa interval.
- Condition (d): 90% interval strictly inside +-0.10 (frequency) or +-log 1.1
  = 0.0953 (log fitness ratio), or a 95% interval opposite the effect. At SD
  0.05 the 90% half-width is about 0.011.
- Condition (e): every grid run replays (digests, bodies, residual <= 1e-9)
  and every sealed lock of PREREG section 9 replays to its pinned digest.

Method basis: the TOST decision equals a 90% interval inside preregistered
bounds and a non-significant result is never evidence of absence; Holm
step-down stops at the first non-rejection and each step's interval is a
step-level interval, not a simultaneous one; paired BCa coverage is close to
nominal at 60 pairs (it falls short only near 10 pairs); the bias-reduced
logit fit removes the first-order bias of the slope and stays finite under
separation.
"""

from __future__ import annotations

import inspect
import json
import math
import shutil
from copy import deepcopy
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.claimgate.jr5_verdict import (
    E4_WINDOW_SIGNS,
    PREREG_CONSTANTS_SHA256,
    PREREG_RECORD_DIGEST,
    SEALED_LOCK_DIGESTS,
    Interval,
    Jr5Evidence,
    _Paired,
    assert_jr5_red_queen_claim_allowed,
    evaluate_jr5_verdict,
    jr5_bundle_fields,
    jr5_run_grid,
    verify_jr5_verdict,
)
from codontrace.errors import ConfigurationError
from tests import _jr5_raw_evidence as raw

ROOT = Path(__file__).resolve().parents[1]
PREREG_DIR = ROOT / "docs" / "prereg" / "jr5"
FIXTURE = ROOT / "tests" / "fixtures" / "claimgate" / "level2_difference.json"
FAIL_GATE = {"passed": False, "instrument_failure": True}


@cache
def _positive() -> str:
    return json.dumps(raw.build()[0])


def positive() -> dict[str, Any]:
    return json.loads(_positive())


def build(gate: dict[str, bool] | None = None, **plan: Any) -> dict[str, Any]:
    ev, _ = raw.build(**plan)
    if gate is not None:
        ev["e1_gate_record"] = raw.gate_record(ev["runs"], **gate)
    return ev


def failed(ev: dict[str, Any]) -> set[str]:
    verdict = evaluate_jr5_verdict(ev)
    return {k for k, v in verdict.conditions.items() if not v}


def bound_bundle(ev: dict[str, Any]) -> dict[str, Any]:
    """The level-2 fixture bound to ``ev``: pinned prereg digest, evidence seeds, evidence digest artifact."""

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    parsed = Jr5Evidence.from_dict(ev)
    payload["red_queen_proved"] = True
    payload["jr5_evidence"] = ev
    payload["jr5_verdict"] = evaluate_jr5_verdict(parsed).to_dict()
    payload.update(jr5_bundle_fields(parsed))
    return payload


def _baseline_level() -> int:
    return int(audit_bundle(json.loads(FIXTURE.read_text(encoding="utf-8"))).achieved_level)


# ---------------------------------------------------------------- required pair


def test_raw_dataset_meeting_the_prereg_proves_the_claim() -> None:
    """Full grid at the planted defaults: every condition sits inside its prereg bound, so the flag is True.

    E1 log w is centred on log(1/(1 - m)) with the bias-reduced SDs, E2 high is
    -0.25 (t near -19), the alternatives are 0 with SD 0.05 (90% half-width
    0.011 < 0.10 and < 0.0953), and the host time-shift effect is -0.05 with
    SD 0.05 (95% interval below 0, the sign expected under cycling). The
    claim path and the auditor both accept it end to end.
    """

    ev = positive()
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.outcome == "rq_consistent"
    assert verdict.red_queen_proved is True
    assert assert_jr5_red_queen_claim_allowed(verdict.to_dict(), ev) == "red_queen_proved"
    assert audit_bundle(bound_bundle(ev)).achieved_level >= _baseline_level()


def test_raw_dataset_failing_the_prereg_does_not_prove_the_claim() -> None:
    """E2 copassaged minus fixed planted at 0 at both N: (b) needs a Holm-significant drop, so the flag is False.

    With mean exactly 0 the paired t is 0 (p = 1) and no Holm step rejects;
    (c) fails with it. No alternative explains an absent effect, so the
    outcome is ``none`` and the auditor keeps the ban.
    """

    ev = build(e2_effect={(200, "high"): 0.0, (50, "high"): 0.0, (200, "low"): 0.0, (50, "low"): 0.0})
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.red_queen_proved is False
    assert {"b", "c"} <= failed(ev)
    assert verdict.outcome == "none"
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(verdict.to_dict(), ev)
    assert audit_bundle(bound_bundle(ev)).achieved_level < _baseline_level()


# ---------------------------------------------------------------- single failures

SINGLE_FAILURES = [
    # (a) m = 0.5 log w shifted by +0.15: ratio 2 * e^0.15 = 2.32 > 2.2, so the 90% interval leaves the bounds.
    ("a_tost", dict(gate=FAIL_GATE, e1_log_shift={0.5: 0.15, 0.25: 0.0}), {"a"}, "instrument_fail"),
    # (a) 9 of 40 N = 50 populations fixed at generation 1: above the cap of 8 (report-only N still counts).
    ("a_cap", dict(gate={"passed": True, "instrument_failure": True}, e1_early_fixed={(0.5, 50): 9}), {"a"}, "instrument_fail"),
    # (b) N = 50 high planted at 0: p = 1, so the N = 50 high test is not rejected.
    ("b_N50", dict(e2_effect={(200, "high"): -0.25, (50, "high"): 0.0, (200, "low"): 0.0, (50, "low"): 0.0}), {"b"}, "none"),
    # (b) N = 200 high planted at 0. Condition (c) uses the same N = 200 high contrast, so it fails with (b).
    ("b_N200", dict(e2_effect={(200, "high"): 0.0, (50, "high"): -0.25, (200, "low"): 0.0, (50, "low"): 0.0}), {"b", "c"}, "none"),
    # (c) frozen replay planted on copassaged (frozen minus fixed -0.25): copassaged minus frozen is about 0.
    # The diversity alternative is then not ruled out either, so (d) fails with (c).
    ("c_frozen", dict(frozen_minus_fixed=-0.25), {"c", "d"}, "diversity_without_rqd"),
    # (d) load: outcross minus self +0.2 at mu 0.05: 90% interval outside +-0.0953 and not below 0.
    ("d_load", dict(load_effect=0.2), {"d"}, "rq_consistent"),
    # (d) diversity arm: frozen minus fixed -0.12 (90% interval about [-0.131, -0.109], outside +-0.10, same
    # side as the effect) while copassaged minus frozen stays near -0.13 and significant.
    ("d_diversity", dict(frozen_minus_fixed=-0.12), {"d"}, "rq_consistent"),
    # (d) E4: host effect +0.05 (95% interval above 0, against the cycling sign) and parasite effect 0.
    # Typed rq_consistent only needs any excluding window (PREREG section 2); expected sign is (d) alone.
    ("d_window_sign", dict(e4={"host_effect": 0.05, "parasite_effect": 0.0}), {"d"}, "rq_consistent"),
    # (d) tax: uniform tax minus fixed -0.2, same side as the effect and outside +-0.10.
    ("d_tax", dict(tax_minus_fixed=-0.2), {"d"}, "none"),
]


@pytest.mark.parametrize(("name", "plan", "expect_failed", "outcome"), SINGLE_FAILURES, ids=[s[0] for s in SINGLE_FAILURES])
def test_single_failed_condition_keeps_the_flag_false(name: str, plan: dict[str, Any], expect_failed: set[str], outcome: str) -> None:
    """Each planted change crosses exactly the prereg bound named in its comment; the flag stays False."""

    ev = build(**plan)
    verdict = evaluate_jr5_verdict(ev)
    assert failed(ev) == expect_failed
    assert verdict.outcome == outcome
    assert verdict.red_queen_proved is False


def test_e_fails_on_one_bad_replay_and_on_a_wrong_lock() -> None:
    """(e): one run whose replay digest differs, or a sealed lock that replays to another digest, gives instrument_fail."""

    ev = positive()
    run = ev["runs"][123]
    run["replay"]["replayed_digest"] = "0" * 64
    raw.readdress(run)
    assert failed(ev) == {"e"}
    assert evaluate_jr5_verdict(ev).outcome == "instrument_fail"

    ev = positive()
    ev["runs"][7]["replay"]["atp_ledger_residual"] = 2e-9  # above the 1e-9 validity bound
    raw.readdress(ev["runs"][7])
    assert failed(ev) == {"e"}

    ev = positive()
    ev["sealed_locks"]["rq_v2_phase6.summary_sha256"] = "f" * 64
    assert failed(ev) == {"e"}


def test_e_coverage_missing_run_missing_lock_duplicate_id_are_refused() -> None:
    """(e) covers every run of (a) to (d) and every section 9 lock, so the run set must equal the grid."""

    ev = positive()
    ev["runs"].pop(5)
    with pytest.raises(ConfigurationError, match="grid"):
        evaluate_jr5_verdict(ev)

    ev = positive()
    del ev["sealed_locks"]["mating_ledger.design"]
    with pytest.raises(ConfigurationError, match="missing"):
        evaluate_jr5_verdict(ev)

    ev = positive()
    ev["runs"][1]["run_id"] = ev["runs"][0]["run_id"]
    raw.readdress(ev["runs"][1])
    with pytest.raises(ConfigurationError, match="unique"):
        evaluate_jr5_verdict(ev)

    ev = positive()
    dup = deepcopy(ev["runs"][0])
    dup["run_id"] = "copy"
    ev["runs"].append(raw.readdress(dup))
    with pytest.raises(ConfigurationError, match="more than one run"):
        evaluate_jr5_verdict(ev)


def test_holm_bca_level_follows_the_step() -> None:
    """N = 200 high sits at Holm step 2: its t test rejects but its 98.333% BCa interval holds 0, so inconclusive.

    The deltas are -0.022 + 0.0625 * z with z the standardised exponential
    scores (right-skewed): p = 0.0084 < 0.05 / 3, the 98.333% BCa interval
    reaches above 0 while the 95% one excludes it. N = 50 high (t near -19)
    takes step 1. Reading every BCa at 95% would wrongly call it significant.
    """

    n = 60
    w = [-math.log(1 - (i + 0.5) / n) for i in range(n)]
    m = math.fsum(w) / n
    sd = math.sqrt(math.fsum((x - m) ** 2 for x in w) / (n - 1))
    deltas = [-0.022 + 0.0625 * (x - m) / sd for x in w]
    pair = _Paired(tuple(deltas), 12345, 10000)
    assert pair.p_two_sided() < 0.05 / 3
    assert pair.bca(0.9833333333333333).side() == 0
    assert pair.bca(0.95).side() == -1
    ev = build(e2_deltas={(200, "high"): deltas})
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.conditions["b"] is False
    assert verdict.outcome == "inconclusive"
    assert verdict.red_queen_proved is False




@pytest.mark.parametrize("n_low", [200, 50], ids=["N200_low", "N50_low"])
def test_low_virulence_disagreement_on_positive_path_is_inconclusive(n_low: int) -> None:
    """All four E2 family members must agree; a disagreeing low contrast blocks the claim.

    Derived from the same right-skewed lattice used in the Holm BCa step test:
    deltas = -0.022 + 0.0625 * z with z the standardised exponential scores of
    length 60. The paired t two-sided p-value is 0.008413206354653575, which is
    below the Holm step-3 alpha 0.025, while the matching 97.5% BCa interval
    [-0.03685881297959533, 0.000316852861967653] includes 0, so the call is
    agree=False. On an otherwise qualifying positive (high contrasts still at
    -0.25), PREREG section 3 and section 2 require ``inconclusive`` and the
    flag must stay False; omitting the low family members would wrongly yield
    ``rq_consistent`` with ``red_queen_proved=True``.
    """

    n = 60
    w = [-math.log(1.0 - (i + 0.5) / n) for i in range(n)]
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in w) / (n - 1))
    deltas = [-0.022 + 0.0625 * (x - mean) / sd for x in w]
    pair = _Paired(tuple(deltas), 12345, 10000)
    assert pair.p_two_sided() == pytest.approx(0.008413206354653575, rel=1e-12)
    bca = pair.bca(0.975)
    assert bca.lo == pytest.approx(-0.03685881297959533, rel=1e-12)
    assert bca.hi == pytest.approx(0.000316852861967653, rel=1e-12)
    assert bca.side(0.0) == 0
    ev = build(e2_deltas={(n_low, "low"): deltas})
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.outcome == "inconclusive"
    assert verdict.red_queen_proved is False
    assert verdict.conditions["b"] is True  # high contrasts still pass Holm
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(verdict.to_dict(), ev)


@pytest.mark.parametrize("n_low", [200, 50], ids=["N200_low_load", "N50_low_load"])
def test_low_virulence_disagreement_on_load_path_is_inconclusive(n_low: int) -> None:
    """Load attribution also depends on every E2 family member agreeing.

    High-virulence E2 effects are planted at 0 (no invasion signal) and the
    mutation-load arm is set to the load_consistent signature (+0.10 at every
    rate plus slope 4). The same disagreeing low-virulence deltas as the
    positive-path case (p = 0.008413, 97.5% BCa holding 0) make that family
    member inconclusive. PREREG section 2 therefore returns ``inconclusive``
    rather than ``load_consistent``.
    """

    n = 60
    w = [-math.log(1.0 - (i + 0.5) / n) for i in range(n)]
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in w) / (n - 1))
    deltas = [-0.022 + 0.0625 * (x - mean) / sd for x in w]
    zero = {(200, "high"): 0.0, (50, "high"): 0.0, (200, "low"): 0.0, (50, "low"): 0.0}
    ev = build(e2_effect=zero, e2_deltas={(n_low, "low"): deltas}, load_effect=0.10, load_slope=4.0)
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.outcome == "inconclusive"
    assert verdict.red_queen_proved is False


def test_wrong_sign_excluding_window_is_typed_rq_consistent() -> None:
    """PREREG section 2 line 20: typed rq_consistent needs any CI excluding 0, not the cycling sign.

    Host effect +0.05 with SD 0.05 gives a 95% interval above 0 (side +1), so
    the expected-cycling sign check fails and condition (d) is False, but the
    interval still excludes 0. The typed outcome is therefore ``rq_consistent``
    while ``red_queen_proved`` stays False.
    """

    ev = build(e4={"host_effect": 0.05, "parasite_effect": 0.0})
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.outcome == "rq_consistent"
    assert verdict.conditions["d"] is False
    assert verdict.red_queen_proved is False


def test_holm_stops_at_the_first_non_rejection() -> None:
    """Every t=-2.4 has p about.0196>.0125, so step 1 fails and all subsequent tests must be retained.

    Without the stop, the last step would compare .0196<.05 and reject.
    """

    # Smallest p at step 1 is above 0.0125: t = -2.4 gives p about 0.0196.
    eff = -2.4 * 0.10 / math.sqrt(60)
    ev = build(e2_effect={(200, "high"): eff, (50, "high"): eff, (200, "low"): eff, (50, "low"): eff})
    verdict = evaluate_jr5_verdict(ev)
    # All four p are about 0.0196: step 1 (0.0125) fails, so none is rejected; with
    # no step-down stop, step 4 would test 0.0196 < 0.05 and reject.
    assert "b" in failed(ev)
    assert verdict.red_queen_proved is False


def test_interval_inside_is_strict() -> None:
    """Inside means strictly inside: an interval touching a bound is not inside.

    A one-sided test at level alpha rejects only when its statistic passes the
    critical value, so a 90% bound equal to the margin is p = 0.05, not below.
    """

    assert Interval(1.8, 2.0).inside(1.8, 2.2) is False
    assert Interval(1.9, 2.2).inside(1.8, 2.2) is False
    assert Interval(1.8000001, 2.1999999).inside(1.8, 2.2) is True


# ---------------------------------------------------------------- typed outcomes


def test_load_outcome() -> None:
    """No E2 effect, outcross beats self: +0.10 at every rate plus 4 per unit rate, so the 95% interval at mu 0.05
    is above 0 and Spearman over the 3 x 60 values rises (one-sided p < 0.05)."""

    zero = {(200, "high"): 0.0, (50, "high"): 0.0, (200, "low"): 0.0, (50, "low"): 0.0}
    ev = build(e2_effect=zero, load_effect=0.10, load_slope=4.0)
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.outcome == "load_consistent"
    assert verdict.red_queen_proved is False


def test_diversity_outcome_when_no_window_excludes_zero() -> None:
    """E2 holds but both E4 effects are planted at 0: no window excludes 0, so diversity_without_rqd."""

    ev = build(e4={"host_effect": 0.0, "parasite_effect": 0.0})
    verdict = evaluate_jr5_verdict(ev)
    assert verdict.outcome == "diversity_without_rqd"
    assert verdict.red_queen_proved is False


# ---------------------------------------------------------------- refusals


def test_hand_set_flag_and_unknown_keys_are_refused() -> None:
    """No decision is taken from the input: a hand-set flag or an extra key is refused."""

    ev = positive()
    ev["red_queen_proved"] = True
    with pytest.raises(ConfigurationError, match="hand-set"):
        evaluate_jr5_verdict(ev)
    ev = positive()
    ev["runs"][0]["data"]["red_queen_proved"] = True
    raw.readdress(ev["runs"][0])
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(evaluate_jr5_verdict(positive()).to_dict(), ev)


def test_edited_run_without_new_address_is_refused() -> None:
    """Run records are content-addressed: changing a value without re-addressing the record is refused."""

    ev = positive()
    ev["runs"][10]["data"]["uniparental_counts"][2] += 1
    with pytest.raises(ConfigurationError, match="sha256"):
        evaluate_jr5_verdict(ev)


def test_unregistered_e4_window_or_input_sign_is_refused() -> None:
    """E4 windows and signs are pinned from the phase 6 lock; an extra window or an input sign is refused."""

    for extra in ({"other_window": 0.1}, {"expected_sign": 1}):
        ev = positive()
        for run in ev["runs"]:
            if "e4" in run["data"]:
                run["data"]["e4"].update(extra)
                raw.readdress(run)
                break
        with pytest.raises(ConfigurationError, match="unknown keys"):
            evaluate_jr5_verdict(ev)


def test_e4_signs_follow_the_phase6_lock_estimand() -> None:
    """Host effect = I(H now, P past) - I(H past, P past) falls when hosts resist past parasites; parasite effect
    = I(H now, P now) - I(H now, P past) rises when parasites track current hosts."""

    lock = (ROOT / "runs" / "rq-mechanism-v2" / "PHASE6_CONFIRM_LOCK.md").read_text(encoding="utf-8")
    assert "Host effect, parasites held at the past generation:" in lock
    assert "`I(hosts at the horizon, parasites at horizon - lag) - I(hosts at horizon - lag, parasites at horizon - lag)`" in lock
    assert "Parasite effect, hosts held at the horizon:" in lock
    assert dict(E4_WINDOW_SIGNS) == {"host_effect": -1, "parasite_effect": 1}


def test_sealed_lock_digests_match_prereg_section_9() -> None:
    """Section 9 selects five lock digests; full values must match the underlying sealed records, not an abbreviated suffix."""
    text = (PREREG_DIR / "PREREG.md").read_text(encoding="utf-8")
    for digest in SEALED_LOCK_DIGESTS.values():
        assert digest[:8] in text
    for name, filename in (("selfing_hold", "CLOSED_LOOP_HP_ARM01_SELFING_HOLD_RESULTS_20260926.md"),
                           ("mating_ledger", "CLOSED_LOOP_HP_ARM01_MATING_LEDGER_RESULTS_20260926.md")):
        lock = (ROOT / "docs/handoff" / filename).read_text()
        assert SEALED_LOCK_DIGESTS[f"{name}.design"] in lock
        assert SEALED_LOCK_DIGESTS[f"{name}.campaign"] in lock
    summary = json.loads((ROOT / "runs/rq-mechanism-v2/phase6-coevolution/summary.json").read_bytes())
    assert SEALED_LOCK_DIGESTS["rq_v2_phase6.summary_sha256"] == summary["summary_sha256"]


def test_e1_gate_record_needs_the_pinned_constants_sha_and_must_agree() -> None:
    """The phase 3 gate record must carry the pinned constants sha256 and match the fit recomputed here."""

    for sha in (None, "0" * 64):
        ev = positive()
        ev["e1_gate_record"] = raw.gate_record(passed=True, instrument_failure=False, sha=sha)
        with pytest.raises(ConfigurationError, match="constants_sha256"):
            evaluate_jr5_verdict(ev)
    ev = positive()
    ev["e1_gate_record"] = raw.gate_record(passed=False, instrument_failure=True)
    with pytest.raises(ConfigurationError, match="disagrees"):
        evaluate_jr5_verdict(ev)
    ev = positive()
    ev["e1_gate_record"]["passed"] = False  # body edited, digest not recomputed
    with pytest.raises(ConfigurationError, match="digest"):
        evaluate_jr5_verdict(ev)


def test_forged_verdict_record_is_refused() -> None:
    """The record must equal the verdict recomputed from the evidence."""

    ev = build(tax_minus_fixed=-0.2)
    record = evaluate_jr5_verdict(ev).to_dict()
    record["red_queen_proved"] = True
    record["conditions"]["d"] = True
    with pytest.raises(ConfigurationError, match="does not match"):
        verify_jr5_verdict(record, ev)


# ---------------------------------------------------------------- prereg pin


def test_prereg_is_pinned_and_shipped_copy_is_the_hashed_file() -> None:
    """The package copy of the constants is byte-identical to the locked file, whose sha the locked record lists."""

    record = json.loads((PREREG_DIR / "record.json").read_text(encoding="utf-8"))
    assert record["manifest"]["digest"] == PREREG_RECORD_DIGEST
    files = dict(record["manifest"]["files"])
    assert files["docs/prereg/jr5/jr5_prereg_constants.json"] == PREREG_CONSTANTS_SHA256
    shipped = ROOT / "src" / "codontrace" / "claimgate" / "data" / "jr5_prereg_constants.json"
    assert shipped.read_bytes() == (PREREG_DIR / "jr5_prereg_constants.json").read_bytes()
    assert len(jr5_run_grid()) == 3760  # budget.runs_total


def test_copied_edited_rehashed_prereg_is_refused(tmp_path: Path) -> None:
    """A copied prereg with widened E1 bounds, re-hashed into a new record, cannot be used.

    The claim path takes no prereg folder, and evidence that names the new
    record digest is refused because only the pinned digest is accepted.
    """

    from codontrace.preregistration.manifest import hash_plan

    root = tmp_path / "repo"
    shutil.copytree(PREREG_DIR, root / "docs" / "prereg" / "jr5")
    path = root / "docs" / "prereg" / "jr5" / "jr5_prereg_constants.json"
    k = json.loads(path.read_text(encoding="utf-8"))
    k["gate_e1"]["equivalence_bounds"] = {"0.5": [0.1, 100.0], "0.25": [0.1, 100.0]}
    path.write_text(json.dumps(k), encoding="utf-8")
    record = json.loads((PREREG_DIR / "record.json").read_text(encoding="utf-8"))
    swapped = hash_plan([p for p, _ in record["manifest"]["files"]], root=root, title=record["manifest"]["title"])
    assert swapped.digest != PREREG_RECORD_DIGEST
    for fn in (evaluate_jr5_verdict, verify_jr5_verdict, assert_jr5_red_queen_claim_allowed, audit_bundle):
        assert "prereg_dir" not in inspect.signature(fn).parameters
    ev = positive()
    ev["prereg_record_digest"] = swapped.digest
    with pytest.raises(ConfigurationError, match="pinned"):
        evaluate_jr5_verdict(ev)


# ---------------------------------------------------------------- auditor


def test_auditor_ban_cannot_be_lifted_by_a_caller_callable() -> None:
    """audit_bundle takes no exemption hook; a lambda that says yes cannot lift the ban."""

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["red_queen_proved"] = True
    assert audit_bundle(payload).achieved_level < _baseline_level()
    with pytest.raises(TypeError):
        audit_bundle(payload, red_queen_exemption=lambda e: True)  # type: ignore[call-arg]


def test_valid_verdict_stapled_onto_an_unrelated_bundle_is_refused() -> None:
    """A genuine positive lifts the ban only on the bundle it is bound to (prereg digest, seeds, evidence digest)."""

    ev = positive()
    good = bound_bundle(ev)
    assert audit_bundle(good).achieved_level >= _baseline_level()
    stapled = json.loads(FIXTURE.read_text(encoding="utf-8"))
    stapled.update({"red_queen_proved": True, "jr5_evidence": good["jr5_evidence"], "jr5_verdict": good["jr5_verdict"]})
    assert audit_bundle(stapled).achieved_level < _baseline_level()
    for key, value in (("preregistration_digest", "0" * 64), ("seeds", [1, 2, 3]), ("artifacts", stapled["artifacts"])):
        bad = deepcopy(good)
        bad[key] = value
        assert audit_bundle(bad).achieved_level < _baseline_level()


def test_host_parasite_profile_gate_still_refuses() -> None:
    """The host-parasite profile gate is unchanged and keeps refusing the flag."""

    with pytest.raises(ConfigurationError):
        assert_claim_allowed("red_queen_proved")
