"""CausalTape-6 -- biotic (Red Queen) vs abiotic (Court Jester) turnover share.

Implements the red-team corrections to the first factorial:

* primary metric is temporal F_ST(w) on per-locus allele frequencies, with a
  closed-form haploid Wright-Fisher drift null built from the *effective*
  breeding number N_e(t) = (sum k)^2 / sum k^2, not from census size;
* the abiotic shock is aperiodic (Poisson, mean 25 generations) so the w-sweep
  cannot alias with a fixed period;
* host mutation, parasite mutation and shock draws use separate RNG forks, so
  the biotic contrast does not perturb the host mutation sequence and the seed
  pairing stays valid; the census is recomputed after mortality;
* a genotype-blind uniform-tax cell (74% of hosts pay the infection cost, no
  parasite) isolates "frequency-dependent selection" from "a uniform energy
  tax". If the uniform tax reproduces the biotic share, the biotic label is
  refused.
"""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

import sys

REPO_SRC = Path(__file__).resolve().parents[1] / "codontrace-genesis" / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from codontrace.rng import RNGManager  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

WORKERS = 4
LOCI = 6
GENOTYPES = 1 << LOCI
HOST_CAP = 400
PARASITE_CAP = 16
PARASITE_POOL = 2
INITIAL_HOSTS = 200
GENERATIONS = 400
INTAKE = 2.0
METABOLISM = 1.0
INFECTION_COST = 0.4
BIRTH_COST = 4.0
START_ENERGY = 2.0
TOLERANCE = 1
HOST_MUTATION = 0.02
PARASITE_MUTATION = 0.08
MORTALITY = 0.10
SHOCK_MEAN_INTERVAL = 25
SHOCK_FACTOR = 4.0
TAX_FRACTION = 0.74
WINDOWS = (5, 10, 20, 25, 50)
SEEDS = tuple(range(7000, 7100))
POWERS = 1 << np.arange(LOCI)


def _genotype_index(row: np.ndarray) -> int:
    return int(row @ POWERS)


def _mutate(genomes: np.ndarray, stream: RNGManager, index: np.ndarray, rate: float) -> np.ndarray:
    if index.size == 0:
        return genomes
    draws = np.array([[stream.random() for _ in range(genomes.shape[1])] for _ in index])
    genomes[np.ix_(index, np.arange(genomes.shape[1]))] ^= (draws < rate).astype(genomes.dtype)
    return genomes


def run_world(
    seed: int,
    *,
    parasite: bool,
    shock: bool,
    uniform_tax: bool = False,
    generations: int = GENERATIONS,
) -> dict:
    root = RNGManager(seed=seed).fork("rjcj")
    host_stream = root.fork("host")
    par_stream = root.fork("parasite")
    shock_stream = root.fork("shock")
    rng = np.random.default_rng(seed)

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

    allele_freq = np.zeros((generations, LOCI))
    census = np.zeros(generations)
    breeding = np.zeros(generations)
    infected_series = np.zeros(generations)
    energy_total = float(host_energy[host_alive].sum())
    ledger_residual = 0.0

    for generation in range(generations):
        alive = np.flatnonzero(host_alive)
        if alive.size == 0:
            census[generation] = 0.0
            continue

        intake = INTAKE
        if shock and shock_stream.random() < 1.0 / SHOCK_MEAN_INTERVAL:
            intake = INTAKE * SHOCK_FACTOR
        before = energy_total
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
        infected_series[generation] = float(infected[alive].mean()) if alive.size else 0.0

        eligible = host_alive & (host_energy >= BIRTH_COST)
        offspring_counts = np.zeros(HOST_CAP)
        if eligible.any():
            eligible_idx = np.flatnonzero(eligible)
            ranked = eligible_idx[np.argsort(-host_energy[eligible_idx], kind="stable")]
            free = np.flatnonzero(~host_alive)
            n_births = min(ranked.size, free.size)
            parents = ranked[:n_births]
            child_slots = free[:n_births]
            children = host_genome[parents].copy()
            children = _mutate(children, host_stream, np.arange(n_births), HOST_MUTATION)
            host_energy[parents] -= BIRTH_COST
            host_genome[child_slots] = children
            host_energy[child_slots] = START_ENERGY
            host_alive[child_slots] = True
            offspring_counts = np.bincount(parents, minlength=HOST_CAP).astype(float)

        bankrupt = host_alive & (host_energy < 0.0)
        host_energy[bankrupt] = 0.0
        host_alive[bankrupt] = False
        mortal = host_alive & (rng.random(HOST_CAP) < MORTALITY)
        host_energy[mortal] = 0.0
        host_alive[mortal] = False

        alive_after = np.flatnonzero(host_alive)
        energy_total = float(host_energy[host_alive].sum())
        ledger_residual = max(ledger_residual, abs(energy_total - (before + intake * alive.size - METABOLISM * alive.size - INFECTION_COST * int(infected.sum()) - BIRTH_COST * offspring_counts.sum() + START_ENERGY * offspring_counts.sum())))
        census[generation] = alive_after.size
        total_offspring = offspring_counts.sum()
        breeder_counts = offspring_counts[offspring_counts > 0]
        breeding[generation] = (
            float(total_offspring**2 / (breeder_counts**2).sum()) if breeder_counts.size else 0.0
        )

        if alive_after.size:
            allele_freq[generation] = host_genome[alive_after].mean(axis=0)
        else:
            allele_freq[generation] = np.nan

        if parasite:
            par = np.flatnonzero(parasite_alive)
            if par.size and alive_after.size:
                distances = (host_genome[alive_after, None, :] != parasite_genome[None, par, :]).sum(axis=2)
                success = (distances <= TOLERANCE).sum(axis=0)
                survivors = par[success > 0]
                if survivors.size == 0:
                    parasite_genome[par] = _mutate(
                        parasite_genome[par].copy(), par_stream, np.arange(par.size), PARASITE_MUTATION
                    )
                else:
                    children = np.tile(survivors, int(math.ceil(PARASITE_CAP / survivors.size)))[:PARASITE_CAP]
                    parasite_genome = _mutate(
                        parasite_genome[children].copy(), par_stream, np.arange(PARASITE_CAP), PARASITE_MUTATION
                    )
                    parasite_alive[:] = True

    windows = {}
    for w in WINDOWS:
        observed = []
        nulls = []
        for t in range(0, generations - w):
            p1 = allele_freq[t]
            p2 = allele_freq[t + w]
            if np.isnan(p1).any() or np.isnan(p2).any():
                continue
            pbar = 0.5 * (p1 + p2)
            denom = pbar * (1.0 - pbar)
            valid = denom > 0
            if valid.any():
                observed.append(float(np.mean(((p2 - p1) ** 2)[valid] / denom[valid])))
            ne = breeding[t : t + w]
            ne = ne[ne > 0]
            if ne.size:
                nulls.append(float(1.0 - np.prod(1.0 - 1.0 / ne)))
        windows[str(w)] = {
            "fst_mean": float(np.mean(observed)) if observed else 0.0,
            "drift_null_mean": float(np.mean(nulls)) if nulls else 0.0,
        }
        windows[str(w)]["delta_fst"] = windows[str(w)]["fst_mean"] - windows[str(w)]["drift_null_mean"]

    return {
        "seed": seed,
        "parasite": parasite,
        "shock": shock,
        "uniform_tax": uniform_tax,
        "census_mean": float(np.nanmean(census)),
        "breeding_mean": float(np.nanmean(breeding)),
        "infected_mean": float(np.mean(infected_series)),
        "ledger_residual": ledger_residual,
        "windows": windows,
    }


CELLS = (
    {"tag": "b0_s0", "parasite": False, "shock": False},
    {"tag": "b1_s0", "parasite": True, "shock": False},
    {"tag": "b0_s1", "parasite": False, "shock": True},
    {"tag": "b1_s1", "parasite": True, "shock": True},
    {"tag": "tax_s0", "parasite": False, "shock": False, "uniform_tax": True},
    {"tag": "tax_s1", "parasite": False, "shock": True, "uniform_tax": True},
)


def _task(spec: dict, seed: int) -> dict:
    kwargs = {k: v for k, v in spec.items() if k != "tag"}
    return run_world(seed, **kwargs)


def main() -> int:
    started = time.perf_counter()
    report: dict = {"experiment": "CausalTape-6", "workers": WORKERS, "seeds": len(SEEDS), "cells": {}}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for spec in CELLS:
            rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
            report["cells"][spec["tag"]] = {
                "census_mean": float(np.mean([r["census_mean"] for r in rows])),
                "breeding_mean": float(np.mean([r["breeding_mean"] for r in rows])),
                "infected_mean": float(np.mean([r["infected_mean"] for r in rows])),
                "ledger_max_residual": float(np.max([r["ledger_residual"] for r in rows])),
                "windows": {
                    str(w): {
                        "delta_fst_mean": float(np.mean([r["windows"][str(w)]["delta_fst"] for r in rows])),
                        "delta_fst_sd": float(np.std([r["windows"][str(w)]["delta_fst"] for r in rows])),
                        "per_seed": [r["windows"][str(w)]["delta_fst"] for r in rows],
                    }
                    for w in WINDOWS
                },
            }
            cell = report["cells"][spec["tag"]]
            print(
                f"{spec['tag']:<8} census={cell['census_mean']:.0f} N_e={cell['breeding_mean']:.1f} "
                f"infected={cell['infected_mean']:.2f} ledger={cell['ledger_max_residual']:.1e} "
                + " ".join(f"dFst{w}={cell['windows'][str(w)]['delta_fst_mean']:+.4f}" for w in WINDOWS),
                flush=True,
            )

    def series(tag: str, w: int) -> np.ndarray:
        return np.array(report["cells"][tag]["windows"][str(w)]["per_seed"])

    rng = np.random.default_rng(17)

    def ci(diff: np.ndarray) -> list[float]:
        idx = rng.integers(0, diff.size, size=(2000, diff.size))
        return [float(np.percentile(diff[idx].mean(axis=1), 2.5)), float(np.percentile(diff[idx].mean(axis=1), 97.5))]

    verdicts: dict = {"window_curves": {}}
    for w in WINDOWS:
        biotic = series("b1_s0", w) - series("b0_s0", w)
        abiotic = series("b0_s1", w) - series("b0_s0", w)
        interaction = (series("b1_s1", w) - series("b1_s0", w)) - (series("b0_s1", w) - series("b0_s0", w))
        tax = series("tax_s0", w) - series("b0_s0", w)
        verdicts["window_curves"][str(w)] = {
            "biotic_effect": {"mean": float(biotic.mean()), "ci": ci(biotic)},
            "abiotic_effect": {"mean": float(abiotic.mean()), "ci": ci(abiotic)},
            "interaction": {"mean": float(interaction.mean()), "ci": ci(interaction)},
            "uniform_tax_effect": {"mean": float(tax.mean()), "ci": ci(tax)},
            "biotic_share_of_abs_total": float(
                abs(biotic.mean()) / max(abs(biotic.mean()) + abs(abiotic.mean()), 1e-12)
            ),
            "ranking_is_biotic_dominant": bool(abs(biotic.mean()) > abs(abiotic.mean())),
            "uniform_tax_reproduces_biotic": bool(
                tax.mean() >= 0.5 * biotic.mean() and tax.mean() > 0
            ),
        }

    ranks = [verdicts["window_curves"][str(w)]["ranking_is_biotic_dominant"] for w in WINDOWS]
    shares = [verdicts["window_curves"][str(w)]["biotic_share_of_abs_total"] for w in WINDOWS]
    verdicts["claim"] = {
        "ranking_stable_across_windows": bool(len(set(ranks)) == 1),
        "share_range": [min(shares), max(shares)],
        "uniform_tax_control_passes": bool(
            not any(verdicts["window_curves"][str(w)]["uniform_tax_reproduces_biotic"] for w in WINDOWS)
        ),
    }
    report["verdicts"] = verdicts
    report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    (RESULTS / "rjcj_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"]["claim"], indent=2), flush=True)
    print("RJCJ_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

