"""General power analysis and its use in the ClaimGate auditor."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.power import (
    minimum_detectable_effect,
    power_t_test,
    power_two_proportions,
    sample_size_t_test,
    sample_size_two_proportions,
    simulate_power,
    t_cdf,
    t_ppf,
)
from codontrace.errors import ConfigurationError

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "claimgate"


def test_cohen_1988_and_gpower_sample_sizes():
    # Two-sample, two-sided, alpha .05, power .80. Cohen (1988) Table 2.4.1
    # gives 26 and 64 per group; G*Power 3 (Faul et al. 2007) gives 394 for
    # d = 0.2 (Cohen's table rounds to 393).
    assert sample_size_t_test(0.8, kind="two_sample") == 26
    assert sample_size_t_test(0.5, kind="two_sample") == 64
    assert sample_size_t_test(0.2, kind="two_sample") == 394
    # Paired d_z = 0.5: 34 pairs (G*Power).
    assert sample_size_t_test(0.5, kind="paired") == 34


def test_t_distribution_matches_known_quantiles():
    assert t_ppf(0.975, 10) == pytest.approx(2.228138852, abs=1e-8)
    assert t_ppf(0.95, 1) == pytest.approx(6.313751515, abs=1e-7)
    assert t_cdf(0.0, 7) == pytest.approx(0.5)


@settings(max_examples=60, deadline=None)
@given(
    d=st.floats(0.0, 2.5),
    n=st.integers(3, 120),
    kind=st.sampled_from(["paired", "two_sample"]),
    alt=st.sampled_from(["two-sided", "greater"]),
)
def test_power_matches_scipy_noncentral_t(d, n, kind, alt):
    stats = pytest.importorskip("scipy.stats")
    df = 2 * n - 2 if kind == "two_sample" else n - 1
    ncp = d * math.sqrt(n / 2) if kind == "two_sample" else d * math.sqrt(n)
    if alt == "greater":
        ref = stats.nct.sf(stats.t.ppf(0.95, df), df, ncp)
    else:
        c = stats.t.ppf(0.975, df)
        ref = stats.nct.sf(c, df, ncp) + stats.nct.cdf(-c, df, ncp)
    assume(math.isfinite(ref))  # scipy 1.18 nct returns nan far in the tail
    assert power_t_test(d, n, kind=kind, alternative=alt) == pytest.approx(ref, abs=1e-7)


def test_power_is_alpha_at_zero_effect_and_monotone():
    assert power_t_test(0.0, 20) == pytest.approx(0.05, abs=1e-9)
    ps = [power_t_test(0.4, n) for n in (5, 10, 20, 40)]
    assert ps == sorted(ps)
    mde = minimum_detectable_effect(16)
    assert power_t_test(mde, 16) == pytest.approx(0.8, abs=1e-6)


def test_two_proportions_cohen_h():
    # Cohen (1988) ch. 6: h = 0.5 needs n = 63 per group (normal approximation).
    p1 = math.sin(math.asin(math.sqrt(0.5)) + 0.25) ** 2
    assert sample_size_two_proportions(p1, 0.5) == 63
    assert power_two_proportions(0.5, 0.5, 50) == pytest.approx(0.05)


def test_simulation_power_agrees_with_exact_power():
    from statistics import NormalDist, fmean, stdev

    def trial(rng):
        nd = NormalDist()
        xs = [nd.inv_cdf(min(max(rng.random(), 1e-12), 1 - 1e-12)) + 0.5 for _ in range(16)]
        t = fmean(xs) / (stdev(xs) / 4.0)
        return abs(t) > t_ppf(0.975, 15)

    est = simulate_power(trial, n_sim=2000, seed=3)
    assert est.ci_low <= power_t_test(0.5, 16) <= est.ci_high
    assert simulate_power(trial, n_sim=50, seed=3) == simulate_power(trial, n_sim=50, seed=3)


def test_invalid_inputs():
    with pytest.raises(ConfigurationError):
        power_t_test(0.5, 1)
    with pytest.raises(ConfigurationError):
        power_t_test(0.5, 10, kind="anova")
    with pytest.raises(ConfigurationError):
        sample_size_t_test(0.0)


def _level4_payload():
    payload = json.loads((FIXTURES / "level2_difference.json").read_text(encoding="utf-8"))
    payload["arms"].append({"name": "off_gate", "role": "mechanism_ablation", "n": 3})
    payload["arms"].append({"name": "shuffled", "role": "negative_control", "n": 3})
    payload["replay"] = {"verified": True, "digests": ["d" * 64]}
    payload["seeds"] = list(range(16))
    payload["arms"][0]["n"] = 16
    payload["doi"] = "10.5281/zenodo.99999999"
    return payload


def test_claimgate_unchanged_without_declared_power():
    report = audit_bundle(_level4_payload())
    assert report.achieved_level == 5
    assert not any(w.startswith("power_analysis") for w in report.warnings)


def test_claimgate_caps_underpowered_declared_design():
    payload = _level4_payload()
    payload["power_analysis"] = {"effect_size": 0.5, "test": "paired"}
    report = audit_bundle(payload)
    # 16 seeds give power 0.465 for d_z = 0.5: not a replicated effect.
    assert report.achieved_level == 3
    assert report.missing_for_next == ("adequate_power",)
    assert "underpowered_for_declared_effect" in report.warnings
    assert any("power=0.465" in w for w in report.warnings)


def test_claimgate_accepts_adequately_powered_declared_design():
    payload = _level4_payload()
    payload["power_analysis"] = {"effect_size": 0.8, "test": "paired"}
    report = audit_bundle(payload)
    assert report.achieved_level == 5
    assert "underpowered_for_declared_effect" not in report.warnings


def test_claimgate_malformed_power_declaration_fails_closed():
    payload = _level4_payload()
    payload["power_analysis"] = {"test": "paired"}
    report = audit_bundle(payload)
    assert report.achieved_level == 3
    assert "power_analysis_invalid:KeyError" in report.warnings
