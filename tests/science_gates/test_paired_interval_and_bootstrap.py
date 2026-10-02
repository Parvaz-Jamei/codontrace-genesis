"""Phase 3: Student-t intervals and run-level bootstrap eligibility.

The n=32 series is the audit witness. With the old df>30 fallback of 1.96 the
interval is (0.03, 3.95) and excludes zero. The Student-t quantile at df=31
puts zero inside. Reference quantiles below are scipy.stats.t.ppf(0.975, df).
"""

from __future__ import annotations

import math

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.causal_validation import (
    _historical_t975,
    paired_mean_interval,
    student_t_quantile,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (
    CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS,
    run_level_cluster_bootstrap_interval,
)

# scipy 1.16, scipy.stats.t.ppf(0.975, df)
_SCIPY_T975 = {
    30: 2.0422724563012378,
    31: 2.039513446396408,
    120: 1.9799304050824402,
    1000: 1.9623390808264083,
}


def _witness_32() -> list[float]:
    return [1.99 - math.sqrt(31)] * 16 + [1.99 + math.sqrt(31)] * 16


def test_df30_and_df31_use_the_t_quantile_not_a_normal_cliff() -> None:
    q30 = student_t_quantile(30)
    q31 = student_t_quantile(31)
    assert q30 == pytest.approx(_SCIPY_T975[30], abs=1e-9)
    assert q31 == pytest.approx(_SCIPY_T975[31], abs=1e-9)
    assert student_t_quantile(120) == pytest.approx(_SCIPY_T975[120], abs=1e-9)
    assert student_t_quantile(1000) == pytest.approx(_SCIPY_T975[1000], abs=1e-8)
    assert q31 > 2.03
    assert _historical_t975(31) == 1.96
    assert _historical_t975(30) == 2.042
    assert q30 > q31 > student_t_quantile(1000) > 1.96


def test_n32_witness_contains_zero_and_the_old_interval_does_not() -> None:
    result = paired_mean_interval(_witness_32())
    assert result.n == 32
    assert result.df == 31
    assert result.interval_defined is True
    assert result.low is not None and result.high is not None
    assert result.low < 0.0 < result.high
    assert result.statistical_support is False
    assert result.historical_critical == 1.96
    assert result.historical_low == pytest.approx(0.03)
    assert result.historical_high == pytest.approx(3.95)
    assert result.historical_low > 0.0
    assert result.low == pytest.approx(-0.0495134464)
    assert result.high == pytest.approx(4.0295134464)
    assert result.estimator == "student_t_paired_mean_v2"


def test_zero_variance_keeps_the_point_and_does_not_invent_an_origin_interval() -> None:
    result = paired_mean_interval([1.0, 1.0, 1.0, 1.0])
    assert result.point == 1.0
    assert result.interval_defined is False
    assert result.low is None and result.high is None
    assert result.status == "degenerate_variance"
    assert result.statistical_support is False
    with pytest.raises(ConfigurationError, match="not defined"):
        result.endpoints()


def test_scipy_student_t_matches_when_installed() -> None:
    scipy_stats = pytest.importorskip("scipy.stats")
    for df in (1, 30, 31, 120, 1000):
        assert student_t_quantile(df) == pytest.approx(float(scipy_stats.t.ppf(0.975, df)), rel=1e-9, abs=1e-8)


def test_one_run_is_not_an_inferential_witness() -> None:
    alone = run_level_cluster_bootstrap_interval([1.0], n_resamples=10_000, seed=1)
    assert alone["point"] == 1.0
    assert alone["n_runs"] == 1
    assert alone["n_resamples"] == 10_000
    assert alone["n_runs"] != alone["n_resamples"]
    assert alone["lo"] == alone["hi"] == 1.0
    assert alone["interval_defined"] is False
    assert alone["inferential_eligible"] is False
    assert alone["excludes_zero"] is False
    assert alone["status"] == "insufficient_runs"
    assert alone["variability"] == "between_run_variability_not_estimable"

    many = [1.0 + (i % 3) * 0.1 for i in range(CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS)]
    eligible = run_level_cluster_bootstrap_interval(many, n_resamples=200, seed=3)
    assert eligible["inferential_eligible"] is True
    assert eligible["excludes_zero"] is True
    assert eligible["status"] == "percentile_interval"

    short = many[:-1]
    blocked = run_level_cluster_bootstrap_interval(short, n_resamples=200, seed=3)
    assert len(short) == CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS - 1
    assert blocked["percentile_excludes_zero"] is True
    assert blocked["inferential_eligible"] is False
    assert blocked["excludes_zero"] is False
    assert blocked["status"] == "below_auditor_floor"


def test_bootstrap_rejects_non_finite_and_degenerate_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        run_level_cluster_bootstrap_interval([1.0, math.nan])
    with pytest.raises(ValueError, match="finite"):
        run_level_cluster_bootstrap_interval([1.0, math.inf])
    flat = run_level_cluster_bootstrap_interval([1.0, 1.0])
    assert flat["point"] == 1.0
    assert flat["status"] == "degenerate_variance"
    assert flat["excludes_zero"] is False
    assert flat["inferential_eligible"] is False
