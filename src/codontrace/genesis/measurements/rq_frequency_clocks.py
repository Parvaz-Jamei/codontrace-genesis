"""Lagged frequency clocks for Red Queen / NFDS measurement (Fork A scaffold).

Dybdahl & Lively (1998) style lagged association between host class
frequencies and parasite class pressure, plus dense-series extractors and a
simple phase/lag summary. Ashby (2020): polymorphism / cycle ≠ RQD.

Measurement vocabulary (2026-09-28 split)
----------------------------------------
Two quantities that were previously conflated are now separate:

1. **Parasite class frequency** — the class histogram of the parasite
   population (``parasite_class_hist`` / ``parasite_class_hist_series`` in the
   structural arm, consumed here as ``parasite_infect_by_class``). It is a
   *parasite genotype/class frequency*: it counts antagonists, it is **not**
   the pressure acting on a host class, and it is blind to the contact rule.
2. **Realised conditional pressure on a host class** — computed from the
   actual contact/effect rules (graded affinity, ATP debit, survival) over the
   full host × parasite interaction under equal exposure. See
   :func:`realised_conditional_host_pressure` and
   :func:`host_realised_pressure_from_contacts` for the exact formula.

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
from collections.abc import Mapping, Sequence
from typing import Any

from codontrace.dynvalues import same_float
from codontrace.rng import RNGManager

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


# --- Realised conditional host pressure (P0.1 measurement separation) --------

#: Bits per sub-locus in the recognition window (3 sub-loci × 2 bits = 6 bits).
_SUB_LOCUS_BIT_WIDTH = 2
#: Number of sub-loci in the recognition window.
_N_SUB_LOCI = 3
#: Default per-contact ATP debit per unit affinity (structural arm locks).
_DEFAULT_VIRULENCE = 8.0
#: Default fraction of host runtime ATP taken per unit affinity (structural arm locks).
_DEFAULT_STEAL_FRACTION = 0.15
#: Rounding used for reported pressure values (10 dp, repo convention).
_PRESSURE_DP = 10

#: Engine-exact one-seat-per-pair rule (``StructuralRQArm._apply_hp_env_contact``).
CONTACT_MODE_ENGINE_SEATS = "engine_seats"
#: Full host × parasite cross product with uniform per-pair multiplicity.
CONTACT_MODE_FULL_MATRIX = "full_matrix"
CONTACT_MODES = (CONTACT_MODE_ENGINE_SEATS, CONTACT_MODE_FULL_MATRIX)


def reference_graded_affinity(host_window: str, parasite_window: str) -> float:
    """Reference affinity law: mean over sub-loci of per-locus bit agreement.

    ``A(h, p) = (1/L) * Σ_l (agree_l(h, p) / w)`` with ``L = 3`` sub-loci of
    ``w = 2`` bits, so ``A ∈ {0, 1/6, …, 1}``. This is a measurement-side
    mirror of ``closed_loop_hp_arm01_structural_rq.graded_affinity``; that
    function stays the engine authority. Raises ``ValueError`` on a window
    whose width is not ``L * w``.
    """

    width = _N_SUB_LOCI * _SUB_LOCUS_BIT_WIDTH
    if len(host_window) != width or len(parasite_window) != width:
        raise ValueError(f"recognition windows must be {width} bits")
    scores: list[float] = []
    for offset in range(0, width, _SUB_LOCUS_BIT_WIDTH):
        h = host_window[offset : offset + _SUB_LOCUS_BIT_WIDTH]
        p = parasite_window[offset : offset + _SUB_LOCUS_BIT_WIDTH]
        agree = sum(1 for a, b in zip(h, p, strict=True) if a == b)
        scores.append(agree / float(_SUB_LOCUS_BIT_WIDTH))
    return float(sum(scores) / len(scores))


def affinity_matrix(
    host_windows: Mapping[str, str],
    parasite_windows: Mapping[str, str],
) -> dict[str, dict[str, float]]:
    """Full host-class × parasite-class contact-quality matrix ``A[h][p]``."""

    return {
        str(h): {
            str(p): reference_graded_affinity(str(hw), str(pw))
            for p, pw in parasite_windows.items()
        }
        for h, hw in host_windows.items()
    }


def realised_conditional_host_pressure(
    host_class_windows: Mapping[str, str],
    parasite_class_windows: Mapping[str, str],
    *,
    parasite_class_counts: Mapping[str, int | float] | None = None,
    contact_mode: str = CONTACT_MODE_FULL_MATRIX,
    virulence: float = _DEFAULT_VIRULENCE,
    steal_fraction: float = _DEFAULT_STEAL_FRACTION,
    host_per_contact_units: float | Mapping[str, float] = 1.0,
    host_capacity_units: float | Mapping[str, float] | None = None,
    contact_matrix: Mapping[str, Mapping[str, float]] | None = None,
    affinity: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, object]:
    """Realised conditional pressure on a host class under equal exposure.

    Definition (directive P0.1(b))
    -----------------------------
    Let ``H`` be the host classes with recognition windows ``h``, ``P`` the
    parasite classes with windows ``p``, ``A(h, p)`` the graded affinity of the
    model's contact rule (default: :func:`reference_graded_affinity`, injectable
    through ``affinity``/``contact_matrix`` for a different affinity family),
    ``κ`` the per-contact ATP debit per unit affinity
    (``κ = virulence × steal_fraction``), and ``R(h)`` the per-host ATP reserve
    available before the contact round. The contact matrix used is
    *exposure-fixed*: under ``contact_mode='full_matrix'`` every host class
    faces every parasite class with uniform multiplicity,

        C(h, p) = E     for all (h, p)     (equal exposure; E = 1 by default),

    and under ``contact_mode='engine_seats'`` ``C`` is the one-seat-per-pair
    matrix reproduced from ``StructuralRQArm._apply_hp_env_contact`` (host
    classes registered in address order, each parasite seat meeting exactly one
    host). The engine rotates that register per tick to avoid index-0 bias; the
    measurement kernel keeps the unrotated register so ``C`` is a function of
    the class tally under equal exposure rather than of one run's tick phase.

    The **realised conditional pressure** on host class ``h`` is the mean ATP
    actually debited per host of class ``h`` over that contact matrix,
    normalised per host generation:

        P(h) = Π(h) × ( Σ_p C(h, p) × min[ c(h), κ × A(h, p) ] )
                         / ( Σ_p C(h, p) )

    where

        Π(h)  = host_per_contact_units(h)   (default 1 contact per host per round)
        c(h)  = R(h) when ``host_capacity_units`` is given, else ∞
                (``host_capacity_units`` is the per-host ATP reserve available
                before the contact round; the engine uses the observed
                pre-contact ``runtime_available`` of each host)

    Units: ATP per host per generation (reserve-currency units; ``0`` when the
    host class is never contacted, ``min[R(h), Π κ]`` at saturation).

    Survivorship is encoded in the ``min``: a host of class ``h`` survives the
    round iff its pre-contact reserve exceeds the debit, i.e. iff
    ``c(h) > κ A(h, p)``; the branch ``min = κ A`` is the surviving branch and
    the branch ``min = c`` is the lethal branch. Because a dead host's loss is
    capped at its reserve, the pressure is *not* proportional to ``κ A`` and
    the survival signal cannot be read off the affinity sum alone.

    Explicit non-dependence
    -----------------------
    ``parasite_class_counts`` enters only through the *classes present*; it is
    the engine's own class multiset (counts of antagonists). The returned
    pressure is **invariant to any rescaling of the counts** (duplicating every
    parasite class leaves the per-host mean effect unchanged), so the parasite
    class histogram — including its normalised shape — is not the estimand.
    Class frequencies are neither an input nor an output of this function.

    The contact matrix ``C``, the affinity matrix ``A`` and the reserve
    ``R(h)`` are the only determinants of ``P``: two worlds with the same
    ``C``/``A``/``R`` but different parasite class histograms give identical
    pressure, and two worlds with the same histogram but different ``A``/``R``
    give different pressure.
    """

    if contact_mode not in CONTACT_MODES:
        raise ValueError(f"contact_mode must be one of {CONTACT_MODES!r}")

    host_ids = [str(h) for h in host_class_windows]
    para_ids = [str(p) for p in parasite_class_windows]
    # Counts are validated but never enter the law; they only label the multiset
    # of parasite classes actually present. No frequency is computed here.
    counts = (
        {str(p): float(c) for p, c in parasite_class_counts.items()}
        if parasite_class_counts is not None
        else {p: 1.0 for p in para_ids}
    )
    unknown = sorted(set(counts) - set(para_ids))
    if unknown:
        raise ValueError(f"parasite_class_counts has unknown classes: {unknown}")

    aff = (
        {
            str(h): {str(p): float(v) for p, v in row.items()}
            for h, row in affinity.items()
        }
        if affinity is not None
        else affinity_matrix(host_class_windows, parasite_class_windows)
    )
    if contact_matrix is not None:
        cm = {
            str(h): {str(p): float(v) for p, v in row.items()}
            for h, row in contact_matrix.items()
        }
    elif contact_mode == CONTACT_MODE_FULL_MATRIX:
        cm = {h: {p: 1.0 for p in para_ids} for h in host_ids}
    else:  # CONTACT_MODE_ENGINE_SEATS
        cm = _engine_seat_contact_matrix(host_ids, para_ids)

    if isinstance(host_per_contact_units, Mapping):
        per_host = {h: float(host_per_contact_units.get(h, 0.0)) for h in host_ids}
    else:
        per_host = {h: float(host_per_contact_units) for h in host_ids}
    if host_capacity_units is None:
        cap = {h: math.inf for h in host_ids}
    elif isinstance(host_capacity_units, Mapping):
        cap = {h: float(host_capacity_units.get(h, 0.0)) for h in host_ids}
    else:
        cap = {h: float(host_capacity_units) for h in host_ids}

    kappa = float(virulence) * float(steal_fraction)
    pressure: dict[str, float] = {}
    affinity_sum: dict[str, float] = {}
    contact_count: dict[str, float] = {}
    survival: dict[str, float] = {}
    for h in host_ids:
        row = {str(p): float(c) for p, c in cm.get(h, {}).items()}
        total_contacts = sum(row.values())
        if total_contacts <= 0.0:
            pressure[h] = 0.0
            affinity_sum[h] = 0.0
            contact_count[h] = 0.0
            survival[h] = 0.0
            continue
        reserve = cap[h]
        # Preregistered "no budget competition in the measurement kernel" clause:
        # every contact of a host class is evaluated against its own pre-contact
        # reserve (each contact is the host's whole round), so no cumulative
        # saturation artefact is introduced here. The engine's one-seat rule
        # gives exactly one contact per host per round anyway.
        debited = 0.0
        aff_product = 0.0
        lethal_weight = 0.0
        for p, multiplicity in sorted(row.items()):
            a_hp = float(aff.get(h, {}).get(p, 0.0))
            per_contact_effect = min(reserve, kappa * a_hp)
            debited += multiplicity * per_contact_effect
            aff_product += multiplicity * a_hp
            if per_contact_effect >= reserve:
                lethal_weight += multiplicity
        policy = per_host[h]
        pressure[h] = round(policy * debited / total_contacts, _PRESSURE_DP)
        affinity_sum[h] = round(aff_product / total_contacts, _PRESSURE_DP)
        contact_count[h] = total_contacts
        survival[h] = round(1.0 - lethal_weight / total_contacts, _PRESSURE_DP)

    return {
        "pressure": pressure,
        "pressure_units": "atp_per_host_per_generation",
        "affinity_sum": affinity_sum,
        "contact_count": contact_count,
        "survival_fraction": survival,
        "contact_matrix": cm,
        "affinity": aff,
        "kappa": kappa,
        "contact_mode": contact_mode,
        "equal_exposure": {
            "full_matrix": contact_mode == CONTACT_MODE_FULL_MATRIX,
            "per_host_contact_policy": dict(per_host),
            "host_capacity_units": {
                h: (None if math.isinf(cap[h]) else cap[h]) for h in host_ids
            },
        },
        "host_classes": list(host_ids),
        "parasite_classes": list(para_ids),
        "host_class_windows": {str(h): str(w) for h, w in host_class_windows.items()},
        "parasite_class_windows": {
            str(p): str(w) for p, w in parasite_class_windows.items()
        },
        "parasite_class_counts": dict(counts),
        "histogram_used": False,
        "class_frequency_used": False,
        "red_queen_proved": False,
    }


def _engine_seat_contact_matrix(
    host_ids: Sequence[str],
    para_ids: Sequence[str],
) -> dict[str, dict[str, float]]:
    """Contact multiplicities of the engine's one-seat-per-pair rule.

    Mirrors ``StructuralRQArm._apply_hp_env_contact``: ``pair_n =
    min(len(hosts), len(parasites))`` and seat ``i`` pairs host ``i`` with
    parasite ``i``. Under equal exposure the host-class register is *not*
    rotated (every host class would otherwise see a different slice of the
    parasite multiset, so the class-level contact matrix could not be written
    down without the class sizes); rotation is an engine-side sampling device,
    not part of the estimand. This reproduces the engine matrix exactly when
    the host list is class-contiguous with equal multiplicities.
    """

    pair_n = min(len(host_ids), len(para_ids))
    cm: dict[str, dict[str, float]] = {h: {} for h in host_ids}
    for seat in range(pair_n):
        host = host_ids[seat]
        para = para_ids[seat]
        cm[host][para] = cm[host].get(para, 0.0) + 1.0
    return cm


def host_realised_pressure_from_contacts(
    *,
    host_affinity_sums: Mapping[str, float],
    host_contact_counts: Mapping[str, int | float],
    host_min_available: Mapping[str, float] | None = None,
    host_per_contact_units: float | Mapping[str, float] = 1.0,
    virulence: float = _DEFAULT_VIRULENCE,
    steal_fraction: float = _DEFAULT_STEAL_FRACTION,
) -> dict[str, float]:
    """Per-class realised pressure from observed contacts (engine-callable).

    Applies the same law as :func:`realised_conditional_host_pressure` to the
    generation's *observed* contact records instead of a synthetic matrix:

        P_obs(h) = Π(h) × min[ c(h), κ × Ā(h) ]

    with ``κ = virulence × steal_fraction``, ``c(h) = host_min_available(h)``
    the per-host ATP reserve observed before the contact round (omit it to use
    the cap-free branch ``c(h) = ∞``), and
    ``Ā(h) = host_affinity_sums(h) / host_contact_counts(h)`` the mean realised
    affinity over that class's contacts. Host classes come from
    ``host_affinity_sums``; ``host_contact_counts`` must be accumulated over the
    same contact round and for the same classes. Units: ATP per host per
    generation. ``0.0`` for a class with no recorded contact.
    """

    per_host_map = host_per_contact_units if isinstance(host_per_contact_units, Mapping) else None
    reserve = {str(h): float(v) for h, v in (host_min_available or {}).items()}
    kappa = float(virulence) * float(steal_fraction)
    out: dict[str, float] = {}
    for key in sorted({str(h) for h in host_affinity_sums} | {str(h) for h in host_contact_counts}):
        cls = str(key)
        if per_host_map is not None:
            policy = float(per_host_map.get(cls, 0.0))
        else:
            policy = same_float(host_per_contact_units)
        aff_sum = float(host_affinity_sums.get(cls, 0.0))
        contacts = float(host_contact_counts.get(cls, 0) or 0.0)
        if contacts <= 0.0:
            out[cls] = 0.0
            continue
        a_obs = aff_sum / contacts
        capacity = reserve[cls] if cls in reserve else math.inf
        out[cls] = round(policy * min(capacity, kappa * a_obs), _PRESSURE_DP)
    return out


# --- Frequency-swap mechanism statistic (campaign rq_redesign_20260928) ------
#
# The campaign's mechanism estimand is the swap-signal
# (`SCIENTIFIC_QUESTION_AND_DAG.md` section 6.1, `PREREG_V2.md` section 4.2):
#
#     S = pi_A(swap) - pi_A(swap^-1)
#
# where `pi_A` is the realised conditional pressure on the designated class `A`
# (:func:`realised_conditional_host_pressure`), `swap` is the counterfactual in
# which the host class frequencies of the designated common and designated rare
# class are exchanged in place while the census, the resource state, the host
# genotype multiset, the contact count and the random stream are held fixed, and
# `swap^-1` is the matched inverse counterfactual. The exchange is an
# involution, so applying `swap^-1` to the swapped assignment restores the
# baseline and the inverse counterfactual is the unswapped world.
#
# The pre-registered expectation is `S < 0` with `|S| >= 0.20` ATP per host per
# contact opportunity (T9); every counter-sample must give `S = 0`.
#
# These helpers are additive. They do not touch `lagged_nfds_score`, any
# pre-registered threshold, any recorded number or any decision branch.

#: Pre-registered run-level cluster-bootstrap resample count (`PREREG_V2.md` T17).
DEFAULT_CLUSTER_BOOTSTRAP_RESAMPLES = 10_000
#: Pre-registered cluster-bootstrap seed (`PREREG_V2.md` T18).
DEFAULT_CLUSTER_BOOTSTRAP_SEED = 20260928
#: Auditor floor from STATS_AND_NULL_DESIGN.md section 6. It is the smallest n
#: at which this percentile interval may be read as an inferential statement.
#: It is not a power-based confirmatory sample size, and n>=2 is not enough.
CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS = 16
CLUSTER_BOOTSTRAP_METHOD = "run_level_cluster_bootstrap_percentile_v2"
HISTORICAL_CLUSTER_BOOTSTRAP_METHOD = "run_level_cluster_bootstrap_percentile"
#: Units of the swap-signal (same currency as :func:`realised_conditional_host_pressure`).
SWAP_SIGNAL_UNITS = "atp_per_host_per_contact_opportunity"


def exchange_class_shares(
    shares: Mapping[str, float],
    class_a: str,
    class_b: str,
) -> dict[str, float]:
    """Exchange the shares of two classes in place, leaving the rest untouched.

    This is the frequency-swap intervention: population size (`sum(shares)`),
    every other class share, the resource state, the host genotype multiset and
    the contact count are unchanged; only which class carries which share moves.
    The exchange is an involution, so applying it to its own output returns the
    input.
    """

    a, b = str(class_a), str(class_b)
    if a == b:
        raise ValueError("class_a and class_b must be distinct")
    out = {str(k): float(v) for k, v in shares.items()}
    out[a], out[b] = out.get(b, 0.0), out.get(a, 0.0)
    return out


def frequency_swap_signal(
    pressure_swap: Mapping[int, float],
    pressure_inverse: Mapping[int, float],
    *,
    window: Sequence[int] | None = None,
    instantaneous_generation: int | None = None,
) -> dict[str, object]:
    """Swap-signal ``S = pi_A(swap) - pi_A(swap^-1)`` on one run's paired series.

    Parameters
    ----------
    pressure_swap, pressure_inverse
        Per-generation realised conditional pressure on the *designated* class
        `A` in the swapped and in the inverse (unswapped) counterfactual, keyed
        by generation boundary. The two counterfactuals must share the same
        census, resource state, host genotype multiset, contact count and random
        stream; only the frequency assignment differs.
    window
        Generations averaged over. Defaults to the sorted intersection of the
        two key sets. The mechanism acts through the delayed adaptation channel
        (`SCIENTIFIC_QUESTION_AND_DAG.md` L5-L8), so a window strictly after the
        swap boundary is what carries the signal.
    instantaneous_generation
        Optional generation at which the lag-0 component is also reported.

    Returns a mapping with `s`, the two window means, the window used, the
    optional `instantaneous_component` (zero whenever the contact matrix is
    held fixed, because under equal exposure the per-opportunity pressure on a
    class does not depend on that class' own share) and the literal definition.
    """

    swap = {int(g): float(v) for g, v in pressure_swap.items()}
    inverse = {int(g): float(v) for g, v in pressure_inverse.items()}
    if window is None:
        used = sorted(set(swap) & set(inverse))
    else:
        used = sorted(int(g) for g in window)
    if not used:
        raise ValueError("the swap window is empty")
    missing = [g for g in used if g not in swap or g not in inverse]
    if missing:
        raise ValueError(f"swap window generations missing from a series: {missing}")
    mean_swap = sum(swap[g] for g in used) / len(used)
    mean_inverse = sum(inverse[g] for g in used) / len(used)

    out: dict[str, object] = {
        "s": mean_swap - mean_inverse,
        "mean_swap": mean_swap,
        "mean_inverse": mean_inverse,
        "window": used,
        "n_generations": len(used),
        "units": SWAP_SIGNAL_UNITS,
        "definition": "s = pi_A(swap) - pi_A(swap^-1)",
        "instantaneous_generation": None,
        "instantaneous_component": None,
    }
    if instantaneous_generation is not None:
        g0 = int(instantaneous_generation)
        out["instantaneous_generation"] = g0
        out["instantaneous_component"] = swap.get(g0, 0.0) - inverse.get(g0, 0.0)
    return out


def run_level_cluster_bootstrap_interval(
    run_values: Sequence[float],
    *,
    n_resamples: int = DEFAULT_CLUSTER_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_CLUSTER_BOOTSTRAP_SEED,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Percentile cluster bootstrap over runs (the unit of replication).

    A run is one cluster. Resampling runs with replacement is the interval
    method in ``STATS_AND_NULL_DESIGN.md`` section 2. Generation-level values
    are never resampled here.

    ``n_resamples`` is not a sample size. One run cannot estimate between-run
    variability, so it is not an interval and ``excludes_zero`` is false no
    matter how many times that single value is redrawn. A sample with no
    between-run variance is the same: the point estimate is kept and no
    confidence interval is invented at that point. Fewer than
    ``CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS`` runs can still return a
    descriptive percentile, but that percentile is not an inferential decision.
    Meeting the floor is necessary for this method and is still not a
    power-based confirmatory n.
    """

    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    if not run_values:
        raise ValueError("run_values is empty")
    values: list[float] = []
    for value in run_values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("run_values must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("run_values must be finite numbers")
        values.append(number)

    n = len(values)
    point = sum(values) / n
    base = {
        "point": point,
        "n_runs": n,
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "alpha": float(alpha),
        "method": CLUSTER_BOOTSTRAP_METHOD,
        "historical_method": HISTORICAL_CLUSTER_BOOTSTRAP_METHOD,
        "unit_of_replication": "run",
        "design_min_runs": CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS,
        "design_floor_source": "STATS_AND_NULL_DESIGN.md section 6 auditor floor; not a power calculation",
    }
    if n < 2:
        return {
            **base,
            "lo": point,
            "hi": point,
            "interval_defined": False,
            "inferential_eligible": False,
            "excludes_zero": False,
            "percentile_excludes_zero": False,
            "status": "insufficient_runs",
            "variability": "between_run_variability_not_estimable",
        }
    variance = sum((value - point) ** 2 for value in values) / (n - 1)
    if variance <= 0.0:
        return {
            **base,
            "lo": point,
            "hi": point,
            "interval_defined": False,
            "inferential_eligible": False,
            "excludes_zero": False,
            "percentile_excludes_zero": False,
            "status": "degenerate_variance",
            "variability": "no_between_run_variance",
        }

    rng = RNGManager(seed=int(seed), namespace="run_level_cluster_bootstrap")
    samples: list[float] = []
    for _ in range(n_resamples):
        total = 0.0
        for _ in range(n):
            total += values[rng.randrange(n)]
        samples.append(total / n)
    samples.sort()

    def _percentile(q: float) -> float:
        if len(samples) == 1:
            return samples[0]
        pos = q * (len(samples) - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(samples) - 1)
        frac = pos - lo
        return samples[lo] * (1.0 - frac) + samples[hi] * frac

    lo = _percentile(float(alpha) / 2.0)
    hi = _percentile(1.0 - float(alpha) / 2.0)
    percentile_excludes = bool(lo > 0.0 or hi < 0.0)
    eligible = n >= CLUSTER_BOOTSTRAP_AUDITOR_FLOOR_RUNS
    return {
        **base,
        "lo": lo,
        "hi": hi,
        "interval_defined": True,
        "inferential_eligible": eligible,
        "excludes_zero": bool(eligible and percentile_excludes),
        "percentile_excludes_zero": percentile_excludes,
        "status": "percentile_interval" if eligible else "below_auditor_floor",
        "variability": "between_run",
    }


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

        x = host class frequency of ``c`` at ``t``
        y = **parasite class frequency** of ``c`` at ``t + lag``

    then compute Pearson ``corr(x, y)`` across all such pairs.

    ``parasite_infect_by_class`` is a *parasite class frequency* (how many
    antagonists carry class ``c``), **not** the realised pressure acting on a
    host class. The empirical pressure estimand is
    :func:`realised_conditional_host_pressure` /
    :func:`host_realised_pressure_from_contacts`; it is deliberately not
    derived from this histogram. The argument name is retained for backward
    compatibility of the public signature.

    ``pass_prelim`` is True only when ``n >= min_points``, ``corr`` is
    finite, and ``corr <= -threshold`` (default threshold 0.3).
    Contemporaneous-only noise (lag=0 random) should fail.

    Historical pooled estimator, kept for reproducibility. ``n`` counts
    class×time pairs, not paired generations and not independent runs. A
    time-invariant contrast between classes (no change along time) can
    therefore yield ``corr == -1`` and ``pass_prelim is True``. That pass is
    not temporal evidence. The versioned temporal estimand is
    :func:`within_class_lagged_association`; it does not rewrite this result
    and it does not treat a negative correlation as NFDS.

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


# --- Within-class lagged association (temporal estimand v1) ------------------
#
# ``lagged_nfds_score`` stays the historical pooled Pearson. The function below
# is a separately versioned estimand. It does not edit archived numbers.
#
# Dybdahl & Lively (1998), Evolution 52(4):1057–1066,
# doi:10.1111/j.1558-5646.1998.tb01833.x, correlated *changes* in clone
# frequency with a lagged change in infection, and the association peaked at a
# lag rather than at the same generation. Pooling every class×time pair lets a
# constant between-class contrast impersonate that result.
#
# The within-class correlation removes each class mean first (the panel within
# transformation), so a time-invariant difference between classes cannot pass.
# A circular shift of the parasite series, applied once to every class, is the
# predetermined null: it keeps each series' autocorrelation and the
# cross-class composition (Theiler et al. 1992, Physica D 58:77–94, surrogate
# principle). The observed alignment is included, so the test cannot reject at
# alpha 0.05 with fewer than 20 paired times. That floor is locked here; a
# caller cannot lower it by adding classes or by passing a smaller minimum.
#
# Expected sign is not "negative means NFDS". It is read from this model's
# recognition rule, :func:`reference_graded_affinity`: agreement of bits raises
# affinity and therefore the ATP debit. The parasite class that carries a host
# class's window is the matching type. Tracking means that class becomes more
# common after the host class was common, which is a positive within-class
# lag, not a negative one.

TEMPORAL_ASSOCIATION_ESTIMATOR = "within_class_lagged_association_v1"
TEMPORAL_NULL_METHOD = "circular_time_shift_shared"
TEMPORAL_NULL_ALPHA = 0.05
# Inclusive shift enumeration: the smallest p is 1/n, so n >= ceil(1/alpha).
MIN_PAIRED_TIMES_FLOOR = 20
RECOGNITION_RULE_MATCHING = "graded_affinity_bit_agreement"
_WITHIN_SS_EPS = 1e-18
_NULL_TIE_EPS = 1e-9


def expected_lag_sign(recognition_rule: str = RECOGNITION_RULE_MATCHING) -> int:
    """Sign implied by the contact rule. Negative is not treated as NFDS.

    ``graded_affinity_bit_agreement`` is the model's graded match
    (:func:`reference_graded_affinity`). Affinity, and the ATP debit that
    follows it, increase with bit agreement. The parasite class labelled with
    a host class's own window is the type that presses that host. Adaptation
    that tracks previously common hosts therefore raises the frequency of
    class ``c`` after host class ``c`` was common: the within-class
    correlation of host frequency at ``t`` with parasite frequency of the same
    class at ``t + lag`` is predicted to be positive.
    """

    if recognition_rule != RECOGNITION_RULE_MATCHING:
        raise ValueError(
            "unsupported recognition rule "
            f"{recognition_rule!r}; the model rule is {RECOGNITION_RULE_MATCHING!r}"
        )
    return 1


def _as_frequency_map(raw: Mapping[Any, Any], *, generation: int) -> dict[str, float]:
    """Renormalize one generation. A pure change of population size drops out."""

    if isinstance(raw, (str, bytes)) or not isinstance(raw, Mapping):
        raise ValueError(f"generation {generation} must be a class-frequency map")
    cleaned: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"frequency at generation {generation} class {key!r} must be a finite number >= 0"
            )
        number = float(value)
        if not math.isfinite(number) or number < 0.0:
            raise ValueError(
                f"frequency at generation {generation} class {key!r} must be finite and >= 0"
            )
        cleaned[str(key)] = number
    total = sum(cleaned.values())
    if total <= 0.0:
        return {key: 0.0 for key in cleaned}
    return {key: value / total for key, value in cleaned.items()}


def _class_demeaned(values: Sequence[float]) -> list[float]:
    mean = sum(values) / len(values)
    return [value - mean for value in values]


def _sum_of_squares(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values)


def _linear_detrend(values: Sequence[float]) -> list[float] | None:
    """Remove a within-class linear time trend. ``None`` if the fit is undefined."""

    n = len(values)
    if n < 3:
        return None
    mean_i = (n - 1) / 2.0
    mean_v = sum(values) / n
    var_i = sum((index - mean_i) ** 2 for index in range(n))
    if var_i <= 0.0:
        return None
    cov = sum((index - mean_i) * (value - mean_v) for index, value in enumerate(values))
    slope = cov / var_i
    intercept = mean_v - slope * mean_i
    return [value - (intercept + slope * index) for index, value in enumerate(values)]


def _frequency_panel(
    host_class_freq: Mapping[int, Mapping[str, float]],
    parasite_class_freq: Mapping[int, Mapping[str, float]],
    *,
    lag: int,
) -> tuple[list[int], list[str], dict[str, list[float]], dict[str, list[float]]]:
    host_at = {
        int(gen): _as_frequency_map(freqs, generation=int(gen))
        for gen, freqs in host_class_freq.items()
    }
    para_at = {
        int(gen): _as_frequency_map(freqs, generation=int(gen))
        for gen, freqs in parasite_class_freq.items()
    }
    times = sorted(gen for gen in host_at if gen + lag in para_at)
    classes = sorted(
        {
            class_id
            for gen in times
            for class_id in set(host_at[gen]) | set(para_at[gen + lag])
        }
    )
    host_series: dict[str, list[float]] = {class_id: [] for class_id in classes}
    para_series: dict[str, list[float]] = {class_id: [] for class_id in classes}
    for gen in times:
        host_map = host_at[gen]
        para_map = para_at[gen + lag]
        for class_id in classes:
            host_series[class_id].append(host_map.get(class_id, 0.0))
            para_series[class_id].append(para_map.get(class_id, 0.0))
    return times, classes, host_series, para_series


def _pooled_within_corr(
    host_series: Mapping[str, Sequence[float]],
    para_series: Mapping[str, Sequence[float]],
    *,
    detrend: bool,
) -> float | None:
    xs: list[float] = []
    ys: list[float] = []
    for class_id in host_series:
        if detrend:
            left = _linear_detrend(host_series[class_id])
            right = _linear_detrend(para_series[class_id])
            if left is None or right is None:
                return None
        else:
            left = _class_demeaned(host_series[class_id])
            right = _class_demeaned(para_series[class_id])
        if sum(value * value for value in left) <= _WITHIN_SS_EPS:
            continue
        if sum(value * value for value in right) <= _WITHIN_SS_EPS:
            continue
        xs.extend(left)
        ys.extend(right)
    if len(xs) < 2:
        return None
    return _pearson(xs, ys)


def _between_class_corr(
    host_series: Mapping[str, Sequence[float]],
    para_series: Mapping[str, Sequence[float]],
) -> float | None:
    if not host_series:
        return None
    host_means = [sum(host_series[key]) / len(host_series[key]) for key in host_series]
    para_means = [sum(para_series[key]) / len(para_series[key]) for key in host_series]
    return _pearson(host_means, para_means)


def _circular_shift_p(
    host_series: Mapping[str, Sequence[float]],
    para_series: Mapping[str, Sequence[float]],
    *,
    observed: float,
    sign: int,
) -> float:
    """One-sided p from a shared circular shift of every class's parasite series."""

    n_times = len(next(iter(para_series.values())))
    as_extreme = 0
    for shift in range(n_times):
        shifted = {
            class_id: list(values[shift:]) + list(values[:shift])
            for class_id, values in para_series.items()
        }
        corr = _pooled_within_corr(host_series, shifted, detrend=True)
        if corr is not None and sign * corr >= sign * observed - _NULL_TIE_EPS:
            as_extreme += 1
    return as_extreme / n_times


def within_class_lagged_association(
    host_class_freq: Mapping[int, Mapping[str, float]],
    parasite_class_freq: Mapping[int, Mapping[str, float]],
    *,
    lag: int,
    min_paired_times: int = MIN_PAIRED_TIMES_FLOOR,
    n_independent_runs: int = 1,
    recognition_rule: str = RECOGNITION_RULE_MATCHING,
) -> dict[str, object]:
    """Within-class lagged association. Not a rewrite of ``lagged_nfds_score``.

    Counts that stay separate
    -------------------------
    ``n_paired_times`` is the number of generations ``t`` at which both ``t``
    and ``t + lag`` exist. ``n_classes`` is the number of classes in those
    maps. ``n_independent_runs`` is only what the caller declares (default 1);
    it is never inferred by repeating class×time pairs. ``n_class_time_pairs``
    is the historical ``n`` and is not the sufficiency count.

    A pass (``temporal_evidence``) requires all of the following, locked
    before the controls in this module were scored:

    * at least ``max(min_paired_times, 20)`` paired generations;
    * within-class variation, otherwise ``no_temporal_variation``;
    * a detrended within-class correlation (a pure shared line is
      ``shared_trend_not_tracking``);
    * that correlation's sign equal to :func:`expected_lag_sign`;
    * a shared circular-shift p-value at or below 0.05;
    * the lagged detrended correlation strictly larger than the
      contemporaneous one (Dybdahl & Lively: the peak is not at lag 0).

    ``temporal_evidence`` is a property of this series. It is not a
    confirmatory claim, and ``hypothesis_supported`` stays false.
    """

    if isinstance(lag, bool) or not isinstance(lag, int) or lag < 0:
        raise ValueError("lag must be an integer >= 0")
    if isinstance(min_paired_times, bool) or not isinstance(min_paired_times, int) or min_paired_times < 1:
        raise ValueError("min_paired_times must be an integer >= 1")
    if (
        isinstance(n_independent_runs, bool)
        or not isinstance(n_independent_runs, int)
        or n_independent_runs < 1
    ):
        raise ValueError("n_independent_runs must be an integer >= 1")
    sign = expected_lag_sign(recognition_rule)
    applied_min = max(min_paired_times, MIN_PAIRED_TIMES_FLOOR)

    times, classes, host_series, para_series = _frequency_panel(
        host_class_freq, parasite_class_freq, lag=lag
    )
    n_times = len(times)
    n_classes = len(classes)
    varying = 0
    for class_id in classes:
        host_ss = _sum_of_squares(host_series[class_id])
        para_ss = _sum_of_squares(para_series[class_id])
        if host_ss > _WITHIN_SS_EPS and para_ss > _WITHIN_SS_EPS:
            varying += 1
    within_corr = (
        _pooled_within_corr(host_series, para_series, detrend=False) if n_times >= 2 else None
    )
    within_detrended = (
        _pooled_within_corr(host_series, para_series, detrend=True) if n_times >= 3 else None
    )
    between = _between_class_corr(host_series, para_series) if n_classes >= 2 else None
    contemporaneous = None
    if lag == 0:
        contemporaneous = within_detrended
    else:
        _c_times, _c_classes, c_host, c_para = _frequency_panel(
            host_class_freq, parasite_class_freq, lag=0
        )
        if len(_c_times) >= 3:
            contemporaneous = _pooled_within_corr(c_host, c_para, detrend=True)
    null_p: float | None = None
    if within_detrended is not None and n_classes > 0:
        null_p = _circular_shift_p(
            host_series, para_series, observed=within_detrended, sign=sign
        )

    if n_times < applied_min:
        status = "insufficient_paired_times"
    elif within_corr is None:
        status = "no_temporal_variation"
    elif within_detrended is None:
        status = "shared_trend_not_tracking"
    elif sign * within_detrended <= 0.0:
        status = "sign_inconsistent"
    elif null_p is None or null_p > TEMPORAL_NULL_ALPHA:
        status = "null_not_rejected"
    elif contemporaneous is None or not within_detrended > contemporaneous:
        status = "contemporaneous_not_lagged"
    else:
        status = "temporal_tracking"

    historical = lagged_nfds_score(
        host_class_freq,
        parasite_class_freq,
        lag=lag,
        min_points=MIN_PAIRED_TIMES_FLOOR,
    )
    return {
        "estimator": TEMPORAL_ASSOCIATION_ESTIMATOR,
        "historical_estimator": "lagged_nfds_score",
        "historical_pooled": historical,
        "recognition_rule": recognition_rule,
        "expected_sign": sign,
        "lag": lag,
        "n_paired_times": n_times,
        "n_classes": n_classes,
        "n_classes_with_temporal_variation": varying,
        "n_independent_runs": n_independent_runs,
        "n_class_time_pairs": n_times * n_classes,
        "class_time_pairs_are_not_time_points": True,
        "independent_runs_are_not_inferred": True,
        "min_paired_times_requested": min_paired_times,
        "min_paired_times_applied": applied_min,
        "between_class_corr": between,
        "within_corr": within_corr,
        "within_corr_detrended": within_detrended,
        "contemporaneous_within_corr_detrended": contemporaneous,
        "null_method": TEMPORAL_NULL_METHOD,
        "null_alpha": TEMPORAL_NULL_ALPHA,
        "null_p": null_p,
        "null_n_shifts": n_times if n_times else 0,
        "status": status,
        "temporal_evidence": status == "temporal_tracking",
        "hypothesis_supported": False,
        "confirmatory_claim": False,
    }


def per_sublocus_richness_series(
    snaps: Mapping[int, Mapping[str, object]],
) -> dict[str, list[int]]:
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

    out: dict[str, list[int]] = {f"sublocus_{i}": [] for i in range(n_loci)}
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


def parasite_class_frequency_from_hist(
    hist: Mapping[str, float] | Mapping[str, object],
) -> dict[str, float]:
    """Normalize a **parasite class histogram** into a class-frequency map.

    Compatibility alias ``parasite_pressure_from_hist`` is retained, but this
    is a frequency normaliser: the result is the parasite class frequency
    (sums to 1 when non-empty) and carries **no** contact/ATP/survival
    information, so it is not a pressure on any host class. The pressure
    estimand is :func:`realised_conditional_host_pressure`.
    """

    raw = {str(k): same_float(v) for k, v in hist.items()}
    total = sum(raw.values())
    if total <= 0.0:
        return {}
    return {k: v / total for k, v in raw.items()}


#: Deprecated name — kept so existing callers keep working. Semantics are
#: *parasite class frequency*, not pressure on a host class.
parasite_pressure_from_hist = parasite_class_frequency_from_hist


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


# --- Two named pressure estimands (phase 4) ---------------------------------
#
# ``realised_conditional_host_pressure`` stays the class-balanced assay: the
# parasite histogram does not enter its law. The archived RQ-1 matrices were
# built from the keys of ``antagonist_class_frequencies``, so they are that
# assay. They are not the pressure of the living class composition, and an
# infinite reserve is not ATP that a host paid.

CLASS_BALANCED_ASSAY = "class_balanced_assay"
FREQUENCY_WEIGHTED_PRESSURE = "frequency_weighted_abundance_pressure"


def _reserve_reading(result: Mapping[str, object]) -> str:
    exposure = result.get("equal_exposure")
    if not isinstance(exposure, Mapping):
        return "unknown_reserve"
    caps = exposure.get("host_capacity_units")
    if not isinstance(caps, Mapping) or not caps:
        return "unknown_reserve"
    values = list(caps.values())
    if all(value is None for value in values):
        return "infinity_standardised_assay"
    if any(value is None for value in values):
        return "mixed_reserve"
    return "capacity_capped_assay"


def _finite_count(name: str, value: object) -> float:
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be a finite, non-negative count")
    return number


def class_balanced_assay(
    host_class_windows: Mapping[str, str],
    parasite_class_windows: Mapping[str, str],
    **kwargs: object,
) -> dict[str, object]:
    """Equal assay of the parasite classes that are present.

    Frequencies are not weights. Passing them does not change the result.
    ``host_capacity_units=None`` is an infinite-reserve standardised assay,
    not ATP paid in a living history.
    """

    kwargs.pop("parasite_class_counts", None)
    kwargs.pop("contact_matrix", None)
    result = realised_conditional_host_pressure(
        host_class_windows,
        parasite_class_windows,
        **kwargs,  # type: ignore[arg-type]
    )
    result["estimand"] = CLASS_BALANCED_ASSAY
    result["histogram_used"] = False
    result["class_frequency_used"] = False
    result["equals_living_history_atp"] = False
    result["reserve_reading"] = _reserve_reading(result)
    result["red_queen_proved"] = False
    return result


def frequency_weighted_abundance_pressure(
    host_class_windows: Mapping[str, str],
    parasite_class_windows: Mapping[str, str],
    parasite_class_counts: Mapping[str, int | float],
    **kwargs: object,
) -> dict[str, object]:
    """Pressure of the actual class composition.

    Each parasite class is weighted by its share of the count. Multiplying every
    count by the same positive constant does not change the value: this is the
    composition, not the census size. It is not the class-balanced assay, and
    it is not observed ATP.
    """

    if not parasite_class_counts:
        raise ValueError("frequency-weighted pressure requires class counts")
    counts = {str(key): _finite_count(str(key), value) for key, value in parasite_class_counts.items()}
    if sum(counts.values()) <= 0.0:
        raise ValueError("frequency-weighted pressure requires a positive total count")
    missing = sorted(set(map(str, parasite_class_windows)) - set(counts))
    extra = sorted(set(counts) - set(map(str, parasite_class_windows)))
    if missing or extra:
        raise ValueError("counts and parasite classes must name the same support")
    hosts = [str(host) for host in host_class_windows]
    weighted = {host: {parasite: counts[parasite] for parasite in counts} for host in hosts}
    kwargs.pop("contact_matrix", None)
    kwargs.pop("parasite_class_counts", None)
    result = realised_conditional_host_pressure(
        host_class_windows,
        parasite_class_windows,
        parasite_class_counts=counts,
        contact_matrix=weighted,
        **kwargs,  # type: ignore[arg-type]
    )
    result["estimand"] = FREQUENCY_WEIGHTED_PRESSURE
    result["histogram_used"] = True
    result["class_frequency_used"] = True
    result["equals_living_history_atp"] = False
    result["scale_invariant_composition"] = True
    result["reserve_reading"] = _reserve_reading(result)
    result["red_queen_proved"] = False
    return result


def separate_pressure_accounts(
    *,
    affinity: float,
    kappa: float,
    reserve: float | None,
    contact_opportunities: float,
    lineage_growth: float,
    paid_atp: float | None = None,
) -> dict[str, object]:
    """Keep intended pressure, the capped assay, paid ATP, contacts and growth apart.

    The capacity cap is not a payment. ``paid_pressure`` is set only when an
    observed ``paid_atp`` is supplied, and that observation cannot exceed a
    known finite reserve.
    """

    intended = _finite_count("affinity", affinity) * float(kappa)
    if not math.isfinite(float(kappa)) or float(kappa) < 0.0 or not math.isfinite(intended):
        raise ValueError("intended pressure must be finite and non-negative")
    opportunities = _finite_count("contact_opportunities", contact_opportunities)
    growth = float(lineage_growth)
    if not math.isfinite(growth):
        raise ValueError("lineage_growth must be finite")
    if reserve is None or math.isinf(float(reserve)):
        capped = None
    else:
        reserve_value = float(reserve)
        if not math.isfinite(reserve_value) or reserve_value < 0.0:
            raise ValueError("reserve must be finite and non-negative, or infinite")
        capped = min(reserve_value, intended)
    if paid_atp is None:
        paid = None
    else:
        paid = _finite_count("paid_atp", paid_atp)
        if capped is not None and paid > same_float(reserve):
            raise ValueError("paid ATP cannot exceed the known reserve")
    return {
        "intended_pressure": intended,
        "capacity_capped_assay": capped,
        "paid_pressure": paid,
        "paid_is_observed_atp": paid_atp is not None,
        "capacity_cap_is_paid_atp": False,
        "infinite_reserve_is_living_history_atp": False,
        "contact_opportunity": opportunities,
        "lineage_growth": growth,
        "red_queen_proved": False,
    }


def algebraic_frozen_zero(*, debit_multiplier: float, pressure: float) -> dict[str, object]:
    """A frozen arm that multiplies the debit by zero is an algebraic control.

    The zero does not, by itself, show that the metric is biologically or
    causally valid.
    """

    exact_zero = abs(float(pressure)) <= 1e-15
    algebraic = float(debit_multiplier) == 0.0 and exact_zero
    return {
        "frozen_exactly_zero": exact_zero,
        "algebraic_control": algebraic,
        "biological_validity": False,
        "causal_validity": False,
        "red_queen_proved": False,
    }


def rq_path_components(
    *,
    lag_contrast: float,
    rarity_delta: float,
    host_delta: float,
    parasite_delta: float,
    pressure_with_path: float,
    pressure_path_cut: float,
    sham_pressure: float,
) -> dict[str, object]:
    """Four checks. Passing one does not pass the others and proves nothing."""

    return {
        "lag_condition": float(lag_contrast) < 0.0,
        "rarity_advantage": float(rarity_delta) > 0.0,
        "reciprocal_feedback": (
            float(host_delta) != 0.0
            and float(parasite_delta) != 0.0
            and float(host_delta) * float(parasite_delta) < 0.0
        ),
        "path_cut_control": (
            float(pressure_with_path) > 0.0
            and abs(float(pressure_path_cut)) <= 1e-15
            and abs(float(sham_pressure) - float(pressure_with_path)) <= 1e-15
        ),
        "any_implies_the_others": False,
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }


def confirmatory_seed_disagreement(
    by_seed: Mapping[int, float],
    *,
    generation_rows: int | None = None,
) -> dict[str, object]:
    """The confirmatory sample size is the number of seeds, not generations."""

    values = []
    for key in sorted(by_seed):
        number = float(by_seed[key])
        if not math.isfinite(number):
            raise ValueError("a seed estimate must be finite")
        values.append(number)
    if generation_rows is not None and (
        isinstance(generation_rows, bool)
        or not isinstance(generation_rows, int)
        or generation_rows < len(values)
    ):
        raise ValueError("generation_rows must be an integer and at least the seed count")
    spread = 0.0 if len(values) < 2 else max(values) - min(values)
    return {
        "n_confirmatory_seeds": len(values),
        "n_generation_rows": generation_rows,
        "n_used_for_inference": len(values),
        "between_seed_range": spread,
        "replicate_unit": "seed",
        "generations_are_independent_replicates": False,
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }


__all__ = [
    "CLASS_BALANCED_ASSAY",
    "CONTACT_MODE_ENGINE_SEATS",
    "CONTACT_MODE_FULL_MATRIX",
    "CONTACT_MODES",
    "DEFAULT_CLUSTER_BOOTSTRAP_RESAMPLES",
    "DEFAULT_CLUSTER_BOOTSTRAP_SEED",
    "DEFAULT_NFDS_THRESHOLD",
    "FREQUENCY_WEIGHTED_PRESSURE",
    "MIN_PAIRED_TIMES_FLOOR",
    "RECOGNITION_RULE_MATCHING",
    "SWAP_SIGNAL_UNITS",
    "TEMPORAL_ASSOCIATION_ESTIMATOR",
    "TEMPORAL_NULL_ALPHA",
    "TEMPORAL_NULL_METHOD",
    "affinity_matrix",
    "algebraic_frozen_zero",
    "class_balanced_assay",
    "confirmatory_seed_disagreement",
    "dominant_class_series",
    "expected_lag_sign",
    "exchange_class_shares",
    "frequency_swap_signal",
    "frequency_weighted_abundance_pressure",
    "host_realised_pressure_from_contacts",
    "joint_freq_counter_to_map",
    "lagged_nfds_score",
    "parasite_class_frequency_from_hist",
    "parasite_pressure_from_hist",
    "per_sublocus_richness_series",
    "phase_lag_host_parasite",
    "realised_conditional_host_pressure",
    "reference_graded_affinity",
    "rq_path_components",
    "run_level_cluster_bootstrap_interval",
    "separate_pressure_accounts",
    "within_class_lagged_association",
]
