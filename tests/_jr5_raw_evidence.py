"""Builder of raw JR5 evidence (every run of the prereg grid) for the verdict tests.

Every per-seed value is ``mean + sd * z``, where ``z`` is a fixed set of 60
normal scores (quantiles at (i + 0.5) / 60), shuffled per arm by a sha256 key
and rescaled to mean 0 and SD 1 exactly. A planted mean and SD are therefore
the sample mean and SD of the arm, with no random draw and no seed to tune.

Defaults are a full Red Queen signal sized from the prereg constants:
- E1: each population's log w is log(theoretical cost) + sd * z with the
  bias-reduced SDs at N = 200 (0.076 at m = 0.5, 0.051 at m = 0.25,
  power.e1.bias_reduced.sd) and, at N = 50, 0.158 and 0.123. Counts follow
  logit p_t = logit(0.2) + t log w, rounded, for the registered horizon.
- E2: copassaged minus fixed is -0.25 per seed at high virulence (the
  planning difference in power.e2) with SD 0.10, and 0 at low virulence.
- (c): frozen replay sits on the fixed arm (frozen minus fixed mean 0, SD
  0.05), so copassaged minus frozen is also about -0.25.
- (d): uniform tax minus fixed mean 0, SD 0.05; outcross minus self log
  fitness mean 0, SD 0.05 at every mutation rate; E4 host effect -0.05 and
  parasite effect 0, SD 0.05 (host side expected below 0 under cycling).
- (e): every replay digest, body sha and sealed lock matches; residual 0.
"""

from __future__ import annotations

import hashlib
import math
from copy import deepcopy
from functools import cache
from statistics import NormalDist
from typing import Any

import numpy as np
from scipy import stats

from codontrace.claimgate.jr5_verdict import (
    PREREG_CONSTANTS_SHA256,
    PREREG_RECORD_DIGEST,
    SEALED_LOCK_DIGESTS,
    jr5_constants,
    jr5_run_grid,
    run_record_sha256,
)
from codontrace.genesis.canonical import canonical_digest
from tests._jr5_e1_fit import fit_logit

N_SEEDS = 60
E1_SD = {(0.5, 200): 0.076, (0.25, 200): 0.051, (0.5, 50): 0.158, (0.25, 50): 0.123}


def scores(label: str, n: int = N_SEEDS) -> list[float]:
    """n normal scores, shuffled by ``label``, with mean exactly 0 and SD exactly 1."""

    base = [NormalDist().inv_cdf((i + 0.5) / n) for i in range(n)]
    order = sorted(range(n), key=lambda i: hashlib.sha256(f"{label}:{i}".encode()).hexdigest())
    z = [base[i] for i in order]
    mean = math.fsum(z) / n
    sd = math.sqrt(math.fsum((v - mean) ** 2 for v in z) / (n - 1))
    return [(v - mean) / sd for v in z]


def _hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


DEFAULTS: dict[str, Any] = {
    "e1_log_shift": {0.5: 0.0, 0.25: 0.0},  # added to every log w of that sex ratio
    "e1_early_fixed": {},  # (sex_ratio, host_n) -> number of populations fixed at generation 1
    "e2_effect": {(200, "high"): -0.25, (50, "high"): -0.25, (200, "low"): 0.0, (50, "low"): 0.0},
    "e2_sd": 0.10,
    "e2_deltas": {},  # (host_n, virulence) -> explicit 60 deltas (overrides effect and sd)
    "frozen_minus_fixed": 0.0,
    "frozen_sd": 0.05,
    "tax_minus_fixed": 0.0,
    "load_effect": 0.0,  # outcross minus self log fitness at every mutation rate
    "load_slope": 0.0,  # added per unit mutation rate
    "e4": {"host_effect": -0.05, "parasite_effect": 0.0},
}


def build(**overrides: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (evidence, plan). ``plan`` is the parameter set used."""

    plan = deepcopy(DEFAULTS)
    plan.update(overrides)
    k = jr5_constants()
    g = k["gate_e1"]
    runs: list[dict[str, Any]] = []

    def add(exp: str, cell: dict[str, Any], n: int, seed: int, data: dict[str, Any]) -> None:
        run_id = f"{exp}|{'|'.join(f'{a}={b}' for a, b in sorted(cell.items()))}|N{n}|s{seed}"
        rec: dict[str, Any] = {
            "run_id": run_id,
            "experiment": exp,
            "cell": cell,
            "host_n": n,
            "seed": seed,
            "data": data,
            "replay": {
                "expected_digest": _hex(run_id + ":replay"),
                "replayed_digest": _hex(run_id + ":replay"),
                "one_shot_body_sha256": _hex(run_id + ":body"),
                "resumed_body_sha256": _hex(run_id + ":body"),
                "atp_ledger_residual": 0.0,
            },
        }
        rec["sha256"] = run_record_sha256(rec)
        runs.append(rec)

    grid = sorted(jr5_run_grid(), key=repr)
    confirm = sorted({key[3] for key in grid if key[0] == "e2"})
    idx = {s: i for i, s in enumerate(confirm)}

    def val(label: str, seed: int) -> float:
        return scores(label)[idx[seed]]

    e1_seeds: dict[float, list[int]] = {}
    for exp, cell_t, _n, seed in grid:
        cell = dict(cell_t)
        if exp == "e1":
            e1_seeds.setdefault(cell["sex_ratio"], []).append(seed)
    for exp, cell_t, n, seed in grid:
        cell = dict(cell_t)
        data: dict[str, Any] = {}
        if exp == "e1":
            m = cell["sex_ratio"]
            seeds = sorted(set(e1_seeds[m]))
            i = seeds.index(seed)
            z = scores(f"e1:{m}:{n}", len(seeds))[i]
            log_w = math.log(float(g["theoretical_cost"][str(m)])) + plan["e1_log_shift"][m] + E1_SD[(m, n)] * z
            gens = int(g["generations"][str(m)])
            p0 = float(g["founder_uniparental_frequency"])
            counts = []
            for t in range(gens + 1):
                lo = math.log(p0 / (1 - p0)) + t * log_w
                counts.append(int(round(n / (1 + math.exp(-lo)))))
            if i < plan["e1_early_fixed"].get((m, n), 0):
                counts = [counts[0]] + [n] * gens
            data = {"uniparental_counts": counts}
        elif exp == "e2":
            arm = cell["parasite"]
            base = 0.65 + 0.05 * val(f"base:{arm.split('_')[-1]}:{n}", seed)
            if arm.endswith(("high", "low")) and not arm.startswith("frozen_replay_low"):
                v = arm.split("_")[-1]
                fixed = 0.65 + 0.05 * val(f"fixed:{v}:{n}", seed)
                if arm.startswith("fixed"):
                    x = fixed
                elif arm.startswith("copassaged"):
                    deltas = plan["e2_deltas"].get((n, v))
                    if deltas is not None:
                        x = fixed + deltas[idx[seed]]
                    else:
                        x = fixed + plan["e2_effect"][(n, v)] + plan["e2_sd"] * val(f"e2:{v}:{n}", seed)
                else:  # frozen_replay_high
                    x = fixed + plan["frozen_minus_fixed"] + plan["frozen_sd"] * val(f"frozen:{n}", seed)
            else:
                x = base
            data = {"terminal_uniparental_frequency": min(1.0, max(0.0, x))}
            if arm == "copassaged_high" and n == 200:
                data["e4_window"] = [67, 70]
                data["e4"] = {w: mu + 0.05 * val(f"e4:{w}", seed) for w, mu in plan["e4"].items()}
        elif exp == "uniform_tax":
            v = cell["virulence"]
            fixed = 0.65 + 0.05 * val(f"fixed:{v}:{n}", seed)
            x = fixed + plan["tax_minus_fixed"] + 0.05 * val(f"tax:{v}:{n}", seed)
            data = {"terminal_uniparental_frequency": min(1.0, max(0.0, x))}
        elif exp == "mutation_load":
            mu = cell["mutation"]
            self_ = 0.02 * val(f"self:{mu}:{n}", seed)
            if cell["mating"] == "obligate_self":
                x = self_
            else:
                x = self_ + plan["load_effect"] + plan["load_slope"] * mu + 0.05 * val(f"load:{mu}:{n}", seed)
            data = {"log_terminal_fitness": x}
        add(exp, cell, n, seed, data)
    evidence = {
        "prereg_record_digest": PREREG_RECORD_DIGEST,
        "runs": runs,
        "sealed_locks": dict(SEALED_LOCK_DIGESTS),
        "e1_gate_record": gate_record(runs),
    }
    return evidence, plan


@cache
def _slope(counts: tuple[int, ...], n: int) -> float:
    """The modified score solves the registered penalised binomial fit on generations 0..T."""
    return float(fit_logit(np.asarray(counts, dtype=float), np.full(len(counts), n, dtype=float),
                           np.arange(len(counts), dtype=float), bias_reduced=True)[1])


def gate_record(runs: list[dict[str, Any]] | None = None, *, passed: bool | None = None,
                instrument_failure: bool | None = None, sha: str | None = PREREG_CONSTANTS_SHA256) -> dict[str, Any]:
    """Build v3 independently: fitted slopes, mean +/- t*SD/sqrt(n), and both one-sided tails."""
    if runs is None:
        runs = build()[0]["runs"]
    g = jr5_constants()["gate_e1"]
    spec_keys = ("test", "alpha", "ci_level", "relative_margin", "must_exclude", "must_exclude_ci_level",
                 "exclusion_cap_fraction", "early_fixation_generation", "host_n_gate", "populations_per_cell",
                 "sex_ratios", "host_n_reported", "seed_split")
    spec = {key: g[key] for key in spec_keys}
    spec.update(constants_sha256=PREREG_CONSTANTS_SHA256, prereg_manifest_digest=PREREG_RECORD_DIGEST)
    cells = []
    for m in g["sex_ratios"]:
        for n in g["host_n_reported"]:
            rows = sorted((r for r in runs if r["experiment"] == "e1" and r["host_n"] == n and r["cell"]["sex_ratio"] == m), key=lambda r: r["seed"])
            seeds, excluded, fixed, lost, slopes = [], [], [], [], []
            for r in rows:
                seed = r["seed"]
                counts = r["data"]["uniparental_counts"]
                seeds.append(seed)
                fixed_generation = next((i for i, c in enumerate(counts) if c == n), None)
                if fixed_generation is not None:
                    fixed.append(seed)
                if 0 in counts:
                    lost.append(seed)
                if fixed_generation is not None and fixed_generation < g["early_fixation_generation"]:
                    excluded.append(seed)
                else:
                    slopes.append(_slope(tuple(counts), n))
            bounds = list(g["equivalence_bounds"][str(m)])
            lo, hi = map(math.log, bounds)
            cap = len(excluded) > g["exclusion_cap_fraction"] * len(rows)
            ci90 = ci95 = tost = None
            if len(slopes) >= 2:
                mean = math.fsum(slopes) / len(slopes)
                sd = math.sqrt(math.fsum((v - mean) ** 2 for v in slopes) / (len(slopes) - 1))
                se = sd / math.sqrt(len(slopes))
                df = len(slopes) - 1
                half90 = float(stats.t.ppf(1 - g["alpha"], df)) * se
                half95 = float(stats.t.ppf((1 + g["must_exclude_ci_level"]) / 2, df)) * se
                ci90, ci95 = [mean - half90, mean + half90], [mean - half95, mean + half95]
                tl, tu = (mean - lo) / se, (mean - hi) / se
                pl, pu = float(stats.t.sf(tl, df)), float(stats.t.cdf(tu, df))
                tost = {"test": "one_sample_tost", "n": len(slopes), "df": df, "mean": mean, "sd": sd,
                        "standard_error": se, "lower_bound": lo, "upper_bound": hi, "alpha": g["alpha"],
                        "t_lower": tl, "t_upper": tu, "p_lower": pl, "p_upper": pu, "p_value": max(pl, pu),
                        "ci_level": g["ci_level"], "ci_low": ci90[0], "ci_high": ci90[1],
                        "equivalent": pl < g["alpha"] and pu < g["alpha"]}
            equivalent = tost is not None and tost["equivalent"]
            excludes = ci95 is not None and (ci95[0] > math.log(g["must_exclude"]) or ci95[1] < math.log(g["must_exclude"]))
            cells.append({"sex_ratio": m, "host_n": n, "gated": n == g["host_n_gate"], "n_total": len(rows),
                          "seeds": seeds, "n_used": len(slopes), "excluded_seeds": excluded,
                          "fixed_seeds": fixed, "lost_seeds": lost, "exclusion_cap_exceeded": cap,
                          "log_bounds": [lo, hi], "ratio_bounds": bounds, "tost": tost,
                          "ratio_ci": None if ci90 is None else list(map(math.exp, ci90)),
                          "ratio_ci95": None if ci95 is None else list(map(math.exp, ci95)),
                          "exclusion_interval_log": ci95, "equivalent": equivalent, "excludes_null": excludes,
                          "passed": equivalent and excludes and not cap})
    gate_pass = all(c["passed"] for c in cells if c["gated"])
    failure = not gate_pass or any(c["exclusion_cap_exceeded"] for c in cells)
    body: dict[str, Any] = {"schema": "jr5_e1_gate_v3", "prereg_manifest_digest": PREREG_RECORD_DIGEST,
                            "spec": spec, "cells": cells, "passed": gate_pass if passed is None else passed,
                            "instrument_failure": failure if instrument_failure is None else instrument_failure}
    if sha is not None:
        body["constants_sha256"] = sha
    body["digest"] = canonical_digest(body)
    return body


def readdress(run: dict[str, Any]) -> dict[str, Any]:
    run["sha256"] = run_record_sha256(run)
    return run
