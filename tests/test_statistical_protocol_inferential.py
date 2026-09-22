"""Known-value checks for Wave 0 inferential helpers.

These functions measure paired deltas. They do not unlock intelligence,
collective_intelligence, AGI, Tokyo Type 1, or Avida-replacement claims.
"""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.statistical_protocol import (
    _norm_cdf,
    _norm_ppf,
    bootstrap_ci_paired,
    exact_sign_flip_permutation_p,
    holm_correction,
    meet_in_the_middle_sign_flip_p,
    sign_flip_permutation_detail,
)


def test_exact_sign_flip_permutation_known_values() -> None:
    # [1, 2, 3]: |mean|=2. Only the all-plus and all-minus patterns reach it.
    # 2 / 2^3 = 0.25
    assert exact_sign_flip_permutation_p([1.0, 2.0, 3.0]) == pytest.approx(0.25)
    # Four equal positive deltas: 2 / 16 = 0.125
    assert exact_sign_flip_permutation_p([5.0, 5.0, 5.0, 5.0]) == pytest.approx(0.125)
    assert exact_sign_flip_permutation_p([0.0, 0.0, 0.0]) == pytest.approx(1.0)
    assert exact_sign_flip_permutation_p([1.0]) == pytest.approx(1.0)


def test_exact_sign_flip_monte_carlo_is_seed_deterministic() -> None:
    deltas = [1.0, -0.4] * 10 + [0.2]
    assert len(deltas) == 21
    first = exact_sign_flip_permutation_p(deltas, seed=7)
    second = exact_sign_flip_permutation_p(deltas, seed=7)
    other = exact_sign_flip_permutation_p(deltas, seed=8)
    # Same seed must replay on this interpreter. Absolute Monte Carlo
    # p-values are not pinned: CPython 3.11 vs 3.12+ RNG streams differ.
    assert first == second
    assert 0.0 < first <= 1.0
    assert 0.0 < other <= 1.0
    assert first != other
    floor = 1.0 / 20001.0
    assert first >= floor
    assert other >= floor
    # Finite Monte Carlo cannot report p=0 (adds the observed draw).
    extreme = exact_sign_flip_permutation_p([1.0] * 21, seed=1)
    assert extreme >= floor
    assert extreme > 0.0


def test_holm_correction_known_values() -> None:
    # Sorted 0.01, 0.03, 0.04 → 0.03, 0.06, 0.06 in that order; map back.
    adjusted = holm_correction([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx((0.03, 0.06, 0.06))
    # Wikipedia-style m=4: 0.005, 0.01, 0.03, 0.04 → 0.02, 0.03, 0.06, 0.06
    adjusted_four = holm_correction([0.01, 0.04, 0.03, 0.005])
    assert adjusted_four == pytest.approx((0.03, 0.06, 0.06, 0.02))
    assert holm_correction([]) == ()
    assert holm_correction([0.0, 1.0]) == pytest.approx((0.0, 1.0))


def test_holm_correction_rejects_out_of_range() -> None:
    with pytest.raises(ConfigurationError):
        holm_correction([-0.01])
    with pytest.raises(ConfigurationError):
        holm_correction([1.2])


def test_norm_ppf_known_quantiles() -> None:
    assert _norm_ppf(0.5) == pytest.approx(0.0, abs=1e-10)
    assert _norm_cdf(0.0) == pytest.approx(0.5)
    assert _norm_ppf(_norm_cdf(1.0)) == pytest.approx(1.0, abs=1e-6)
    assert _norm_ppf(0.975) == pytest.approx(1.959963984540, abs=1e-6)


def test_bca_undefined_edges_fall_back_honestly() -> None:
    # n=1: jackknife acceleration is undefined; report the point.
    assert bootstrap_ci_paired([3.0], method="bca") == (3.0, 3.0)
    # Zero variance: BCa cloud has no interior, so the interval is the point.
    assert bootstrap_ci_paired([2.0, 2.0, 2.0], method="bca", resamples=50) == (
        2.0,
        2.0,
    )


def test_percentile_bootstrap_ci_known_values() -> None:
    assert bootstrap_ci_paired([3.0], method="percentile") == (3.0, 3.0)
    assert bootstrap_ci_paired([2.0, 2.0, 2.0], method="percentile", resamples=50) == (
        2.0,
        2.0,
    )
    # With seed=1, n=2, B=4 the resampled means of [0, 10] are fully enumerated
    # by the RNG path; both bounds must sit on {0, 5, 10} and low ≤ high.
    # RNGManager seed=1, B=4 resampled means of [0, 10] are [10, 5, 10, 10].
    # Linear 0.25/0.75 percentiles of the sorted sample are 8.75 and 10.
    assert bootstrap_ci_paired(
        [0.0, 10.0], method="percentile", resamples=4, seed=1, confidence=0.5
    ) == (8.75, 10.0)


def test_bca_bootstrap_matches_hand_calculation() -> None:
    deltas = [1.0, 2.0, 4.0]
    # Fixed seed / B so the interval is a regression pin, not a claim.
    assert bootstrap_ci_paired(
        deltas, method="bca", resamples=200, seed=11, confidence=0.8
    ) == pytest.approx((4.0 / 3.0, 3.0))
    assert bootstrap_ci_paired(
        deltas, method="percentile", resamples=200, seed=11, confidence=0.8
    ) == pytest.approx((4.0 / 3.0, 3.0333333333333314))


def test_studentized_bootstrap_is_opt_in_and_does_not_change_default() -> None:
    deltas = [1.0, 2.0, 4.0]
    default = bootstrap_ci_paired(deltas, resamples=200, seed=11, confidence=0.8)
    bca = bootstrap_ci_paired(deltas, method="bca", resamples=200, seed=11, confidence=0.8)
    assert default == pytest.approx((4.0 / 3.0, 3.0))
    assert bca == pytest.approx(default)
    assert bootstrap_ci_paired([3.0], method="studentized") == (3.0, 3.0)
    assert bootstrap_ci_paired([2.0, 2.0, 2.0], method="studentized", resamples=50) == (
        2.0,
        2.0,
    )
    studentized = bootstrap_ci_paired(
        deltas, method="studentized", resamples=200, seed=11, confidence=0.8
    )
    assert studentized == pytest.approx((1.0104576778010383, 4.979084644397925))
    mean = sum(deltas) / 3.0
    assert studentized[0] <= mean <= studentized[1]
    assert studentized[0] < default[0] or studentized[1] > default[1]


def test_bootstrap_ci_rejects_bad_inputs() -> None:
    with pytest.raises(ConfigurationError):
        bootstrap_ci_paired([])
    with pytest.raises(ConfigurationError):
        bootstrap_ci_paired([1.0], method="jackknife")  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        exact_sign_flip_permutation_p([])


def test_meet_in_the_middle_matches_exhaustive_for_small_n() -> None:
    deltas = (1.0, 2.0, 3.0, -0.5, 0.25, 4.0, 0.0, -1.5)
    exhaustive = exact_sign_flip_permutation_p(deltas)
    mitm = meet_in_the_middle_sign_flip_p(deltas)
    assert mitm == pytest.approx(exhaustive)
    detail = sign_flip_permutation_detail(deltas)
    assert detail.method == "exhaustive"
    assert detail.censored_floor is False
    assert detail.p == pytest.approx(exhaustive)


def test_sign_flip_detail_flags_monte_carlo_floor_and_mitm_is_exact() -> None:
    deltas = (1.0,) * 21
    auto = sign_flip_permutation_detail(deltas, seed=1)
    assert auto.method == "monte_carlo"
    assert auto.censored_floor is True
    assert auto.floor == pytest.approx(1.0 / 20001.0)
    assert auto.p >= auto.floor
    assert exact_sign_flip_permutation_p(deltas, seed=1) == pytest.approx(auto.p)
    mitm = sign_flip_permutation_detail(deltas, method="meet_in_the_middle")
    assert mitm.method == "meet_in_the_middle"
    assert mitm.censored_floor is False
    assert mitm.p == pytest.approx(2.0 / float(1 << 21))
    assert mitm.p < auto.floor


def test_meet_in_the_middle_rejects_n_above_40() -> None:
    with pytest.raises(ConfigurationError):
        meet_in_the_middle_sign_flip_p([1.0] * 41)
