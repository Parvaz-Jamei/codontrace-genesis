"""General statistical power analysis (stdlib only).

Used by the ClaimGate auditor: a bundle that declares a target effect size in
a top-level ``power_analysis`` object is checked for adequate power at its replicate count
(see ``auditor._power_findings``). Power is a *design* property: it is
computed for a declared, a-priori effect size, never from the observed effect
("observed power" is a monotone function of the p-value and adds no
information).

* t-tests (one-sample/paired, two-sample, one- or two-sided): exact power from
  the noncentral t distribution, computed by integrating
  the normal tail over the chi distribution of the variance estimate.
* Two proportions: normal approximation with the arcsine effect size
  h = 2 asin(sqrt(p1)) - 2 asin(sqrt(p2)).
* Anything else: Monte Carlo power from a user simulation, with draws from
  ``RNGManager`` and a score interval for the estimated proportion.

The t-test numbers are checked against scipy.stats.nct (when installed) and
against published sample-size tables in tests/test_claimgate_power.py.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from statistics import NormalDist

from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager

__all__ = [
    "PowerEstimate",
    "minimum_detectable_effect",
    "power_t_test",
    "power_two_proportions",
    "sample_size_t_test",
    "sample_size_two_proportions",
    "simulate_power",
    "t_cdf",
    "t_ppf",
]

_N = NormalDist()
_KINDS = ("one_sample", "paired", "two_sample")
_ALTS = ("two-sided", "greater")


# ---- Student t ---------------------------------------------------------------
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    if df <= 0:
        raise ConfigurationError("degrees of freedom must be positive")
    x = df / (df + t * t)
    tail = 0.5 * _betainc(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def t_ppf(p: float, df: float) -> float:
    if not 0.0 < p < 1.0:
        raise ConfigurationError("p must be in (0, 1)")
    lo, hi = -1.0, 1.0
    while t_cdf(lo, df) > p:
        lo *= 2.0
    while t_cdf(hi, df) < p:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return 0.5 * (lo + hi)


def _nct_sf(c: float, df: float, ncp: float) -> float:
    """P(T' > c) for noncentral t with ``df`` and noncentrality ``ncp``.

    T' = (Z + ncp) / U with U = sqrt(chi2_df / df); integrate over U.
    """
    # log-density of U = sqrt(V/df), V ~ chi2(df)
    k = df / 2.0
    log_norm = math.log(2.0) + k * math.log(k) - math.lgamma(k)

    def f(u: float) -> float:
        if u <= 0.0:
            # The density at u = 0 is 0 for df > 1 but exp(log_norm) for
            # df = 1 (U = |Z|, a half-normal). Returning 0 there under-weighted
            # the Simpson endpoint and biased P(T' > c) by up to 7e-4 at df = 1.
            return math.exp(log_norm) if df == 1.0 else 0.0
        return math.exp(log_norm + (df - 1.0) * math.log(u) - k * u * u)

    sd = 1.0 / math.sqrt(2.0 * df)
    lo = max(0.0, 1.0 - 12.0 * sd - 0.5 / math.sqrt(df))
    hi = 1.0 + 12.0 * sd + 1.0 / math.sqrt(df)
    n = 4000
    h = (hi - lo) / n
    total = 0.0
    for i in range(n + 1):
        u = lo + i * h
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        total += w * f(u) * (1.0 - _N.cdf(c * u - ncp))
    return min(1.0, max(0.0, total * h / 3.0))


def _t_design(kind: str, n: int, n2: int | None) -> tuple[float, float]:
    """(degrees of freedom, factor so that ncp = d * factor)."""
    if kind not in _KINDS:
        raise ConfigurationError(f"kind must be one of {_KINDS}")
    if kind == "two_sample":
        m = n if n2 is None else n2
        if n < 2 or m < 2:
            raise ConfigurationError("two-sample t needs at least 2 per group")
        return float(n + m - 2), math.sqrt(n * m / (n + m))
    if n < 2:
        raise ConfigurationError("one-sample/paired t needs at least 2 observations")
    return float(n - 1), math.sqrt(n)


def power_t_test(
    effect_size: float,
    n: int,
    *,
    alpha: float = 0.05,
    kind: str = "paired",
    alternative: str = "two-sided",
    n2: int | None = None,
) -> float:
    """Power of a t-test for standardized effect ``effect_size`` (standardized mean difference d, or d_z for paired data).

    ``n`` is the number of pairs/observations, or the size of group 1 for
    ``two_sample`` (``n2`` defaults to ``n``).
    """
    if not 0.0 < alpha < 1.0:
        raise ConfigurationError("alpha must be in (0, 1)")
    if alternative not in _ALTS:
        raise ConfigurationError(f"alternative must be one of {_ALTS}")
    if not math.isfinite(effect_size):
        raise ConfigurationError("effect size must be finite")
    df, factor = _t_design(kind, n, n2)
    ncp = effect_size * factor
    if alternative == "greater":
        return _nct_sf(t_ppf(1.0 - alpha, df), df, ncp)
    c = t_ppf(1.0 - alpha / 2.0, df)
    return _nct_sf(c, df, ncp) + _nct_sf(c, df, -ncp)


def sample_size_t_test(
    effect_size: float,
    *,
    power: float = 0.8,
    alpha: float = 0.05,
    kind: str = "paired",
    alternative: str = "two-sided",
    max_n: int = 100_000,
) -> int:
    """Smallest n (pairs, observations, or per group) reaching ``power``."""
    if effect_size == 0.0:
        raise ConfigurationError("a zero effect cannot be detected")
    if not 0.0 < power < 1.0:
        raise ConfigurationError("power must be in (0, 1)")

    def ok(m: int) -> bool:
        return power_t_test(effect_size, m, alpha=alpha, kind=kind, alternative=alternative) >= power

    lo, hi = 2, 2
    while not ok(hi):
        lo, hi = hi, hi * 2
        if hi > max_n:
            raise ConfigurationError(f"needs more than {max_n} per group")
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return hi


def minimum_detectable_effect(
    n: int, *, power: float = 0.8, alpha: float = 0.05, kind: str = "paired",
    alternative: str = "two-sided",
) -> float:
    """Smallest standardized effect detectable with ``power`` at sample size ``n``."""
    lo, hi = 0.0, 1.0
    while power_t_test(hi, n, alpha=alpha, kind=kind, alternative=alternative) < power:
        hi *= 2.0
        if hi > 1e6:
            raise ConfigurationError("no detectable effect at this sample size")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if power_t_test(mid, n, alpha=alpha, kind=kind, alternative=alternative) < power:
            lo = mid
        else:
            hi = mid
    return hi


# ---- proportions ---------------------------------------------------------------
def _cohen_h(p1: float, p2: float) -> float:
    for p in (p1, p2):
        if not 0.0 <= p <= 1.0:
            raise ConfigurationError("proportions must be in [0, 1]")
    return 2.0 * math.asin(math.sqrt(p1)) - 2.0 * math.asin(math.sqrt(p2))


def power_two_proportions(
    p1: float, p2: float, n1: int, n2: int | None = None, *, alpha: float = 0.05,
    alternative: str = "two-sided",
) -> float:
    m = n1 if n2 is None else n2
    if n1 < 1 or m < 1:
        raise ConfigurationError("group sizes must be positive")
    h = abs(_cohen_h(p1, p2))
    z = h * math.sqrt(n1 * m / (n1 + m))
    if alternative == "greater":
        return 1.0 - _N.cdf(_N.inv_cdf(1.0 - alpha) - z)
    c = _N.inv_cdf(1.0 - alpha / 2.0)
    return (1.0 - _N.cdf(c - z)) + _N.cdf(-c - z)


def sample_size_two_proportions(
    p1: float, p2: float, *, power: float = 0.8, alpha: float = 0.05, alternative: str = "two-sided"
) -> int:
    h = abs(_cohen_h(p1, p2))
    if h == 0.0:
        raise ConfigurationError("equal proportions cannot be distinguished")
    za = _N.inv_cdf(1.0 - (alpha if alternative == "greater" else alpha / 2.0))
    n = math.ceil(2.0 * ((za + _N.inv_cdf(power)) / h) ** 2)
    while power_two_proportions(p1, p2, n, alpha=alpha, alternative=alternative) < power:
        n += 1
    return n


# ---- simulation ----------------------------------------------------------------
@dataclass(frozen=True)
class PowerEstimate:
    power: float
    n_sim: int
    ci_low: float
    ci_high: float


def simulate_power(
    trial: Callable[[RNGManager], bool], *, n_sim: int = 1000, seed: int = 0, confidence: float = 0.95
) -> PowerEstimate:
    """Monte Carlo power: fraction of simulated studies in which ``trial`` rejects H0.

    Each study gets its own ``RNGManager`` stream (``fork``), so results are
    reproducible and studies are independent.
    """
    if n_sim < 1:
        raise ConfigurationError("n_sim must be positive")
    root = RNGManager(seed=seed, namespace="claimgate/power")
    hits = sum(1 for i in range(n_sim) if trial(root.fork(f"study/{i}")))
    p = hits / n_sim
    z = _N.inv_cdf(0.5 + confidence / 2.0)
    den = 1.0 + z * z / n_sim
    centre = (p + z * z / (2 * n_sim)) / den
    half = z * math.sqrt(p * (1 - p) / n_sim + z * z / (4 * n_sim * n_sim)) / den
    return PowerEstimate(p, n_sim, max(0.0, centre - half), min(1.0, centre + half))
