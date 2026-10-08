"""Phase-5 full coevolution. Two claims, scored separately.

Claim A is a directional time-shift on the engine debit path with evolution
off during the assay. Claim B is frequency-dependent selection with an
oscillating Red Queen, and it is not implied by claim A. ``red_queen_proved`` is not set from an in-model support call.
A limited claim is ``in_model_support``. The public flag stays false.

Birth chamber. Prediction: a nonzero outcross locus refuses COPY_SELF unless
the birth chamber is on. Full coevolution still uses the structural host
bit-flip. Engine path: ``enable_coevolution_birth_chamber`` sets
``SexualRecombinationConfig(enabled=True, pairing_policy='birth_chamber')``
and writes installed host ids into the life role map. ``bit_flip_rate`` stays
``STRUCT_HOST_BIT_FLIP`` on coevolve and constant-parasite, and 0 on the
adaptation cut. ``parent_atp_cost`` stays the booted cost. Control: the
adaptation cut keeps ``reproduction.enabled`` true and does not call
``freeze_host_genotypic_inheritance``. Source: the chamber phase 4b opened.
Hall et al. 2011 full text was not read. Limit: virulence, steal fraction,
maintenance, birth ATP, bolus, ``max_population``, and ``MEASUREMENT_FLOOR``
are not retuned. Census stays 60 so a birth can fit under the cap of 64.
Estimand: births can enter the lineage claim B reads. They are not ATP loss.

Arms. Prediction: reciprocal coevolution is passage ``coevolve`` with both
mutation rates structural. A held parasite composition is not that treatment.
Cutting reciprocal adaptation is not reproduction-off and not
``shuffled_labels``. Engine path: boot ``build_arm(ARM_A)``, install equal
A/B genomes. ``constant_parasite`` uses ``PASSAGE_FROZEN`` so advance reseats
founder parasite windows while the debit stays. ``adaptation_cut`` sets host
bit-flip to 0, passage frozen, and a host-composition hold before contact.
Control: ``PASSAGE_ABSENT`` is not used. The parasite population is not
deleted. Source: Zaman et al. 2014 as read in PHASE1.md. Limit: the hold is
only on the adaptation cut. Estimand: claim A uses the coevolve arm.

Claims. Prediction: ``I(hosts_t, parasites_t) - I(hosts_t, parasites_{t-lag})``
is positive. Claim B also needs genotype-frequency counts, real contact
pressure, lineage relative fitness, and a sign reversal of ``I(A)-I(B)``.
A census wave is not that conjunction. Engine path: ``infectivity`` calls
``replay_archived_contact`` with evolution off. Source: Decaestecker et al.
2007 as read in PHASE1.md (contemporary infectivity 0.65 versus previous
0.55) and Papkou et al. 2019 as read there (time-shifts consistent with
aFDS). Limit: importance is undeclared. The published 0.10 gap is not this
engine's importance bound. The MDE is not importance. Estimand: null stays
null. The public flag does not stand in for that in-model claim.

Control contrast, phase 5b. Prediction: the phase-5 control score is
identically zero because ``score_arm_contrast`` assays horizon hosts twice,
once against each parasite generation, and frozen passage reseats the same
windows. Engine path: ``infectivity`` calls ``replay_archived_contact`` with
``atp_override``, which rewrites ATP, and ``_apply_hp_env_contact`` pairs by
seat index. ``AntagonistPopulation._reseat_frozen`` writes the founder window
back onto each seat, and frozen mode sets mutation to 0. Control: constant
parasite is host change against that one horizon roster, not the difference
of two parasite copies. Adaptation cut is the matched-pair change, so one
changed host window or one changed parasite window can move it. Source: the
rejected phase-5 archives, where generations 1 through 10 share one parasite
window sequence on both control arms, and the seat assay. Limit: claim A and
claim B on the coevolve arm are not redefined. Importance stays undeclared.
Lag 3 and horizon 10 are not retuned. The birth, mutation, and passage engine
is not changed to enlarge the coevolve contrast. Estimand: a control zero is
no longer forced by duplicate parasite inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from codontrace.dynvalues import same_float, same_int, same_iter, same_mapping
from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import SexualRecombinationConfig
from codontrace.genesis.closed_loop_hp_arm01 import _window
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_BIRTH_ATP,
    STRUCT_HOST_BIT_FLIP,
    STRUCT_PARASITE_MUTATION,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
    StructuralRQArm,
)
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_ABSENT, PASSAGE_COEVOLVE, PASSAGE_FROZEN
from codontrace.genesis.host_parasite_life_plugin import ROLE_SECONDARY
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import LineageRecord
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARM_A,
    build_arm,
    config_digest,
    invariant_status,
    replay_archived_contact,
)
from codontrace.genesis.rq_bidirectional_timeshift_confirm import (
    MEASUREMENT_FLOOR,
    infectivity,
    noncentral_t_sf,
    student_t_ppf,
    student_t_sf,
)
from codontrace.genesis.rq_mechanism_v2_phase3 import TURNOVER_MULTIPLE, pure_host_rows
from codontrace.genesis.rq_mechanism_v2_phase4 import (
    GENOME_A,
    GENOME_B,
    WINDOW_A,
    WINDOW_B,
    equal_host_seats,
)

PROBE_SEED = 9600
PROBE_GENERATIONS = 24
MAX_HISTORIES = 24
MAX_WORKERS = 7
N_PRIMARY = 2
ALPHA_FAMILY = 0.05
ALPHA = ALPHA_FAMILY / N_PRIMARY
POWER = 0.80
PLANNING_SIGMA_A = 0.25
PLANNING_SIGMA_B = 0.5
PRECISION_A = 0.25
PRECISION_B = 0.5
ASSAY_SCALE = float(STRUCT_VIRULENCE) * float(STRUCT_STEAL_FRACTION)
REPLAY_ABS_TOL = 1e-6
STREAM_ROOT = "RQ-MECHANISM-V2-PHASE5"
ARM_COEVOLVE = "coevolve"
ARM_ADAPTATION_CUT = "adaptation_cut"
ARM_CONSTANT_PARASITE = "constant_parasite"
ARMS: tuple[str, ...] = (ARM_COEVOLVE, ARM_ADAPTATION_CUT, ARM_CONSTANT_PARASITE)
ARCHIVE_SCHEMA = "rq-mechanism-v2-phase5/1"
CLAIM_A_DIRECTION = "contemporary_minus_past_positive"
VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_NEGATIVE = "NEGATIVE"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"
VERDICT_BLOCKED = "BLOCKED_MEASUREMENT"
VERDICT_NOT_DECLARED = "NOT_DECLARED"
NO_CONFIRMATORY_SENTENCE = "No confirmatory number has been computed."
OUTPUT_CONFIRMATORY = Path("runs/rq-mechanism-v2/phase5-coevolution")
OUTPUT_PROBE = Path("runs/rq-mechanism-v2/phase5-probe")
OUTPUT_PHASE5B = Path("runs/rq-mechanism-v2/phase5b-coevolution")
PHASE5B_LAG = 3
PHASE5B_HORIZON = 10
PHASE5B_SEED_START = 9701
PHASE5B_N = 12
PHASE5B_LOCK = Path("runs/rq-mechanism-v2/PHASE5B_LOCK.md")
_BANNED_OUTPUT_PARTS = (
    Path("runs/rq-bidirectional-timeshift-01"),
    Path("runs/rq-mechanism-v2/phase2-short"),
    Path("runs/rq-mechanism-v2/phase3-frequency"),
    Path("runs/rq-mechanism-v2/phase3-selection"),
    Path("runs/rq-mechanism-v2/phase4-fitness"),
    Path("runs/rq-mechanism-v2/phase4b-fitness"),
)
FORBIDDEN_SEEDS: frozenset[int] = frozenset(
    {
        9099,
        9101,
        9102,
        9103,
        9104,
        *range(9201, 9225),
        *range(9301, 9305),
        9401,
        *range(9500, 9505),
    }
)


def assert_measurement_floor(floor: int | None = None) -> int:
    """``MEASUREMENT_FLOOR`` stays 12. A lower value is rejected."""

    value = int(MEASUREMENT_FLOOR if floor is None else floor)
    if int(MEASUREMENT_FLOOR) < 12 or value < 12:
        raise ConfigurationError("MEASUREMENT_FLOOR must not be lowered")
    return value


def _finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _rate_allowed(rate: float, *allowed: float) -> bool:
    return any(math.isclose(float(rate), float(item), abs_tol=1e-12) for item in allowed)


def resolve_workers(requested: int | None) -> int:
    """Cap at 7. Reject 8. Do not read cpu_count."""

    workers = MAX_WORKERS if requested is None else int(requested)
    if workers < 1 or workers > MAX_WORKERS:
        raise ConfigurationError(f"phase-5 workers must be in 1..{MAX_WORKERS}, got {workers}")
    return workers


def assert_output_dir(root: Path) -> None:
    """Refuse previous-run trees."""

    resolved = root.resolve()
    for banned in _BANNED_OUTPUT_PARTS:
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise ConfigurationError(f"phase-5 output must not be inside {banned}")


def locked_confirmatory_seeds(n: int) -> tuple[int, ...]:
    """Contiguous seeds from 9601. The probe seed 9600 is not included."""

    count = int(n)
    floor = assert_measurement_floor()
    if count < floor:
        raise ConfigurationError(f"phase-5 history count {count} is below MEASUREMENT_FLOOR")
    if count > MAX_HISTORIES:
        raise ConfigurationError(f"phase-5 history count {count} exceeds the registered cap")
    seeds = tuple(range(9601, 9601 + count))
    if PROBE_SEED in seeds or (set(seeds) & FORBIDDEN_SEEDS):
        raise ConfigurationError("phase-5 confirmatory seeds overlap a forbidden or probe seed")
    return seeds


def contemporary_minus_past(i_now: float | None, i_past: float | None) -> float | None:
    """Claim A contrast. Either null stays null. A numeric 0 stays 0."""

    if i_now is None or i_past is None or not _finite(i_now) or not _finite(i_past):
        return None
    return float(i_now) - float(i_past)


def specialization_gap(i_a: float | None, i_b: float | None) -> float | None:
    """``I(A) - I(B)``. Null stays null."""

    if i_a is None or i_b is None or not _finite(i_a) or not _finite(i_b):
        return None
    return float(i_a) - float(i_b)


def direction_reversal(gap_now: float | None, gap_past: float | None) -> bool | None:
    """True when the nonzero signs differ. A zero gap has no rank and is null."""

    if gap_now is None or gap_past is None or not _finite(gap_now) or not _finite(gap_past):
        return None
    if float(gap_now) == 0.0 or float(gap_past) == 0.0:
        return None
    return (float(gap_now) > 0.0) != (float(gap_past) > 0.0)


def genotype_frequency(windows: Sequence[str] | None) -> dict[str, int] | None:
    """Window counts. A missing census is null, not a renamed class."""

    if windows is None:
        return None
    counts: dict[str, int] = {}
    for window in windows:
        text = str(window)
        if len(text) != 6 or any(ch not in "01" for ch in text):
            return None
        counts[text] = counts.get(text, 0) + 1
    if not counts:
        return None
    return counts


def frequency_is_measured(counts: Mapping[str, int] | None) -> bool:
    """A label without window counts is not a genotype frequency."""

    if not isinstance(counts, Mapping) or not counts:
        return False
    total = 0
    for key, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return False
        text = str(key)
        if len(text) != 6 or any(ch not in "01" for ch in text):
            return False
        total += int(value)
    return total > 0


def census_wave_supports_claim_b(wave: object) -> bool:
    """A frequency wave is not claim B."""

    del wave
    return False


def lineage_relative_fitness(
    start_windows: Sequence[str] | None,
    births: Sequence[Mapping[str, object]] | None,
    deaths: Sequence[object] | None,
) -> dict[str, object]:
    """Next-generation share over start frequency. ATP is not an argument.

    No births, a missing death list, or an unresolved parent is null, not 0.
    A present class with no offspring has measured fitness 0. An absent class
    is omitted, not entered as 0.
    """

    empty: dict[str, object] = {"by_window": None, "deaths_recorded": False, "measured": False, "n_births": 0}
    if start_windows is None or births is None or deaths is None:
        return empty
    frequencies = genotype_frequency(start_windows)
    if frequencies is None:
        return empty
    n_start = sum(frequencies.values())
    parent_windows: list[str] = []
    for birth in births:
        parent = birth.get("parent_window")
        if not isinstance(parent, str):
            return empty
        parent_windows.append(parent)
    if not parent_windows:
        return {"by_window": None, "deaths_recorded": True, "measured": False, "n_births": 0}
    offspring = Counter(parent_windows)
    n_births = len(parent_windows)
    by_window: dict[str, float] = {}
    for window, count in frequencies.items():
        if count <= 0:
            continue
        share = offspring.get(window, 0) / float(n_births)
        by_window[window] = share / (count / float(n_start))
    return {"by_window": by_window, "deaths_recorded": True, "measured": True, "n_births": n_births}




def descendant_fitness(
    start_hosts: Sequence[Mapping[str, object]] | None,
    births: Sequence[Mapping[str, object]] | None,
    living: Sequence[Mapping[str, object]] | None,
    deaths_recorded: bool,
) -> dict[str, object]:
    """Living descendant share over generation-1 frequency. ATP is not an argument.

    An unresolved parent chain is null, not a zero share. A founder class that
    is present at generation 1 and has no living descendant has measured
    fitness 0. A class absent at generation 1 is omitted.
    """

    empty: dict[str, object] = {"by_window": None, "measured": False}
    if not deaths_recorded or start_hosts is None or births is None or living is None:
        return empty
    founders: dict[str, str] = {}
    for host in start_hosts:
        host_id = host.get("id")
        window = host.get("window")
        if not isinstance(host_id, str) or not isinstance(window, str):
            return empty
        founders[host_id] = window
    if not founders or not living:
        return empty
    parent: dict[str, str] = {}
    for birth in births:
        child = birth.get("id")
        parent_id = birth.get("parent_id")
        if isinstance(child, str) and isinstance(parent_id, str):
            parent[child] = parent_id
    labels: list[str] = []
    for host in living:
        host_id = host.get("id")
        if not isinstance(host_id, str):
            return empty
        if isinstance(host.get("parent_id"), str):
            parent.setdefault(host_id, str(host["parent_id"]))
        seen: set[str] = set()
        current: str | None = host_id
        while current is not None and current not in founders:
            if current in seen or current not in parent:
                return empty
            seen.add(current)
            current = parent[current]
        if current is None:
            return empty
        labels.append(founders[current])
    frequencies = genotype_frequency(list(founders.values()))
    if frequencies is None:
        return empty
    n_start = sum(frequencies.values())
    n_living = len(labels)
    counts = Counter(labels)
    by_window: dict[str, float] = {}
    for window, count in frequencies.items():
        if count <= 0:
            continue
        by_window[window] = (counts.get(window, 0) / float(n_living)) / (count / float(n_start))
    return {"by_window": by_window, "measured": True}

def phase5_mde(sigma: float, n: int) -> float:
    """One-sided MDE at the phase-5 alpha. Not an importance bound."""

    if int(n) < 3:
        raise ConfigurationError("MDE requires n >= 3")
    if float(sigma) < 0.0 or not math.isfinite(float(sigma)):
        raise ConfigurationError("sigma must be non-negative and finite")
    df = int(n) - 1
    critical = student_t_ppf(1.0 - ALPHA, df)
    lo = 0.0
    hi = 1.0
    while noncentral_t_sf(critical, df, hi) < POWER:
        hi *= 2.0
        if hi > 1e6:
            raise ConfigurationError("noncentral-t search did not reach the target power")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if noncentral_t_sf(critical, df, mid) < POWER:
            lo = mid
        else:
            hi = mid
    return hi * float(sigma) / math.sqrt(float(n))


def history_count_from_power(sigma_a: float, sigma_b: float) -> dict[str, object]:
    """Smallest n >= 12 whose MDE meets both precision targets, else the cap."""

    floor = assert_measurement_floor()
    chosen = MAX_HISTORIES
    met = False
    for n in range(floor, MAX_HISTORIES + 1):
        if phase5_mde(float(sigma_a), n) <= PRECISION_A and phase5_mde(float(sigma_b), n) <= PRECISION_B:
            chosen = n
            met = True
            break
    return {
        "mde_a": phase5_mde(float(sigma_a), chosen),
        "mde_b": phase5_mde(float(sigma_b), chosen),
        "n": chosen,
        "precision_met": met,
        "sigma_a": float(sigma_a),
        "sigma_b": float(sigma_b),
    }


def choose_lag_and_horizon(
    *,
    mean_newborns: float | None,
    census: int,
    measurable: bool,
    probe_generations: int = PROBE_GENERATIONS,
) -> dict[str, object]:
    """Lag and horizon from parasite replacement time. No contrast is an argument."""

    if not measurable or mean_newborns is None or not _finite(mean_newborns) or float(mean_newborns) <= 0.0:
        raise ConfigurationError("parasite turnover is unmeasurable; lag and horizon are not 0")
    if int(census) < 1:
        raise ConfigurationError("parasite census must be positive")
    replacement = float(census) / float(mean_newborns)
    lag = max(1, int(round(replacement)))
    horizon = max(int(math.ceil(float(TURNOVER_MULTIPLE) * replacement)), lag + 1)
    if horizon > int(probe_generations):
        raise ConfigurationError("horizon exceeds the registered probe budget; it is not shortened")
    if lag >= horizon:
        raise ConfigurationError("primary lag does not leave a past partner inside the horizon")
    return {
        "census": int(census),
        "horizon": horizon,
        "mean_seated_newborns": float(mean_newborns),
        "primary_lag": lag,
        "replacement_generations": replacement,
        "turnover_multiple": int(TURNOVER_MULTIPLE),
    }


def sampling_interval(values: Sequence[float]) -> dict[str, object]:
    """One-sample interval. A sample SE of 0 leaves the t p-value null, not 0."""

    clean = [float(value) for value in values]
    if any(not math.isfinite(value) for value in clean):
        raise ConfigurationError("sample contains NaN or Infinity")
    n = len(clean)
    if n < 2:
        return {"ci95": None, "lower": None, "mean": None, "n": n, "p_one_sided": None, "se_zero": False, "upper": None}
    mean = float(statistics.fmean(clean))
    sd = float(statistics.stdev(clean))
    se = sd / math.sqrt(n)
    if se == 0.0:
        return {
            "ci95": None,
            "lower": None,
            "mean": mean,
            "n": n,
            "p_one_sided": None,
            "se_zero": True,
            "upper": None,
        }
    df = n - 1
    t_ci = student_t_ppf(0.975, df)
    t_lo = student_t_ppf(1.0 - ALPHA, df)
    lower = mean - t_lo * se
    upper = mean + t_ci * se
    return {
        "ci95": [mean - t_ci * se, upper],
        "lower": lower,
        "mean": mean,
        "n": n,
        "p_one_sided": float(student_t_sf(mean / se, df)),
        "se_zero": False,
        "upper": upper,
    }


def _statistical_verdict(interval: Mapping[str, object], importance_bound: float | None) -> str:
    """SUPPORTED only when a declared importance bound is cleared by the lower bound."""

    if bool(interval.get("se_zero")) or interval.get("p_one_sided") is None or interval.get("upper") is None:
        return VERDICT_INCONCLUSIVE
    upper = float(interval["upper"])  # type: ignore[arg-type]
    mean = float(interval["mean"])  # type: ignore[arg-type]
    p_value = float(interval["p_one_sided"])  # type: ignore[arg-type]
    lower = float(interval["lower"])  # type: ignore[arg-type]
    if upper < 0.0:
        return VERDICT_NEGATIVE
    if importance_bound is None:
        if p_value < ALPHA and mean > 0.0 and lower > 0.0:
            return VERDICT_NOT_DECLARED
        return VERDICT_INCONCLUSIVE
    if p_value < ALPHA and mean > 0.0 and lower >= float(importance_bound):
        return VERDICT_SUPPORTED
    return VERDICT_INCONCLUSIVE


def normal_ppf(p: float) -> float:
    """Acklam's inverse normal. Used only as the Wilson kappa."""

    if not 0.0 < float(p) < 1.0:
        raise ConfigurationError("normal quantile requires a probability in (0, 1)")
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00)
    plow = 0.02425
    phigh = 1.0 - plow
    prob = float(p)
    if prob < plow:
        q = math.sqrt(-2.0 * math.log(prob))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if prob > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - prob))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    q = prob - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    )


REVERSAL_NULL = 0.5


def _binom_terms(n: int, p: float) -> list[float]:
    """P(X=k) for k = 0..n. p = 0.5 uses exact powers of one half."""

    count = int(n)
    if count < 1:
        raise ConfigurationError("binomial n must be positive")
    prob = float(p)
    if prob < 0.0 or prob > 1.0 or not math.isfinite(prob):
        raise ConfigurationError("binomial probability is not in [0, 1]")
    if math.isclose(prob, 0.5, abs_tol=1e-15):
        unit = 0.5 ** count
        terms = [unit]
        for k in range(count):
            terms.append(terms[-1] * (count - k) / (k + 1))
        return terms
    if prob == 0.0:
        return [1.0] + [0.0] * count
    if prob == 1.0:
        return [0.0] * count + [1.0]
    terms = [(1.0 - prob) ** count]
    for k in range(count):
        terms.append(terms[-1] * (count - k) / (k + 1) * prob / (1.0 - prob))
    return terms


def wilson_interval(successes: int, n: int, *, confidence: float = 0.95) -> dict[str, object]:
    """Two-sided Wilson interval. 0/n keeps 0 and n/n keeps 1.

    The Wald standard error is recorded and is not the p-value. A zero Wald
    standard error does not delete the boundary or set p to 0.
    Source: Brown, Cai, and DasGupta 2001, Statistical Science 16:101-133,
    equation (4), the interval they recommend for small n.
    """

    count = int(n)
    k = int(successes)
    if isinstance(successes, bool) or isinstance(n, bool):
        raise ConfigurationError("binomial counts must be integers")
    if count < 1 or k < 0 or k > count:
        raise ConfigurationError("binomial counts are outside 0..n")
    if not 0.0 < float(confidence) < 1.0:
        raise ConfigurationError("confidence must be in (0, 1)")
    z = normal_ppf(0.5 + float(confidence) / 2.0)
    phat = k / float(count)
    z2 = z * z
    denom = 1.0 + z2 / float(count)
    center = (phat + z2 / (2.0 * float(count))) / denom
    margin = z * math.sqrt(phat * (1.0 - phat) / float(count) + z2 / (4.0 * float(count) ** 2)) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    if k == 0:
        lower = 0.0
    if k == count:
        upper = 1.0
    wald_se = math.sqrt(phat * (1.0 - phat) / float(count))
    terms = _binom_terms(count, REVERSAL_NULL)
    p_upper = float(sum(terms[k:]))
    p_lower = float(sum(terms[: k + 1]))
    p_one = p_upper if phat >= REVERSAL_NULL else p_lower
    p_two = min(1.0, 2.0 * min(p_lower, p_upper))
    return {
        "ci95": [lower, upper],
        "k": k,
        "lower": lower,
        "mean": phat,
        "n": count,
        "null": REVERSAL_NULL,
        "p_one_sided": p_one,
        "p_two_sided": p_two,
        "se_zero": False,
        "upper": upper,
        "wald_se": wald_se,
        "wald_se_zero": wald_se == 0.0,
    }


def _binary_verdict(interval: Mapping[str, object], importance_bound: float | None) -> str:
    """Directional success is a rate above the null. The Wilson upper below the null is negative.

    Importance left undeclared forbids SUPPORTED. The continuous effect size is not this index.
    """

    if interval.get("lower") is None or interval.get("upper") is None or interval.get("p_one_sided") is None:
        return VERDICT_INCONCLUSIVE
    upper = float(interval["upper"])  # type: ignore[arg-type]
    lower = float(interval["lower"])  # type: ignore[arg-type]
    mean = float(interval["mean"])  # type: ignore[arg-type]
    p_value = float(interval["p_one_sided"])  # type: ignore[arg-type]
    null = float(interval["null"])  # type: ignore[arg-type]
    if upper < null:
        return VERDICT_NEGATIVE
    if importance_bound is None:
        if p_value < ALPHA and mean > null and lower > null:
            return VERDICT_NOT_DECLARED
        return VERDICT_INCONCLUSIVE
    if p_value < ALPHA and mean > null and lower >= float(importance_bound) and lower > null:
        return VERDICT_SUPPORTED
    return VERDICT_INCONCLUSIVE


def _reject_duplicate_inputs(
    rows: Sequence[Mapping[str, object]],
    locked: Sequence[int],
) -> dict[int, Mapping[str, object]]:
    """Unique seeds and unique generations. A second payload for one seed is not a second history."""

    if len(locked) != len(set(locked)):
        raise ConfigurationError("duplicate seeds")
    by_seed: dict[int, Mapping[str, object]] = {}
    for row in rows:
        seed = same_int(row["seed"])
        generations = row.get("generations")
        if isinstance(generations, list):
            gens = [int(item) for item in generations]
            if len(gens) != len(set(gens)):
                raise ConfigurationError("duplicate generations")
        if seed in by_seed:
            previous = by_seed[seed]
            if previous.get("claim_a") != row.get("claim_a") or previous.get("reversal") != row.get("reversal"):
                raise ConfigurationError("contradictory rows")
            raise ConfigurationError("duplicate seeds")
        by_seed[seed] = row
    return by_seed


def _bind_evidence(
    by_seed: Mapping[int, Mapping[str, object]],
    locked: Sequence[int],
    evidence: Mapping[str, object] | None,
) -> dict[str, object]:
    """Identity, config, and provenance travel with the claim. A missing bundle is not a match."""

    if evidence is None:
        return {"bound": False, "config_digest": None, "identity": None, "provenance": None}
    identity = evidence.get("identity")
    digest = evidence.get("config_digest")
    provenance = evidence.get("provenance")
    if not isinstance(identity, str) or not identity:
        raise ConfigurationError("evidence identity is not bound")
    if not isinstance(digest, str) or not digest:
        raise ConfigurationError("evidence config is not bound")
    if not isinstance(provenance, str) or not provenance:
        raise ConfigurationError("evidence provenance is not bound")
    for seed in locked:
        row = by_seed.get(int(seed))
        if row is None:
            continue
        if row.get("evidence_id") != identity:
            raise ConfigurationError("evidence identity is not bound to the claim")
        if row.get("config_digest") != digest:
            raise ConfigurationError("evidence config is not bound to the claim")
        if row.get("provenance") != provenance:
            raise ConfigurationError("evidence provenance is not bound to the claim")
    return {
        "bound": True,
        "config_digest": digest,
        "identity": identity,
        "provenance": provenance,
    }


def assess_phase5(
    rows: Sequence[Mapping[str, object]],
    locked_seeds: Sequence[int],
    *,
    importance_bound: float | None,
    mde_a: float | None = None,
    mde_b: float | None = None,
    measurement_floor: int | None = None,
    evidence: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Score claim A and claim B separately.

    A missing seed or a null required piece is BLOCKED_MEASUREMENT. The mean
    is then null, not the mean of the remaining rows and not a zero fill.
    Importance undeclared forbids SUPPORTED. A census wave cannot support B.
    Duplicate seeds, contradictory rows, and duplicate generations are rejected.
    Two copies of one history are not twelve histories.

    The reversal index is a binomial proportion. Its Wilson interval is not the
    continuous effect size. ``red_queen_proved`` is not that in-model claim.
    """

    floor = assert_measurement_floor(measurement_floor)
    locked = tuple(int(seed) for seed in locked_seeds)
    if len(locked) < floor:
        raise ConfigurationError("locked history count is below MEASUREMENT_FLOOR")
    if importance_bound is not None and not _finite(importance_bound):
        raise ConfigurationError("importance bound must be finite or null")
    by_seed = _reject_duplicate_inputs(rows, locked)
    bound = _bind_evidence(by_seed, locked, evidence)
    dropped_a: list[int] = []
    dropped_b: list[int] = []
    a_values: list[float] = []
    b_values: list[float] = []
    frequency_n = 0
    contact_n = 0
    fitness_n = 0
    reversal_n = 0
    conjunction = True
    for seed in locked:
        row = by_seed.get(seed)
        if row is None:
            dropped_a.append(seed)
            dropped_b.append(seed)
            conjunction = False
            continue
        contrast = row.get("claim_a")
        if contrast is None or not _finite(contrast):
            dropped_a.append(seed)
        else:
            a_values.append(same_float(contrast))
        if bool(row.get("census_wave")) and census_wave_supports_claim_b(row.get("frequency")):
            raise ConfigurationError("census wave was treated as claim B")
        frequency = row.get("frequency")
        contact = row.get("contact_pressure")
        contacts = row.get("contacts")
        fitness_measured = row.get("fitness_measured")
        reversal = row.get("reversal")
        measured_frequency = frequency_is_measured(frequency if isinstance(frequency, Mapping) else None)
        piece_missing = (
            not measured_frequency
            or contact is None
            or not _finite(contact)
            or not isinstance(contacts, int)
            or isinstance(contacts, bool)
            or not isinstance(fitness_measured, bool)
            or not isinstance(reversal, bool)
        )
        if piece_missing:
            dropped_b.append(seed)
            conjunction = False
            continue
        frequency_n += 1
        if same_int(contacts) > 0 and same_float(contact) > 0.0:
            contact_n += 1
        else:
            conjunction = False
        if bool(fitness_measured):
            fitness_n += 1
        else:
            conjunction = False
        if bool(reversal):
            reversal_n += 1
            b_values.append(1.0)
        else:
            b_values.append(0.0)
    claim_a: dict[str, object] = {
        "dropped_seeds": dropped_a,
        "mean": None,
        "n_locked": len(locked),
        "n_used": len(a_values),
        "verdict": VERDICT_BLOCKED,
    }
    claim_b: dict[str, object] = {
        "contact_ok_n": contact_n,
        "continuous_effect": None,
        "criterion_met": False,
        "dropped_seeds": dropped_b,
        "fitness_measured_n": fitness_n,
        "frequency_measured_n": frequency_n,
        "mean": None,
        "n_locked": len(locked),
        "n_used": len(locked) - len(dropped_b),
        "reversal_true_n": reversal_n,
        "used_census_wave_as_estimand": False,
        "verdict": VERDICT_BLOCKED,
    }
    if not dropped_a and len(a_values) == len(locked):
        interval_a = sampling_interval(a_values)
        claim_a["interval"] = interval_a
        claim_a["mean"] = interval_a["mean"]
        claim_a["verdict"] = _statistical_verdict(interval_a, importance_bound)
    if not dropped_b and len(b_values) == len(locked):
        interval_b = wilson_interval(reversal_n, len(locked))
        claim_b["interval"] = interval_b
        claim_b["mean"] = interval_b["mean"]
        # The binary index is the reversal count. A continuous gap, when the
        # caller stored one, is not substituted for it.
        gaps = [row.get("effect_size") for row in (by_seed[seed] for seed in locked)]
        if all(_finite(gap) for gap in gaps):
            claim_b["continuous_effect"] = sampling_interval([float(gap) for gap in gaps])  # type: ignore[arg-type]
        statistical = _binary_verdict(interval_b, importance_bound)
        claim_b["criterion_met"] = bool(conjunction and statistical == VERDICT_SUPPORTED and bound["bound"])
        if not conjunction:
            claim_b["verdict"] = VERDICT_NEGATIVE if statistical == VERDICT_NEGATIVE else VERDICT_INCONCLUSIVE
        else:
            claim_b["verdict"] = statistical
    if importance_bound is None or not bound["bound"]:
        if claim_a["verdict"] == VERDICT_SUPPORTED:
            claim_a["verdict"] = VERDICT_NOT_DECLARED
        if claim_b["verdict"] == VERDICT_SUPPORTED:
            claim_b["verdict"] = VERDICT_NOT_DECLARED
        claim_b["criterion_met"] = False
    in_model = bool(
        claim_b["verdict"] == VERDICT_SUPPORTED
        and claim_b["criterion_met"] is True
        and importance_bound is not None
        and bound["bound"]
        and floor >= 12
    )
    # The public flag does not stand in for ``in_model``. A later locked run
    # would have to meet its own pre-registered criterion. This function does
    # not take a caller flag that sets it.
    return {
        "claim_a": claim_a,
        "claim_a_direction": CLAIM_A_DIRECTION,
        "claim_b": claim_b,
        "evidence": bound,
        "importance_bound": None if importance_bound is None else float(importance_bound),
        "importance_is_mde": False,
        "in_model_support": in_model,
        "mde_a": None if mde_a is None else float(mde_a),
        "mde_b": None if mde_b is None else float(mde_b),
        "measurement_floor": floor,
        "measurement_floor_lowered": False,
        "public_flag_is_in_model_claim": False,
        "red_queen_proved": False,
        "supported_forbidden": importance_bound is None or not bound["bound"],
    }


def _install_hosts(arm: StructuralRQArm, seats: Sequence[Mapping[str, str]]) -> None:
    """Install genomes. Does not clear a hold and does not touch parasites."""

    patches = list(arm.food_patches)
    if not patches:
        raise ConfigurationError("phase-5 hosts require the shared food patches")
    organisms: list[GenesisOrganism] = []
    roles: dict[str, str] = {"parasite_stock": ROLE_SECONDARY}
    seen: set[str] = set()
    for index, seat in enumerate(seats):
        host_id = str(seat["host_id"])
        if host_id in seen:
            raise ConfigurationError(f"duplicate host id {host_id}")
        seen.add(host_id)
        organism = GenesisOrganism.from_bits(
            host_id,
            str(seat["genome"]),
            initial_runtime_atp=float(STRUCT_BIRTH_ATP),
            position=patches[index % len(patches)],
        )
        if _window(organism) != str(seat["window"]):
            raise ConfigurationError("installed genome does not decode to its window")
        organisms.append(organism)
        roles[host_id] = "primary"
    arm.runner.population = replace(arm.runner.population, organisms=tuple(organisms))
    arm.roles = roles


def hold_founder_genotypes(arm: StructuralRQArm, seats: Sequence[Mapping[str, str]]) -> None:
    """Keep founder windows without resetting a living host.

    A living id keeps its ATP, ATP ledger, execution age (``_step_index``),
    position, execution cursor, and memory object. A missing id is a
    replacement and is the only path that constructs a body. An id that is
    alive and not in the seat list is a ``population_exit`` with its energy
    out. Replacing every living id is ``rebuilt_population``, not this hold.
    Genotype restore, population exit, and energy resupply are not the same
    line. This hold writes neither an energy resupply nor a full rebuild.
    """

    patches = list(arm.food_patches)
    if not patches:
        raise ConfigurationError("phase-5 hosts require the shared food patches")
    ledger = getattr(cast(Any, arm), "intervention_ledger", None)
    if not isinstance(ledger, list):
        ledger = []
        cast(Any, arm).intervention_ledger = ledger
    ledger_start = len(ledger)
    by_id = {str(org.id): org for org in arm.runner.population.organisms}
    if len(by_id) != len(tuple(arm.runner.population.organisms)):
        raise ConfigurationError("duplicate host id")
    sum_before = sum(float(org.atp_state.runtime_available) for org in by_id.values())
    ordered: list[GenesisOrganism] = []
    roles: dict[str, str] = {"parasite_stock": ROLE_SECONDARY}
    seen: set[str] = set()
    for index, seat in enumerate(seats):
        host_id = str(seat["host_id"])
        if host_id in seen:
            raise ConfigurationError(f"duplicate host id {host_id}")
        seen.add(host_id)
        genome = str(seat["genome"])
        window = str(seat["window"])
        existing = by_id.get(host_id)
        if existing is None:
            organism = GenesisOrganism.from_bits(
                host_id,
                genome,
                initial_runtime_atp=float(STRUCT_BIRTH_ATP),
                position=patches[index % len(patches)],
            )
            ledger.append(
                {
                    "host_id": host_id,
                    "initial_atp": float(STRUCT_BIRTH_ATP),
                    "kind": "replacement",
                    "reset_memory": False,
                    "resupply": False,
                }
            )
        else:
            atp_before = float(existing.atp_state.runtime_available)
            memory_before = existing.episodic_memory
            age_before = int(existing._step_index)
            cursor_before = int(existing._cursor)
            position_before = existing.position
            ledger_before = existing.atp_state.ledger_digest()
            if _window(existing) != window:
                scratch = GenesisOrganism.from_bits(
                    host_id + ":genotype-scratch",
                    genome,
                    initial_runtime_atp=0.0,
                    position=existing.position,
                )
                existing.genome = scratch.genome
                existing.ribosome = scratch.ribosome
                existing.compiled_brain = scratch.compiled_brain
                if float(existing.atp_state.runtime_available) != atp_before:
                    raise ConfigurationError("genotype restore changed ATP")
                if existing.atp_state.ledger_digest() != ledger_before:
                    raise ConfigurationError("genotype restore changed the ATP ledger")
                if int(existing._step_index) != age_before:
                    raise ConfigurationError("genotype restore changed age")
                if existing.position != position_before:
                    raise ConfigurationError("genotype restore changed position")
                if int(existing._cursor) != cursor_before:
                    raise ConfigurationError("genotype restore changed execution state")
                if existing.episodic_memory is not memory_before:
                    raise ConfigurationError("genotype restore changed memory")
                ledger.append(
                    {
                        "host_id": host_id,
                        "kind": "genotype_restore",
                        "reset_atp": False,
                        "reset_memory": False,
                        "resupply": False,
                    }
                )
            organism = existing
        if _window(organism) != window:
            raise ConfigurationError("installed genome does not decode to its window")
        if int(organism._step_index) != (0 if existing is None else age_before):
            raise ConfigurationError("hold changed age")
        if organism.position != (patches[index % len(patches)] if existing is None else position_before):
            raise ConfigurationError("hold changed position")
        if int(organism._cursor) != (0 if existing is None else cursor_before):
            raise ConfigurationError("hold changed execution state")
        ordered.append(organism)
        roles[host_id] = "primary"
    rebuilt = bool(ordered) and all(str(org.id) not in by_id for org in ordered)
    fresh = ledger[ledger_start:]
    if rebuilt:
        for item in fresh:
            if item.get("kind") == "replacement":
                item["kind"] = "rebuilt_population"
    cast(Any, arm).intervention_name = "rebuilt_population" if rebuilt else "hold_founder_genotypes"
    for host_id, org in by_id.items():
        if host_id in seen:
            continue
        ledger.append(
            {
                "energy_out": float(org.atp_state.runtime_available),
                "host_id": host_id,
                "kind": "population_exit",
                "reset_atp": False,
                "resupply": False,
            }
        )
    # Earlier calls stay on the ledger. This call's balance uses only its own lines.
    fresh = ledger[ledger_start:]
    entries = sum(
        float(item["initial_atp"])
        for item in fresh
        if item.get("kind") in {"replacement", "rebuilt_population"}
    )
    exits = sum(float(item["energy_out"]) for item in fresh if item.get("kind") == "population_exit")
    sum_after = sum(float(org.atp_state.runtime_available) for org in ordered)
    if abs(sum_after - (sum_before - exits + entries)) > 1e-6:
        raise ConfigurationError("intervention energy does not balance")
    cast(Any, arm).energy_account = {
        "entries": entries,
        "exits": exits,
        "kind": cast(Any, arm).intervention_name,
        "sum_after": sum_after,
        "sum_before": sum_before,
        "target_quantity": "paired_infectivity_margin",
    }
    arm.runner.population = replace(arm.runner.population, organisms=tuple(ordered))
    arm.roles = roles


def enable_coevolution_birth_chamber(arm: StructuralRQArm) -> None:
    """Open the birth chamber without changing the locked mutation rate."""

    configs = arm.runner.configs
    parent_cost = float(configs.reproduction.parent_atp_cost)
    bit_flip = float(configs.mutation.bit_flip_rate)
    if not configs.reproduction.enabled or parent_cost <= 0.0:
        raise ConfigurationError("birth chamber requires reproduction and its cost")
    if not _rate_allowed(bit_flip, 0.0, float(STRUCT_HOST_BIT_FLIP)):
        raise ConfigurationError("host mutation is not the structural rate or the adaptation cut")
    chamber = SexualRecombinationConfig(
        enabled=True,
        same_length_only=True,
        recombination_prob=1.0,
        two_fold_cost_sex=False,
        diploid_meiosis=False,
        timeout_policy="asexual_fallback",
    )
    if not chamber.uses_birth_chamber:
        raise ConfigurationError("outcross birth requires the birth chamber")
    life = replace(configs.closed_loop_hp_life, role_by_id=tuple(sorted(arm.roles.items())))
    arm.runner.configs = replace(configs, sexual_recombination=chamber, closed_loop_hp_life=life)
    after = arm.runner.configs
    if not after.reproduction.enabled or float(after.reproduction.parent_atp_cost) != parent_cost:
        raise ConfigurationError("birth chamber changed reproduction")
    if not _rate_allowed(float(after.mutation.bit_flip_rate), bit_flip):
        raise ConfigurationError("birth chamber changed the host mutation rate")


def build_phase5_arm(arm_name: str, seed: int) -> StructuralRQArm:
    """One coevolution arm from the shared boot. Parasites are not deleted."""

    key = str(arm_name)
    if key not in ARMS:
        raise ConfigurationError(f"unknown phase-5 arm {arm_name!r}")
    if int(seed) in FORBIDDEN_SEEDS:
        raise ConfigurationError(f"phase-5 seed {seed} is forbidden")
    arm = build_arm(ARM_A, int(seed))
    arm.stream_root = STREAM_ROOT
    arm.stream_history = str(int(seed))
    if arm.antagonist_pop is None or not arm.antagonist_pop.units:
        raise ConfigurationError("phase-5 boot deleted the parasite population")
    if not arm.runner.configs.reproduction.enabled:
        raise ConfigurationError("phase-5 boot turned reproduction off")
    seats = equal_host_seats()
    _install_hosts(arm, seats)
    if key == ARM_ADAPTATION_CUT:
        configs = arm.runner.configs
        arm.runner.configs = replace(configs, mutation=replace(configs.mutation, bit_flip_rate=0.0))
        arm.passage = PASSAGE_FROZEN
        captured = [dict(seat) for seat in seats]
        cast(Any, arm).intervention_ledger = []

        def _hold(target: StructuralRQArm) -> None:
            hold_founder_genotypes(target, captured)

        arm.host_composition_hold = _hold
    elif key == ARM_CONSTANT_PARASITE:
        arm.passage = PASSAGE_FROZEN
        arm.host_composition_hold = None
    else:
        arm.passage = PASSAGE_COEVOLVE
        arm.host_composition_hold = None
    if arm.passage not in {PASSAGE_COEVOLVE, PASSAGE_FROZEN} or arm.passage == "shuffled_labels":
        raise ConfigurationError("phase-5 passage is not a locked control")
    if arm.host_inheritance != "transmit" or not arm.runner.configs.reproduction.enabled:
        raise ConfigurationError("phase-5 turned reproduction off")
    pop = arm.antagonist_pop
    if not _rate_allowed(float(pop.mutation_rate), float(STRUCT_PARASITE_MUTATION)):
        raise ConfigurationError("parasite mutation is not the structural rate")
    host_rate = float(arm.runner.configs.mutation.bit_flip_rate)
    if key == ARM_ADAPTATION_CUT and not _rate_allowed(host_rate, 0.0):
        raise ConfigurationError("adaptation cut left host mutation on")
    if key != ARM_ADAPTATION_CUT and not _rate_allowed(host_rate, float(STRUCT_HOST_BIT_FLIP)):
        raise ConfigurationError("host mutation is not the structural rate")
    enable_coevolution_birth_chamber(arm)
    if not arm._hosts():
        raise ConfigurationError("phase-5 deleted the host population")
    return arm


def _start_hosts(arm: StructuralRQArm) -> list[dict[str, str]]:
    return [{"id": str(org.id), "window": _window(org)} for org in arm._hosts()]


def _end_state(arm: StructuralRQArm) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    parents = {rec.organism_id: rec.parent_id for rec in arm.runner.population.lineage}
    hosts = [
        {
            "id": str(org.id),
            "parent_id": parents.get(org.id),
            "runtime_atp": float(org.atp_state.runtime_available),
            "window": _window(org),
        }
        for org in arm._hosts()
    ]
    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("end state requires parasites")
    parasites = [
        {
            "born_generation": int(unit.born_generation),
            "energy": float(unit.energy),
            "parent_id": unit.parent_id,
            "unit_id": unit.unit_id,
            "window": unit.window,
        }
        for unit in pop.units
    ]
    return cast(
        tuple[list[dict[str, object]], list[dict[str, object]]],
        (hosts, parasites),
    )


def _install_contact_tap(arm: StructuralRQArm) -> list[dict[str, object]]:
    snaps: list[dict[str, object]] = []
    original = arm._apply_hp_env_contact

    def wrapped() -> tuple[int, list[str]]:
        hosts, parasites = _end_state(arm)
        snaps.append({"hosts": hosts, "parasites": parasites, "tick": int(arm.tick_index)})
        return original()

    arm._apply_hp_env_contact = wrapped  # type: ignore[method-assign]
    return snaps


def scientific_body(arm: StructuralRQArm) -> dict[str, object]:
    """Fields a one-shot run and a resumed run must share."""

    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("scientific body requires parasites")
    hosts = sorted(
        (
            {
                "id": str(org.id),
                "runtime_atp": round(float(org.atp_state.runtime_available), 9),
                "window": _window(org),
            }
            for org in arm._hosts()
        ),
        key=lambda row: str(row["id"]),
    )
    parasites = sorted(
        (
            {
                "energy": round(float(unit.energy), 9),
                "parent_id": unit.parent_id,
                "unit_id": unit.unit_id,
                "window": unit.window,
            }
            for unit in pop.units
        ),
        key=lambda row: str(row["unit_id"]),
    )
    paid = [round(float(sum(record[4] for record in records)), 9) for records in arm.contact_pair_records]
    return {
        "contacts": list(arm.graded_contact_count),
        "hosts": hosts,
        "paid": paid,
        "parasites": parasites,
        "tick_index": int(arm.tick_index),
    }


def _first_diff(left: object, right: object, prefix: str = "") -> str | None:
    if type(left) is not type(right):
        return prefix or "type"
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                return f"{prefix}.{key}" if prefix else str(key)
            found = _first_diff(left[key], right[key], f"{prefix}.{key}" if prefix else str(key))
            if found:
                return found
        return None
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return f"{prefix}.len" if prefix else "len"
        for index, (item, other) in enumerate(zip(left, right, strict=True)):
            found = _first_diff(item, other, f"{prefix}[{index}]")
            if found:
                return found
        return None
    if left != right:
        return prefix or "value"
    return None


class _Append:
    def __init__(self, path: Path) -> None:
        self._has_flock: bool = False
        try:
            import fcntl

            self._flock = fcntl.flock
            self._lock_ex = fcntl.LOCK_EX
            self._lock_un = fcntl.LOCK_UN
            self._has_flock = True
        except ImportError:
            pass

        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8", buffering=1)

    def line(self, text: str) -> None:
        payload = text if text.endswith("\n") else text + "\n"
        if self._has_flock:
            self._flock(self._fh.fileno(), self._lock_ex)
        try:
            self._fh.write(payload)
            self._fh.flush()
        finally:
            if self._has_flock:
                self._flock(self._fh.fileno(), self._lock_un)

    def close(self) -> None:
        self._fh.close()


def birth_archive_witness(
    record: LineageRecord,
    start_windows: Mapping[str, str],
    contact_windows: Mapping[str, str],
) -> dict[str, object]:
    """Preserve both genetic parents and recombination/mutation birth metadata.

    Legacy fields remain readable. Missing windows are unmeasured, not an
    invented genotype. Parentage identifies contributors; it does not assume
    equal contributions of recognition loci in a recombined child.
    """
    parents_list: list[str] = []
    if record.parent_id:
        parents_list.append(record.parent_id)
    second = record.second_parent_id
    if second:
        # Selfing keeps both slots. A missing primary must not erase the mate.
        if (record.parent_id and second == record.parent_id) or second not in parents_list:
            parents_list.append(second)
    parents = tuple(parents_list)
    windows = {parent: start_windows.get(parent, contact_windows.get(parent)) for parent in parents}
    sources = {parent: "generation_start" if parent in start_windows else
               "pre_contact" if parent in contact_windows else "unmeasured" for parent in parents}
    lineage = record.to_dict()
    if second and lineage.get("parent_ids") != list(parents):
        lineage["parent_ids"] = list(parents)
    # to_dict stores this flag only when it is true, which erases a real false.
    if record.recombination_window_differed is False:
        lineage["recombination_window_differed"] = False
    return {
        "id": record.organism_id,
        "parent_id": record.parent_id,
        "parent_window": None if not record.parent_id else start_windows.get(str(record.parent_id)),
        "second_parent_id": record.second_parent_id,
        "parent_ids": list(parents),
        "parent_windows": windows,
        "parent_window_sources": sources,
        "parent_windows_complete": bool(parents) and all(window is not None for window in windows.values()),
        "child_window_pre_contact": contact_windows.get(record.organism_id),
        "lineage_record": lineage,
        "evidence_schema": "genesis-birth-witness/2",
    }


def run_phase5_history(
    seed: int,
    root_text: str,
    generations: int,
    *,
    arms: Sequence[str] = ARMS,
    compare_one_shot: bool = True,
    passage_override: str | None = None,
) -> dict[str, object]:
    """Advance one generation at a time. A failure keeps the partial archive."""

    root = Path(root_text)
    assert_output_dir(root)
    if int(seed) in FORBIDDEN_SEEDS:
        raise ConfigurationError(f"phase-5 seed {seed} is forbidden")
    seed_dir = root / "by_seed" / f"seed{int(seed)}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    stop = root / "STOP"
    live = _Append(root / "live.log")
    archive_path = seed_dir / "archive.jsonl"
    failed: str | None = None
    completed = 0
    try:
        built = {name: build_phase5_arm(name, int(seed)) for name in arms}
        if passage_override is not None:
            if str(passage_override) != PASSAGE_ABSENT:
                raise ConfigurationError("passage override is only the no-parasite baseline")
            for arm in built.values():
                arm.passage = PASSAGE_ABSENT
        taps = {name: _install_contact_tap(built[name]) for name in arms}
        founders = {name: {org.id for org in built[name]._hosts()} for name in arms}
        with archive_path.open("a", encoding="utf-8", buffering=1) as archive:
            for name in arms:
                while (root / "PAUSE").is_file() or ((root.parent / "PAUSE").is_file()):
                    if stop.exists() or (root.parent / "STOP").is_file():
                        break
                    time.sleep(0.2)
                if failed or stop.exists() or (root.parent / "STOP").is_file():
                    if failed is None:
                        failed = "stopped"
                    break
                arm = built[name]
                for generation in range(1, int(generations) + 1):
                    while (root / "PAUSE").is_file() or ((root.parent / "PAUSE").is_file()):
                        if stop.exists() or (root.parent / "STOP").is_file():
                            break
                        time.sleep(0.2)
                    if stop.exists() or (root.parent / "STOP").is_file():
                        failed = "stopped"
                        break
                    start = _start_hosts(arm)
                    start_ids = {row["id"] for row in start}
                    window_by_id = {row["id"]: row["window"] for row in start}
                    before_lineage = {rec.organism_id for rec in arm.runner.population.lineage}
                    try:
                        arm.run_generations(1)
                    except Exception as exc:
                        failed = f"exception:{type(exc).__name__}:{exc}"[:500]
                        break
                    status = invariant_status(arm, generation=generation, founder_ids=founders[name])
                    hosts, parasites = _end_state(arm)
                    end_ids = {str(row["id"]) for row in hosts}
                    births = [
                        rec
                        for rec in arm.runner.population.lineage
                        if rec.organism_id not in before_lineage and rec.parent_id and int(rec.generation) != 0
                    ]
                    birth_ids = {rec.organism_id for rec in births}
                    deaths = sorted((start_ids - end_ids) | (birth_ids - end_ids))
                    pop = arm.antagonist_pop
                    if pop is None or len(taps[name]) < generation:
                        failed = "missing-population"
                        break
                    contact = taps[name][generation - 1]
                    events = arm.antagonist_contact_events[-1] if arm.antagonist_contact_events else ()
                    paid = float(sum(float(event.atp_paid) for event in events))
                    record = {
                        "arm": name,
                        "config_digest": config_digest(),
                        "contact_credit": float(pop.energy_accounts[-1].contact_income),
                        "contact_debit": paid,
                        "contact_hosts": contact["hosts"],
                        "contact_parasites": contact["parasites"],
                        "contact_tick": same_int(contact["tick"]),
                        "contacts": int(arm.graded_contact_count[-1]) if arm.graded_contact_count else 0,
                        "generation": int(generation),
                        "host_births": [
                            birth_archive_witness(
                                rec, window_by_id,
                                {str(host["id"]): str(host["window"]) for host in (same_mapping(item) for item in same_iter(contact["hosts"]))},
                            )
                            for rec in births
                        ],
                        "birth_evidence_schema": "genesis-birth-witness/2",
                        "host_deaths": deaths,
                        "hosts": hosts,
                        "invariant": status,
                        "parasite_births": len(pop.ledgers[-1].newborns),
                        "parasite_census": len(pop.units),
                        "parasites": parasites,
                        "passage": arm.passage,
                        "red_queen_proved": False,
                        "reproduction_enabled": bool(arm.runner.configs.reproduction.enabled),
                        "schema": ARCHIVE_SCHEMA,
                        "seed": int(seed),
                        "start_hosts": start,
                        "start_windows": [row["window"] for row in start],
                    }
                    archive.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
                    archive.flush()
                    live.line(
                        f"phase=5 seed={seed} arm={name} generation={generation} "
                        f"contacts={record['contacts']} invariant={status} red_queen_proved=false"
                    )
                    completed = generation
                    if status != "ok":
                        failed = str(status)
                        break
                    if not bool(record["reproduction_enabled"]):
                        failed = "reproduction-off"
                        break
                if failed:
                    break
        if failed is None and compare_one_shot and not stop.exists():
            for name in arms:
                other = build_phase5_arm(name, int(seed))
                _install_contact_tap(other)
                other.run_generations(int(generations))
                diff = _first_diff(scientific_body(built[name]), scientific_body(other))
                if diff:
                    failed = f"one-shot-resume-mismatch:{name}:{diff}"
                    break
    finally:
        live.close()
    if failed is None:
        persisted = _load_jsonl(archive_path)
        expected = {(name, generation) for name in arms for generation in range(1, int(generations) + 1)}
        observed = {(row.get("arm"), row.get("generation")) for row in persisted}
        if not expected or len(persisted) != len(expected) or observed != expected:
            failed = "archive-integrity:incomplete-or-duplicated-generation"
        elif stop.exists():
            failed = "stopped"
    if failed:
        (seed_dir / "COMPLETE").unlink(missing_ok=True)
        (seed_dir / "REASON.txt").write_text(failed + "\n", encoding="utf-8")
        stop.write_text(failed + "\n", encoding="utf-8")
        return {"failed": failed, "generations_completed": completed, "red_queen_proved": False, "seed": int(seed)}
    (seed_dir / "COMPLETE").write_text(f"generations={int(generations)} red_queen_proved=false\n", encoding="utf-8")
    return {"failed": None, "generations_completed": int(generations), "red_queen_proved": False, "seed": int(seed)}


def _worker(payload: Mapping[str, object]) -> dict[str, object]:
    arms = payload["arms"]
    if not isinstance(arms, list):
        raise ConfigurationError("worker arms must be a list")
    return run_phase5_history(
        same_int(payload["seed"]),
        str(payload["root"]),
        same_int(payload["generations"]),
        arms=tuple(str(item) for item in arms),
        compare_one_shot=bool(payload["compare_one_shot"]),
        passage_override=None if payload.get("passage_override") is None else str(payload["passage_override"]),
    )


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    return rows


def replay_phase5_archive(path: Path) -> dict[str, object]:
    """Re-score contact populations with evolution, reproduction, and mutation off."""

    mismatches: list[dict[str, object]] = []
    compared = 0
    unmeasurable = 0
    for line_number, row in enumerate(_load_jsonl(path), start=1):
        hosts = row.get("contact_hosts")
        parasites = row.get("contact_parasites")
        if not isinstance(hosts, list) or not isinstance(parasites, list):
            mismatches.append({"generation": row.get("generation"), "reason": "contact-population-missing"})
            continue
        if not hosts or not parasites:
            unmeasurable += 1
            if same_int(row.get("contacts") or 0) != 0 or same_float(row.get("contact_debit") or 0.0) != 0.0:
                mismatches.append({"generation": row.get("generation"), "reason": "empty-population-had-contact"})
            continue
        scored = replay_archived_contact(
            json.loads(json.dumps(hosts)),
            json.loads(json.dumps(parasites)),
            tick_index=same_int(row["contact_tick"]),
            seed=0,
        )
        compared += 1
        debit_gap = abs(same_float(scored["total_debit"]) - same_float(row["contact_debit"]))
        credit_gap = abs(same_float(scored["credit"]) - same_float(row["contact_credit"]))
        flags_off = scored["evolution"] is False and scored["reproduction"] is False and scored["mutation"] is False
        if debit_gap > REPLAY_ABS_TOL or credit_gap > REPLAY_ABS_TOL or not flags_off:
            mismatches.append(
                {
                    "arm": row.get("arm"),
                    "credit_gap": credit_gap,
                    "debit_gap": debit_gap,
                    "generation": row.get("generation"),
                    "line": line_number,
                    "reason": "replay-field-mismatch",
                }
            )
            if len(mismatches) >= 5:
                break
    return {
        "compared_generations": compared,
        "matched": not mismatches,
        "mismatches": mismatches,
        "red_queen_proved": False,
        "unmeasurable_generations": unmeasurable,
    }


def _arm_rows(rows: Sequence[Mapping[str, object]], arm: str) -> dict[int, Mapping[str, object]]:
    mapped: dict[int, Mapping[str, object]] = {}
    for row in rows:
        if str(row.get("arm")) != arm:
            continue
        generation = same_int(row["generation"])
        if generation in mapped:
            raise ConfigurationError("duplicate generations")
        mapped[generation] = row
    return mapped


def _people(row: Mapping[str, object], key: str) -> list[dict[str, object]] | None:
    value = row.get(key)
    if not isinstance(value, list) or not value:
        return None
    people = [dict(item) for item in value if isinstance(item, dict)]
    return people or None


def _window_tuple(people: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    return tuple(str(person["window"]) for person in people)


def score_arm_contrast(rows: Sequence[Mapping[str, object]], arm: str, *, lag: int, horizon: int) -> float | None:
    """Claim A on the coevolve arm. A missing population stays null.

    This is horizon hosts against two parasite generations. It is not a
    control. On a frozen roster the two parasite inputs are the same windows.
    """

    mapped = _arm_rows(rows, arm)
    now = mapped.get(int(horizon))
    past = mapped.get(int(horizon) - int(lag))
    if now is None or past is None:
        return None
    hosts = _people(now, "hosts")
    parasites_now = _people(now, "parasites")
    parasites_past = _people(past, "parasites")
    if hosts is None or parasites_now is None or parasites_past is None:
        return None
    return contemporary_minus_past(infectivity(hosts, parasites_now), infectivity(hosts, parasites_past))


def score_constant_parasite_contrast(
    rows: Sequence[Mapping[str, object]], *, lag: int, horizon: int
) -> dict[str, object]:
    """Host change against one frozen parasite roster.

    Prediction: subtracting two frozen parasite generations from the same
    hosts is identically zero, and it hides host change. Engine path: both
    ``infectivity`` calls receive the horizon parasite list only.
    ``replay_archived_contact`` rewrites ATP and pairs by seat. The past
    parasite generation is not a second input. Control: the past term is the
    earlier hosts against that same roster, so a changed host window can move
    the seat mean. Source: frozen reseat, not a coevolve sign. Limit: this
    does not replace claim A. Estimand: host change, not a parasite time-shift.
    """

    blank: dict[str, object] = {
        "frozen_rosters_match": None,
        "hosts_differ": None,
        "inputs_are_copies": None,
        "parasite_inputs": "single_horizon_roster",
        "past_parasite_used_as_second_input": False,
        "value": None,
    }
    mapped = _arm_rows(rows, ARM_CONSTANT_PARASITE)
    now = mapped.get(int(horizon))
    past = mapped.get(int(horizon) - int(lag))
    if now is None or past is None:
        return blank
    hosts_now = _people(now, "hosts")
    hosts_past = _people(past, "hosts")
    parasites = _people(now, "parasites")
    parasites_past = _people(past, "parasites")
    if hosts_now is None or hosts_past is None or parasites is None:
        return blank
    hosts_differ = _window_tuple(hosts_now) != _window_tuple(hosts_past)
    frozen_match = parasites_past is not None and _window_tuple(parasites) == _window_tuple(parasites_past)
    value = contemporary_minus_past(infectivity(hosts_now, parasites), infectivity(hosts_past, parasites))
    return {
        "frozen_rosters_match": frozen_match,
        "hosts_differ": hosts_differ,
        "inputs_are_copies": not hosts_differ,
        "parasite_inputs": "single_horizon_roster",
        "past_parasite_used_as_second_input": False,
        "value": value,
    }


def score_adaptation_cut_contrast(
    rows: Sequence[Mapping[str, object]], *, lag: int, horizon: int
) -> dict[str, object]:
    """Matched-pair change. Either side can move it.

    Prediction: a held population stays put, but the contrast is not built by
    copying one parasite list onto both times. Engine path: each generation's
    own hosts and parasites go through ``infectivity``. One seat whose window
    differs changes that seat's ``graded_affinity`` inside
    ``_apply_hp_env_contact``. Control: the other term is the earlier pair,
    not a second copy of the horizon parasites. Source: the seat assay, which
    already moves when one window changes. Limit: claim A on coevolve stays
    the parasite time-shift on horizon hosts. Estimand: change of the matched
    pair, so a real host change or a real parasite change is visible.
    """

    blank: dict[str, object] = {
        "hosts_differ": None,
        "inputs_are_copies": None,
        "parasites_differ": None,
        "value": None,
    }
    mapped = _arm_rows(rows, ARM_ADAPTATION_CUT)
    now = mapped.get(int(horizon))
    past = mapped.get(int(horizon) - int(lag))
    if now is None or past is None:
        return blank
    hosts_now = _people(now, "hosts")
    hosts_past = _people(past, "hosts")
    parasites_now = _people(now, "parasites")
    parasites_past = _people(past, "parasites")
    if hosts_now is None or hosts_past is None or parasites_now is None or parasites_past is None:
        return blank
    hosts_differ = _window_tuple(hosts_now) != _window_tuple(hosts_past)
    parasites_differ = _window_tuple(parasites_now) != _window_tuple(parasites_past)
    value = contemporary_minus_past(
        infectivity(hosts_now, parasites_now),
        infectivity(hosts_past, parasites_past),
    )
    return {
        "hosts_differ": hosts_differ,
        "inputs_are_copies": not hosts_differ and not parasites_differ,
        "parasites_differ": parasites_differ,
        "value": value,
    }


def score_claim_b_pieces(rows: Sequence[Mapping[str, object]], *, lag: int, horizon: int) -> dict[str, object]:
    """Claim B pieces from the coevolve archive. Missing pieces stay null."""

    mapped = _arm_rows(rows, ARM_COEVOLVE)
    focal = mapped.get(int(horizon))
    past = mapped.get(int(horizon) - int(lag))
    blank: dict[str, object] = {
        "contact_pressure": None,
        "contacts": None,
        "fitness_measured": None,
        "frequency": None,
        "reversal": None,
    }
    if focal is None or past is None:
        return blank
    windows = focal.get("start_windows")
    frequency = genotype_frequency([str(item) for item in windows] if isinstance(windows, list) else None)
    contacts = 0
    paid = 0.0
    births_all: list[dict[str, object]] = []
    deaths_recorded = True
    for generation in range(1, int(horizon) + 1):
        row = mapped.get(generation)
        if row is None or not _finite(row.get("contact_debit")) or not isinstance(row.get("contacts"), int):
            return blank
        if not isinstance(row.get("host_deaths"), list):
            deaths_recorded = False
        birth_rows = row.get("host_births")
        if isinstance(birth_rows, list):
            births_all.extend(item for item in birth_rows if isinstance(item, dict))
        else:
            deaths_recorded = False
        contacts += same_int(row["contacts"])
        paid += same_float(row["contact_debit"])
    first = mapped.get(1)
    start_hosts = first.get("start_hosts") if first is not None else None
    living = focal.get("hosts")
    fitness = descendant_fitness(
        [item for item in start_hosts if isinstance(item, dict)] if isinstance(start_hosts, list) else None,
        births_all,
        [item for item in living if isinstance(item, dict)] if isinstance(living, list) else None,
        deaths_recorded,
    )
    parasites_now = _people(focal, "parasites")
    parasites_past = _people(past, "parasites")
    reversal: bool | None = None
    if parasites_now is not None and parasites_past is not None:
        gap_now = specialization_gap(
            infectivity(pure_host_rows(WINDOW_A, GENOME_A, len(parasites_now), label="A"), parasites_now),
            infectivity(pure_host_rows(WINDOW_B, GENOME_B, len(parasites_now), label="B"), parasites_now),
        )
        gap_past = specialization_gap(
            infectivity(pure_host_rows(WINDOW_A, GENOME_A, len(parasites_past), label="A"), parasites_past),
            infectivity(pure_host_rows(WINDOW_B, GENOME_B, len(parasites_past), label="B"), parasites_past),
        )
        reversal = direction_reversal(gap_now, gap_past)
    return {
        "contact_pressure": paid,
        "contacts": contacts,
        "fitness_measured": bool(fitness["measured"]),
        "frequency": frequency,
        "lineage_fitness": fitness["by_window"],
        "reversal": reversal,
    }


def probe_turnover(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Replacement time. This does not score a time-shift contrast."""

    newborns: list[int] = []
    censuses: list[int] = []
    infectivities: list[float] = []
    host_births: list[int] = []
    for row in rows:
        if str(row.get("arm")) != ARM_COEVOLVE:
            continue
        newborns.append(same_int(row["parasite_births"]))
        censuses.append(same_int(row["parasite_census"]))
        births = row.get("host_births")
        host_births.append(len(births) if isinstance(births, list) else 0)
        contacts = row.get("contacts")
        if isinstance(contacts, int) and contacts > 0 and _finite(row.get("contact_debit")):
            infectivities.append(same_float(row["contact_debit"]) / same_float(contacts) / ASSAY_SCALE)
    if not newborns:
        raise ConfigurationError("probe archive has no coevolve generations")
    mean_newborns = float(statistics.fmean(newborns))
    census = int(round(float(statistics.fmean(censuses))))
    sigma = PLANNING_SIGMA_A
    sigma_source = "planning"
    if len(infectivities) >= 2:
        measured = float(statistics.stdev(infectivities))
        if measured > 0.0:
            sigma = max(measured, PLANNING_SIGMA_A)
            sigma_source = "max(probe infectivity sd, planning sigma)"
    return {
        "census": census,
        "generations": len(newborns),
        "host_births_mean": float(statistics.fmean(host_births)) if host_births else None,
        "mean_seated_newborns": mean_newborns,
        "measurable": mean_newborns > 0.0 and census > 0,
        "sigma_a": sigma,
        "sigma_a_source": sigma_source,
        "sigma_b": PLANNING_SIGMA_B,
    }


def design_from_probe(turnover: Mapping[str, object]) -> dict[str, object]:
    """Choose lag, horizon, and n. A claim contrast in the input is refused."""

    if "claim_a" in turnover or "reversal" in turnover:
        raise ConfigurationError("probe design must not be chosen from a claim contrast")
    chosen = choose_lag_and_horizon(
        mean_newborns=same_float(turnover["mean_seated_newborns"]) if turnover.get("measurable") else None,
        census=same_int(turnover["census"]),
        measurable=bool(turnover.get("measurable")),
    )
    power = history_count_from_power(same_float(turnover["sigma_a"]), same_float(turnover["sigma_b"]))
    seeds = locked_confirmatory_seeds(same_int(power["n"]))
    return {
        "horizon": same_int(chosen["horizon"]),
        "importance_bound": None,
        "mde_a": power["mde_a"],
        "mde_b": power["mde_b"],
        "n": same_int(power["n"]),
        "precision_met": bool(power["precision_met"]),
        "primary_lag": same_int(chosen["primary_lag"]),
        "replacement_generations": chosen["replacement_generations"],
        "seeds": list(seeds),
        "sigma_a": power["sigma_a"],
        "sigma_b": power["sigma_b"],
    }


def render_phase5_lock(design: Mapping[str, object], *, code_commit: str) -> str:
    """Lock text. The required sentence is first and last."""

    seeds = [same_int(seed) for seed in same_iter(design["seeds"])]
    payload = {
        "horizon": same_int(design["horizon"]),
        "importance_bound": None,
        "mde_a": design["mde_a"],
        "mde_b": design["mde_b"],
        "measurement_floor": int(MEASUREMENT_FLOOR),
        "n": same_int(design["n"]),
        "primary_lag": same_int(design["primary_lag"]),
        "probe_generations": PROBE_GENERATIONS,
        "probe_seed": PROBE_SEED,
        "seeds": seeds,
        "workers": MAX_WORKERS,
    }
    block = json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        "# Phase-5 lock",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
        f"Code commit: `{code_commit}` on branch `rq/mechanism-v2`.",
        "Nothing has been pushed, merged, or rebased.",
        "`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.",
        "Previous mechanism-v2 runs are not modified. `PHASE3_LOCK.md` is not modified.",
        "",
        "## Claim A",
        "",
        "Directional reciprocal adaptation.",
        "Direction, locked before the confirmatory:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag) > 0`.",
        "Contemporary parasite performance on the focal hosts is predicted to exceed performance of the past parasites.",
        "The score is `infectivity` on `replay_archived_contact` with evolution, reproduction, and mutation off.",
        "The direction is the contemporary-versus-previous comparison read from Decaestecker et al. 2007 in `PHASE1.md`",
        "(contemporary infectivity 0.65, previous 0.55). It was not chosen from a probe contrast.",
        "The primary arm is `coevolve`.",
        "",
        "## Claim B",
        "",
        "Frequency-dependent selection and an oscillating Red Queen.",
        "Required together on the coevolve arm: genotype frequency as window counts;",
        "real contact pressure (contacts and ATP paid on the debit path);",
        "relative fitness from the lineage (parent ids, births, deaths, next-generation share over start frequency);",
        "and a sign reversal of `I(A) - I(B)` between the contemporary and past parasite populations.",
        "ATP loss is not fitness. A census wave, a lagged correlation, or a renamed class is not claim B.",
        "Claim A is not claim B. A positive D or a nonzero F from an earlier phase is not this confirmatory.",
        "`red_queen_proved` is true only if claim B's locked criterion is met, including a declared importance bound.",
        "",
        "## Controls",
        "",
        "`adaptation_cut`: host bit-flip 0, parasite passage `frozen`, founder host genomes restored before contact.",
        "Host `reproduction.enabled` stays true. This is not reproduction-off and not `freeze_host_genotypic_inheritance`.",
        "`shuffled_labels` is not used. `shuffled_labels` is not a frozen genotype.",
        "`constant_parasite`: parasite passage `frozen`, so parasite genotype composition is held.",
        "Contact and the debit stay. Host bit-flip stays the structural rate. The host population is not deleted.",
        "Passage `absent` is not used.",
        "",
        "## Lag, horizon, and n",
        "",
        f"Probe seed: {PROBE_SEED} only. It is not a confirmatory history.",
        f"Exploratory budget: {PROBE_GENERATIONS} generations, coevolve arm only, no lag grid.",
        "Primary lag is `max(1, round(parasite census / mean seated newborns))`.",
        f"Turnover multiple: {int(TURNOVER_MULTIPLE)}, the phase-3 multiple, not a contrast search.",
        f"Primary lag: {same_int(design['primary_lag'])}.",
        f"Horizon: {same_int(design['horizon'])} generations.",
        f"Replacement generations: {design['replacement_generations']}.",
        f"n: {same_int(design['n'])}.",
        f"Seeds: {seeds[0]} through {seeds[-1]} ({', '.join(str(seed) for seed in seeds)}).",
        "",
        "## Importance and the minimum detectable effect",
        "",
        "Importance for this estimand is undeclared. SUPPORTED is forbidden.",
        "The Decaestecker gap of 0.10 is a different system and is not this engine's importance bound.",
        "The probe was not used to invent an importance bound after a sign.",
        f"Planning sigma for claim A is {design['sigma_a']} (at least {PLANNING_SIGMA_A}).",
        f"Planning sigma for claim B is {PLANNING_SIGMA_B}. It is not a probe reversal rate.",
        f"Precision targets, separate from importance: claim A {PRECISION_A}, claim B {PRECISION_B}.",
        f"MDE claim A: {design['mde_a']}. MDE claim B: {design['mde_b']}.",
        "The minimum detectable effect is not the importance bound.",
        f"`MEASUREMENT_FLOOR` stays {int(MEASUREMENT_FLOOR)} and is not lowered.",
        f"`precision_met`: {bool(design['precision_met'])}.",
        "",
        "## Run rules",
        "",
        "CPU workers at most 7.",
        f"Output: `{OUTPUT_CONFIRMATORY}`.",
        "Raw archives are kept. A partial run is kept. A seed is not replaced.",
        "Extinction and fixation stay in the archive.",
        "Energy invariants are checked every generation. A real invariant failure stops the run.",
        "Replay of the same confirmatory run is required. One-shot and resume must match.",
        "Evolution, reproduction, and mutation are off on the replay copy.",
        "If replay does not match, stop. That is a bug. Do not edit the engine after the verdict.",
        "",
        "```json",
        block,
        "```",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
    ]
    return "\n".join(lines)


def _lock_payload(lock_text: str) -> dict[str, object]:
    if NO_CONFIRMATORY_SENTENCE not in lock_text:
        raise ConfigurationError("phase-5 lock is missing its sentence")
    start = lock_text.find("```json")
    end = lock_text.find("```", start + 7)
    if start < 0 or end < 0:
        raise ConfigurationError("phase-5 lock has no json block")
    parsed = json.loads(lock_text[start + len("```json") : end])
    if not isinstance(parsed, dict):
        raise ConfigurationError("phase-5 lock block is not an object")
    return parsed


def execute_probe(root: Path | None = None) -> dict[str, object]:
    """Seed 9600 only. No confirmatory seed is opened."""

    target = OUTPUT_PROBE if root is None else root
    assert_output_dir(target)
    if (target / "by_seed").exists():
        raise ConfigurationError("probe output already exists; a seed is not replaced")
    outcome = run_phase5_history(
        PROBE_SEED,
        str(target),
        PROBE_GENERATIONS,
        arms=(ARM_COEVOLVE,),
        compare_one_shot=False,
    )
    rows = _load_jsonl(target / "by_seed" / f"seed{PROBE_SEED}" / "archive.jsonl")
    if outcome["failed"]:
        summary: dict[str, object] = {"failed": outcome["failed"], "red_queen_proved": False, "seed": PROBE_SEED}
    else:
        turnover = probe_turnover(rows)
        summary = {
            "design": design_from_probe(turnover),
            "failed": None,
            "red_queen_proved": False,
            "turnover": turnover,
        }
    target.mkdir(parents=True, exist_ok=True)
    (target / "probe_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _score_seed(seed_dir: Path, *, lag: int, horizon: int) -> dict[str, object]:
    rows = _load_jsonl(seed_dir / "archive.jsonl")
    pieces = score_claim_b_pieces(rows, lag=lag, horizon=horizon)
    cut = score_adaptation_cut_contrast(rows, lag=lag, horizon=horizon)
    held = score_constant_parasite_contrast(rows, lag=lag, horizon=horizon)
    return {
        "adaptation_cut_detail": cut,
        "claim_a": score_arm_contrast(rows, ARM_COEVOLVE, lag=lag, horizon=horizon),
        "claim_a_adaptation_cut": cut["value"],
        "claim_a_constant_parasite": held["value"],
        "constant_parasite_detail": held,
        "contact_pressure": pieces["contact_pressure"],
        "contacts": pieces["contacts"],
        "fitness_measured": pieces["fitness_measured"],
        "frequency": pieces["frequency"],
        "lineage_fitness": pieces.get("lineage_fitness"),
        "reversal": pieces["reversal"],
        "seed": int(seed_dir.name.removeprefix("seed")),
    }


def execute_confirmatory(lock_path: Path, root: Path | None = None) -> dict[str, object]:
    """Run the locked seeds. Do not add seeds. Stop on a real failure and keep it."""

    target = OUTPUT_CONFIRMATORY if root is None else root
    assert_output_dir(target)
    payload = _lock_payload(lock_path.read_text(encoding="utf-8"))
    n = same_int(payload["n"])
    lag = same_int(payload["primary_lag"])
    horizon = same_int(payload["horizon"])
    seeds = locked_confirmatory_seeds(n)
    if [same_int(seed) for seed in same_iter(payload["seeds"])] != list(seeds):
        raise ConfigurationError("lock seeds are not 9601 through 9600+n")
    if same_int(payload["workers"]) > MAX_WORKERS:
        raise ConfigurationError("lock workers exceed 7")
    if payload.get("importance_bound") is not None:
        raise ConfigurationError("this lock declared an importance bound that was not justified")
    if (target / "by_seed").exists():
        raise ConfigurationError("confirmatory output already exists; a seed is not replaced")
    target.mkdir(parents=True, exist_ok=True)
    workers = resolve_workers(min(MAX_WORKERS, len(seeds)))
    payloads = [
        {"arms": list(ARMS), "compare_one_shot": True, "generations": horizon, "root": str(target), "seed": seed}
        for seed in seeds
    ]
    outcomes: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_worker, item) for item in payloads]
        for future in as_completed(futures):
            outcomes.append(future.result())
    outcomes.sort(key=lambda item: same_int(item["seed"]))
    failed = [item for item in outcomes if item["failed"]]
    replays: list[dict[str, object]] = []
    if not failed:
        for seed in seeds:
            replays.append(replay_phase5_archive(target / "by_seed" / f"seed{seed}" / "archive.jsonl"))
    replay_matched = bool(replays) and all(bool(item["matched"]) for item in replays)
    mde_a = same_float(payload["mde_a"]) if _finite(payload.get("mde_a")) else None
    mde_b = same_float(payload["mde_b"]) if _finite(payload.get("mde_b")) else None
    if failed or not replay_matched:
        if not failed:
            (target / "REASON.txt").write_text("replay-mismatch\n", encoding="utf-8")
        present = []
        for seed in seeds:
            if (target / "by_seed" / f"seed{seed}" / "COMPLETE").is_file():
                present.append(_score_seed(target / "by_seed" / f"seed{seed}", lag=lag, horizon=horizon))
        report = assess_phase5(present, seeds, importance_bound=None, mde_a=mde_a, mde_b=mde_b)
        report["red_queen_proved"] = False
        cast(dict[str, object], report["claim_b"])["criterion_met"] = False
        summary: dict[str, object] = {
            "failed": failed,
            "horizon": horizon,
            "n_locked": len(seeds),
            "primary_lag": lag,
            "replay": replays,
            "replay_matched": replay_matched,
            "report": report,
            "seeds": list(seeds),
            "stopped": failed[0]["failed"] if failed else "replay-mismatch",
            "workers": workers,
        }
        (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary
    scored = [_score_seed(target / "by_seed" / f"seed{seed}", lag=lag, horizon=horizon) for seed in seeds]
    report = assess_phase5(scored, seeds, importance_bound=None, mde_a=mde_a, mde_b=mde_b)
    summary = {
        "by_seed": scored,
        "controls": {
            "adaptation_cut": [row["claim_a_adaptation_cut"] for row in scored],
            "constant_parasite": [row["claim_a_constant_parasite"] for row in scored],
        },
        "horizon": horizon,
        "n_locked": len(seeds),
        "one_shot_vs_resume": "matched on scientific_body inside each history before COMPLETE",
        "primary_lag": lag,
        "replay": replays,
        "replay_matched": True,
        "report": report,
        "seeds": list(seeds),
        "stopped": None,
        "workers": workers,
    }
    summary["summary_sha256"] = hashlib.sha256(
        json.dumps({key: value for key, value in summary.items() if key != "summary_sha256"}, sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()
    (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def locked_phase5b_seeds() -> tuple[int, ...]:
    """Seeds 9701 through 9712. Probe 9600 and the rejected seeds are excluded."""

    count = int(PHASE5B_N)
    floor = assert_measurement_floor()
    if count < floor:
        raise ConfigurationError("phase-5b history count is below MEASUREMENT_FLOOR")
    seeds = tuple(range(PHASE5B_SEED_START, PHASE5B_SEED_START + count))
    banned = set(FORBIDDEN_SEEDS) | set(range(9600, 9613)) | {PROBE_SEED, 9700}
    if len(seeds) != count or len(set(seeds)) != count or (set(seeds) & banned):
        raise ConfigurationError("phase-5b seeds are not 9701 through 9712")
    if seeds[0] != 9701 or seeds[-1] != 9712:
        raise ConfigurationError("phase-5b seeds are not 9701 through 9712")
    return seeds


def assert_phase5b_output_dir(root: Path) -> None:
    """Phase 5b writes only its own tree. The rejected run stays put."""

    assert_output_dir(root)
    resolved = root.resolve()
    for banned in (OUTPUT_CONFIRMATORY, OUTPUT_PROBE):
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise ConfigurationError(f"phase-5b must not write into {banned}")


def render_phase5b_lock(*, code_commit: str) -> str:
    """Lock the control fix before any phase-5b history exists.

    Importance is undeclared. The minimum detectable effect is computed from
    the planning sigmas and n = 12. It is not taken from a confirmatory sign.
    """

    seeds = list(locked_phase5b_seeds())
    mde_a = phase5_mde(PLANNING_SIGMA_A, len(seeds))
    mde_b = phase5_mde(PLANNING_SIGMA_B, len(seeds))
    payload = {
        "horizon": PHASE5B_HORIZON,
        "importance_bound": None,
        "importance_undeclared": True,
        "mde_a": mde_a,
        "mde_b": mde_b,
        "mde_is_importance": False,
        "measurement_floor": int(MEASUREMENT_FLOOR),
        "n": len(seeds),
        "primary_lag": PHASE5B_LAG,
        "seeds": seeds,
        "supported_forbidden": True,
        "workers": MAX_WORKERS,
    }
    block = json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        "# Phase-5b lock",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
        f"Code commit: `{code_commit}` on branch `rq/mechanism-v2`.",
        "Nothing has been pushed, merged, or rebased.",
        "This lock is committed before the phase-5b run.",
        "`runs/rq-mechanism-v2/phase5-coevolution/` is not rewritten.",
        "`PHASE5_LOCK.md` is not rewritten. Commit `60a9a0fec9b542bd216c23d1ac6c080e3c254918` is not amended.",
        "Seeds 9601 through 9612 are not reused. Seed 9600 is not rerun. Seed 9700 is not used.",
        "",
        "## Claim A on the coevolve arm",
        "",
        "Unchanged. Direction, already locked from the seed-9600 probe:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag) > 0`.",
        "The primary arm is `coevolve`. This estimand was not redefined to make the coevolve arm look larger.",
        "The score is `infectivity` on `replay_archived_contact` with evolution, reproduction, and mutation off.",
        "",
        "## Claim B on the coevolve arm",
        "",
        "Unchanged. Required together: genotype frequency as window counts;",
        "real contact pressure; lineage relative fitness; and a sign reversal of `I(A) - I(B)`",
        "between the contemporary and past parasite populations.",
        "A census wave is not claim B. Claim A is not claim B.",
        "`red_queen_proved` is true only if claim B's locked criterion is met, including a declared importance bound.",
        "Importance is undeclared, so that criterion is not met by declaration.",
        "",
        "## Controls",
        "",
        "The phase-5 control zero was an instrument failure. It is not reused as a bound.",
        "`constant_parasite`: host change against the same frozen parasite.",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at the horizon)`.",
        "The past parasite generation is not a second input. This is not the difference of two parasite copies.",
        "`adaptation_cut`: matched-pair change.",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Past and present parasite inputs are the two generations' own rosters, not copies of one roster.",
        "The contrast can be nonzero if the host windows change or the parasite windows change.",
        "Host bit-flip stays 0 on this arm, parasite passage stays `frozen`, and reproduction stays enabled.",
        "`shuffled_labels` is not used. Passage `absent` is not used.",
        "",
        "## Lag, horizon, and n",
        "",
        "Primary lag 3 and horizon 10 are taken from the seed-9600 probe already locked in `PHASE5_LOCK.md`.",
        "They are not re-chosen from the rejected confirmatory. Exploratory lag search is forbidden.",
        f"Primary lag: {PHASE5B_LAG}.",
        f"Horizon: {PHASE5B_HORIZON} generations.",
        f"n: {len(seeds)}.",
        f"Seeds: {seeds[0]} through {seeds[-1]} ({', '.join(str(seed) for seed in seeds)}).",
        "No seed is added after a sign.",
        "",
        "## Importance and the minimum detectable effect",
        "",
        "Importance for this estimand is undeclared. SUPPORTED is forbidden.",
        "The rejected coevolve mean and the rejected control zeros are not an importance bound.",
        "The Decaestecker gap of 0.10 is not this engine's importance bound.",
        f"Planning sigma for claim A is {PLANNING_SIGMA_A}. Planning sigma for claim B is {PLANNING_SIGMA_B}.",
        f"MDE claim A: {mde_a}. MDE claim B: {mde_b}.",
        "The minimum detectable effect is not the importance bound.",
        f"`MEASUREMENT_FLOOR` stays {int(MEASUREMENT_FLOOR)} and is not lowered.",
        "",
        "## Run rules",
        "",
        "CPU workers at most 7.",
        f"Output: `{OUTPUT_PHASE5B}`.",
        "Do not write into `runs/rq-mechanism-v2/phase5-coevolution/`.",
        "Raw archives are kept. A partial run is kept. A seed is not replaced.",
        "Replay of the same run is required.",
        "If replay does not match, stop. Do not edit the engine after the verdict.",
        "",
        "```json",
        block,
        "```",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
    ]
    return "\n".join(lines)


def _phase5b_controls(scored: Sequence[Mapping[str, object]]) -> dict[str, object]:
    def _detail(row: Mapping[str, object], key: str) -> Mapping[object, object]:
        return same_mapping(row[key])

    return {
        "adaptation_cut": {
            "definition": "I(hosts_horizon, parasites_horizon) - I(hosts_horizon_minus_lag, parasites_horizon_minus_lag)",
            "hosts_differ": [_detail(row, "adaptation_cut_detail")["hosts_differ"] for row in scored],
            "inputs_are_copies": [_detail(row, "adaptation_cut_detail")["inputs_are_copies"] for row in scored],
            "parasites_differ": [_detail(row, "adaptation_cut_detail")["parasites_differ"] for row in scored],
            "values": [row["claim_a_adaptation_cut"] for row in scored],
        },
        "constant_parasite": {
            "definition": "I(hosts_horizon, parasites_horizon) - I(hosts_horizon_minus_lag, parasites_horizon)",
            "frozen_rosters_match": [_detail(row, "constant_parasite_detail")["frozen_rosters_match"] for row in scored],
            "hosts_differ": [_detail(row, "constant_parasite_detail")["hosts_differ"] for row in scored],
            "inputs_are_copies": [_detail(row, "constant_parasite_detail")["inputs_are_copies"] for row in scored],
            "past_parasite_used_as_second_input": False,
            "values": [row["claim_a_constant_parasite"] for row in scored],
        },
        "coevolve_claim_a_definition": "I(hosts_horizon, parasites_horizon) - I(hosts_horizon, parasites_horizon_minus_lag)",
    }


def execute_phase5b(lock_path: Path, root: Path | None = None) -> dict[str, object]:
    """Run seeds 9701-9712. Do not open the rejected tree or add seeds."""

    target = OUTPUT_PHASE5B if root is None else root
    assert_phase5b_output_dir(target)
    payload = _lock_payload(lock_path.read_text(encoding="utf-8"))
    seeds = locked_phase5b_seeds()
    if [same_int(seed) for seed in same_iter(payload["seeds"])] != list(seeds):
        raise ConfigurationError("phase-5b lock seeds are not 9701 through 9712")
    if same_int(payload["primary_lag"]) != PHASE5B_LAG or same_int(payload["horizon"]) != PHASE5B_HORIZON:
        raise ConfigurationError("phase-5b lag and horizon are not the locked 3 and 10")
    if same_int(payload["n"]) != len(seeds):
        raise ConfigurationError("phase-5b n is not 12")
    if same_int(payload["workers"]) > MAX_WORKERS:
        raise ConfigurationError("phase-5b workers exceed 7")
    if payload.get("importance_bound") is not None or payload.get("supported_forbidden") is not True:
        raise ConfigurationError("phase-5b importance is undeclared; SUPPORTED stays forbidden")
    if payload.get("mde_is_importance") is True:
        raise ConfigurationError("phase-5b must not alias the MDE to importance")
    if (target / "by_seed").exists():
        raise ConfigurationError("phase-5b output already exists; a seed is not replaced")
    target.mkdir(parents=True, exist_ok=True)
    workers = resolve_workers(min(MAX_WORKERS, len(seeds)))
    lag = PHASE5B_LAG
    horizon = PHASE5B_HORIZON
    payloads = [
        {"arms": list(ARMS), "compare_one_shot": True, "generations": horizon, "root": str(target), "seed": seed}
        for seed in seeds
    ]
    outcomes: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_worker, item) for item in payloads]
        for future in as_completed(futures):
            outcomes.append(future.result())
    outcomes.sort(key=lambda item: same_int(item["seed"]))
    failed = [item for item in outcomes if item["failed"]]
    replays: list[dict[str, object]] = []
    if not failed:
        for seed in seeds:
            replays.append(replay_phase5_archive(target / "by_seed" / f"seed{seed}" / "archive.jsonl"))
    replay_matched = bool(replays) and all(bool(item["matched"]) for item in replays)
    mde_a = same_float(payload["mde_a"]) if _finite(payload.get("mde_a")) else None
    mde_b = same_float(payload["mde_b"]) if _finite(payload.get("mde_b")) else None
    if failed or not replay_matched:
        if not failed:
            (target / "REASON.txt").write_text("replay-mismatch\n", encoding="utf-8")
        present = []
        for seed in seeds:
            if (target / "by_seed" / f"seed{seed}" / "COMPLETE").is_file():
                present.append(_score_seed(target / "by_seed" / f"seed{seed}", lag=lag, horizon=horizon))
        report = assess_phase5(present, seeds, importance_bound=None, mde_a=mde_a, mde_b=mde_b)
        report["red_queen_proved"] = False
        cast(dict[str, object], report["claim_b"])["criterion_met"] = False
        summary: dict[str, object] = {
            "controls": _phase5b_controls(present) if present else None,
            "failed": failed,
            "horizon": horizon,
            "n_locked": len(seeds),
            "primary_lag": lag,
            "replay": replays,
            "replay_matched": replay_matched,
            "report": report,
            "seeds": list(seeds),
            "stopped": failed[0]["failed"] if failed else "replay-mismatch",
            "workers": workers,
        }
        (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary
    scored = [_score_seed(target / "by_seed" / f"seed{seed}", lag=lag, horizon=horizon) for seed in seeds]
    report = assess_phase5(scored, seeds, importance_bound=None, mde_a=mde_a, mde_b=mde_b)
    summary = {
        "by_seed": scored,
        "controls": _phase5b_controls(scored),
        "horizon": horizon,
        "n_locked": len(seeds),
        "one_shot_vs_resume": "matched on scientific_body inside each history before COMPLETE",
        "primary_lag": lag,
        "replay": replays,
        "replay_matched": True,
        "report": report,
        "seeds": list(seeds),
        "stopped": None,
        "workers": workers,
    }
    summary["summary_sha256"] = hashlib.sha256(
        json.dumps({key: value for key, value in summary.items() if key != "summary_sha256"}, sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()
    (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
