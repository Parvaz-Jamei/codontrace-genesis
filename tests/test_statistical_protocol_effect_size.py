"""Known-value checks for descriptive effect-size helpers.

These are measurement formulas only. They do not unlock intelligence,
collective_intelligence, AGI, Tokyo Type 1, or Avida-replacement claims.
"""

from __future__ import annotations

import math

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.statistical_protocol import (
    estimate_effect_size_lite,
    paired_effect_size,
    _pooled_std,
)


def test_pooled_std_is_classical_two_group_formula() -> None:
    baseline = [1.0, 2.0, 3.0]
    treatment = [2.0, 3.0, 4.0]
    # s1² = s2² = 1, so pooled SD = 1. Concatenating the groups would mix in
    # between-group variance and yield sqrt(5.5/6) ≈ 0.957 — that is wrong.
    assert _pooled_std(baseline, treatment) == pytest.approx(1.0)
    assert _pooled_std(baseline, treatment) != pytest.approx(math.sqrt(5.5 / 6.0))


def test_estimate_effect_size_lite_uses_classical_pooled_sd() -> None:
    effect = estimate_effect_size_lite("fitness", [1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
    assert effect.mean_delta == pytest.approx(1.0)
    assert effect.standardized_delta_lite == pytest.approx(1.0)
    assert effect.interpretation == "large_descriptive_effect"


def test_paired_effect_size_is_mean_over_sample_sd() -> None:
    # mean(Δ)=2, s_Δ=1 (ddof=1) → dz=2
    assert paired_effect_size([1.0, 2.0, 3.0]) == pytest.approx(2.0)
    assert paired_effect_size([2.0, 2.0, 2.0]) == pytest.approx(0.0)


def test_paired_effect_size_rejects_too_few_or_non_numeric() -> None:
    with pytest.raises(ConfigurationError):
        paired_effect_size([1.0])
    with pytest.raises(ConfigurationError):
        paired_effect_size([])  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        paired_effect_size([True, False])  # type: ignore[list-item]
