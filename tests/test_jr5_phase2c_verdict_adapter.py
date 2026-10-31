"""JR5 phase 2c: the verdict adapter is the only path to ``red_queen_proved``.

The inputs are planted summary statistics, not engine runs. Every planted
number is chosen against a bound that the prereg fixes in
``docs/prereg/jr5/jr5_prereg_constants.json`` and ``RED_QUEEN_CLAIM_PATH.md``,
so each expected outcome follows from the preregistered rule and not from the
adapter's own code:

- E1 bounds: theory 1/(1 - m) is 2.0 at m = 0.5 and 4/3 at m = 0.25; the TOST
  bounds are +-10% of that, [1.8, 2.2] and [1.2, 1.4667].
- E2 Holm: four tests at family alpha 0.05, so step k uses 0.05 / (5 - k):
  0.0125, 0.01667, 0.025, 0.05, with BCa levels 98.75 / 98.333 / 97.5 / 95%.
- Condition (c): one-sided 0.025 and a two-sided 95% BCa interval.
- Condition (d): equivalence margins +-0.10 (frequency) and +-log 1.1 = 0.0953
  (log fitness ratio), or a 95% interval on the side opposite the effect.
- Condition (e): replay digests equal, one-shot body equal to resumed body,
  ATP ledger residual at most 1e-9.

The planted RQ signal sits well inside every bound, so a single change pushes
exactly one condition over its bound.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.claimgate.adapters.jr5_verdict import (
    Jr5Evidence,
    assert_jr5_red_queen_claim_allowed,
    audit_bundle_with_jr5_verdict,
    evaluate_jr5_verdict,
    verify_jr5_verdict,
)
from codontrace.errors import ConfigurationError

ROOT = Path(__file__).resolve().parents[1]
PREREG_DIR = ROOT / "docs" / "prereg" / "jr5"
FIXTURE = ROOT / "tests" / "fixtures" / "claimgate" / "level2_difference.json"

# Holm step levels for the four E2 tests (family alpha 0.05).
LEVELS = (0.9875, 0.9833333333333333, 0.975, 0.95)


def _record_digest() -> str:
    data: dict[str, Any] = json.loads((PREREG_DIR / "record.json").read_text(encoding="utf-8"))
    return str(data["manifest"]["digest"])


def _contrast(est: float, p: float, half90: float, half95: float, n: int = 60) -> dict[str, Any]:
    """A paired contrast whose BCa intervals are centred like the t intervals.

    The BCa half-width grows with the level (98.75% widest). With these
    plants the BCa interval agrees with the t test, as the prereg requires
    for a test to count.
    """

    bca = {repr(lv): [est - half95 * (1 + (lv - 0.95) * 10), est + half95 * (1 + (lv - 0.95) * 10)] for lv in LEVELS}
    return {
        "n_seeds": n,
        "estimate": est,
        "p_two_sided": p,
        "ci90": [est - half90, est + half90],
        "ci95": [est - half95, est + half95],
        "bca": bca,
    }


def _replay(run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "expected_digest": "d" * 64,
        "replayed_digest": "d" * 64,
        "one_shot_body_sha256": "b" * 64,
        "resumed_body_sha256": "b" * 64,
        "atp_ledger_residual": 0.0,
    }


def planted_rq() -> dict[str, Any]:
    """A full Red Queen signal: (a) to (e) hold with room to spare."""

    return {
        "prereg_record_digest": _record_digest(),
        "e1": [
            # Centred on 2.0 and 4/3, inside [1.8, 2.2] and [1.2, 1.4667];
            # the 95% intervals are far above 1.
            {"sex_ratio": 0.5, "n_populations": 40, "n_excluded": 0, "ci90": [1.92, 2.08], "ci95": [1.90, 2.10]},
            {"sex_ratio": 0.25, "n_populations": 40, "n_excluded": 1, "ci90": [1.29, 1.38], "ci95": [1.28, 1.39]},
        ],
        "e2": {
            # High virulence: copassaged 0.25 below fixed, p far below 0.0125.
            "e2_N200_high": _contrast(-0.25, 1e-6, 0.05, 0.06),
            "e2_N50_high": _contrast(-0.20, 1e-4, 0.06, 0.07),
            # Low virulence: no effect, 95% interval spans 0.
            "e2_N200_low": _contrast(-0.01, 0.60, 0.03, 0.04),
            "e2_N50_low": _contrast(0.01, 0.70, 0.03, 0.04),
        },
        "copassaged_minus_fixed": _contrast(-0.25, 1e-6, 0.05, 0.06),
        "copassaged_minus_frozen": _contrast(-0.22, 1e-5, 0.05, 0.06),
        # Load: outcross-minus-self log ratio 0.00 +- 0.05, inside +-0.0953.
        "load": {"at_mu_005": _contrast(0.0, 0.9, 0.05, 0.06), "spearman_rho": 0.0, "spearman_p_one_sided": 0.5},
        # Diversity and tax: 0.00 +- 0.05, inside +-0.10.
        "frozen_minus_fixed": _contrast(0.0, 0.9, 0.05, 0.06),
        "tax_minus_fixed": _contrast(0.0, 0.9, 0.05, 0.06),
        "time_shift_windows": [{"name": "host_past_vs_contemporary", "ci95": [-0.20, -0.05], "expected_sign": -1}],
        "runs": [_replay("e2_N200_high_13001")],
        "sealed_locks": [_replay("selfing_hold"), _replay("mating_ledger")],
    }


def _verdict(ev: dict[str, Any]) -> Any:
    return evaluate_jr5_verdict(ev, prereg_dir=PREREG_DIR)


def test_planted_rq_signal_proves_the_claim() -> None:
    v = _verdict(planted_rq())
    assert v.outcome == "rq_consistent"
    assert dict(v.conditions) == {"a": True, "b": True, "c": True, "d": True, "e": True}
    assert v.red_queen_proved is True
    assert v.prereg_record_digest == _record_digest()


def _set(ev: dict[str, Any], path: tuple[Any, ...], value: Any) -> dict[str, Any]:
    out = deepcopy(ev)
    node = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return out


# One failed condition each, the other four left as planted. The comment says
# which bound is crossed.
SINGLE_FAILURES = {
    # (a) upper end 2.25 is above the TOST bound 2.2.
    "a_tost_upper": ((("e1", 0, "ci90"), [1.95, 2.25]), "a"),
    # (a) 95% interval at m = 0.25 reaches 1, so it does not exclude 1.
    "a_excludes_one": ((("e1", 1, "ci95"), [0.99, 1.39]), "a"),
    # (a) 9 of 40 excluded is above the 20% cap (8).
    "a_cap": ((("e1", 0, "n_excluded"), 9), "a"),
    # (b) N50 high p = 0.03 is above every Holm step it can reach (step 2: 0.01667).
    "b_n50_holm": ((("e2", "e2_N50_high"), _contrast(-0.20, 0.03, 0.06, 0.20)), "b"),
    # (c) copassaged-minus-frozen not below 0: p = 0.4, 95% BCa spans 0.
    "c_frozen": ((("copassaged_minus_frozen",), _contrast(-0.02, 0.4, 0.05, 0.06)), "c"),
    # (d) load: 90% interval [-0.05, 0.15] leaves +-0.0953 and 95% is not below 0.
    "d_load": ((("load", "at_mu_005"), _contrast(0.05, 0.2, 0.10, 0.12)), "d"),
    # (d) diversity: no window excludes 0 with the cycling sign.
    "d_windows": ((("time_shift_windows",), [{"name": "w", "ci95": [-0.1, 0.1], "expected_sign": -1}]), "d"),
    # (d) tax: 90% [-0.15, 0.05] leaves +-0.10; non-significance does not rule it out.
    "d_tax": ((("tax_minus_fixed",), _contrast(-0.05, 0.2, 0.10, 0.12)), "d"),
    # (e) one replay digest differs.
    "e_digest": ((("runs", 0, "replayed_digest"), "e" * 64), "e"),
    # (e) ledger residual 2e-9 is above 1e-9.
    "e_ledger": ((("runs", 0, "atp_ledger_residual"), 2e-9), "e"),
    # (e) resumed body differs from one-shot body.
    "e_resume": ((("sealed_locks", 1, "resumed_body_sha256"), "c" * 64), "e"),
}


@pytest.mark.parametrize("name", sorted(SINGLE_FAILURES))
def test_each_single_failed_condition_keeps_the_flag_false(name: str) -> None:
    (path, value), cond = SINGLE_FAILURES[name]
    ev = _set(planted_rq(), path, value)
    v = _verdict(ev)
    assert v.red_queen_proved is False
    assert v.conditions[cond] is False
    assert [k for k, ok in v.conditions.items() if not ok] == [cond]
    record = v.to_dict()
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(record, ev, prereg_dir=PREREG_DIR)


def test_cost_gate_or_replay_failure_is_instrument_fail() -> None:
    # PREREG section 2: E1 failure or a section 8 validity failure is instrument_fail.
    for key in ("a_tost_upper", "a_cap", "e_ledger"):
        (path, value), _ = SINGLE_FAILURES[key]
        assert _verdict(_set(planted_rq(), path, value)).outcome == "instrument_fail"


def test_planted_load_alternative() -> None:
    # No E2 effect (p = 0.5, intervals span 0); outcross beats self by log 0.2
    # with 95% interval [0.14, 0.26] above 0 and a rising trend (rho 0.4, p 0.001).
    ev = planted_rq()
    for name in ("e2_N200_high", "e2_N50_high"):
        ev["e2"][name] = _contrast(-0.01, 0.5, 0.04, 0.05)
    ev["copassaged_minus_fixed"] = _contrast(-0.01, 0.5, 0.04, 0.05)
    ev["copassaged_minus_frozen"] = _contrast(0.0, 0.9, 0.04, 0.05)
    ev["load"] = {"at_mu_005": _contrast(0.2, 1e-6, 0.05, 0.06), "spearman_rho": 0.4, "spearman_p_one_sided": 0.001}
    v = _verdict(ev)
    assert (v.outcome, v.red_queen_proved) == ("load_consistent", False)


def test_planted_diversity_without_cycles() -> None:
    # E2 effect as planted, but frozen replay does as well as copassaged
    # (copassaged-minus-frozen 0.00 +- 0.05 inside +-0.10) and no window excludes 0.
    ev = planted_rq()
    ev["copassaged_minus_frozen"] = _contrast(0.0, 0.9, 0.05, 0.06)
    ev["time_shift_windows"] = [{"name": "w", "ci95": [-0.05, 0.05], "expected_sign": -1}]
    v = _verdict(ev)
    assert (v.outcome, v.red_queen_proved) == ("diversity_without_rqd", False)


def test_planted_fitness_tax_reproduces_effect() -> None:
    # The genotype-blind tax gives the same drop as copassaged (-0.25, 95% below 0),
    # so the effect is not shown to need coevolution: no RQ outcome.
    ev = planted_rq()
    ev["tax_minus_fixed"] = _contrast(-0.25, 1e-6, 0.05, 0.06)
    v = _verdict(ev)
    assert (v.outcome, v.red_queen_proved) == ("none", False)
    assert v.conditions["d"] is False


def test_planted_null_gives_none() -> None:
    # Nothing differs anywhere: E2 null and no load advantage.
    ev = planted_rq()
    for name in ("e2_N200_high", "e2_N50_high"):
        ev["e2"][name] = _contrast(0.0, 0.9, 0.04, 0.05)
    ev["copassaged_minus_fixed"] = _contrast(0.0, 0.9, 0.04, 0.05)
    ev["copassaged_minus_frozen"] = _contrast(0.0, 0.9, 0.04, 0.05)
    v = _verdict(ev)
    assert (v.outcome, v.red_queen_proved) == ("none", False)


def test_t_and_bca_disagreement_is_inconclusive() -> None:
    # Agreement rule: N200 high t test p = 1e-6, but its BCa interval spans 0.
    ev = planted_rq()
    c = _contrast(-0.25, 1e-6, 0.05, 0.06)
    c["bca"] = {repr(lv): [-0.3, 0.02] for lv in LEVELS}
    ev["e2"]["e2_N200_high"] = c
    v = _verdict(ev)
    assert (v.outcome, v.red_queen_proved) == ("inconclusive", False)


def test_holm_uses_the_step_level_not_the_raw_alpha() -> None:
    # p = 0.02 for N50 high would pass a raw 0.05 test. Sorted second of four,
    # Holm tests it at 0.05 / 3 = 0.01667, so it is retained and (b) fails.
    ev = planted_rq()
    ev["e2"]["e2_N50_high"] = _contrast(-0.20, 0.02, 0.06, 0.30)
    v = _verdict(ev)
    assert v.conditions["b"] is False
    # Just under the step-2 level it passes: 0.0166 < 0.01667.
    ev["e2"]["e2_N50_high"] = _contrast(-0.20, 0.0166, 0.06, 0.07)
    assert _verdict(ev).conditions["b"] is True


def test_effect_in_the_wrong_direction_is_not_rq() -> None:
    # Copassaged higher than fixed (+0.25): significant but against the prediction.
    ev = planted_rq()
    for name in ("e2_N200_high", "e2_N50_high"):
        ev["e2"][name] = _contrast(0.25, 1e-6, 0.05, 0.06)
    v = _verdict(ev)
    assert v.conditions["b"] is False
    assert v.red_queen_proved is False


def test_hand_set_flag_and_unknown_keys_are_refused() -> None:
    ev = planted_rq()
    ev["red_queen_proved"] = True
    with pytest.raises(ConfigurationError, match="hand-set"):
        _verdict(ev)
    ev = planted_rq()
    ev["e2"]["e2_N200_high"]["red_queen_proved"] = True
    with pytest.raises(ConfigurationError, match="hand-set"):
        _verdict(ev)
    ev = planted_rq()
    ev["outcome"] = "rq_consistent"
    with pytest.raises(ConfigurationError, match="unknown keys"):
        _verdict(ev)


def test_forged_or_foreign_records_are_refused() -> None:
    ev = planted_rq()
    good = _verdict(ev).to_dict()
    assert assert_jr5_red_queen_claim_allowed(good, ev, prereg_dir=PREREG_DIR) == "red_queen_proved"
    # A failing evidence set with a copied passing record: recomputation differs.
    bad_ev = _set(ev, ("runs", 0, "replayed_digest"), "e" * 64)
    with pytest.raises(ConfigurationError, match="does not match"):
        verify_jr5_verdict(good, bad_ev, prereg_dir=PREREG_DIR)
    # A flag flipped by hand on a failing record.
    forged = _verdict(bad_ev).to_dict()
    forged["red_queen_proved"] = True
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(forged, bad_ev, prereg_dir=PREREG_DIR)
    # Evidence produced under another prereg record digest.
    with pytest.raises(ConfigurationError, match="different JR5 prereg"):
        _verdict(_set(ev, ("prereg_record_digest",), "0" * 64))


def test_design_counts_must_match_the_prereg() -> None:
    # 40 populations per E1 cell and 60 paired seeds per contrast are preregistered.
    with pytest.raises(ConfigurationError):
        _verdict(_set(planted_rq(), ("e1", 0, "n_populations"), 39))
    with pytest.raises(ConfigurationError):
        _verdict(_set(planted_rq(), ("tax_minus_fixed", "n_seeds"), 40))


def test_tampered_prereg_folder_is_refused(tmp_path: Path) -> None:
    # Thresholds come only from the hashed prereg: an edited constants file
    # no longer matches record.json and the adapter stops.
    dst = tmp_path / "docs" / "prereg" / "jr5"
    dst.mkdir(parents=True)
    for p in PREREG_DIR.rglob("*"):
        if p.is_file():
            out = dst / p.relative_to(PREREG_DIR)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(p.read_bytes())
    assert evaluate_jr5_verdict(planted_rq(), prereg_dir=dst).red_queen_proved is True
    path = dst / "jr5_prereg_constants.json"
    path.write_text(path.read_text(encoding="utf-8").replace('"family_alpha": 0.05', '"family_alpha": 0.5'))
    with pytest.raises(ConfigurationError, match="do not match"):
        evaluate_jr5_verdict(planted_rq(), prereg_dir=dst)


def test_profile_gate_still_refuses_every_other_caller() -> None:
    # assert_claim_allowed is unchanged: the JR5 path is a separate check.
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("red_queen_proved")


def test_auditor_ban_lifts_only_for_a_verified_jr5_verdict() -> None:
    # The auditor ban holds for a plain audit_bundle call even with a passing
    # record; only the JR5 adapter's audit path lifts it, and only for a
    # record that recomputes from its evidence with (a) to (e) true.
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    baseline = audit_bundle(payload).achieved_level
    ev = planted_rq()
    marked = deepcopy(payload)
    marked["red_queen_proved"] = True
    assert audit_bundle(marked).achieved_level < baseline
    marked["jr5_evidence"] = ev
    marked["jr5_verdict"] = _verdict(ev).to_dict()
    assert audit_bundle(marked).achieved_level < baseline
    assert audit_bundle_with_jr5_verdict(marked, prereg_dir=PREREG_DIR).achieved_level == baseline
    # A failing verdict, or a passing record over failing evidence, keeps the ban.
    bad_ev = _set(ev, ("runs", 0, "atp_ledger_residual"), 1e-6)
    for record, evidence in ((_verdict(bad_ev).to_dict(), bad_ev), (marked["jr5_verdict"], bad_ev)):
        again = deepcopy(marked)
        again["jr5_evidence"] = evidence
        again["jr5_verdict"] = record
        assert audit_bundle_with_jr5_verdict(again, prereg_dir=PREREG_DIR).achieved_level < baseline
    # Without the JR5 fields the adapter path grades like the plain auditor.
    plain = deepcopy(payload)
    plain["red_queen_proved"] = True
    assert audit_bundle_with_jr5_verdict(plain, prereg_dir=PREREG_DIR).achieved_level < baseline


def test_planted_margins_match_the_prereg_constants() -> None:
    # Ties the comments above to the JSON, so a prereg change shows up here.
    c = json.loads((PREREG_DIR / "jr5_prereg_constants.json").read_text(encoding="utf-8"))
    assert c["gate_e1"]["equivalence_bounds"]["0.5"] == [1.8, 2.2]
    assert c["gate_e1"]["equivalence_bounds"]["0.25"] == pytest.approx([1.2, 1.1 * 4 / 3])
    assert c["condition_d"]["margin_log_fitness_ratio"] == pytest.approx(math.log(1.1))
    assert c["condition_d"]["margin_frequency"] == 0.1
    assert c["e2"]["bootstrap"]["ci_level_by_holm_step"] == pytest.approx([1 - 0.05 / (4 - k) for k in range(4)])
    assert c["validity"]["atp_ledger_max_residual"] == 1e-9
    assert Jr5Evidence.from_dict(planted_rq()).digest().startswith("jr5-evidence:")


def _wide(est: float, p: float) -> dict[str, Any]:
    """A contrast whose BCa intervals all span 0 (half-width 0.3 at 95%)."""

    return _contrast(est, p, 0.2, 0.3)


def test_holm_stops_at_the_first_retained_step() -> None:
    # Smallest p 0.013 fails step 1 (0.0125). Holm then retains every later
    # test, including N50 high at p 0.014 that alone would pass step 2
    # (0.01667). Both BCa intervals span 0, so t and BCa agree: (b) fails and
    # the outcome is not inconclusive.
    ev = planted_rq()
    ev["e2"]["e2_N200_high"] = _wide(-0.10, 0.013)
    ev["e2"]["e2_N50_high"] = _wide(-0.10, 0.014)
    v = _verdict(ev)
    assert v.conditions["b"] is False
    assert v.outcome == "none"


def test_holm_retained_test_with_a_significant_bca_is_inconclusive() -> None:
    # N50 high p = 0.02 is above its step-2 level 0.01667, but its 98.333%
    # BCa interval [-0.27, -0.13] excludes 0: one rejects, one does not, so
    # the agreement rule gives inconclusive.
    ev = planted_rq()
    ev["e2"]["e2_N50_high"] = _contrast(-0.20, 0.02, 0.05, 0.06)
    v = _verdict(ev)
    assert (v.outcome, v.conditions["b"], v.red_queen_proved) == ("inconclusive", False, False)


def test_condition_c_is_one_sided_at_0_025() -> None:
    # Two-sided p 0.06 is one-sided 0.03, above 0.025; the 95% BCa spans 0,
    # so both say not significant: (c) fails without disagreement. The other
    # rq_consistent rules still hold, so the typed outcome stays rq_consistent
    # while the flag is False.
    ev = planted_rq()
    ev["copassaged_minus_fixed"] = _wide(-0.10, 0.06)
    v = _verdict(ev)
    assert v.conditions["c"] is False
    assert (v.outcome, v.red_queen_proved) == ("rq_consistent", False)


def test_window_with_the_wrong_sign_does_not_count() -> None:
    # The only window excludes 0 but on the side opposite to the sign that
    # cycling predicts, so no registered window supports cycling.
    ev = planted_rq()
    ev["time_shift_windows"] = [{"name": "w", "ci95": [0.05, 0.20], "expected_sign": -1}]
    v = _verdict(ev)
    assert v.conditions["d"] is False
    assert v.outcome == "diversity_without_rqd"


def test_load_above_zero_is_not_ruled_out() -> None:
    # Outcross beats self by log 0.2 with 95% interval [0.14, 0.26]: that is
    # the load signature, not its absence. Only a 95% interval below 0 or
    # equivalence inside +-0.0953 rules load out.
    ev = planted_rq()
    ev["load"]["at_mu_005"] = _contrast(0.2, 1e-6, 0.05, 0.06)
    v = _verdict(ev)
    assert v.conditions["d"] is False
    assert v.red_queen_proved is False
    # A 95% interval entirely below 0 does rule load out.
    ev["load"]["at_mu_005"] = _contrast(-0.2, 1e-6, 0.05, 0.06)
    assert _verdict(ev).conditions["d"] is True


# ---------------------------------------------------------------- raw-data pair
#
# The pair below starts from synthetic per-seed values, not from intervals.
# Intervals and p-values are computed the way the prereg says the analysis
# computes them: a one-sample t interval on the log scale for E1, a paired t
# test and a paired BCa bootstrap (10,000 resamples, seed 12345) for every
# contrast. The adapter then decides from those numbers.
#
# Where the planted values come from (all N = 200):
# - E1: per-population log w drawn around log 2 and log 4/3 with SD 0.077 and
#   0.050, the first-pass SDs in PREREG section 7. With 40 populations the 90%
#   half-width is about 1.685 * 0.077 / sqrt(40) = 0.021 on the log scale,
#   well inside the margin -0.105 / +0.095.
# - E2 high virulence: paired differences around -0.25 with SD 0.30, the
#   pessimistic case of the E2 power section (20 seeds give 80% power). With
#   60 seeds the t statistic is near -6.5, far past the first Holm step.
# - Low virulence, load, diversity and tax: mean 0 with SD 0.25. With 60
#   seeds the 90% half-width is about 1.671 * 0.25 / sqrt(60) = 0.054, inside
#   +-0.10 and +-0.0953 (equivalence power 0.84 at SD 0.25 in PREREG).
# - Time-shift window: effect -0.10 with SD 0.20 over 60 seeds, so the 95%
#   interval sits near [-0.15, -0.05], below 0 as cycling predicts.
# Each draw is rescaled to its exact sample mean and SD, so these figures are
# exact for the data used, not expected values over draws.
# The failing set is the same draw with the copassaged effect removed (mean
# 0 instead of -0.25): the E2 tests are then null, so (b) fails and the flag
# must be False. Nothing else changes.


def _raw_evidence(copassaged_effect: float) -> dict[str, Any]:
    np = pytest.importorskip("numpy")
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(20261101)

    def draw(mean: float, sd: float, n: int) -> Any:
        # Normal draws rescaled to the exact planted sample mean and SD, so the
        # intervals below follow from the stated numbers and not from the draw.
        z = rng.normal(0.0, 1.0, n)
        z = (z - z.mean()) / z.std(ddof=1)
        return mean + sd * z

    def t_interval(x: Any, level: float) -> list[float]:
        m, se = float(np.mean(x)), float(stats.sem(x))
        h = float(stats.t.ppf(0.5 + level / 2, len(x) - 1)) * se
        return [m - h, m + h]

    def paired(d: Any) -> dict[str, Any]:
        bca = {}
        for lv in LEVELS:
            res = stats.bootstrap(
                (d,), np.mean, confidence_level=lv, n_resamples=10_000, method="BCa", random_state=12345
            )
            bca[repr(lv)] = [float(res.confidence_interval.low), float(res.confidence_interval.high)]
        return {
            "n_seeds": len(d),
            "estimate": float(np.mean(d)),
            "p_two_sided": float(stats.ttest_1samp(d, 0.0).pvalue),
            "ci90": t_interval(d, 0.90),
            "ci95": t_interval(d, 0.95),
            "bca": bca,
        }

    e1 = []
    for ratio, theory, sd in ((0.5, 2.0, 0.077), (0.25, 4 / 3, 0.050)):
        logw = draw(math.log(theory), sd, 40)
        e1.append(
            {
                "sex_ratio": ratio,
                "n_populations": 40,
                "n_excluded": 0,
                "ci90": [math.exp(v) for v in t_interval(logw, 0.90)],
                "ci95": [math.exp(v) for v in t_interval(logw, 0.95)],
            }
        )
    high200 = draw(copassaged_effect, 0.30, 60)
    window = draw(-0.10, 0.20, 60)
    load = draw(0.0, 0.25, 60)
    return {
        "prereg_record_digest": _record_digest(),
        "e1": e1,
        "e2": {
            "e2_N200_high": paired(high200),
            "e2_N50_high": paired(draw(copassaged_effect, 0.30, 60)),
            "e2_N200_low": paired(draw(0.0, 0.25, 60)),
            "e2_N50_low": paired(draw(0.0, 0.25, 60)),
        },
        "copassaged_minus_fixed": paired(high200),
        "copassaged_minus_frozen": paired(draw(copassaged_effect, 0.30, 60)),
        "load": {
            "at_mu_005": paired(load),
            "spearman_rho": 0.0,
            "spearman_p_one_sided": 0.5,
        },
        "frozen_minus_fixed": paired(draw(0.0, 0.25, 60)),
        "tax_minus_fixed": paired(draw(0.0, 0.25, 60)),
        "time_shift_windows": [
            {"name": "host_past_vs_contemporary", "ci95": t_interval(window, 0.95), "expected_sign": -1}
        ],
        "runs": [_replay("e2_N200_high_13001")],
        "sealed_locks": [_replay("selfing_hold"), _replay("mating_ledger")],
    }


def test_raw_dataset_meeting_the_prereg_proves_the_claim() -> None:
    ev = _raw_evidence(-0.25)
    v = _verdict(ev)
    assert dict(v.conditions) == {"a": True, "b": True, "c": True, "d": True, "e": True}
    assert (v.outcome, v.red_queen_proved) == ("rq_consistent", True)
    # The verified record also passes the claim check and the auditor ban.
    assert assert_jr5_red_queen_claim_allowed(v.to_dict(), ev, prereg_dir=PREREG_DIR) == "red_queen_proved"


def test_raw_dataset_failing_the_prereg_keeps_the_flag_false() -> None:
    ev = _raw_evidence(0.0)
    v = _verdict(ev)
    assert v.red_queen_proved is False
    assert v.conditions["a"] is True and v.conditions["e"] is True
    assert v.conditions["b"] is False
    with pytest.raises(ConfigurationError):
        assert_jr5_red_queen_claim_allowed(v.to_dict(), ev, prereg_dir=PREREG_DIR)
