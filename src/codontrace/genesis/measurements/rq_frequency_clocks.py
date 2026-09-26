"""Lagged frequency clocks for Red Queen / NFDS measurement (Fork A scaffold).

Dybdahl & Lively (1998) style lagged association between host class
frequencies and parasite class pressure, plus dense-series extractors and a
simple phase/lag summary. Ashby (2020): polymorphism / cycle ≠ RQD.

Invariants
----------
* Pure functions: no ClaimGate side effects; never set ``red_queen_proved``.
* ``lagged_nfds_score`` is a **paired host↔parasite class series** with
  explicit lag τ. It must **not** alias or wrap dominant-flip oscillation
  detectors (``_oscillation_on_arm``).
* Callers must restrict RQ-earn / lag scoring to **debit-active** arms
  (coevolve / fixed); avirulent / absent arms never grant RQ-earn credit.
* ``regime_hostile_ne`` seeds are excluded from any lagged_nfds pass
  fraction by the runner, not by these helpers.
* Estimand default is Fork A (asexual clone RQD). Fork B / Slowinski and
  unpaid two-fold cost of sex remain deferred — helpers do not claim
  sex maintained by RQ.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Mapping, Sequence

DEFAULT_NFDS_THRESHOLD = 0.3


def dominant_class_series(
    snaps: Mapping[int, Mapping[str, object]],
) -> list[str | None]:
    """Ordered by generation key; uses snap['dominant_joint'] when present."""

    series: list[str | None] = []
    for gen in sorted(int(g) for g in snaps.keys()):
        snap = snaps[gen]
        if "dominant_joint" in snap:
            dom = snap.get("dominant_joint")
            series.append(None if dom is None else str(dom))
            continue
        freq = snap.get("joint_freq") or {}
        if not isinstance(freq, Mapping) or not freq:
            series.append(None)
            continue
        best = max(float(v) for v in freq.values())
        winners = sorted(str(k) for k, v in freq.items() if float(v) == best)
        series.append(winners[0] if winners else None)
    return series


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0.0 or var_y <= 0.0:
        return None
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    return cov / math.sqrt(var_x * var_y)


def lagged_nfds_score(
    host_class_freq: Mapping[int, Mapping[str, float]],
    parasite_infect_by_class: Mapping[int, Mapping[str, float]],
    *,
    lag: int,
    min_points: int,
    threshold: float = DEFAULT_NFDS_THRESHOLD,
) -> dict[str, object]:
    """Dybdahl–Lively style lagged association (paired class series + τ).

    Convention (host-leads, parasite follows)
    ----------------------------------------
    For every generation ``t`` where both maps have keys ``t`` and
    ``t + lag``, and for every class ``c`` present in either map at those
    times, pair:

        x = host frequency of ``c`` at ``t``
        y = parasite pressure on ``c`` at ``t + lag``

    then compute Pearson ``corr(x, y)`` across all such pairs.

    ``pass_prelim`` is True only when ``n >= min_points``, ``corr`` is
    finite, and ``corr <= -threshold`` (default threshold 0.3).
    Contemporaneous-only noise (lag=0 random) should fail.

    This function never sets ``red_queen_proved``. It is not an oscillation
    flip-count wrapper.
    """

    lag_i = int(lag)
    min_pts = int(min_points)
    thr = float(threshold)
    if lag_i < 0:
        raise ValueError("lag must be >= 0")
    if min_pts < 1:
        raise ValueError("min_points must be >= 1")

    host_gens = {int(g) for g in host_class_freq.keys()}
    para_gens = {int(g) for g in parasite_infect_by_class.keys()}
    xs: list[float] = []
    ys: list[float] = []
    for t in sorted(host_gens):
        t_lag = t + lag_i
        if t not in host_gens or t_lag not in para_gens:
            continue
        host_map = host_class_freq[t]
        para_map = parasite_infect_by_class[t_lag]
        classes = set(str(k) for k in host_map.keys()) | set(
            str(k) for k in para_map.keys()
        )
        for c in sorted(classes):
            xs.append(float(host_map.get(c, 0.0)))
            ys.append(float(para_map.get(c, 0.0)))

    n = len(xs)
    corr = _pearson(xs, ys) if n >= 2 else None
    finite = corr is not None and math.isfinite(corr)
    pass_prelim = bool(n >= min_pts and finite and corr is not None and corr <= -thr)
    return {
        "corr": corr if finite else None,
        "n": n,
        "pass_prelim": pass_prelim,
        "lag": lag_i,
        "min_points": min_pts,
        "threshold": thr,
        "convention": "host_freq_at_t__parasite_pressure_at_t_plus_lag",
    }


def per_sublocus_richness_series(
    snaps: Mapping[int, Mapping[str, object]],
) -> dict[str, list]:
    """Per-sublocus richness over generations (sorted by generation key).

    If snaps carry ``sub_locus_richness`` lists, use them. Otherwise derive
    richness from ``joint_freq`` keys shaped like ``'ab|cd|ef'`` (3 subloci).
    """

    gens = sorted(int(g) for g in snaps.keys())
    if not gens:
        return {}

    # Prefer explicit per-snap sub_locus_richness.
    first = snaps[gens[0]]
    n_loci = 0
    if isinstance(first.get("sub_locus_richness"), (list, tuple)):
        n_loci = len(first["sub_locus_richness"])  # type: ignore[arg-type]
    if n_loci <= 0:
        # Infer from joint keys.
        for gen in gens:
            freq = snaps[gen].get("joint_freq") or {}
            if isinstance(freq, Mapping):
                for key in freq.keys():
                    parts = str(key).split("|")
                    if len(parts) >= 2:
                        n_loci = max(n_loci, len(parts))
        if n_loci <= 0:
            n_loci = 3

    out: dict[str, list] = {f"sublocus_{i}": [] for i in range(n_loci)}
    for gen in gens:
        snap = snaps[gen]
        sub_rich = snap.get("sub_locus_richness")
        if isinstance(sub_rich, (list, tuple)) and len(sub_rich) >= n_loci:
            for i in range(n_loci):
                out[f"sublocus_{i}"].append(int(sub_rich[i]))
            continue
        # Derive from joint_freq keys 'a|b|c'.
        freq = snap.get("joint_freq") or {}
        allele_sets: list[set[str]] = [set() for _ in range(n_loci)]
        if isinstance(freq, Mapping):
            for key, val in freq.items():
                if float(val) <= 0.0:
                    continue
                parts = str(key).split("|")
                for i in range(min(n_loci, len(parts))):
                    allele_sets[i].add(parts[i])
        for i in range(n_loci):
            out[f"sublocus_{i}"].append(len(allele_sets[i]))
    return out


def phase_lag_host_parasite(
    host_dom: Sequence[str | None],
    parasite_dom: Sequence[str | None],
) -> dict[str, object]:
    """Simple phase/lag summary on dense dominant-class series.

    Reports host/parasite flip counts and a best-agreement lag guess over a
    small search window. Never sets ``red_queen_proved``.
    """

    n = min(len(host_dom), len(parasite_dom))
    host = list(host_dom[:n])
    para = list(parasite_dom[:n])

    def _flips(series: Sequence[str | None]) -> int:
        flips = 0
        prev: str | None = None
        started = False
        for val in series:
            if val is None:
                continue
            if not started:
                prev = val
                started = True
                continue
            if val != prev:
                flips += 1
                prev = val
        return flips

    host_flips = _flips(host)
    para_flips = _flips(para)

    max_lag = min(8, max(0, n // 4))
    best_lag = 0
    best_agree = -1
    agreements: dict[int, int] = {}
    for tau in range(0, max_lag + 1):
        agree = 0
        compared = 0
        for i in range(0, n - tau):
            h = host[i]
            p = para[i + tau]
            if h is None or p is None:
                continue
            compared += 1
            if h == p:
                agree += 1
        agreements[tau] = agree
        if compared > 0 and agree > best_agree:
            best_agree = agree
            best_lag = tau

    return {
        "n": n,
        "host_flips": host_flips,
        "parasite_flips": para_flips,
        "best_agreement_lag": best_lag,
        "agreement_by_lag": agreements,
        "same_index_agreement": agreements.get(0, 0),
    }


def parasite_pressure_from_hist(
    hist: Mapping[str, float] | Mapping[str, object],
) -> dict[str, float]:
    """Normalize a class histogram into a pressure map (sums to 1 if nonempty)."""

    raw = {str(k): float(v) for k, v in hist.items()}
    total = sum(raw.values())
    if total <= 0.0:
        return {}
    return {k: v / total for k, v in raw.items()}


def joint_freq_counter_to_map(
    pairs: Sequence[tuple[str, int]] | Mapping[str, float],
) -> dict[str, float]:
    """Convert count pairs or a frequency map into a frequency dict."""

    if isinstance(pairs, Mapping):
        return {str(k): float(v) for k, v in pairs.items()}
    counts = Counter({str(k): int(v) for k, v in pairs})
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: counts[k] / total for k in sorted(counts)}


__all__ = [
    "DEFAULT_NFDS_THRESHOLD",
    "dominant_class_series",
    "joint_freq_counter_to_map",
    "lagged_nfds_score",
    "parasite_pressure_from_hist",
    "per_sublocus_richness_series",
    "phase_lag_host_parasite",
]
