"""Temporal NFDS estimand. The historical pooled score is left unchanged.

Witnesses (audit of ``lagged_nfds_score``)
------------------------------------------
1. Forty generations, host fixed at A=0.9, B=0.1 and parasite fixed at the
   mirror. ``lagged_nfds_score`` reports ``corr=-1``, ``n=72``,
   ``pass_prelim=True`` even though nothing changes in time.
2. One paired generation and 20 classes is enough for that same function to
   report ``n=20`` and ``pass_prelim=True``. ``n`` there is class×time pairs.

``within_class_lagged_association`` is the versioned replacement. It must
refuse both witnesses, and it must separate a real lagged match from a
constant mirror, an independent drift, a shared line, and a pure change in
population size. The expected sign is the matching rule's sign (+), not
"negative means NFDS".
"""

from __future__ import annotations

import math

import pytest

from codontrace.genesis.measurements.rq_frequency_clocks import (
    MIN_PAIRED_TIMES_FLOOR,
    expected_lag_sign,
    lagged_nfds_score,
    within_class_lagged_association,
)

_LAG = 4


def _constant_mirror() -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]]:
    host = {t: {"A": 0.9, "B": 0.1} for t in range(40)}
    para = {t: {"A": 0.1, "B": 0.9} for t in range(40)}
    return host, para


def _one_time_pair() -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]]:
    n_classes = 20
    host_counts = {f"c{i}": float(i + 1) for i in range(n_classes)}
    para_counts = {f"c{i}": float(n_classes - i) for i in range(n_classes)}
    return {0: host_counts}, {_LAG: para_counts}


def _irregular_shares(n_gens: int) -> list[float]:
    """Deterministic shares in (0.15, 0.85). Not a line and not a short cycle."""

    state = 0.2
    shares: list[float] = []
    for _ in range(n_gens):
        state = (state * 1.7 + 0.13) % 1.0
        shares.append(0.15 + 0.7 * state)
    return shares


def _two_class(shares: list[float], *, other: list[float] | None = None) -> dict[int, dict[str, float]]:
    used = shares if other is None else other
    return {t: {"A": used[t], "B": 1.0 - used[t]} for t in range(len(used))}


def test_expected_sign_comes_from_the_matching_rule_not_from_negativity() -> None:
    assert expected_lag_sign() == 1
    with pytest.raises(ValueError, match="recognition rule"):
        expected_lag_sign("negative_means_nfds")


def test_constant_mirror_is_not_temporal_evidence() -> None:
    """Witness 1. The historical score still passes; the temporal score must not."""

    host, para = _constant_mirror()
    retired = lagged_nfds_score(host, para, lag=_LAG, min_points=20)
    assert retired["corr"] == -1.0
    assert retired["n"] == 72
    assert retired["pass_prelim"] is True

    result = within_class_lagged_association(host, para, lag=_LAG, min_paired_times=20)
    assert result["n_paired_times"] == 36
    assert result["n_classes"] == 2
    assert result["n_independent_runs"] == 1
    assert result["n_class_time_pairs"] == 72
    assert result["n_class_time_pairs"] == retired["n"]
    assert result["between_class_corr"] == -1.0
    assert result["within_corr"] is None
    assert result["status"] == "no_temporal_variation"
    assert result["temporal_evidence"] is False
    assert result["hypothesis_supported"] is False
    assert result["confirmatory_claim"] is False
    assert "red_queen_proved" not in result
    historical = result["historical_pooled"]
    assert isinstance(historical, dict)
    assert historical["pass_prelim"] is True


def test_one_time_pair_cannot_be_rescued_by_many_classes() -> None:
    """Witness 2. Twenty classes at one time are not twenty time points."""

    host, para = _one_time_pair()
    retired = lagged_nfds_score(host, para, lag=_LAG, min_points=20)
    assert retired["n"] == 20
    assert retired["pass_prelim"] is True
    assert float(retired["corr"]) == pytest.approx(-1.0)

    result = within_class_lagged_association(host, para, lag=_LAG, min_paired_times=1)
    assert result["n_paired_times"] == 1
    assert result["n_classes"] == 20
    assert result["n_class_time_pairs"] == 20
    assert result["min_paired_times_requested"] == 1
    assert result["min_paired_times_applied"] == MIN_PAIRED_TIMES_FLOOR
    assert result["status"] == "insufficient_paired_times"
    assert result["temporal_evidence"] is False
    pooled = result["historical_pooled"]
    assert isinstance(pooled, dict)
    assert pooled["pass_prelim"] is True


def test_declaring_more_runs_does_not_invent_time_points() -> None:
    host, para = _constant_mirror()
    result = within_class_lagged_association(
        host, para, lag=_LAG, n_independent_runs=7
    )
    assert result["n_independent_runs"] == 7
    assert result["n_paired_times"] == 36
    assert result["n_class_time_pairs"] == 72
    assert result["independent_runs_are_not_inferred"] is True
    assert result["temporal_evidence"] is False


def test_positive_tracking_passes_and_the_negative_controls_do_not() -> None:
    shares = _irregular_shares(48)
    host = _two_class(shares)
    # Parasite share at t equals the host share at t-lag: matching tracking.
    para_shares = [shares[0]] * _LAG + shares[:-_LAG]
    para = _two_class(para_shares)

    positive = within_class_lagged_association(host, para, lag=_LAG)
    assert positive["expected_sign"] == 1
    assert positive["n_paired_times"] == 44
    assert positive["n_classes"] == 2
    assert positive["n_independent_runs"] == 1
    assert float(positive["within_corr_detrended"]) == pytest.approx(1.0)
    assert float(positive["within_corr_detrended"]) > float(
        positive["contemporaneous_within_corr_detrended"]
    )
    assert float(positive["null_p"]) <= 0.05
    assert positive["null_method"] == "circular_time_shift_shared"
    assert positive["status"] == "temporal_tracking"
    assert positive["temporal_evidence"] is True
    assert positive["hypothesis_supported"] is False
    assert positive["confirmatory_claim"] is False
    assert "red_queen_proved" not in positive

    # Same shape, opposite sign: parasites avoid the previously common class.
    # A negative correlation is real temporal structure and still not NFDS.
    avoided = [1.0 - value for value in para_shares]
    negative = within_class_lagged_association(host, _two_class(avoided), lag=_LAG)
    assert float(negative["within_corr_detrended"]) == pytest.approx(-1.0)
    assert negative["status"] == "sign_inconsistent"
    assert negative["temporal_evidence"] is False

    # Independent deterministic drifts. A chance positive sign is not evidence:
    # the predetermined shift null does not reject.
    other = [0.2 + 0.6 * ((t * 5 % 13) / 12) for t in range(48)]
    independent = within_class_lagged_association(host, _two_class(other), lag=_LAG)
    assert independent["temporal_evidence"] is False
    assert independent["status"] == "null_not_rejected"
    assert float(independent["null_p"]) > 0.05

    # Shared line: within correlation before detrending is perfect, after it is gone.
    line = [0.2 + 0.01 * t for t in range(40)]
    shared = within_class_lagged_association(_two_class(line), _two_class(line), lag=_LAG)
    assert float(shared["within_corr"]) == pytest.approx(1.0)
    assert shared["within_corr_detrended"] is None
    assert shared["status"] == "shared_trend_not_tracking"
    assert shared["temporal_evidence"] is False

    # Counts grow, composition does not. Same constant mirror as witness 1.
    host_counts = {t: {"A": 9.0 * (1 + t), "B": 1.0 * (1 + t)} for t in range(40)}
    para_counts = {t: {"A": 1.0 * (1 + t), "B": 9.0 * (1 + t)} for t in range(40)}
    size_only = within_class_lagged_association(host_counts, para_counts, lag=_LAG)
    assert size_only["status"] == "no_temporal_variation"
    assert size_only["between_class_corr"] == -1.0
    assert size_only["temporal_evidence"] is False


def test_contemporaneous_match_is_not_a_lagged_peak() -> None:
    shares = _irregular_shares(48)
    series = _two_class(shares)
    result = within_class_lagged_association(series, series, lag=0)
    assert result["n_paired_times"] == 48
    assert float(result["within_corr_detrended"]) == pytest.approx(1.0)
    assert result["status"] == "contemporaneous_not_lagged"
    assert result["temporal_evidence"] is False


def test_non_finite_negative_and_bad_arguments_are_rejected() -> None:
    host = {0: {"A": 1.0}, 1: {"A": math.nan}}
    para = {0: {"A": 1.0}, 1: {"A": 1.0}}
    with pytest.raises(ValueError, match="finite"):
        within_class_lagged_association(host, para, lag=1)
    with pytest.raises(ValueError, match="finite"):
        within_class_lagged_association({0: {"A": -0.1}}, {1: {"A": 1.0}}, lag=1)
    with pytest.raises(ValueError, match="lag"):
        within_class_lagged_association({0: {"A": 1.0}}, {0: {"A": 1.0}}, lag=-1)
    with pytest.raises(ValueError, match="n_independent_runs"):
        within_class_lagged_association(
            {0: {"A": 1.0}}, {0: {"A": 1.0}}, lag=0, n_independent_runs=0
        )
    with pytest.raises(ValueError, match="min_paired_times"):
        within_class_lagged_association(
            {0: {"A": 1.0}}, {0: {"A": 1.0}}, lag=0, min_paired_times=True  # type: ignore[arg-type]
        )
