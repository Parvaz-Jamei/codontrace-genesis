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
