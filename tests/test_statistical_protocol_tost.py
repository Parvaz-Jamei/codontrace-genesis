"""Known-value checks for the one-sample TOST in the engine stats section.

Expected values are hand-derived from closed forms of Student's t:
df = 1 is the Cauchy law, P(T > t) = 1/2 - atan(t)/pi, and
df = 2 has P(T > t) = (1 - t / sqrt(2 + t^2)) / 2. Quantiles come from
inverting those two forms. scipy, when installed, is only a cross-check.
"""

from __future__ import annotations

import math

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.statistical_protocol import (
    one_sample_t_interval,
    one_sample_tost,
    student_t_sf,
)


def _sf_df2(t: float) -> float:
    return 0.5 * (1.0 - t / math.sqrt(2.0 + t * t))


def test_student_t_sf_matches_closed_forms() -> None:
    # df = 1: P(T > 1) = 1/2 - atan(1)/pi = 1/4 exactly.
    assert student_t_sf(1.0, 1) == pytest.approx(0.25, abs=1e-12)
    # df = 2 closed form at a few points, and symmetry P(T > -t) = 1 - P(T > t).
    for t in (0.5, 1.0, 2.0, 3.4641016151377544):
        assert student_t_sf(t, 2) == pytest.approx(_sf_df2(t), abs=1e-12)
        assert student_t_sf(-t, 2) == pytest.approx(1.0 - _sf_df2(t), abs=1e-12)
    assert student_t_sf(0.0, 7) == pytest.approx(0.5, abs=1e-15)
    assert student_t_sf(math.inf, 3) == 0.0
    assert student_t_sf(-math.inf, 3) == 1.0


def test_tost_hand_derived_df2_not_equivalent() -> None:
    # [1, 2, 3]: mean 2, SD 1, SE 1/sqrt(3).
    # t_lower = (2 - 0) * sqrt(3) = 3.4641, p_lower = (1 - 3.4641/sqrt(14)) / 2 = 0.03709.
    # t_upper = (2 - 3) * sqrt(3) = -1.7321, p_upper = (1 - sqrt(3)/sqrt(5)) / 2 = 0.11270.
    # p_upper > 0.05, so not equivalent. The 90% interval uses t(0.95, 2),
    # from the df = 2 form: t^2 = 2 * 0.9^2 / (1 - 0.9^2), t = 2.919986, so the
    # half-width is 2.919986 / sqrt(3) = 1.685854 and the interval crosses 3.
    r = one_sample_tost([1.0, 2.0, 3.0], 0.0, 3.0, alpha=0.05)
    assert r.t_lower == pytest.approx(2.0 * math.sqrt(3.0))
    assert r.t_upper == pytest.approx(-math.sqrt(3.0))
    assert r.p_lower == pytest.approx(0.5 * (1.0 - math.sqrt(12.0) / math.sqrt(14.0)), abs=1e-10)
    assert r.p_upper == pytest.approx(0.5 * (1.0 - math.sqrt(3.0) / math.sqrt(5.0)), abs=1e-10)
    assert r.p_value == pytest.approx(r.p_upper)
    # df = 2 quantile: solve (1 - t/sqrt(2+t^2))/2 = 0.05 -> t^2 = 2*0.9^2/(1-0.9^2).
    t95 = math.sqrt(2.0 * 0.81 / 0.19)
    assert r.ci_low == pytest.approx(2.0 - t95 / math.sqrt(3.0), abs=1e-9)
    assert r.ci_high == pytest.approx(2.0 + t95 / math.sqrt(3.0), abs=1e-9)
    assert r.ci_level == pytest.approx(0.90)
    assert not r.equivalent


def test_tost_hand_derived_df2_equivalent() -> None:
    # Same data, bounds (0, 4): t_upper = -2 sqrt(3), p_upper = p_lower =
    # (1 - sqrt(12/14)) / 2 = 0.03709 < 0.05.
    r = one_sample_tost([1.0, 2.0, 3.0], 0.0, 4.0)
    assert r.p_lower == pytest.approx(r.p_upper, abs=1e-12)
    assert r.p_value == pytest.approx(0.5 * (1.0 - math.sqrt(12.0 / 14.0)), abs=1e-10)
    assert r.equivalent
    assert 0.0 < r.ci_low and r.ci_high < 4.0


def test_tost_mean_on_a_bound_is_never_equivalent() -> None:
    # Mean exactly on the lower bound: t_lower = 0, p_lower = 1/2 by symmetry.
    r = one_sample_tost([0.9, 1.0, 1.1], 1.0, 5.0)
    assert r.p_lower == pytest.approx(0.5, abs=1e-12)
    assert not r.equivalent


def test_tost_decision_equals_interval_inclusion() -> None:
    # Both p < alpha  <=>  the (1 - 2 alpha) t interval lies strictly inside
    # the bounds: p_lower < alpha iff mean - t(1-alpha) se > lower, and the
    # same for the upper side. Checked across shifts that cross both bounds.
    base = [-0.3, -0.1, 0.0, 0.05, 0.2, 0.4]
    for step in range(-40, 41):
        shift = step * 0.02
        r = one_sample_tost([v + shift for v in base], -0.5, 0.6, alpha=0.05)
        inside = r.lower_bound < r.ci_low and r.ci_high < r.upper_bound
        assert r.equivalent == inside, shift
        assert (r.p_lower < 0.05) == (r.ci_low > r.lower_bound)
        assert (r.p_upper < 0.05) == (r.ci_high < r.upper_bound)


def test_tost_asymmetric_bounds_use_each_side() -> None:
    # Swapping which bound is near must move which one-sided p is large.
    near_low = one_sample_tost([1.0, 1.1, 1.2], 1.0, 3.0)
    near_high = one_sample_tost([2.8, 2.9, 3.0], 1.0, 3.0)
    assert near_low.p_lower > 0.05 > near_low.p_upper
    assert near_high.p_upper > 0.05 > near_high.p_lower


def test_tost_zero_spread() -> None:
    # No spread: infinite t, the decision is whether the value is inside.
    assert one_sample_tost([2.0, 2.0], 1.0, 3.0).equivalent
    outside = one_sample_tost([3.5, 3.5], 1.0, 3.0)
    assert not outside.equivalent and outside.p_upper == 1.0


def test_tost_rejects_bad_input() -> None:
    with pytest.raises(ConfigurationError):
        one_sample_tost([1.0], 0.0, 2.0)
    with pytest.raises(ConfigurationError):
        one_sample_tost([1.0, 2.0], 2.0, 1.0)
    with pytest.raises(ConfigurationError):
        one_sample_tost([1.0, 2.0], 0.0, 3.0, alpha=0.5)
    with pytest.raises(ConfigurationError):
        one_sample_tost([1.0, math.nan], 0.0, 3.0)


def test_t_interval_df1_cauchy() -> None:
    # [0, 2]: mean 1, SD sqrt(2), SE 1. t(0.975, 1) = tan(0.475 pi) = 12.7062.
    low, high = one_sample_t_interval([0.0, 2.0], 0.95)
    q = math.tan(math.pi * 0.475)
    assert low == pytest.approx(1.0 - q, abs=1e-7)
    assert high == pytest.approx(1.0 + q, abs=1e-7)


def test_tost_matches_scipy_when_installed() -> None:
    stats = pytest.importorskip("scipy.stats")
    values = [0.61, 0.70, 0.66, 0.74, 0.69, 0.72, 0.65, 0.71]
    r = one_sample_tost(values, math.log(1.8), math.log(2.2))
    lo = stats.ttest_1samp(values, math.log(1.8), alternative="greater").pvalue
    hi = stats.ttest_1samp(values, math.log(2.2), alternative="less").pvalue
    assert r.p_lower == pytest.approx(lo, rel=1e-8)
    assert r.p_upper == pytest.approx(hi, rel=1e-8)


def test_p_equal_to_alpha_does_not_reject() -> None:
    # A one-sided test rejects only when p < alpha. At p == alpha the
    # (1 - 2 alpha) limit sits exactly on the bound, which is not "inside".
    # [0, 2], df = 1: t_lower = 1, p_lower = 1/2 - atan(1)/pi = 1/4 (up to
    # rounding). Using that computed p as alpha puts the test on its edge,
    # while p_upper (t = -9, about 0.035) is well below it.
    first = one_sample_tost([0.0, 2.0], 0.0, 10.0, alpha=0.25)
    edge = one_sample_tost([0.0, 2.0], 0.0, 10.0, alpha=first.p_lower)
    assert edge.p_lower == edge.alpha
    assert edge.p_upper < edge.alpha
    assert not edge.equivalent
