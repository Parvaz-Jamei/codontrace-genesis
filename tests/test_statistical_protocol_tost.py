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
    # Basis: SE = 0, mean 2 lies in (1, 3) so both one-sided p-values are 0
    # (student_t_sf(+inf) = 0); mean 3.5 lies above 3 so p_upper = 1.
    inside = one_sample_tost([2.0, 2.0], 1.0, 3.0)
    assert inside.equivalent
    assert inside.t_lower == math.inf and inside.t_upper == -math.inf
    record = inside.to_record()
    assert record["t_lower"] == {"$float": "inf"}
    assert record["t_upper"] == {"$float": "-inf"}
    outside = one_sample_tost([3.5, 3.5], 1.0, 3.0)
    assert not outside.equivalent and outside.p_upper == 1.0
    assert outside.to_record()["t_upper"] == {"$float": "inf"}


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


def test_upper_side_p_has_no_cancellation_far_in_the_tail() -> None:
    # Basis: P(T < t) = P(T > -t) by symmetry of Student's t. Taking the
    # lower-side p as the upper tail at -t keeps full relative precision; the
    # complement 1 - P(T > t) rounds to 0 once the tail drops below 1e-16.
    # df = 1 (Cauchy): P(T < -1e9) = 1/2 - atan(1e9)/pi = atan(1e-9)/pi
    # = 3.18310e-10, and at -1e20 it is 3.18310e-21, far below double epsilon.
    for t in (-1e9, -1e20):
        r = one_sample_tost([0.0, 2.0], 1.0 - 1e-6, 1.0 - t, alpha=0.25)
        assert r.p_upper == pytest.approx(math.atan(-1.0 / t) / math.pi, rel=1e-9)
        assert r.p_upper > 0.0


def test_overflowing_values_raise_configuration_error() -> None:
    # Basis: the t procedure needs a finite mean and variance; values whose
    # squared deviations exceed the double range have neither, which is an
    # input error, not an arithmetic crash.
    with pytest.raises(ConfigurationError):
        one_sample_tost([1e308, -1e308, 1e308], -1.0, 1.0)
    with pytest.raises(ConfigurationError):
        one_sample_t_interval([1e200, -1e200], 0.9)


def test_student_t_sf_edges() -> None:
    # Basis: P(T > 0) = 1/2 for every df by symmetry; P(T > +inf) = 0 and
    # P(T > -inf) = 1; NaN t and df < 1 are outside the law's domain.
    for df in (1, 2, 39, 10_000):
        assert student_t_sf(0.0, df) == pytest.approx(0.5, abs=1e-15)
        assert student_t_sf(math.inf, df) == 0.0 and student_t_sf(-math.inf, df) == 1.0
        assert student_t_sf(1.3, df) + student_t_sf(-1.3, df) == pytest.approx(1.0, abs=1e-14)
    for bad_t, bad_df in ((math.nan, 3), (1.0, 0), (1.0, True)):
        with pytest.raises(ConfigurationError):
            student_t_sf(bad_t, bad_df)  # type: ignore[arg-type]


def test_tost_property_against_scipy_on_seeded_samples() -> None:
    # Basis: each TOST side is an ordinary one-sided one-sample t test, so
    # both p-values must equal the reference t test against each bound, and
    # the decision must equal the (1 - 2 alpha) interval lying strictly inside
    # the bounds (interval duality). Samples are drawn through RNGManager with
    # a fixed seed, so the case list is reproducible.
    stats = pytest.importorskip("scipy.stats")
    from codontrace.rng import RNGManager

    rng = RNGManager(seed=20261101).fork("tost-property")
    for _ in range(60):
        n = rng.randrange(2, 60)
        centre = rng.random() * 2.0 - 1.0
        spread = 10.0 ** (rng.random() * 4.0 - 3.0)
        values = [centre + spread * (rng.random() - 0.5) for _ in range(n)]
        low = -rng.random() * 0.5
        high = rng.random() * 0.5 + 1e-3
        alpha = (0.01, 0.05, 0.1, 0.2)[rng.randrange(4)]
        r = one_sample_tost(values, low, high, alpha=alpha)
        ref_lo = stats.ttest_1samp(values, low, alternative="greater").pvalue
        ref_hi = stats.ttest_1samp(values, high, alternative="less").pvalue
        assert r.p_lower == pytest.approx(ref_lo, rel=1e-7, abs=1e-300)
        assert r.p_upper == pytest.approx(ref_hi, rel=1e-7, abs=1e-300)
        assert r.equivalent is (low < r.ci_low and r.ci_high < high)


@pytest.mark.parametrize("confidence", [0.0, 1.0, math.nan, math.inf])
def test_t_interval_refuses_invalid_confidence(confidence: float) -> None:
    """A two-sided interval requires 0 < confidence < 1 so its quantile is
    defined. Expected: invalid endpoints and non-finite confidence are input
    errors rather than unbounded or silently altered intervals.
    """
    with pytest.raises(ConfigurationError):
        one_sample_t_interval([0.0, 2.0], confidence)


def test_t_interval_refuses_missing_spread_data_and_nonfinite_values() -> None:
    """The sample variance uses n-1 degrees of freedom and finite deviations.
    Expected: fewer than two observations, infinity, NaN and overflowing
    squared deviations are refused by both one-sample t procedures.
    """
    for values in ([], [1.0], [1.0, math.inf], [1.0, math.nan], [1e300, -1e300]):
        with pytest.raises(ConfigurationError):
            one_sample_t_interval(values, 0.95)
        with pytest.raises(ConfigurationError):
            one_sample_tost(values, -1.0, 3.0)


def test_zero_variance_on_upper_bound_does_not_show_equivalence() -> None:
    """With every value on the upper bound, t_upper=0 and its one-sided
    p-value is 1/2 by symmetry. Expected: no equivalence, even though the
    degenerate interval has width zero and the lower side rejects.
    """
    result = one_sample_tost([2.0, 2.0], 1.0, 2.0)
    assert result.t_upper == 0.0 and result.p_upper == 0.5
    assert result.ci_low == result.ci_high == 2.0
    assert not result.equivalent


def test_zero_variance_on_lower_bound_does_not_show_equivalence() -> None:
    """With every value on the lower bound, t_lower = 0 and p_lower = 1/2.

    Basis: H0 lower is mean <= lower_bound. A zero-spread sample whose common
    value equals the lower bound has mean - lower = 0 and se = 0. This module
    takes that 0/0 as t = 0, its own convention: scipy 1.18.1
    ``ttest_1samp([1.0] * 3, 1.0)`` returns statistic NaN and p-value NaN for
    every alternative instead. Both fail to reject. The Student t upper tail
    at 0 is 1/2 by symmetry for any df, and 1/2 is not below alpha = 0.05, so
    H0 lower is not rejected. The upper side has mean - upper = -1 < 0 and se = 0, so
    t_upper = -inf and p_upper = sf(+inf) = 0. This mirrors the upper-bound
    case above; a value on either bound is never equivalent.
    Expected: t_lower 0.0, p_lower 0.5, t_upper -inf, p_upper 0.0, interval
    [1, 1], not equivalent; the record writes t_upper as the tagged -inf.
    """
    result = one_sample_tost([1.0, 1.0, 1.0], 1.0, 2.0)
    assert result.t_lower == 0.0 and result.p_lower == 0.5
    assert result.t_upper == -math.inf and result.p_upper == 0.0
    assert result.ci_low == result.ci_high == 1.0
    assert not result.equivalent
    record = result.to_record()
    assert record["t_lower"] == 0.0 and record["t_upper"] == {"$float": "-inf"}


def test_encode_tost_statistic_refuses_nan_and_tags_infinities() -> None:
    """NaN is refused; +/-inf become tagged strings; finite values stay numbers.

    Basis: a NaN t statistic carries no decision (it compares false with every
    bound), so writing it, or a stand-in number, would let a record claim a
    test that was not computed. Only the two signed infinities of a
    zero-spread sample have a TOST meaning, and JSON has no literal for them,
    so they are written as {"$float": "inf"} and {"$float": "-inf"}.
    Expected: ConfigurationError naming NaN for float('nan'); the tagged forms
    for +/-inf; 1.5 and -0.0 unchanged.
    """
    from codontrace.genesis.statistical_protocol import encode_tost_statistic

    with pytest.raises(ConfigurationError, match="NaN"):
        encode_tost_statistic(math.nan)
    assert encode_tost_statistic(math.inf) == {"$float": "inf"}
    assert encode_tost_statistic(-math.inf) == {"$float": "-inf"}
    assert encode_tost_statistic(1.5) == 1.5
    encoded_zero = encode_tost_statistic(-0.0)
    assert isinstance(encoded_zero, float) and encoded_zero == 0.0


def test_constant_sample_on_the_lower_bound_at_n7_is_not_equivalent() -> None:
    """Seven copies of the m = 0.5 lower log bound are not equivalent.

    Basis: v = 0.5877866649021191 is the registered m = 0.5 lower log bound,
    log(0.9 * 2.0). For seven copies the correctly rounded sum 7 * v divided
    by 7 does not round back to v (checked first, so the case is the one that
    needs it). A mean taken as fsum / n is then one ulp above v, every
    deviation is about one ulp, the sample SD comes out near 1.2e-16 instead
    of 0, and t_lower = (mean - v) / se = sqrt(6) = 2.449 with p_lower =
    0.025 < 0.05: a false equivalence. The sample is exactly constant, so its
    mean is v and its SD is 0. Then mean - lower = 0 and se = 0, so t_lower =
    0 (0/0 taken as 0) and p_lower = 1/2; mean - upper < 0 gives t_upper =
    -inf and p_upper = 0. The 90% interval (1 - 2 alpha) is [v, v], whose lower
    end is not strictly above the lower bound, so the interval rule also says
    not equivalent.
    Expected: mean v, sd 0, t_lower 0.0, p_lower 0.5, t_upper -inf, not
    equivalent; one_sample_t_interval at 0.90 and the TOST interval are both
    (v, v), and the decision equals strict inclusion of that interval.
    """
    v = 0.5877866649021191
    upper = 0.7884573603642703
    data = [v] * 7
    assert math.fsum(data) / 7 != v
    r = one_sample_tost(data, v, upper, alpha=0.05)
    assert r.mean == v and r.sd == 0.0 and r.standard_error == 0.0
    assert r.t_lower == 0.0 and r.p_lower == 0.5
    assert r.t_upper == -math.inf and r.p_upper == 0.0
    assert not r.equivalent
    assert one_sample_t_interval(data, 0.90) == (v, v) == (r.ci_low, r.ci_high)
    assert r.equivalent is (r.lower_bound < r.ci_low and r.ci_high < r.upper_bound)


def test_constant_sample_too_large_to_sum_keeps_its_value() -> None:
    """A constant sample is answered from its value, without forming a sum.

    Basis: the mean of n copies of v is v and the spread is 0, exactly; the
    moments need no arithmetic. For v = 1e308 and n = 3 the sum 3e308 exceeds
    the largest double 1.7976931348623157e308, so a path through fsum(x)
    (float or exact moments) overflows and is refused as "too large". With
    bounds (0, 1.7976931348623157e308) the value lies strictly inside, so
    both one-sided t are infinite (+inf below, -inf above), both p are 0,
    and the 90% interval is [v, v], strictly inside.
    Expected: fsum overflows (checked first); mean v, sd 0, t_lower +inf,
    t_upper -inf, p_lower = p_upper = 0, equivalent, and the interval (v, v)
    from both one_sample_tost and one_sample_t_interval.
    """
    v = 1e308
    top = 1.7976931348623157e308
    data = [v] * 3
    with pytest.raises(OverflowError):
        math.fsum(data)
    r = one_sample_tost(data, 0.0, top, alpha=0.05)
    assert r.mean == v and r.sd == 0.0 and r.standard_error == 0.0
    assert r.t_lower == math.inf and r.t_upper == -math.inf
    assert r.p_lower == 0.0 and r.p_upper == 0.0
    assert r.equivalent
    assert (r.ci_low, r.ci_high) == (v, v) == one_sample_t_interval(data, 0.90)


def test_one_ulp_spread_on_the_lower_bound_at_n7_uses_the_exact_mean() -> None:
    """Six copies of the m = 0.5 lower log bound plus one value one ulp above it.

    Basis: v = 0.5877866649021191 is the registered m = 0.5 lower log bound and
    u = ulp(v) = 2^-53. For x = [v] * 6 + [v + u] the exact mean is v + u/7, the
    deviations are -u/7 (six times) and 6u/7, so the exact sum of squares is
    6u^2/49 + 36u^2/49 = 6u^2/7, the variance is u^2/7, sd = u/sqrt(7) and
    se = sd/sqrt(7) = u/7. Then t_lower = (u/7)/(u/7) = 1 exactly. For df = 6
    the closed form for even df gives P(T > 1) = 1/2 - (1/(2 sqrt(7))) *
    (1 + 3/7 + 27/98) = 1/2 - 167/(196 sqrt(7)) = 0.17796 > 0.05: not
    equivalent. A float mean fsum(x)/7 rounds to v + u (the sample maximum),
    which gives sd = 1.1e-16 and t_lower = sqrt(7) = 2.65, p = 0.019: a false
    equivalence. The exact mean rounds to v, so the reported mean is v while
    t uses the exact v + u/7. The 90% lower end is v + u/7 - 1.943 u/7 < v,
    rounded toward the mean to v, so the strict interval rule also says not
    equivalent.
    Expected: fsum / 7 is v + u (the case needs the exact path), mean v, sd
    and se equal to u/sqrt(7) and u/7 correctly rounded, t_lower 1.0, p_lower
    equal to the closed form, sd > 0 and t finite (the sample is not treated
    as constant), not equivalent, and ci_low == v so the interval rule agrees.
    """
    from fractions import Fraction

    v = 0.5877866649021191
    u = math.ulp(v)
    upper = 0.7884573603642703
    data = [v] * 6 + [math.nextafter(v, math.inf)]
    assert math.fsum(data) / 7 == v + u
    r = one_sample_tost(data, v, upper, alpha=0.05)
    assert r.mean == v
    half_ulp = Fraction(math.ulp(r.sd)) / 2
    assert (Fraction(r.sd) - half_ulp) ** 2 <= Fraction(u) ** 2 / 7 <= (Fraction(r.sd) + half_ulp) ** 2
    assert r.standard_error == u / 7.0
    assert r.sd > 0.0 and math.isfinite(r.t_lower)
    assert r.t_lower == 1.0
    assert r.p_lower == pytest.approx(0.5 - 167.0 / (196.0 * math.sqrt(7.0)), abs=1e-12)
    assert not r.equivalent
    assert r.ci_low == v and not (r.lower_bound < r.ci_low)
    assert one_sample_t_interval(data, 0.90)[0] == v


def test_interval_end_that_rounds_onto_a_bound_stays_inside_when_its_exact_value_is() -> None:
    """Three values a few ulps above a bound, with an exactly representable mean.

    Basis: with b = log(1.8), c = b + u and w = b + 4u (u = ulp(b)), the sample
    [w, c, w] has exact mean b + 3u (a float, so the two-pass float moments are
    exact), deviations u, -2u, u, variance 3u^2, sd sqrt(3) u and se = u. So
    t_lower = 3. For df = 2, P(T > 3) = (1 - 3/sqrt(11))/2 = 0.0477 < 0.05 and
    the 95% quantile is 0.9/sqrt(2 * 0.95 * 0.05) = 2.919986, so the lower end
    b + 3u - 2.919986u = b + 0.08u lies strictly above b and the strict 90%
    interval rule agrees with the TOST. The nearest float to b + 0.08u is b
    itself, which would read as "not inside"; the end is therefore the next
    float above b.
    Expected: mean b + 3u, t_lower 3.0, p_lower equal to the closed form, the
    sample equivalent, ci_low the float after b, and the strict rule equal to
    the decision.
    """
    b = math.log(1.8)
    u = math.ulp(b)
    c = math.nextafter(b, math.inf)
    w = b + 4 * u
    r = one_sample_tost([w, c, w], b, math.log(2.2), alpha=0.05)
    assert r.mean == b + 3 * u and r.t_lower == 3.0
    assert r.p_lower == pytest.approx((1.0 - 3.0 / math.sqrt(11.0)) / 2.0, abs=1e-12)
    assert r.equivalent
    assert r.ci_low == math.nextafter(b, math.inf)
    assert r.equivalent is (r.lower_bound < r.ci_low and r.ci_high < r.upper_bound)


def test_well_conditioned_samples_keep_the_float_two_pass_moments() -> None:
    """For ordinary spreads the result is the plain float computation, bit for bit.

    Basis: the exact moments are used only when the term (sum(x) - n *
    mean)^2 / n, by which the sum of squares about the float mean exceeds the
    one about the exact mean, is visible at double precision. For a sample
    whose spread is far above the ulp of its mean that term is below the
    rounding of the sum of squares, so mean = fsum(x)/n, sd = sqrt(fsum((x -
    mean)^2)/(n - 1)), se = sd/sqrt(n), t = (mean - bound)/se and the ends
    mean -/+ t_{0.95} se are returned unchanged. The samples are seeded
    (RNGManager) with n = 5 to 60 and spreads from 1e-6 to 1 around a centre
    in (-1, 1).
    Expected: every field equal (==) to the float formula.
    """
    from codontrace.genesis.causal_validation import student_t_quantile
    from codontrace.rng import RNGManager

    rng = RNGManager(seed=4502).fork("well-conditioned-moments")
    for _ in range(200):
        n = rng.randrange(5, 61)
        centre = rng.random() * 2.0 - 1.0
        spread = 10.0 ** (rng.random() * 6.0 - 6.0)
        x = [centre + spread * (rng.random() - 0.5) for _ in range(n)]
        mean = math.fsum(x) / n
        sd = math.sqrt(math.fsum((a - mean) * (a - mean) for a in x) / (n - 1))
        se = sd / math.sqrt(n)
        low, high = centre - 0.01, centre + 0.02
        half = student_t_quantile(n - 1, 0.95) * se
        r = one_sample_tost(x, low, high, alpha=0.05)
        assert (r.mean, r.sd, r.standard_error) == (mean, sd, se)
        assert (r.t_lower, r.t_upper) == ((mean - low) / se, (mean - high) / se)
        assert (r.ci_low, r.ci_high) == (mean - half, mean + half)
        half95 = student_t_quantile(n - 1, 0.975) * sd / math.sqrt(n)
        assert one_sample_t_interval(x, 0.95) == (mean - half95, mean + half95)


def test_exact_square_root_is_correctly_rounded() -> None:
    """The square root used with exact moments rounds once, to nearest.

    Basis: IEEE 754 requires math.sqrt to be correctly rounded, so for a float
    y the correctly rounded root of the rational value of y is math.sqrt(y).
    Squares of floats have exact roots. The inputs span normal, subnormal and
    large magnitudes (seeded, RNGManager).
    Expected: equality with math.sqrt for every float input, exact roots for
    exact squares, and 0.0 for 0.
    """
    from fractions import Fraction

    from codontrace.genesis.statistical_protocol import _sqrt_of_fraction
    from codontrace.rng import RNGManager

    rng = RNGManager(seed=4503).fork("exact-sqrt")
    assert _sqrt_of_fraction(Fraction(0)) == 0.0
    for y in (2.0, 3.0, 0.5, 5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, 1.0 / 7.0):
        assert _sqrt_of_fraction(Fraction(y)) == math.sqrt(y), y
    for _ in range(2000):
        y = math.ldexp(rng.random() + 0.5, rng.randrange(-1070, 1020))
        assert _sqrt_of_fraction(Fraction(y)) == math.sqrt(y), y
        root = math.ldexp(rng.random() + 0.5, rng.randrange(-500, 500))
        assert _sqrt_of_fraction(Fraction(root) ** 2) == root, root


@pytest.mark.parametrize(
    "values",
    [
        [0.0] * 6 + [5e-324],
        [5e-324] * 6 + [1e-323],
        [-5e-324] * 39 + [-0.0],
        [1e-300] * 6 + [math.nextafter(1e-300, 1.0)],
    ],
    ids=["zeros-and-one-subnormal", "two-subnormals", "negative-subnormal-n40", "two-adjacent-tiny"],
)
def test_tost_with_a_subnormal_spread_gives_an_infinite_t_not_an_overflow(values: list[float]) -> None:
    """A spread of a few subnormal ulps gives t = -inf at bounds near 1, not OverflowError.

    Basis: these samples take the exact-moment path. With m = 0.5 bounds
    (log 1.8, log 2.2) the exact t = (mean - bound) / se has |t| near
    0.6 / 1e-324, beyond the float range (largest float 1.8e308). IEEE 754
    rounding to nearest delivers an overflowing result as an infinity of
    its sign, and the module already encodes t = +-inf (zero-spread rule,
    encode_tost_statistic). Before R47 the exact square root raised
    OverflowError from int-to-float conversion.
    Expected: t_lower = t_upper = -inf, p_lower 1, p_upper 0, not
    equivalent, and a record whose t_lower is the encoded -inf.
    """
    from codontrace.genesis.statistical_protocol import _mean_sd_df

    lower, upper = 0.5877866649021191, 0.7884573603642703
    assert _mean_sd_df(values).exact_mean is not None
    result = one_sample_tost(values, lower, upper, alpha=0.05)
    assert result.t_lower == result.t_upper == -math.inf
    assert (result.p_lower, result.p_upper, result.equivalent) == (1.0, 0.0, False)
    assert result.to_record()["t_lower"] == {"$float": "-inf"}


def test_exact_sqrt_beyond_the_float_range_is_inf() -> None:
    """The exact square root rounds to inf exactly where IEEE 754 rounding overflows.

    Basis: M = sys.float_info.max. sqrt((M + 2**969)**2) = M + 2**969 lies
    below the midpoint between M and 2**1024, so it rounds to M. For
    M + 2**970, the midpoint itself, ties-to-even rounds up to 2**1024,
    which overflows to inf; 2**2048 has root 2**1024, also inf.
    Expected: M, inf and inf.
    """
    import sys
    from fractions import Fraction

    from codontrace.genesis.statistical_protocol import _sqrt_of_fraction

    big = Fraction(sys.float_info.max)
    assert _sqrt_of_fraction((big + 2**969) ** 2) == sys.float_info.max
    assert _sqrt_of_fraction((big + 2**970) ** 2) == math.inf
    assert _sqrt_of_fraction(Fraction(2) ** 2048) == math.inf
