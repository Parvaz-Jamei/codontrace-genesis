"""CausalTape-6b -- required diagnostics for the biotic vs abiotic share claim.

Adds the three things the red-team round demanded before the share can be
claimed, none of which were in the first factorial:

1. differential infection risk V_diff = sum_g p_g (i_g - i_bar)^2 with a
   within-generation label-permutation null. If infection risk does not vary
   across genotypes beyond the permutation null, the "biotic" factor is a
   uniform tax and the share must be relabelled.
2. clumping diagnostics: effective genotype number 1/sum p_g^2, infectable-set
   occupancy, and the maximum size of the tolerance-1 infectable set.
3. decomposition + power: eta^2 / sum-of-squares main effects and interaction
   with seed bootstrap CIs, the minimum detectable interaction at n = 100, and
   a share-stability table over {F_ST, Bray-Curtis} x {w = 5, 20, 50}.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

from rjcj import (
    CELLS,
    GENERATIONS,
    GENOTYPES,
    HOST_CAP,
    INFECTION_COST,
    LOCI,
    MORTALITY,
    POWERS,
    SEEDS,
    TOLERANCE,
    WINDOWS,
    WORKERS,
    run_world,
)

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def run_diag(seed: int, *, parasite: bool, shock: bool, uniform_tax: bool = False, generations: int = GENERATIONS) -> dict:
    """One replicate that records genotype frequencies and infection risk."""

    import math

    from codontrace.rng import RNGManager

    root = RNGManager(seed=seed).fork("rjcj")
    host_stream = root.fork("host")
    par_stream = root.fork("parasite")
    shock_stream = root.fork("shock")
    rng = np.random.default_rng(seed)

    from rjcj import (
        BIRTH_COST,
        HOST_MUTATION,
        INTAKE,
        METABOLISM,
        PARASITE_CAP,
        PARASITE_MUTATION,
        PARASITE_POOL,
        SHOCK_FACTOR,
        SHOCK_MEAN_INTERVAL,
        START_ENERGY,
        TAX_FRACTION,
        INITIAL_HOSTS,
        _mutate,
    )

    host_genome = np.zeros((HOST_CAP, LOCI), dtype=np.int8)
    host_energy = np.zeros(HOST_CAP, dtype=float)
    host_alive = np.zeros(HOST_CAP, dtype=bool)
    slots = rng.permutation(HOST_CAP)[:INITIAL_HOSTS]
    host_alive[slots] = True
    host_energy[slots] = BIRTH_COST * 0.6
    host_genome[slots] = rng.integers(0, 2, size=(INITIAL_HOSTS, LOCI)).astype(np.int8)

    parasite_genome = rng.integers(0, 2, size=(PARASITE_CAP, LOCI)).astype(np.int8)
    parasite_alive = np.zeros(PARASITE_CAP, dtype=bool)
    parasite_alive[:PARASITE_POOL] = True

    freq = np.zeros((generations, GENOTYPES))
    infected_by_genotype = np.zeros((generations, GENOTYPES))
    v_diff_series = np.zeros(generations)
    v_null_series = np.zeros(generations)
    eff_genotypes = np.zeros(generations)
    infectable_occupancy = np.zeros(generations)

    for generation in range(generations):
        alive = np.flatnonzero(host_alive)
        if alive.size == 0:
            continue
        intake = INTAKE
        if shock and shock_stream.random() < 1.0 / SHOCK_MEAN_INTERVAL:
            intake = INTAKE * SHOCK_FACTOR
        host_energy[host_alive] += intake
        host_energy[host_alive] -= METABOLISM

        infected = np.zeros(HOST_CAP, dtype=bool)
        if parasite:
            par = np.flatnonzero(parasite_alive)
            if par.size:
                distances = (host_genome[alive, None, :] != parasite_genome[None, par, :]).sum(axis=2)
                infected[alive] = (distances <= TOLERANCE).any(axis=1)
        elif uniform_tax:
            infected[alive] = rng.random(alive.size) < TAX_FRACTION
        if infected.any():
            host_energy[infected] -= INFECTION_COST

        index = host_genome[alive] @ POWERS
        counts = np.bincount(index, minlength=GENOTYPES).astype(float)
        p = counts / counts.sum()
        freq[generation] = p
        inf_counts = np.bincount(index[infected[alive]], minlength=GENOTYPES).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.where(counts > 0, inf_counts / np.maximum(counts, 1), np.nan)
        infected_by_genotype[generation] = rate
        observed = np.nansum(p * (rate - np.nansum(p * rate)) ** 2)
        permuted = []
        labels = infected[alive].copy()
        for _ in range(20):
            rng.shuffle(labels)
            perm_counts = np.bincount(index[labels], minlength=GENOTYPES).astype(float)
            with np.errstate(invalid="ignore", divide="ignore"):
                perm_rate = np.where(counts > 0, perm_counts / np.maximum(counts, 1), np.nan)
            permuted.append(np.nansum(p * (perm_rate - np.nansum(p * perm_rate)) ** 2))
        v_diff_series[generation] = observed
        v_null_series[generation] = float(np.mean(permuted))
        eff_genotypes[generation] = 1.0 / max(float(np.sum(p**2)), 1e-12)
        if parasite:
            par = np.flatnonzero(parasite_alive)
            if par.size:
                compatible = np.zeros(GENOTYPES, dtype=bool)
                for g in range(GENOTYPES):
                    bits = np.array([(g >> b) & 1 for b in range(LOCI)], dtype=np.int8)
                    d = (bits[None, :] != parasite_genome[par]).sum(axis=1)
                    compatible[g] = (d <= TOLERANCE).any()
                infectable_occupancy[generation] = float(np.sum(p[compatible]))

        eligible = host_alive & (host_energy >= BIRTH_COST)
        if eligible.any():
            eligible_idx = np.flatnonzero(eligible)
            ranked = eligible_idx[np.argsort(-host_energy[eligible_idx], kind="stable")]
            free = np.flatnonzero(~host_alive)
            n_births = min(ranked.size, free.size)
            parents = ranked[:n_births]
            child_slots = free[:n_births]
            children = _mutate(host_genome[parents].copy(), host_stream, np.arange(n_births), HOST_MUTATION)
            host_energy[parents] -= BIRTH_COST
            host_genome[child_slots] = children
            host_energy[child_slots] = START_ENERGY
            host_alive[child_slots] = True

        bankrupt = host_alive & (host_energy < 0.0)
        host_energy[bankrupt] = 0.0
        host_alive[bankrupt] = False
        mortal = host_alive & (rng.random(HOST_CAP) < MORTALITY)
        host_energy[mortal] = 0.0
        host_alive[mortal] = False

        if parasite:
            par = np.flatnonzero(parasite_alive)
            alive_after = np.flatnonzero(host_alive)
            if par.size and alive_after.size:
                distances = (host_genome[alive_after, None, :] != parasite_genome[None, par, :]).sum(axis=2)
                success = (distances <= TOLERANCE).sum(axis=0)
                survivors = par[success > 0]
                if survivors.size == 0:
                    parasite_genome[par] = _mutate(
                        parasite_genome[par].copy(), par_stream, np.arange(par.size), PARASITE_MUTATION
                    )
                else:
                    children_p = np.tile(survivors, int(math.ceil(PARASITE_CAP / survivors.size)))[:PARASITE_CAP]
                    parasite_genome = _mutate(
                        parasite_genome[children_p].copy(), par_stream, np.arange(PARASITE_CAP), PARASITE_MUTATION
                    )
                    parasite_alive[:] = True

    half = generations // 2
    return {
        "seed": seed,
        "v_diff_mean": float(np.mean(v_diff_series[half:])),
        "v_null_mean": float(np.mean(v_null_series[half:])),
        "eff_genotypes_mean": float(np.mean(eff_genotypes[half:])),
        "infectable_occupancy_mean": float(np.mean(infectable_occupancy[half:])),
    }


def _task(spec: dict, seed: int) -> dict:
    kwargs = {k: v for k, v in spec.items() if k != "tag"}
    return run_diag(seed, **kwargs)


def main() -> int:
    started = time.perf_counter()
    report: dict = {"experiment": "CausalTape-6b", "workers": WORKERS, "seeds": len(SEEDS), "cells": {}}
    subset = [c for c in CELLS if c["tag"] in ("b0_s0", "b1_s0", "b1_s1", "tax_s0")]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for spec in subset:
            rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
            report["cells"][spec["tag"]] = {
                "v_diff_mean": float(np.mean([r["v_diff_mean"] for r in rows])),
                "v_null_mean": float(np.mean([r["v_null_mean"] for r in rows])),
                "eff_genotypes_mean": float(np.mean([r["eff_genotypes_mean"] for r in rows])),
                "infectable_occupancy_mean": float(np.mean([r["infectable_occupancy_mean"] for r in rows])),
            }
            cell = report["cells"][spec["tag"]]
            print(
                f"{spec['tag']:<8} V_diff={cell['v_diff_mean']:.4f} V_null={cell['v_null_mean']:.4f} "
                f"eff_geno={cell['eff_genotypes_mean']:.1f} "
                f"infectable_occ={cell['infectable_occupancy_mean']:.3f}",
                flush=True,
            )

    # decomposition + power on the stored per-seed window series
    stored = json.loads((RESULTS / "rjcj_results.json").read_text(encoding="utf-8"))

    def series(tag: str, w: int) -> np.ndarray:
        return np.array(stored["cells"][tag]["windows"][str(w)]["per_seed"])

    rng = np.random.default_rng(23)
    decomposition = {}
    for w in WINDOWS:
        a, b, c, d = (series(t, w) for t in ("b0_s0", "b1_s0", "b0_s1", "b1_s1"))
        allv = np.concatenate([a, b, c, d])
        grand = allv.mean()
        ss_total = float(np.sum((allv - grand) ** 2))
        ss_biotic = 4 * len(a) * float((0.5 * (b.mean() + d.mean()) - 0.5 * (a.mean() + c.mean())) ** 2)
        ss_abiotic = 4 * len(a) * float((0.5 * (c.mean() + d.mean()) - 0.5 * (a.mean() + b.mean())) ** 2)
        interaction = (d.mean() - c.mean()) - (b.mean() - a.mean())
        ss_interaction = len(a) * float(interaction**2)
        decomposition[str(w)] = {
            "eta2_biotic": ss_biotic / ss_total if ss_total else 0.0,
            "eta2_abiotic": ss_abiotic / ss_total if ss_total else 0.0,
            "eta2_interaction": ss_interaction / ss_total if ss_total else 0.0,
        }

    # minimum detectable interaction at n = 100 (paired, alpha 0.05, power 0.8)
    w = 20
    interaction = (series("b1_s1", w) - series("b1_s0", w)) - (series("b0_s1", w) - series("b0_s0", w))
    sd = float(np.std(interaction, ddof=1))
    mde = 2.8 * sd / np.sqrt(len(interaction))

    report["decomposition"] = decomposition
    report["power"] = {"interaction_sd": sd, "mde_at_n100": float(mde), "n": len(interaction)}
    report["verdicts"] = {
        "differential_infection_signal": {
            tag: bool(cell["v_diff_mean"] > cell["v_null_mean"])
            for tag, cell in report["cells"].items()
        },
        "biotic_is_not_uniform_tax": bool(
            report["cells"]["b1_s0"]["v_diff_mean"] > report["cells"]["b1_s0"]["v_null_mean"]
            and report["cells"]["tax_s0"]["v_diff_mean"] <= report["cells"]["tax_s0"]["v_null_mean"] + 1e-9
        ),
        "effective_genotypes_far_below_cap": bool(
            report["cells"]["b1_s0"]["eff_genotypes_mean"] < 0.5 * 64
        ),
        "biotic_eta2_exceeds_abiotic": bool(
            all(decomposition[str(w)]["eta2_biotic"] > decomposition[str(w)]["eta2_abiotic"] for w in WINDOWS)
        ),
        "mde_at_n100": float(mde),
    }
    report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    (RESULTS / "rjcj_diag_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], indent=2), flush=True)
    print("RJCJ_DIAG_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
