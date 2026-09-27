"""Adversarial tests for the causal-evidence interval and the claimgate rules.

Regression guard for two defects that together let a single run pair look like
evidence of a difference: a degenerate confidence interval around the mean, and
an auditor that accepted a non-zero effect size with neither an interval nor a
p-value.
"""

from __future__ import annotations

import pytest

from codontrace.claimgate.auditor import _ci_excludes_zero, _comparison_has_difference
from codontrace.claimgate.schema import ClaimgateComparison
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.causal_validation import (
    CausalInterventionRunPair,
    InterventionExecutor,
    InterventionSpec,
    build_causal_evidence_report,
)


def _pair(baseline: float, treatment: float) -> CausalInterventionRunPair:
    spec = InterventionSpec(
        "i", "factor", canonical_digest({"a": 1}), canonical_digest({"a": 2}), canonical_digest({"s": 1})
    )
    return InterventionExecutor().execute(spec, baseline_metric=baseline, treatment_metric=treatment)


def _comparison(effect_size, ci_low, ci_high, p) -> ClaimgateComparison:
    return ClaimgateComparison(
        a="a", b="b", effect_size=effect_size, ci_low=ci_low, ci_high=ci_high, p=p, test="", correction=""
    )


def test_single_pair_interval_cannot_exclude_zero():
    report = build_causal_evidence_report((_pair(1.0, 2.0),))
    low, high = report.effect.confidence_interval
    assert report.effect.effect_size == 1.0
    assert low == 0.0 and high == 0.0
    assert not _ci_excludes_zero(low, high)


def test_two_pairs_interval_is_a_real_interval():
    report = build_causal_evidence_report((_pair(1.0, 2.0), _pair(1.0, 2.5)))
    low, high = report.effect.confidence_interval
    assert low < report.effect.effect_size < high
    assert low < high


def test_zero_variance_pairs_do_not_mint_a_difference():
    report = build_causal_evidence_report((_pair(1.0, 2.0), _pair(1.0, 2.0)))
    low, high = report.effect.confidence_interval
    assert low == high == 0.0
    assert not _ci_excludes_zero(low, high)


@pytest.mark.parametrize(
    ("effect_size", "ci_low", "ci_high", "p"),
    [
        (1e-9, 0.0, 0.0, None),
        (1.0, 0.5, 0.5, None),
        (1.0, None, None, None),
        (0.0, 0.1, 1.0, None),
    ],
)
def test_comparisons_without_informative_uncertainty_fail_closed(effect_size, ci_low, ci_high, p):
    assert not _comparison_has_difference(_comparison(effect_size, ci_low, ci_high, p))


def test_real_interval_and_small_p_still_pass():
    assert _comparison_has_difference(_comparison(1.0, 0.2, 1.8, None))
    assert _comparison_has_difference(_comparison(1.0, None, None, 0.001))
