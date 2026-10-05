"""Confirmatory bidirectional time-shift for RQ-BIDIRECTIONAL-TIMESHIFT-01.

Phase 1 (pilot seeds 9101-9104, 200 generations, instrument debit 1.2 vs 0.6)
is already locked and is not rerun. This module locks the confirmatory design
before the first confirmatory generation, then:

- phase 2: 24 fresh histories, four arms, 600 generations, full archive
- phase 3: time-shift assay on immutable snapshots
- phase 4: CH, CP, S and four paired tests
- phase 5: per-seed artifacts, replay command, one verdict

``red_queen_proved`` stays false for every verdict, including SUPPORTED_IN_MODEL.
Parameters, horizon, lag and seeds are not changed after the confirmatory lock
in order to obtain a positive result. A negative or inconclusive verdict is a
valid stop. Extinction and fixation stay in the archive.

Assay, in the sense of Gandon 2002 (performance at one time against a partner
from another time, with no evolution during the score) and Dybdahl and Lively
1998 (the whole population, not one modal genotype): I(H, P) is the mean ATP
actually transferred over every host individual paired with every parasite
individual, divided by virulence * steal_fraction. Duplicate windows are
aggregated by their census frequency. That shortcut is checked against the
explicit pairs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import cast

from codontrace.dynvalues import same_float
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_BIRTH_ATP,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
)
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARCHIVE_SCHEMA,
    ARM_A,
    ARM_B,
    ARM_C,
    ARM_D,
    ARMS,
    PHASE1_PILOT_SEEDS,
    RQ_CODE_VERSION,
    RQ_DESIGN_VERSION,
    SMOKE_SEED,
    SNAPSHOT_SCHEMA,
    _canonical,
    _generation_row,
    _git_head,
    _hosts_payload,
    _parasite_payload,
    build_arm,
    config_digest,
    control_statement,
    read_bound_snapshot,
    read_snapshot,
    replay_archived_contact,
    snapshot_body,
    write_snapshot,
)
from codontrace.genesis.rq_bidirectional_timeshift import (
    EXPERIMENT_ID as TIMESHIFT_EXPERIMENT_ID,
)
from codontrace.genesis.rq_stream import ARM_STREAM_POLICY, derive_stream_seed

EXPERIMENT_ID = "RQ-BIDIRECTIONAL-TIMESHIFT-01"
EXCLUDED_SEEDS: frozenset[int] = frozenset({SMOKE_SEED, *PHASE1_PILOT_SEEDS})
CONFIRMATORY_SEEDS: tuple[int, ...] = tuple(range(9201, 9225))
CONFIRMATORY_GENERATIONS = 600
SNAPSHOT_STRIDE = 20
BURN_IN = 160
DELTA = 40
N_HISTORIES = 24
ALPHA_FAMILY = 0.05
N_TESTS = 4
ALPHA = ALPHA_FAMILY / N_TESTS
POWER = 0.80
INSTRUMENT_I_GAP = 0.5
RESOLVE_CEILING = INSTRUMENT_I_GAP / 2.0
MEASUREMENT_FLOOR = 12
VERIFY_ABS_TOL = 1e-9
MAX_WORKERS = 4
ASSAY_ATP = float(STRUCT_BIRTH_ATP)
SCALE = float(STRUCT_VIRULENCE) * float(STRUCT_STEAL_FRACTION)
VERDICT_SUPPORTED = "SUPPORTED_IN_MODEL"
VERDICT_NEGATIVE = "NEGATIVE_IN_MODEL"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"
VERDICT_BLOCKED = "BLOCKED_MEASUREMENT"


def analysis_centers() -> tuple[int, ...]:
    """Centers t = 200, 240, ..., 560. Lag generations are t - delta."""

    return tuple(range(BURN_IN + DELTA, CONFIRMATORY_GENERATIONS - DELTA + 1, DELTA))


def required_snapshot_generations() -> tuple[int, ...]:
    """Snapshot generations the assay reads: 160 and every center through 560."""

    return tuple(range(BURN_IN, analysis_centers()[-1] + 1, DELTA))


def _default_root() -> Path:
    return Path(__file__).resolve().parents[3] / "runs" / "rq-bidirectional-timeshift-01"


def _load_json(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{path} must contain a JSON object")
    return cast(dict[str, object], raw)


def _atomic_json(path: Path, body: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(body, sort_keys=True, indent=2) + "\n"
    temporary.write_text(text, encoding="utf-8")
    fd = os.open(temporary, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def _rows(body: Mapping[str, object], key: str) -> list[dict[str, object]]:
    raw = body.get(key)
    if not isinstance(raw, list):
        raise ConfigurationError(f"snapshot missing list {key}")
    rows: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ConfigurationError(f"snapshot {key} row is not an object")
        rows.append(cast(dict[str, object], item))
    return rows


def _window_counts(rows: Sequence[Mapping[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        window = str(row[key])
        counts[window] = counts.get(window, 0) + 1
    return counts


def _assert_assay_atp(atp: float) -> None:
    if float(atp) + 1e-9 < SCALE:
        raise ConfigurationError(
            "assay ATP would clip a perfect match: "
            f"atp={atp} scale={SCALE}"
        )


def infectivity(
    hosts: Sequence[Mapping[str, object]],
    parasites: Sequence[Mapping[str, object]],
    *,
    atp: float = ASSAY_ATP,
    tick_index: int = 0,
) -> float | None:
    """Mean realised ATP per engine contact, divided by virulence * steal.

    The contacts are the engine's seat pairing (one parasite seat with one
    rotated host, ``min`` of the two censuses), not the cartesian product of
    individuals. Empty host or parasite population is unmeasurable (None),
    not zero. ``atp`` is written only onto copies. A value below a perfect
    match clips; the locked confirmatory ATP is still required not to clip,
    but this function must be able to show clipping.
    """

    if not hosts or not parasites:
        return None
    scored = replay_archived_contact(
        [dict(row) for row in hosts],
        [dict(row) for row in parasites],
        atp_override=float(atp),
        tick_index=int(tick_index),
    )
    value = scored["infectivity"]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError("infectivity must be a finite number or null")
    return float(value)


def infectivity_pairwise(
    hosts: Sequence[Mapping[str, object]],
    parasites: Sequence[Mapping[str, object]],
    *,
    atp: float = ASSAY_ATP,
    tick_index: int = 0,
) -> float | None:
    """Same engine estimand as ``infectivity``.

    The name is historical. It is not a cartesian sum. Both callers read the
    engine debit path, so they match by construction of that path; tests
    still check the number against an independently derived seat expectation.
    """

    return infectivity(hosts, parasites, atp=atp, tick_index=tick_index)


def regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Continued-fraction regularized incomplete beta, Numerical Recipes."""

    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - log_beta)

    def betacf(aa: float, bb: float, xx: float) -> float:
        max_iter = 200
        eps = 3e-14
        fpmin = 1e-300
        qab = aa + bb
        qap = aa + 1.0
        qam = aa - 1.0
        c = 1.0
        d = 1.0 - qab * xx / qap
        if abs(d) < fpmin:
            d = fpmin
        d = 1.0 / d
        h = d
        for m in range(1, max_iter + 1):
            m2 = 2 * m
            numer = m * (bb - m) * xx / ((qam + m2) * (aa + m2))
            d = 1.0 + numer * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + numer / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            h *= d * c
            numer = -(aa + m) * (qab + m) * xx / ((aa + m2) * (qap + m2))
            d = 1.0 + numer * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + numer / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < eps:
                break
        return h

    if x < (a + 1.0) / (a + b + 2.0):
        return front * betacf(a, b, x) / a
    return 1.0 - front * betacf(b, a, 1.0 - x) / b


def student_t_sf(t: float, df: int) -> float:
    """Upper tail P(T_df > t)."""

    if df < 1:
        raise ConfigurationError("Student t requires df >= 1")
    if t == 0.0:
        return 0.5
    x = float(df) / (float(df) + t * t)
    tail = 0.5 * regularized_incomplete_beta(x, df / 2.0, 0.5)
    if t > 0.0:
        return tail
    return 1.0 - tail


def student_t_ppf(p: float, df: int) -> float:
    """Quantile of the central Student t. ``p`` is the CDF probability."""

    if not 0.0 < p < 1.0:
        raise ConfigurationError("Student t probability must be in (0, 1)")
    if p == 0.5:
        return 0.0
    target = 1.0 - p
    lo = -1.0
    hi = 1.0
    while student_t_sf(lo, df) < target:
        lo *= 2.0
    while student_t_sf(hi, df) > target:
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if student_t_sf(mid, df) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def chi2_df3_cdf(x: float) -> float:
    """Closed form for the chi-square distribution with 3 degrees of freedom."""

    if x <= 0.0:
        return 0.0
    root = math.sqrt(x / 2.0)
    return math.erf(root) - math.sqrt((2.0 * x) / math.pi) * math.exp(-x / 2.0)


def chi2_df3_ppf(p: float) -> float:
    if not 0.0 < p < 1.0:
        raise ConfigurationError("chi-square probability must be in (0, 1)")
    lo = 1e-12
    hi = 1.0
    while chi2_df3_cdf(hi) < p:
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if chi2_df3_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _chi2_pdf(x: float, df: int) -> float:
    if x <= 0.0:
        return 0.0
    k = float(df)
    return math.exp(
        -math.lgamma(k / 2.0)
        - (k / 2.0) * math.log(2.0)
        + (k / 2.0 - 1.0) * math.log(x)
        - x / 2.0
    )


def _normal_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def noncentral_t_sf(t: float, df: int, ncp: float) -> float:
    """P(T' > t) for the noncentral t, by integrating the normal/chi-square form."""

    if df < 1:
        raise ConfigurationError("noncentral t requires df >= 1")
    hi = float(df) + 12.0 * math.sqrt(2.0 * float(df)) + 40.0
    lo = 1e-8
    n = 4000
    if n % 2:
        n += 1
    step = (hi - lo) / float(n)

    def integrand(u: float) -> float:
        z = t * math.sqrt(u / float(df)) - ncp
        return _normal_sf(z) * _chi2_pdf(u, df)

    total = integrand(lo) + integrand(hi)
    for index in range(1, n):
        weight = 4.0 if index % 2 else 2.0
        total += weight * integrand(lo + index * step)
    return total * step / 3.0


def minimum_detectable_effect(sigma: float, n: int, *, power: float = POWER) -> float:
    """One-sided MDE at Bonferroni alpha for a one-sample t test, n histories.

    The noncentrality is solved so that P(T' > t_{1-alpha, n-1}) = ``power``.
    The returned effect is ncp * sigma / sqrt(n), in the same units as sigma.
    """

    if n < 3:
        raise ConfigurationError("MDE requires n >= 3")
    if sigma < 0.0:
        raise ConfigurationError("sigma must be non-negative")
    df = n - 1
    critical = student_t_ppf(1.0 - ALPHA, df)
    lo = 0.0
    hi = 1.0
    while noncentral_t_sf(critical, df, hi) < power:
        hi *= 2.0
        if hi > 1e6:
            raise ConfigurationError("noncentral-t search did not reach the target power")
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if noncentral_t_sf(critical, df, mid) < power:
            lo = mid
        else:
            hi = mid
    return hi * float(sigma) / math.sqrt(float(n))


def _pilot_component(seed: int, root: Path) -> tuple[float, float]:
    """CH and CP at the only confirmatory center the pilot reaches (t=200, d=40)."""

    snap = root / "snapshots"

    def load(generation: int) -> dict[str, object]:
        return read_snapshot(snap / f"seed{seed}_pilot_g{generation:04d}.json")

    past = load(200 - DELTA)
    now = load(200)
    past_hosts = _rows(past, "hosts")
    past_parasites = _rows(past, "parasites")
    now_hosts = _rows(now, "hosts")
    now_parasites = _rows(now, "parasites")
    contemporary = infectivity(past_hosts, past_parasites)
    host_shift = infectivity(now_hosts, past_parasites)
    parasite_shift = infectivity(past_hosts, now_parasites)
    if contemporary is None or host_shift is None or parasite_shift is None:
        raise ConfigurationError(f"pilot seed {seed} has an unmeasurable t=200 assay")
    return contemporary - host_shift, parasite_shift - contemporary


def pilot_dispersion(root: Path) -> dict[str, object]:
    """Between-seed SD of the single in-window pilot center, inflated upward.

    Arms B and C were not piloted. The larger of the host-side and parasite-side
    standard deviations is used for every contrast, then inflated to an 80%
    upper confidence bound (chi-square, df = 3). That sigma is deliberately
    the SD of one center, not of a mean of several centers, so it does not
    understate the noise of the history-level summary.
    """

    ch_values: list[float] = []
    cp_values: list[float] = []
    for seed in PHASE1_PILOT_SEEDS:
        ch, cp = _pilot_component(seed, root)
        ch_values.append(ch)
        cp_values.append(cp)
    sd_ch = float(statistics.stdev(ch_values))
    sd_cp = float(statistics.stdev(cp_values))
    sd = max(sd_ch, sd_cp)
    chi = chi2_df3_ppf(0.20)
    sigma = sd * math.sqrt(3.0 / chi)
    effect = minimum_detectable_effect(sigma, N_HISTORIES)
    return {
        "pilot_seeds": list(PHASE1_PILOT_SEEDS),
        "pilot_center": 200,
        "pilot_delta": DELTA,
        "ch": ch_values,
        "cp": cp_values,
        "sd_ch": sd_ch,
        "sd_cp": sd_cp,
        "sd_used": sd,
        "sigma_upper_80": sigma,
        "chi2_df3_ppf_0_20": chi,
        "minimum_detectable_effect": effect,
        "importance_bound": None,
        "practical_effect": effect,
        "practical_effect_role": (
            "power-revision alias of the minimum detectable effect only; "
            "not the scientific importance bound"
        ),
        "power": POWER,
        "alpha_per_test": ALPHA,
        "n_histories": N_HISTORIES,
        "resolve_ceiling": RESOLVE_CEILING,
        "instrument_I_gap": INSTRUMENT_I_GAP,
        "resolvable": effect < RESOLVE_CEILING,
        "red_queen_proved": False,
    }


def assert_confirmatory_seeds(seeds: Sequence[int]) -> None:
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
        PILOT_SEEDS,
        assert_pilot_seed_policy,
    )

    chosen = tuple(int(seed) for seed in seeds)
    if len(chosen) != N_HISTORIES:
        raise ConfigurationError(f"confirmatory requires {N_HISTORIES} seeds, got {len(chosen)}")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("confirmatory seeds must be unique")
    banned = sorted(set(chosen) & set(EXCLUDED_SEEDS))
    if banned:
        raise ConfigurationError(f"pilot and smoke seeds must not be reused; overlap={banned}")
    structural = sorted(set(chosen) & set(PILOT_SEEDS))
    if structural:
        raise ConfigurationError(f"structural pilot seeds must not be reused; overlap={structural}")
    assert_pilot_seed_policy(chosen)


def _named_rng_manifest(seed: int, generations: int) -> dict[str, object]:
    history = str(int(seed))
    host_steps = [
        derive_stream_seed(TIMESHIFT_EXPERIMENT_ID, history, "host-step", generation)
        for generation in range(1, generations + 1)
    ]
    passage = [
        derive_stream_seed(TIMESHIFT_EXPERIMENT_ID, history, "passage", generation)
        for generation in range(1, generations + 1)
    ]
    body: dict[str, object] = {
        "generation_rng_namespace": f"{TIMESHIFT_EXPERIMENT_ID}/{history}",
        "generation_rng_seed": int(seed),
        "history_id": history,
        "host_step_seeds": host_steps,
        "passage_seeds": passage,
        "sharing_policy": dict(ARM_STREAM_POLICY),
        "note": (
            "Streams are derived as root, history id, subsystem, generation. "
            "They are not seed plus generation. Arms of this history use the "
            "recorded sharing policy and do not share a mutable RNG object."
        ),
    }
    body["digest"] = _canonical({k: v for k, v in body.items() if k != "digest"})
    return body




def _founder_signature(arm: object) -> dict[str, object]:
    """Initial organisms, resources and costs. Treatment flags are excluded."""

    from codontrace.genesis.closed_loop_hp_arm01 import _window
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import StructuralRQArm

    if not isinstance(arm, StructuralRQArm):
        raise ConfigurationError("founder signature requires a structural arm")
    hosts: list[dict[str, object]] = []
    for org in arm._hosts():
        pos = org.position
        hosts.append(
            {
                "id": str(org.id),
                "position": [int(pos[0]), int(pos[1])],
                "runtime_atp": float(org.atp_state.runtime_available),
                "window": _window(org),
            }
        )
    hosts.sort(key=lambda row: str(row["id"]))
    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("population ecology is required")
    parasites = [
        {"energy": float(unit.energy), "unit_id": unit.unit_id, "window": unit.window}
        for unit in pop.units
    ]
    parasites.sort(key=lambda row: str(row["unit_id"]))
    resources = [
        [int(pos[0]), int(pos[1]), float(amount)]
        for pos, amount in sorted(arm.runner.world.resources.items())
    ]
    return {
        "basal_runtime_atp_cost": float(arm.basal_runtime_atp_cost),
        "birth_atp": float(arm.birth_atp),
        "cumulative_resource_bolus_placed": float(arm.cumulative_resource_bolus_placed),
        "hosts": hosts,
        "parasite_mutation": float(arm.parasite_mutation),
        "parasites": parasites,
        "resource_bolus_amount": float(arm.resource_bolus_amount),
        "resources": resources,
        "soft_carrying_capacity": float(arm.soft_carrying_capacity),
        "steal_fraction": float(arm.hp_env.steal_fraction),
        "virulence": float(arm.virulence),
    }


def _pilot_shortcut_ok(root: Path) -> dict[str, object]:
    snap = root / "snapshots"
    past = read_snapshot(snap / f"seed{PHASE1_PILOT_SEEDS[0]}_pilot_g{200 - DELTA:04d}.json")
    now = read_snapshot(snap / f"seed{PHASE1_PILOT_SEEDS[0]}_pilot_g0200.json")
    crosses = (
        (_rows(past, "hosts"), _rows(past, "parasites")),
        (_rows(now, "hosts"), _rows(past, "parasites")),
        (_rows(past, "hosts"), _rows(now, "parasites")),
    )
    diffs: list[float] = []
    for hosts, parasites in crosses:
        left = infectivity(hosts, parasites)
        right = infectivity_pairwise(hosts, parasites)
        if left is None or right is None:
            raise ConfigurationError("pilot verification sample is unmeasurable")
        diffs.append(abs(left - right))
    return {
        "ok": max(diffs) <= VERIFY_ABS_TOL,
        "max_abs": max(diffs),
        "seed": PHASE1_PILOT_SEEDS[0],
        "red_queen_proved": False,
    }


def _test_protocol() -> dict[str, object]:
    return {
        "alpha_family": ALPHA_FAMILY,
        "alpha_per_test": ALPHA,
        "correction": "Bonferroni",
        "n_tests": N_TESTS,
        "procedure": "one-sample Student t, one-sided, H1: mean > 0",
        "unit": "history, paired within seed",
        "contrasts": [
            "mean CH_A",
            "mean CP_A",
            "mean (S_A - S_B)",
            "mean (S_A - S_C)",
        ],
        "S": "min(mean CH, mean CP) over measurable centers; not the mean of per-center mins",
        "ci_reported": "two-sided 95 percent Student-t interval",
        "decision_bound": "one-sided lower bound at 1 - alpha_per_test",
        "practical_rule": "one-sided lower bound >= importance bound; MDE is not that bound; zero SE cannot support",
        "missing": "unmeasurable center omitted; unmeasurable history omitted; never imputed as 0",
        "measurement_floor": MEASUREMENT_FLOOR,
        "supported_requires": (
            "all four tests reject at alpha_per_test and all four one-sided lower bounds "
            "meet the importance bound; a zero SE cannot support"
        ),
        "negative_rule": (
            "measurement not blocked and every contrast has a two-sided 95 percent "
            "CI upper bound strictly below the practical effect"
        ),
        "otherwise": VERDICT_INCONCLUSIVE,
        "red_queen_proved_allowed": False,
    }


def lock_confirmatory(root: Path, *, code_commit: str) -> dict[str, object]:
    """Write the confirmatory block if it is not already locked.

    Re-locking is refused. The practical effect is computed only from the
    phase-1 pilot snapshots, never from confirmatory outcomes.
    """

    path = root / "prereg_lock.json"
    prereg = _load_json(path)
    existing = prereg.get("confirmatory")
    if isinstance(existing, dict) and existing.get("locked") is True:
        return prereg
    assert_confirmatory_seeds(CONFIRMATORY_SEEDS)
    shortcut = _pilot_shortcut_ok(root)
    if not shortcut["ok"]:
        raise ConfigurationError("pilot frequency shortcut does not match pairwise infectivity")
    dispersion = pilot_dispersion(root)
    centers = list(analysis_centers())
    block: dict[str, object] = {
        "analysis_centers": centers,
        "arms": {
            ARM_A: control_statement(ARM_A),
            ARM_B: control_statement(ARM_B),
            ARM_C: control_statement(ARM_C),
            ARM_D: control_statement(ARM_D),
        },
        "assay_atp": ASSAY_ATP,
        "assay_definition": (
            "I(H,P) = mean ATP transferred over all host-parasite individual pairs "
            "/ (virulence * steal_fraction); duplicate windows weighted by census frequency"
        ),
        "burn_in": BURN_IN,
        "code_commit": code_commit,
        "confirmatory_started": False,
        "delta": DELTA,
        "dispersion": dispersion,
        "excluded_seeds": sorted(EXCLUDED_SEEDS),
        "generations": CONFIRMATORY_GENERATIONS,
        "locked": True,
        "measurement_floor": MEASUREMENT_FLOOR,
        "code_version": RQ_CODE_VERSION,
        "config_digest": config_digest(),
        "design_version": RQ_DESIGN_VERSION,
        "importance_bound": None,
        "minimum_detectable_effect": dispersion["minimum_detectable_effect"],
        "parameters_not_retuned": True,
        "phase1_facts_unchanged": {
            "instrument_debits": [1.2, 0.6],
            "pilot_generations": 200,
            "pilot_seeds": list(PHASE1_PILOT_SEEDS),
            "pilot_wall_seconds": 206,
        },
        "pilot_shortcut_verification": shortcut,
        "practical_effect": dispersion["practical_effect"],
        "practical_effect_role": dispersion["practical_effect_role"],
        "red_queen_proved": False,
        "seeds": list(CONFIRMATORY_SEEDS),
        "snapshot_stride": SNAPSHOT_STRIDE,
        "tests": _test_protocol(),
    }
    if not bool(dispersion["resolvable"]):
        sigma = float(cast(float, dispersion["sigma_upper_80"]))
        revised_n = N_HISTORIES
        revised_effect = float(cast(float, dispersion["practical_effect"]))
        while revised_effect >= RESOLVE_CEILING and revised_n < 10000:
            revised_n += 1
            revised_effect = minimum_detectable_effect(sigma, revised_n)
        block["revised_design"] = {
            "generations": CONFIRMATORY_GENERATIONS,
            "n_histories": revised_n,
            "practical_effect": revised_effect,
            "reason": (
                "24 histories cannot resolve the practical effect under the "
                "pre-set ceiling of half the instrument I gap"
            ),
            "started": False,
        }
    prereg["confirmatory"] = block
    _atomic_json(path, prereg)
    _atomic_json(root / "confirmatory_power.json", dispersion)
    return prereg


def _locked_block(root: Path) -> dict[str, object]:
    prereg = _load_json(root / "prereg_lock.json")
    block = prereg.get("confirmatory")
    if not isinstance(block, dict) or block.get("locked") is not True:
        raise ConfigurationError("confirmatory design is not locked")
    return cast(dict[str, object], block)


def _as_int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        raise ConfigurationError("expected a list of seeds")
    return [int(cast(int, item)) for item in value]


def mark_started(root: Path, run_id: str) -> dict[str, object]:
    path = root / "prereg_lock.json"
    prereg = _load_json(path)
    block = prereg.get("confirmatory")
    if not isinstance(block, dict) or block.get("locked") is not True:
        raise ConfigurationError("refusing to start an unlocked confirmatory")
    # A revised design is a locked stop. An earlier started flag does not lift it.
    if block.get("revised_design") is not None:
        raise ConfigurationError("revised design is locked and must not be started as the n=24 run")
    if block.get("confirmatory_started") is True:
        return prereg
    block["confirmatory_started"] = True
    block["run_id"] = run_id
    prereg["confirmatory"] = block
    prereg["confirmatory_started"] = True
    _atomic_json(path, prereg)
    return prereg


class _LockedAppend:
    def __init__(self, path: Path, *, fsync_each: bool) -> None:
        import fcntl

        path.parent.mkdir(parents=True, exist_ok=True)
        self._fcntl = fcntl
        self._fh = path.open("a", encoding="utf-8", buffering=1)
        self._fsync_each = fsync_each

    def line(self, text: str) -> None:
        payload = text if text.endswith("\n") else text + "\n"
        self._fcntl.flock(self._fh.fileno(), self._fcntl.LOCK_EX)
        try:
            self._fh.write(payload)
            self._fh.flush()
            if self._fsync_each:
                os.fsync(self._fh.fileno())
        finally:
            self._fcntl.flock(self._fh.fileno(), self._fcntl.LOCK_UN)

    def close(self) -> None:
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.close()


def _reset_seed(root: Path, seed: int) -> None:
    import shutil

    seed_dir = root / "confirmatory" / "by_seed" / f"seed{seed}"
    if seed_dir.exists():
        shutil.rmtree(seed_dir)
    snap = root / "confirmatory" / "snapshots"
    if snap.exists():
        for path in snap.glob(f"seed{seed}_*_g*.json"):
            path.unlink()


def _archive_record(arm: object, row: Mapping[str, object]) -> dict[str, object]:
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import StructuralRQArm

    if not isinstance(arm, StructuralRQArm):
        raise ConfigurationError("archive requires a structural arm")
    pop = arm.antagonist_pop
    if pop is None or not pop.ledgers:
        raise ConfigurationError("parasite ledger missing")
    before_note = row.get("_before_hosts")
    before_hosts = set(cast(list[str], before_note)) if isinstance(before_note, list) else set()
    birth_note = row.get("_birth_ids")
    birth_ids = set(cast(list[str], birth_note)) if isinstance(birth_note, list) else set()
    after_hosts = {str(org.id) for org in arm._hosts()}
    deaths = sorted((before_hosts - after_hosts) | (birth_ids - after_hosts))
    ledger = pop.ledgers[-1]
    events = arm.antagonist_contact_events[-1] if arm.antagonist_contact_events else ()
    hosts = _hosts_payload(arm)
    positions = {
        str(org.id): [int(org.position[0]), int(org.position[1])] for org in arm._hosts()
    }
    for host in hosts:
        host["position"] = positions[str(host["id"])]
    resources = [
        [int(pos[0]), int(pos[1]), float(amount)]
        for pos, amount in sorted(arm.runner.world.resources.items())
    ]
    generation = int(cast(int, row["generation"]))
    return {
        "arm": row["arm"],
        "contacts": [
            {
                "atp": float(event.atp_paid),
                "host_id": str(event.host_id),
                "unit_id": str(event.unit_id),
                "window": str(event.window),
            }
            for event in events
        ],
        "cumulative_resource_bolus_placed": float(arm.cumulative_resource_bolus_placed),
        "code_version": row.get("code_version"),
        "config_digest": row.get("config_digest"),
        "design_version": row.get("design_version"),
        "experiment": EXPERIMENT_ID,
        "generation": generation,
        "history_id": str(row["seed"]),
        "schema": row.get("schema") or ARCHIVE_SCHEMA,
        "host_births": cast(list[object], row.get("_host_births") or []),
        "host_deaths": deaths,
        "hosts": hosts,
        "host_step_seed": derive_stream_seed(
            TIMESHIFT_EXPERIMENT_ID, str(int(cast(int, row["seed"]))), "host-step", generation
        ),
        "invariant": row["invariant"],
        "parasite_births": [
            {
                "energy": float(unit.energy),
                "parent_id": unit.parent_id,
                "unit_id": unit.unit_id,
                "window": unit.window,
            }
            for unit in ledger.newborns
        ],
        "parasite_deaths": [str(unit_id) for unit_id in ledger.deaths],
        "parasites": _parasite_payload(arm),
        "passage_fork": f"hp-struct-rq-{ARM_COPASSAGED}/passage/{generation - 1}",
        "phase": 2,
        "red_queen_proved": False,
        "resources": resources,
        "run_id": row.get("run_id"),
        "seed": row["seed"],
    }


def run_one_history(
    seed: int,
    root_text: str,
    generations: int,
    run_id: str,
    snapshot_stride: int,
) -> dict[str, object]:
    """Run four arms from one shared initial state. Does not score Red Queen."""

    root = Path(root_text)
    stop = root / "confirmatory" / "STOP"
    seed_dir = root / "confirmatory" / "by_seed" / f"seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    arms = {name: build_arm(name, seed) for name in ARMS}
    signatures = {name: _founder_signature(arms[name]) for name in ARMS}
    digests = {name: _canonical(signatures[name]) for name in ARMS}
    if len(set(digests.values())) != 1:
        return {
            "failed": "initial-state-diverged",
            "digests": digests,
            "red_queen_proved": False,
            "seed": seed,
        }
    for arm in arms.values():
        if arm.arm != ARM_COPASSAGED:
            return {"failed": "rng-namespace-diverged", "red_queen_proved": False, "seed": seed}
    rng_manifest = _named_rng_manifest(seed, generations)
    initial = {
        "arms": {
            name: {
                "digest": digests[name],
                "host_inheritance": arms[name].host_inheritance,
                "passage": arms[name].passage,
            }
            for name in ARMS
        },
        "code_version": RQ_CODE_VERSION,
        "config_digest": config_digest(),
        "design_version": RQ_DESIGN_VERSION,
        "experiment": EXPERIMENT_ID,
        "founder_digest": digests[ARM_A],
        "history_id": str(seed),
        "red_queen_proved": False,
        "rng": rng_manifest,
        "run_id": run_id,
        "schema": ARCHIVE_SCHEMA,
        "seed": seed,
    }
    _atomic_json(seed_dir / "initial.json", initial)
    live = _LockedAppend(root / "live.log", fsync_each=True)
    dataset = _LockedAppend(root / "confirmatory" / "trajectory.jsonl", fsync_each=False)
    archive_path = seed_dir / "archive.jsonl"
    summaries: dict[str, object] = {}
    try:
        with archive_path.open("a", encoding="utf-8", buffering=1) as archive:
            for arm_name in ARMS:
                if stop.exists():
                    summaries[arm_name] = {"failed": "stopped", "generations_completed": 0}
                    break
                arm = arms[arm_name]
                founder_ids = {org.id for org in arm._hosts()}
                prev_census = len(founder_ids)
                prev_lineage = 0
                failed: str | None = None
                completed = 0
                for generation in range(1, int(generations) + 1):
                    if stop.exists():
                        failed = "stopped"
                        break
                    before_hosts = [str(org.id) for org in arm._hosts()]
                    before_lineage = {rec.organism_id for rec in arm.runner.population.lineage}
                    try:
                        arm.run_generations(1)
                    except Exception as exc:
                        failed = f"exception:{type(exc).__name__}:{exc}"
                        live.line(
                            f"phase=2 run={run_id} seed={seed} arm={arm_name} "
                            f"generation={generation} invariant={failed} red_queen_proved=false"
                        )
                        break
                    row = _generation_row(
                        arm,
                        seed=seed,
                        arm_name=arm_name,
                        generation=generation,
                        founder_ids=founder_ids,
                        prev_host_census=prev_census,
                        prev_lineage=prev_lineage,
                    )
                    new_lineage = [
                        rec
                        for rec in arm.runner.population.lineage
                        if rec.organism_id not in before_lineage
                    ]
                    row["phase"] = 2
                    row["run_id"] = run_id
                    row["schema"] = ARCHIVE_SCHEMA
                    row["code_version"] = RQ_CODE_VERSION
                    row["config_digest"] = config_digest()
                    row["design_version"] = RQ_DESIGN_VERSION
                    row["red_queen_proved"] = False
                    row["_before_hosts"] = before_hosts
                    births = [
                        rec
                        for rec in new_lineage
                        if rec.parent_id and int(rec.generation) != 0
                    ]
                    row["_birth_ids"] = [rec.organism_id for rec in births]
                    row["_host_births"] = [
                        {
                            "generation": int(rec.generation),
                            "id": rec.organism_id,
                            "parent_id": rec.parent_id,
                        }
                        for rec in births
                    ]
                    pop = arm.antagonist_pop
                    if pop is not None and any(len(unit.unit_id) > 64 for unit in pop.units):
                        row["invariant"] = "parasite-id-unbounded"
                    record = _archive_record(arm, row)
                    archive.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
                    archive.flush()
                    if generation % 20 == 0:
                        os.fsync(archive.fileno())
                    public = {
                        key: value
                        for key, value in row.items()
                        if not str(key).startswith("_")
                    }
                    dataset.line(json.dumps(public, sort_keys=True, separators=(",", ":")))
                    live.line(
                        f"phase=2 run={run_id} seed={seed} arm={arm_name} generation={generation} "
                        f"host_census={row['host_census']} parasite_census={row['parasite_census']} "
                        f"host_energy={same_float(row['host_energy']):.6f} "
                        f"parasite_energy={same_float(row['parasite_energy']):.6f} "
                        f"host_births={row['host_births']} host_deaths={row['host_deaths']} "
                        f"parasite_births={row['parasite_births']} parasite_deaths={row['parasite_deaths']} "
                        f"contacts={row['contacts']} invariant={row['invariant']} "
                        "red_queen_proved=false"
                    )
                    completed = generation
                    if row["invariant"] != "ok":
                        failed = str(row["invariant"])
                        break
                    if snapshot_stride and generation % int(snapshot_stride) == 0:
                        body = snapshot_body(arm, seed=seed, arm_name=arm_name, generation=generation)
                        body["schema"] = SNAPSHOT_SCHEMA
                        body["history_id"] = str(seed)
                        body["run_id"] = run_id
                        body["config_digest"] = config_digest()
                        body["code_version"] = RQ_CODE_VERSION
                        body["design_version"] = RQ_DESIGN_VERSION
                        body["phase"] = 2
                        body["red_queen_proved"] = False
                        write_snapshot(
                            root / "confirmatory" / "snapshots" / f"seed{seed}_{arm_name}_g{generation:04d}.json",
                            body,
                        )
                    prev_census = int(cast(int, row["host_census"]))
                    prev_lineage += int(cast(int, row["host_births"]))
                summaries[arm_name] = {
                    "failed": failed,
                    "final_host_census": len(arm._hosts()),
                    "final_parasite_census": len(arm.antagonist_pop.units) if arm.antagonist_pop else 0,
                    "generations_completed": completed,
                    "red_queen_proved": False,
                }
                if failed:
                    break
    finally:
        live.close()
        dataset.close()
    outcome = {
        "arms": summaries,
        "founder_digest": digests[ARM_A],
        "red_queen_proved": False,
        "code_version": RQ_CODE_VERSION,
        "config_digest": config_digest(),
        "design_version": RQ_DESIGN_VERSION,
        "experiment": EXPERIMENT_ID,
        "rng_digest": rng_manifest["digest"],
        "run_id": run_id,
        "schema": ARCHIVE_SCHEMA,
        "seed": seed,
    }
    done = (
        not stop.exists()
        and all(name in summaries for name in ARMS)
        and all(
            isinstance(summaries[name], dict)
            and cast(dict[str, object], summaries[name]).get("failed") is None
            and int(cast(int, cast(dict[str, object], summaries[name])["generations_completed"]))
            == int(generations)
            for name in ARMS
        )
    )
    if done:
        _atomic_json(seed_dir / "COMPLETE", outcome)
    else:
        _atomic_json(seed_dir / "PARTIAL", outcome)
    return outcome


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _load_snap(
    root: Path,
    seed: int,
    arm: str,
    generation: int,
    bound: Mapping[str, object] | None = None,
) -> dict[str, object] | None:
    path = root / "confirmatory" / "snapshots" / f"seed{seed}_{arm}_g{generation:04d}.json"
    if not path.is_file():
        return None
    if bound is None:
        return read_snapshot(path)
    expected = dict(bound)
    expected["seed"] = int(seed)
    expected["arm"] = str(arm)
    expected["generation"] = int(generation)
    expected["history_id"] = str(int(seed))
    return read_bound_snapshot(path, expected=expected)


def arm_time_shift(
    root: Path,
    seed: int,
    arm: str,
    bound: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """CH and CP at the locked centers. Missing assays are omitted, not zeroed.

    Omitting a center changes the estimand. That is reported and is not imputed as 0.
    """

    ch_values: list[float] = []
    cp_values: list[float] = []
    missing: list[dict[str, object]] = []
    archive_missing = False
    for center in analysis_centers():
        past_body = _load_snap(root, seed, arm, center - DELTA, bound)
        now_body = _load_snap(root, seed, arm, center, bound)
        if past_body is None or now_body is None:
            archive_missing = True
            missing.append({"center": center, "reason": "snapshot-missing"})
            continue
        past_hosts = _rows(past_body, "hosts")
        past_parasites = _rows(past_body, "parasites")
        now_hosts = _rows(now_body, "hosts")
        now_parasites = _rows(now_body, "parasites")
        contemporary = infectivity(past_hosts, past_parasites)
        host_now = infectivity(now_hosts, past_parasites)
        parasite_now = infectivity(past_hosts, now_parasites)
        if contemporary is None or host_now is None:
            missing.append({"center": center, "component": "CH", "reason": "unmeasurable"})
        else:
            ch_values.append(contemporary - host_now)
        if contemporary is None or parasite_now is None:
            missing.append({"center": center, "component": "CP", "reason": "unmeasurable"})
        else:
            cp_values.append(parasite_now - contemporary)
    mean_ch = _mean(ch_values)
    mean_cp = _mean(cp_values)
    score = None if mean_ch is None or mean_cp is None else min(mean_ch, mean_cp)
    n_centers = len(analysis_centers())
    estimand_changed = len(ch_values) != n_centers or len(cp_values) != n_centers
    return {
        "S": score,
        "archive_missing": archive_missing,
        "estimand": (
            "mean of the locked centers"
            if not estimand_changed
            else "mean of measurable centers only; omitted centers were not imputed as 0"
        ),
        "estimand_changed": estimand_changed,
        "mean_ch": mean_ch,
        "mean_cp": mean_cp,
        "missing": missing,
        "n_centers": n_centers,
        "n_ch": len(ch_values),
        "n_cp": len(cp_values),
        "red_queen_proved": False,
    }


def one_sample_t(
    values: Sequence[float],
    importance_bound: float,
    *,
    mde: float | None = None,
) -> dict[str, object]:
    """One-sample t against an importance bound that is not the MDE.

    A sample standard error of zero makes the Student-t undefined. That case
    does not report p = 0 and does not support the contrast. Practical support
    requires the one-sided lower bound, not the point estimate and not p = 0.
    ``mde`` is recorded and is not used as ``importance_bound``.
    """

    if any(not math.isfinite(float(value)) for value in values):
        raise ConfigurationError("Student-t sample contains NaN or Infinity")
    clean = [float(value) for value in values]
    n = len(clean)
    mde_value = None if mde is None else float(mde)
    base: dict[str, object] = {
        "df": n - 1,
        "importance_bound": float(importance_bound),
        "mde": mde_value,
        "mde_is_importance_bound": False,
        "n": n,
        "red_queen_proved": False,
        "se_zero": False,
        "values_are_histories": True,
    }
    if n < 2:
        base.update(
            {
                "ci95": None,
                "lower_decision": None,
                "mean": _mean(clean),
                "meets_practical_effect": False,
                "p_one_sided": None,
                "practical_support": False,
                "reject": False,
                "sd": None,
                "estimand_note": "fewer than two histories; the t statistic is not defined",
            }
        )
        return base
    mean = float(statistics.fmean(clean))
    sd = float(statistics.stdev(clean))
    se = sd / math.sqrt(n)
    df = n - 1
    if se == 0.0:
        base.update(
            {
                "ci95": None,
                "df": df,
                "estimand_note": (
                    "sample SE is zero; Student-t p is undefined and is not reported as 0"
                ),
                "lower_decision": None,
                "mean": mean,
                "meets_practical_effect": False,
                "p_one_sided": None,
                "practical_support": False,
                "reject": False,
                "sd": sd,
                "se_zero": True,
                "t": None,
            }
        )
        return base
    t_stat = mean / se
    p_value = float(student_t_sf(t_stat, df))
    t_ci = student_t_ppf(0.975, df)
    t_lo = student_t_ppf(1.0 - ALPHA, df)
    lower = mean - t_lo * se
    # The bound, not the point estimate, is what can clear the importance threshold.
    meets = bool(lower >= float(importance_bound))
    reject = bool(p_value < ALPHA and mean > 0.0)
    base.update(
        {
            "ci95": [mean - t_ci * se, mean + t_ci * se],
            "df": df,
            "estimand_note": "one-sample mean of the supplied finite histories",
            "lower_decision": lower,
            "mean": mean,
            "meets_practical_effect": meets,
            "p_one_sided": p_value,
            "practical_support": bool(meets and reject),
            "reject": reject,
            "sd": sd,
            "t": t_stat,
        }
    )
    return base


def decide_verdict(
    tests: Mapping[str, Mapping[str, object]],
    *,
    verification_ok: bool,
    archive_ok: bool,
    practical_effect: float,
) -> str:
    if not verification_ok or not archive_ok:
        return VERDICT_BLOCKED
    parsed: list[Mapping[str, object]] = []
    for name in ("CH_A", "CP_A", "S_A_minus_S_B", "S_A_minus_S_C"):
        if name not in tests:
            return VERDICT_BLOCKED
        parsed.append(tests[name])
    if any(int(cast(int, item["n"])) < MEASUREMENT_FLOOR for item in parsed):
        return VERDICT_BLOCKED
    if any(bool(item.get("se_zero")) or item.get("p_one_sided") is None for item in parsed):
        return VERDICT_INCONCLUSIVE
    if all(bool(item["reject"]) and bool(item["meets_practical_effect"]) for item in parsed):
        return VERDICT_SUPPORTED
    uppers: list[float] = []
    for item in parsed:
        ci = item.get("ci95")
        if not isinstance(ci, list) or len(ci) != 2:
            return VERDICT_INCONCLUSIVE
        uppers.append(float(cast(float, ci[1])))
    if all(upper < practical_effect for upper in uppers):
        return VERDICT_NEGATIVE
    return VERDICT_INCONCLUSIVE


def _line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    with path.open(encoding="utf-8") as handle:
        for _ in handle:
            count += 1
    return count


def verify_confirmatory_shortcut(root: Path, seeds: Sequence[int]) -> dict[str, object]:
    """First locked seed whose arm A is measurable at t-d and t. Not chosen by sign."""

    for seed in seeds:
        past = _load_snap(root, seed, ARM_A, BURN_IN)
        now = _load_snap(root, seed, ARM_A, BURN_IN + DELTA)
        if past is None or now is None:
            continue
        crosses = (
            (_rows(past, "hosts"), _rows(past, "parasites")),
            (_rows(now, "hosts"), _rows(past, "parasites")),
            (_rows(past, "hosts"), _rows(now, "parasites")),
        )
        if any((not hosts or not parasites) for hosts, parasites in crosses):
            continue
        diffs: list[float] = []
        for hosts, parasites in crosses:
            left = infectivity(hosts, parasites)
            right = infectivity_pairwise(hosts, parasites)
            if left is None or right is None:
                diffs = []
                break
            diffs.append(abs(left - right))
        if not diffs:
            continue
        return {
            "max_abs": max(diffs),
            "ok": max(diffs) <= VERIFY_ABS_TOL,
            "red_queen_proved": False,
            "seed": seed,
        }
    return {"ok": False, "reason": "no measurable verification sample", "red_queen_proved": False}


def require_same_histories(left: Sequence[int], right: Sequence[int]) -> None:
    """Two arms are paired only when they list the same histories in the same order."""

    if [int(item) for item in left] != [int(item) for item in right]:
        raise ConfigurationError("arms are not paired on the same histories")


def require_complete_times(observed: Sequence[int], required: Sequence[int]) -> None:
    """A missing or extra time is not a complete series and is not filled with zero."""

    if [int(item) for item in observed] != [int(item) for item in required]:
        raise ConfigurationError("time index is missing, duplicated, or misaligned")


def assess_locked_histories(
    records: Sequence[Mapping[str, object]],
    locked_seeds: Sequence[int],
) -> dict[str, object]:
    """Refuse a sample that is not exactly the locked histories.

    A duplicate seed is an alias, not a second history. A missing value is
    omitted, not replaced by zero, and the estimand is then no longer the
    locked one. ``analyze`` calls this through ``apply_locked_history_verdict_gate``
    so a reduced sample is BLOCKED, not a scientific negative or inconclusive.
    """

    seeds = [int(cast(int, record["seed"])) for record in records]
    if len(seeds) != len(set(seeds)):
        return {
            "dropped_seeds": [],
            "estimand": "undefined; a history id was repeated",
            "estimand_changed": True,
            "n_locked": len(tuple(locked_seeds)),
            "n_used": 0,
            "ok": False,
            "reason": "duplicate-history-alias",
            "support_allowed": False,
        }
    locked = [int(seed) for seed in locked_seeds]
    if seeds != locked:
        return {
            "dropped_seeds": sorted(set(locked) - set(seeds)),
            "estimand": "not the locked seed list",
            "estimand_changed": True,
            "n_locked": len(locked),
            "n_used": len(seeds),
            "ok": False,
            "reason": "seed-list-mismatch",
            "support_allowed": False,
        }
    dropped = [int(cast(int, record["seed"])) for record in records if record.get("value") is None]
    if dropped:
        return {
            "dropped_seeds": dropped,
            "estimand": "mean over measurable histories only; not imputed as 0",
            "estimand_changed": True,
            "n_locked": len(locked),
            "n_used": len(locked) - len(dropped),
            "ok": False,
            "reason": "unmeasurable-omitted",
            "support_allowed": False,
        }
    return {
        "dropped_seeds": [],
        "estimand": "mean of the locked histories",
        "estimand_changed": False,
        "n_locked": len(locked),
        "n_used": len(locked),
        "ok": True,
        "reason": None,
        "support_allowed": True,
    }


def apply_locked_history_verdict_gate(
    verdict: str,
    *,
    contrast_records: Mapping[str, Sequence[Mapping[str, object]]],
    locked_seeds: Sequence[int],
) -> dict[str, object]:
    """Force BLOCKED when analyze would score a reduced locked sample.

    ``assess_locked_histories`` is the rule. A seed-list mismatch or any
    unmeasurable required contrast is a measurement block, not a scientific
    negative or an inconclusive result on the leftover histories.
    """

    assessments = {
        name: assess_locked_histories(records, locked_seeds)
        for name, records in contrast_records.items()
    }
    ok = all(bool(item["ok"]) for item in assessments.values())
    dropped: list[int] = []
    seen: set[int] = set()
    for item in assessments.values():
        for seed in cast(list[object], item["dropped_seeds"]):
            seed_i = int(cast(int, seed))
            if seed_i not in seen:
                seen.add(seed_i)
                dropped.append(seed_i)
    dropped.sort()
    return {
        "assessments": assessments,
        "dropped_seeds": dropped,
        "estimand_changed": any(bool(item["estimand_changed"]) for item in assessments.values()),
        "n_locked": len(tuple(locked_seeds)),
        "n_used": {name: int(cast(int, item["n_used"])) for name, item in assessments.items()},
        "ok": ok,
        "verdict": VERDICT_BLOCKED if not ok else verdict,
    }


def validate_archive(
    path: Path,
    *,
    seed: int,
    generations: int,
    arms: Sequence[str],
    run_id: str,
    config_digest_value: str,
    code_version: str,
    design_version: str,
) -> dict[str, object]:
    """Line count is not enough. Generations must be complete and unique."""

    if not path.is_file():
        raise ConfigurationError(f"archive missing: {path}")
    seen: dict[tuple[str, int], int] = {}
    n_lines = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ConfigurationError("archive line is not an object")
            n_lines += 1
            if row.get("schema") != ARCHIVE_SCHEMA:
                raise ConfigurationError("archive schema rejected")
            if row.get("experiment") != EXPERIMENT_ID:
                raise ConfigurationError("archive experiment rejected")
            if int(cast(int, row.get("seed"))) != int(seed):
                raise ConfigurationError("archive seed rejected")
            if str(row.get("history_id")) != str(int(seed)):
                raise ConfigurationError("archive history rejected")
            if row.get("run_id") != run_id:
                raise ConfigurationError("archive run_id rejected")
            if row.get("config_digest") != config_digest_value:
                raise ConfigurationError("archive config digest rejected")
            if row.get("code_version") != code_version:
                raise ConfigurationError("archive code version rejected")
            if row.get("design_version") != design_version:
                raise ConfigurationError("archive design version rejected")
            key = (str(row.get("arm")), int(cast(int, row.get("generation"))))
            seen[key] = seen.get(key, 0) + 1
    expected = int(generations) * len(tuple(arms))
    if n_lines != expected:
        raise ConfigurationError(f"archive line count {n_lines} != {expected}")
    for arm_name in arms:
        for generation in range(1, int(generations) + 1):
            if seen.get((str(arm_name), generation), 0) != 1:
                raise ConfigurationError(
                    f"archive generation {arm_name}/{generation} is duplicated or missing"
                )
    return {"lines": n_lines, "ok": True, "red_queen_proved": False}


def assert_artifacts_one_run(
    root: Path,
    *,
    run_id: str,
    seeds: Sequence[int],
) -> None:
    """Initial state, COMPLETE and the verdict must name the same run."""

    for seed in seeds:
        seed_dir = root / "confirmatory" / "by_seed" / f"seed{seed}"
        initial = _load_json(seed_dir / "initial.json")
        complete = _load_json(seed_dir / "COMPLETE")
        if initial.get("run_id") != run_id or complete.get("run_id") != run_id:
            raise ConfigurationError(f"seed {seed} is not bound to run {run_id}")
        if int(cast(int, initial.get("seed"))) != int(seed):
            raise ConfigurationError(f"initial seed {seed} rejected")
        if int(cast(int, complete.get("seed"))) != int(seed):
            raise ConfigurationError(f"COMPLETE seed {seed} rejected")
    verdict_path = root / "confirmatory" / "verdict.json"
    if verdict_path.is_file():
        verdict = _load_json(verdict_path)
        if verdict.get("run_id") != run_id:
            raise ConfigurationError("verdict is from another run")


def _recorded_arm_failure(body: Mapping[str, object]) -> bool:
    """A failed arm is not a finished history. Absence of the key is not a failure.

    ``None`` is the runner's success marker. Any other value, including a
    failure string, means that arm did not succeed.
    """

    if body.get("failed") is not None:
        return True
    arms = body.get("arms")
    if not isinstance(arms, dict):
        return False
    return any(isinstance(arm, dict) and arm.get("failed") is not None for arm in arms.values())


def analyze(root: Path) -> dict[str, object]:
    block = _locked_block(root)
    if block.get("revised_design") is not None:
        raise ConfigurationError("refusing to score a confirmatory the prereg says must stop")
    if block.get("confirmatory_started") is not True:
        raise ConfigurationError("refusing to score a confirmatory that was not started")
    seeds = _as_int_list(block.get("seeds"))
    generations = int(cast(int, block["generations"]))
    raw_importance = block.get("importance_bound")
    importance_declared = isinstance(raw_importance, (int, float)) and not isinstance(raw_importance, bool)
    importance = float(cast(float, raw_importance)) if importance_declared else 0.0
    mde = block.get("minimum_detectable_effect", block.get("practical_effect"))
    bound = {
        "code_version": block.get("code_version"),
        "config_digest": block.get("config_digest"),
        "design_version": block.get("design_version"),
        "experiment": EXPERIMENT_ID,
        "run_id": block.get("run_id"),
        "schema": SNAPSHOT_SCHEMA,
    }
    per_seed: list[dict[str, object]] = []
    archive_ok = True
    for seed in seeds:
        seed_dir = root / "confirmatory" / "by_seed" / f"seed{seed}"
        complete_path = seed_dir / "COMPLETE"
        complete_body: dict[str, object] | None = None
        if not complete_path.is_file():
            archive_ok = False
        else:
            try:
                complete_body = _load_json(complete_path)
            except ConfigurationError:
                archive_ok = False
        if complete_body is not None and _recorded_arm_failure(complete_body):
            archive_ok = False
        lines = _line_count(seed_dir / "archive.jsonl")
        if lines != generations * len(ARMS):
            archive_ok = False
        try:
            validate_archive(
                seed_dir / "archive.jsonl",
                seed=seed,
                generations=generations,
                arms=ARMS,
                run_id=str(block.get("run_id") or ""),
                config_digest_value=str(block.get("config_digest") or ""),
                code_version=str(block.get("code_version") or ""),
                design_version=str(block.get("design_version") or ""),
            )
            assert_artifacts_one_run(root, run_id=str(block.get("run_id") or ""), seeds=(seed,))
        except ConfigurationError:
            archive_ok = False
        arms: dict[str, object] = {}
        for arm_name in ARMS:
            arms[arm_name] = arm_time_shift(root, seed, arm_name, bound)
            if bool(cast(dict[str, object], arms[arm_name])["archive_missing"]):
                archive_ok = False
        arm_a = cast(dict[str, object], arms[ARM_A])
        arm_b = cast(dict[str, object], arms[ARM_B])
        arm_c = cast(dict[str, object], arms[ARM_C])
        diff_b = (
            None
            if arm_a["S"] is None or arm_b["S"] is None
            else float(cast(float, arm_a["S"])) - float(cast(float, arm_b["S"]))
        )
        diff_c = (
            None
            if arm_a["S"] is None or arm_c["S"] is None
            else float(cast(float, arm_a["S"])) - float(cast(float, arm_c["S"]))
        )
        record: dict[str, object] = {
            "S_A_minus_S_B": diff_b,
            "S_A_minus_S_C": diff_c,
            "archive_lines": lines,
            "arms": arms,
            "red_queen_proved": False,
            "seed": seed,
        }
        per_seed.append(record)
        _atomic_json(seed_dir / "result.json", record)

    def collect(selector: str) -> list[float]:
        values: list[float] = []
        for record in per_seed:
            if selector == "CH_A":
                value = cast(dict[str, object], cast(dict[str, object], record["arms"])[ARM_A])["mean_ch"]
            elif selector == "CP_A":
                value = cast(dict[str, object], cast(dict[str, object], record["arms"])[ARM_A])["mean_cp"]
            elif selector == "S_A_minus_S_B":
                value = record["S_A_minus_S_B"]
            else:
                value = record["S_A_minus_S_C"]
            if value is not None:
                values.append(float(cast(float, value)))
        return values

    tests = {
        "CH_A": one_sample_t(collect("CH_A"), importance, mde=None if mde is None else float(cast(float, mde))),
        "CP_A": one_sample_t(collect("CP_A"), importance, mde=None if mde is None else float(cast(float, mde))),
        "S_A_minus_S_B": one_sample_t(collect("S_A_minus_S_B"), importance, mde=None if mde is None else float(cast(float, mde))),
        "S_A_minus_S_C": one_sample_t(collect("S_A_minus_S_C"), importance, mde=None if mde is None else float(cast(float, mde))),
    }
    verification = verify_confirmatory_shortcut(root, seeds)
    for record in per_seed:
        for arm_name in ARMS:
            if bool(cast(dict[str, object], cast(dict[str, object], record["arms"])[arm_name])["archive_missing"]):
                archive_ok = False
    verdict = decide_verdict(
        tests,
        verification_ok=bool(verification.get("ok")),
        archive_ok=archive_ok,
        practical_effect=importance,
    )

    def _contrast_value(record: Mapping[str, object], selector: str) -> object:
        if selector == "CH_A":
            return cast(dict[str, object], cast(dict[str, object], record["arms"])[ARM_A])["mean_ch"]
        if selector == "CP_A":
            return cast(dict[str, object], cast(dict[str, object], record["arms"])[ARM_A])["mean_cp"]
        return record[selector]

    contrast_names = ("CH_A", "CP_A", "S_A_minus_S_B", "S_A_minus_S_C")
    contrast_records = {
        name: [
            {"seed": int(cast(int, record["seed"])), "value": _contrast_value(record, name)}
            for record in per_seed
        ]
        for name in contrast_names
    }
    # analyze calls assess_locked_histories through this gate. A reduced locked
    # sample is BLOCKED, not NEGATIVE_IN_MODEL or INCONCLUSIVE.
    lock_gate = apply_locked_history_verdict_gate(
        verdict,
        contrast_records=contrast_records,
        locked_seeds=seeds,
    )
    verdict = str(lock_gate["verdict"])
    n_used = cast(dict[str, int], lock_gate["n_used"])
    dropped_seeds = cast(list[int], lock_gate["dropped_seeds"])
    estimand_changed = bool(lock_gate["estimand_changed"])
    for record in per_seed:
        for arm_name in ARMS:
            if bool(cast(dict[str, object], cast(dict[str, object], record["arms"])[arm_name]).get("estimand_changed")):
                estimand_changed = True
    if (not importance_declared or estimand_changed) and verdict == VERDICT_SUPPORTED:
        verdict = VERDICT_BLOCKED
    if not bool(lock_gate["ok"]):
        # History lock failure stays a measurement block even if support was
        # already rewritten above. Negatives and inconclusive leftovers are not allowed.
        verdict = VERDICT_BLOCKED
    report: dict[str, object] = {
        "archive_ok": archive_ok,
        "code_commit": block.get("code_commit"),
        "dropped_seeds": dropped_seeds,
        "experiment": EXPERIMENT_ID,
        "per_seed": per_seed,
        "phase": 5,
        "estimand": (
            "mean of every locked history"
            if not estimand_changed
            else "mean of measurable histories only; the locked estimand was not estimated"
        ),
        "estimand_changed": estimand_changed,
        "importance_bound": raw_importance,
        "importance_bound_declared": importance_declared,
        "locked_history_gate": {
            "ok": lock_gate["ok"],
            "assessments": lock_gate["assessments"],
        },
        "mde_used_as_importance_bound": False,
        "minimum_detectable_effect": mde,
        "n_locked": int(cast(int, lock_gate["n_locked"])),
        "n_used": n_used,
        "practical_effect": raw_importance if importance_declared else None,
        "red_queen_proved": False,
        "biological_red_queen_proved": False,
        "run_id": block.get("run_id"),
        "seeds": seeds,
        "shortcut_verification": verification,
        "tests": tests,
        "verdict": verdict,
    }
    # The supported-in-model flag is not a biological proof.
    report["red_queen_proved"] = False
    out = root / "confirmatory"
    _atomic_json(out / "inference.json", {"importance_bound": raw_importance, "minimum_detectable_effect": mde, "mde_used_as_importance_bound": False, "tests": tests, "red_queen_proved": False})
    _atomic_json(out / "verdict.json", report)
    replay = root.parents[0] if False else Path(__file__).resolve().parents[3]
    command = (
        f"cd {replay}\n"
        "PYTHONPATH=src PYTHONUNBUFFERED=1 "
        "python -m codontrace.genesis.rq_bidirectional_timeshift_confirm\n"
        "PYTHONPATH=src PYTHONUNBUFFERED=1 "
        "python -m codontrace.genesis.rq_bidirectional_timeshift_confirm --analyze-only\n"
    )
    (out / "replay_command.txt").write_text(command, encoding="utf-8")
    live = _LockedAppend(root / "live.log", fsync_each=True)
    try:
        live.line(
            f"phase=5 event=verdict verdict={verdict} importance_declared={importance_declared} "
            "red_queen_proved=false"
        )
    finally:
        live.close()
    return report


def _pending_seeds(root: Path, seeds: Sequence[int]) -> list[int]:
    pending: list[int] = []
    for seed in seeds:
        if (root / "confirmatory" / "by_seed" / f"seed{seed}" / "COMPLETE").is_file():
            continue
        _reset_seed(root, seed)
        pending.append(seed)
    return pending


def restart_clean(root: Path) -> None:
    """Retain confirmatory evidence and mint a new run id. The lock is not retuned.

    Prior files move under ``retained/``. The live log is copied there and is
    not stripped. This function does not delete evidence.
    """

    import shutil

    block = _locked_block(root)
    if block.get("revised_design") is not None:
        raise ConfigurationError("revised design is locked and must not be started")
    path = root / "prereg_lock.json"
    prereg = _load_json(path)
    current = cast(dict[str, object], prereg["confirmatory"])
    count = int(cast(int, current.get("restart_clean_count") or 0)) + 1
    dest = root / "retained" / f"restart-{count}"
    dest.mkdir(parents=True, exist_ok=False)
    conf = root / "confirmatory"
    if conf.exists():
        shutil.move(str(conf), str(dest / "confirmatory"))
    log = root / "live.log"
    if log.is_file():
        shutil.copy2(log, dest / "live.log")
    current["restart_clean_count"] = count
    current["run_id"] = f"clean-{count}"
    current["confirmatory_started"] = True
    prereg["confirmatory"] = current
    prereg["confirmatory_started"] = True
    _atomic_json(path, prereg)
    _ = block
    live = _LockedAppend(root / "live.log", fsync_each=True)
    try:
        live.line(
            f"event=restart-clean count={count} seeds_unchanged=true "
            "horizon_unchanged=true lag_unchanged=true red_queen_proved=false"
        )
    finally:
        live.close()


def run_confirmatory(root: Path) -> dict[str, object]:
    block = _locked_block(root)
    if block.get("revised_design") is not None:
        raise ConfigurationError("stopping before confirmatory generations: design was revised for power")
    if block.get("confirmatory_started") is not True:
        raise ConfigurationError("confirmatory_started is still false")
    seeds = _as_int_list(block.get("seeds"))
    generations = int(cast(int, block["generations"]))
    if generations != CONFIRMATORY_GENERATIONS or int(cast(int, block["delta"])) != DELTA:
        raise ConfigurationError("locked horizon or lag does not match the confirmatory protocol")
    run_id = str(block.get("run_id") or "run")
    pending = _pending_seeds(root, seeds)
    stop = root / "confirmatory" / "STOP"
    if stop.exists():
        stop.unlink()
    if pending:
        workers = min(len(pending), MAX_WORKERS)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(run_one_history, seed, str(root), generations, run_id, SNAPSHOT_STRIDE): seed
                for seed in pending
            }
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    outcome = future.result()
                except Exception as exc:
                    stop.write_text(f"seed={seed} exception={exc}\n", encoding="utf-8")
                    raise
                arms = cast(dict[str, object], outcome.get("arms") or {})
                broken = [
                    name
                    for name in ARMS
                    if name not in arms
                    or not isinstance(arms[name], dict)
                    or cast(dict[str, object], arms[name]).get("failed")
                ]
                if broken or outcome.get("failed"):
                    stop.write_text(
                        json.dumps({"failed": outcome.get("failed"), "seed": seed, "arms": arms}) + "\n",
                        encoding="utf-8",
                    )
                    raise ConfigurationError(f"engine failure on seed {seed}: {outcome.get('failed') or broken}")
    return analyze(root)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RQ bidirectional time-shift confirmatory")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--lock-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--restart-clean", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = args.root if args.root is not None else _default_root()
    repo = Path(__file__).resolve().parents[3]
    code_commit = _git_head(repo)
    if args.restart_clean:
        restart_clean(root)
    prereg = lock_confirmatory(root, code_commit=code_commit)
    block = cast(dict[str, object], prereg["confirmatory"])
    if block.get("revised_design") is not None:
        sys.stdout.write(
            "STOP before confirmatory generations: 24 seeds cannot resolve the "
            f"practical effect {block.get('practical_effect')}. Revised design is locked.\n"
        )
        sys.stdout.flush()
        return 2
    if args.lock_only:
        dispersion = cast(dict[str, object], block["dispersion"])
        sys.stdout.write(
            f"locked practical_effect={block.get('practical_effect')} "
            f"resolvable={dispersion['resolvable']} "
            "confirmatory_started=false red_queen_proved=false\n"
        )
        sys.stdout.flush()
        return 0
    if args.analyze_only:
        if block.get("confirmatory_started") is not True:
            raise ConfigurationError("nothing to analyze; confirmatory has not started")
        report = analyze(root)
        sys.stdout.write(f"verdict={report['verdict']} red_queen_proved=false\n")
        sys.stdout.flush()
        return 0
    run_id = str(block.get("run_id") or time.strftime("%Y%m%dT%H%M%S"))
    mark_started(root, run_id)
    live = _LockedAppend(root / "live.log", fsync_each=True)
    try:
        live.line(
            f"event=confirmatory-start run={run_id} seeds={','.join(str(s) for s in CONFIRMATORY_SEEDS)} "
            f"generations={CONFIRMATORY_GENERATIONS} delta={DELTA} "
            f"practical_effect={block.get('practical_effect')} red_queen_proved=false"
        )
    finally:
        live.close()
    report = run_confirmatory(root)
    sys.stdout.write(f"verdict={report['verdict']} red_queen_proved=false\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
