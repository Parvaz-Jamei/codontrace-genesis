"""Unit tests for lagged NFDS / frequency-clock helpers."""

from __future__ import annotations

import math

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.measurements.rq_frequency_clocks import (
    dominant_class_series,
    lagged_nfds_score,
    per_sublocus_richness_series,
    phase_lag_host_parasite,
)


def _anti_correlated_lagged_series(
    *,
    n_gens: int = 40,
    lag: int = 4,
) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]]:
    """Host high on A at t ⇒ parasite high on A at t+lag (then invert for neg corr).

    Build so host_freq(A,t) is anti-correlated with parasite_pressure(A,t+lag):
    when host A is high, future parasite A is low.
    """

    host: dict[int, dict[str, float]] = {}
    para: dict[int, dict[str, float]] = {}
    for t in range(n_gens):
        # Square wave: host A high on even blocks of `lag` gens.
        block = (t // lag) % 2
        if block == 0:
            host[t] = {"A": 0.8, "B": 0.2}
        else:
            host[t] = {"A": 0.2, "B": 0.8}
        # Parasite at t mirrors host at t-lag inverted → host(t) vs para(t+lag)
        # equals host(t) vs inverted host(t) after shift → negative corr.
        p_block = ((t - lag) // lag) % 2 if t >= lag else 1
        # Invert relative to host block at t-lag: if host was high A, para now high B.
        if p_block == 0:
            para[t] = {"A": 0.15, "B": 0.85}
        else:
            para[t] = {"A": 0.85, "B": 0.15}
    return host, para


def test_lagged_anti_correlated_passes_prelim() -> None:
    lag = 4
    host, para = _anti_correlated_lagged_series(lag=lag)
    result = lagged_nfds_score(
        host, para, lag=lag, min_points=20, threshold=0.3
    )
    assert "red_queen_proved" not in result
    assert result["n"] >= 20
    assert result["corr"] is not None
    assert math.isfinite(float(result["corr"]))
    assert float(result["corr"]) <= -0.3
    assert result["pass_prelim"] is True
    assert result["lag"] == lag


def test_contemporaneous_noise_fails_prelim() -> None:
    # Random-ish contemporaneous pairing: no systematic lag structure.
    host: dict[int, dict[str, float]] = {}
    para: dict[int, dict[str, float]] = {}
    for t in range(30):
        # Deterministic but uncorrelated-at-lag-0 noise pattern.
        host[t] = {"A": 0.5 + 0.1 * ((t * 3) % 5 - 2) / 2.0, "B": 0.5}
        # Renormalize loosely
        s = host[t]["A"] + host[t]["B"]
        host[t] = {"A": host[t]["A"] / s, "B": host[t]["B"] / s}
        para[t] = {"A": 0.5 + 0.1 * ((t * 7) % 5 - 2) / 2.0, "B": 0.5}
        s2 = para[t]["A"] + para[t]["B"]
        para[t] = {"A": para[t]["A"] / s2, "B": para[t]["B"] / s2}
    result = lagged_nfds_score(host, para, lag=0, min_points=20, threshold=0.3)
    assert "red_queen_proved" not in result
    assert result["pass_prelim"] is False


def test_never_emits_red_queen_proved_key() -> None:
    host = {0: {"A": 1.0}, 1: {"A": 0.0, "B": 1.0}}
    para = {0: {"A": 0.0, "B": 1.0}, 1: {"A": 1.0}}
    result = lagged_nfds_score(host, para, lag=1, min_points=2)
    assert "red_queen_proved" not in result
    assert "biological_red_queen_proved" not in result


def test_claimgate_still_refuses_red_queen_proved() -> None:
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")


def test_dominant_class_series_ordered() -> None:
    snaps = {
        50: {"dominant_joint": "a|b|c"},
        10: {"dominant_joint": "x|y|z"},
        25: {"joint_freq": {"p|q|r": 0.6, "a|b|c": 0.4}},
    }
    series = dominant_class_series(snaps)
    assert series == ["x|y|z", "p|q|r", "a|b|c"]


def test_per_sublocus_richness_from_joint_keys() -> None:
    snaps = {
        1: {"joint_freq": {"aa|bb|cc": 0.5, "aa|xx|cc": 0.5}},
        2: {"joint_freq": {"aa|bb|cc": 1.0}},
    }
    rich = per_sublocus_richness_series(snaps)
    assert rich["sublocus_0"] == [1, 1]
    assert rich["sublocus_1"] == [2, 1]
    assert rich["sublocus_2"] == [1, 1]


def test_phase_lag_summary_no_rq_flag() -> None:
    host = ["A", "A", "B", "B", "A", "A"]
    para = ["B", "B", "A", "A", "B", "B"]
    summary = phase_lag_host_parasite(host, para)
    assert "red_queen_proved" not in summary
    assert summary["n"] == 6
    assert summary["host_flips"] >= 1
    assert summary["parasite_flips"] >= 1
