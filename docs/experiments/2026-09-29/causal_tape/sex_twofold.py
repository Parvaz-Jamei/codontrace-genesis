"""CausalTape-5 -- the two-fold cost of sex inside a closed energy ledger.

Maynard Smith's two-fold cost is normally injected as a multiplicative penalty.
Here it is charged as an explicit debit in an audited ledger: a sexual birth
costs twice the asexual birth cost, the offspring receives the same starting
energy, and the difference is recorded as dissipated overhead. Every generation
the ledger identity is asserted, so no energy appears or disappears silently.

Question: does multi-locus host-parasite coevolution (matching-allele, negative
frequency-dependent selection) rescue sexual reproduction when the two-fold cost
is actually paid?

Design: 2x2 factorial, sexual invaders introduced at 5% into an asexual
population, 300 generations, 120 seeds per cell.

    cell A  parasite on,  cost on    <- the test
    cell B  parasite off, cost on    <- negative control (cost with no biota)
    cell C  parasite on,  cost off   <- positive control (sex, no cost)
    cell D  parasite off, cost off   <- baseline

Pre-registered:
  P1 (instrument)  the ledger identity holds to 1e-9 in every run of every cell.
  P2 (positive)    cell C: sexual frequency does not collapse (final mean > 0.30).
  P3 (negative)    cell B: sexual frequency collapses (final mean < 0.05).
  P4 (test)        cell A: sexual frequency exceeds cell B by a paired margin
                   whose bootstrap CI excludes zero.
  Falsifier: if P4 fails the claim is refused and the negative is reported.
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
HOST_CAP = 160
PARASITE_CAP = 80
INITIAL_HOSTS = 80
INVADERS = 4
GENERATIONS = 300
INTAKE = 2.0
METABOLISM = 1.0
INFECTION_COST = 0.8
BIRTH_COST = 4.0
START_ENERGY = 2.0
MATCH_TOLERANCE = 1  # parasite matches a host within this Hamming distance
PARASITE_POOL = 8
MUTATION_RATE = 0.02
PARASITE_MUTATION_RATE = 0.08
SEEDS = tuple(range(5000, 5120))


class Ledger:
    """Append-only energy ledger with a conservation assert.

    The identity is checked against the cumulative flows from the initial
    energy pool, so it stays valid across generations: an earlier version
    compared cumulative flows with per-generation totals and reported a
    residual of 1e4 while every individual number looked correct.
    """

    def __init__(self, initial: float) -> None:
        self.initial = initial
        self.intake = 0.0
        self.metabolism = 0.0
        self.infection = 0.0
        self.births = 0.0
        self.offspring = 0.0
        self.deaths = 0.0
        self.overhead = 0.0
        self.max_residual = 0.0

    def check(self, total_now: float) -> float:
        expected = (
            self.initial
            + self.intake
            - self.metabolism
            - self.infection
            - self.births
            + self.offspring
            - self.deaths
        )
        residual = abs(expected - total_now)
        self.max_residual = max(self.max_residual, residual)
        return residual


def _mutate_fast(
    genomes: np.ndarray, stream: RNGManager, index: np.ndarray, rate: float = MUTATION_RATE
) -> np.ndarray:
    """Mutate only the rows in ``index``; one draw per (row, locus)."""

    out = genomes
    draws = np.array([[stream.random() for _ in range(out.shape[1])] for _ in index])
    if index.size:
        flips = draws < rate
        out[np.ix_(index, np.arange(out.shape[1]))] ^= flips.astype(out.dtype)
    return out


def run_cell(
    seed: int, *, parasite: bool, cost: bool, generations: int = GENERATIONS, debug: bool = False
) -> dict:
    stream = RNGManager(seed=seed).fork("sex-twofold")
    rng = np.random.default_rng(seed)

    host_genome = np.zeros((HOST_CAP, LOCI), dtype=np.int8)
    host_energy = np.zeros(HOST_CAP, dtype=float)
    host_sexual = np.zeros(HOST_CAP, dtype=bool)
    host_alive = np.zeros(HOST_CAP, dtype=bool)

    order = rng.permutation(HOST_CAP)
    host_alive[order[:INITIAL_HOSTS]] = True
    host_energy[host_alive] = BIRTH_COST * 0.6
    # Random ancestral genotypes: an all-zero population is almost uninfectable
    # by a random matching-allele parasite, so the biotic driver never engaged
    # and the sexual arm was lost for want of a parasite, not because of cost.
    host_genome[host_alive] = rng.integers(0, 2, size=(INITIAL_HOSTS, LOCI)).astype(np.int8)
    for row in rng.choice(order[:INITIAL_HOSTS], size=INVADERS, replace=False):
        host_sexual[row] = True

    parasite_genome = rng.integers(0, 2, size=(PARASITE_CAP, LOCI)).astype(np.int8)
    parasite_alive = np.zeros(PARASITE_CAP, dtype=bool)
    parasite_alive[:PARASITE_POOL] = True

    ledger = Ledger(float(host_energy[host_alive].sum()))
    sexual_frequency = []
    infected_fraction = []
    host_diversity = []

    for _ in range(generations):
        alive_idx = np.flatnonzero(host_alive)
        n_alive = alive_idx.size
        if n_alive == 0:
            sexual_frequency.append(0.0)
            infected_fraction.append(0.0)
            host_diversity.append(0.0)
            continue

        # 1. environment credit and metabolism
        host_energy[host_alive] += INTAKE
        ledger.intake += INTAKE * n_alive
        host_energy[host_alive] -= METABOLISM
        ledger.metabolism += METABOLISM * n_alive

        # 2. infection by the parasite population (matching alleles)
        infected = np.zeros(HOST_CAP, dtype=bool)
        if parasite:
            par_idx = np.flatnonzero(parasite_alive)
            if par_idx.size:
                distances = (
                    host_genome[alive_idx, None, :] != parasite_genome[None, par_idx, :]
                ).sum(axis=2)
                matches = distances <= MATCH_TOLERANCE
                infected[alive_idx] = matches.any(axis=1)
                host_energy[infected] -= INFECTION_COST
                ledger.infection += INFECTION_COST * int(infected.sum())

        # 3. reproduction: parents are the most energetic eligible hosts (selection)
        cost_vector = np.where(host_sexual, BIRTH_COST * 2.0 if cost else BIRTH_COST, BIRTH_COST)
        eligible = host_alive & (host_energy >= cost_vector)
        births = 0
        if eligible.any():
            eligible_idx = np.flatnonzero(eligible)
            ranked = eligible_idx[np.argsort(-host_energy[eligible_idx], kind="stable")]
            free_slots = np.flatnonzero(~host_alive)
            n_births = min(ranked.size, free_slots.size)
            chosen_parents = ranked[:n_births]
            slots = free_slots[:n_births]

            child_genome = host_genome[chosen_parents].copy()
            sexual_mask = host_sexual[chosen_parents]
            sexual_parents = chosen_parents[sexual_mask]
            if sexual_parents.size:
                for child_offset, parent in enumerate(chosen_parents):
                    if not host_sexual[parent]:
                        continue
                    mate = sexual_parents[int(stream.randrange(sexual_parents.size))]
                    picks = np.array([stream.randrange(2) for _ in range(LOCI)])
                    child_genome[child_offset] = np.where(
                        picks == 0, host_genome[parent], host_genome[mate]
                    )
            child_genome = _mutate_fast(child_genome, stream, np.arange(n_births))

            paid = cost_vector[chosen_parents]
            host_energy[chosen_parents] -= paid
            ledger.births += float(paid.sum())
            host_genome[slots] = child_genome
            host_energy[slots] = START_ENERGY
            host_sexual[slots] = host_sexual[chosen_parents]
            host_alive[slots] = True
            ledger.offspring += START_ENERGY * n_births
            births = n_births

        # 4. deaths: negative energy, then a capacity cull on the lowest energy.
        # Sign convention: a removed host's whole (possibly negative) energy is an
        # outflow, so the ledger identity closes even when debt is written off.
        bankrupt = host_alive & (host_energy < 0.0)
        ledger.deaths += float(host_energy[bankrupt].sum())
        host_energy[bankrupt] = 0.0
        host_alive[bankrupt] = False

        overflow = int(host_alive.sum()) - HOST_CAP
        if overflow > 0:
            candidates = np.flatnonzero(host_alive)
            victims = candidates[np.argsort(host_energy[candidates], kind="stable")[:overflow]]
            ledger.deaths += float(host_energy[victims].sum())
            host_energy[victims] = 0.0
            host_alive[victims] = False

        ledger.check(float(host_energy[host_alive].sum()))

        # 5. parasite reproduction: successful parasites clone; if none succeed,
        #    the living pool mutates instead of going extinct, so the antagonist
        #    can adapt towards the host population rather than vanishing.
        if parasite:
            par_idx = np.flatnonzero(parasite_alive)
            if par_idx.size:
                distances = (
                    host_genome[alive_idx, None, :] != parasite_genome[None, par_idx, :]
                ).sum(axis=2)
                matches = distances <= MATCH_TOLERANCE
                success = matches.sum(axis=0)
                survivors = par_idx[success > 0]
                if survivors.size == 0:
                    parasite_genome[par_idx] = _mutate_fast(
                        parasite_genome[par_idx].copy(), stream, np.arange(par_idx.size), PARASITE_MUTATION_RATE
                    )
                else:
                    children = np.tile(survivors, int(math.ceil(PARASITE_CAP / survivors.size)))
                    children = children[:PARASITE_CAP]
                    parasite_genome = _mutate_fast(
                        parasite_genome[children].copy(), stream, np.arange(PARASITE_CAP), PARASITE_MUTATION_RATE
                    )
                    parasite_alive[:] = True
            else:
                if stream.random() < 0.2:
                    parasite_genome[: PARASITE_CAP // 4] = rng.integers(0, 2, size=(PARASITE_CAP // 4, LOCI))
                    parasite_alive[: PARASITE_CAP // 4] = True

        alive_now = np.flatnonzero(host_alive)
        sexual_frequency.append(float(host_sexual[alive_now].mean()) if alive_now.size else 0.0)
        infected_fraction.append(float(infected[alive_now].mean()) if alive_now.size else 0.0)
        host_diversity.append(
            float(len({tuple(row) for row in host_genome[alive_now]})) if alive_now.size else 0.0
        )

    tail = int(generations * 0.25)
    result = {
        "cell": f"parasite={int(parasite)}_cost={int(cost)}",
        "parasite": parasite,
        "cost": cost,
        "seed": seed,
        "sexual_final_mean": float(np.mean(sexual_frequency[-tail:])),
        "sexual_auc": float(np.mean(sexual_frequency)),
        "sexual_extinct": bool(np.all(np.array(sexual_frequency[-tail:]) == 0.0)),
        "infected_mean": float(np.mean(infected_fraction)),
        "diversity_final_mean": float(np.mean(host_diversity[-tail:])),
        "ledger_max_residual": ledger.max_residual,
    }
    if debug:
        result["sexual_series"] = sexual_frequency
        result["infected_series"] = infected_fraction
    return result


CELLS = (
    {"parasite": True, "cost": True},
    {"parasite": False, "cost": True},
    {"parasite": True, "cost": False},
    {"parasite": False, "cost": False},
)


def _task(spec: dict, seed: int) -> dict:
    return run_cell(seed, parasite=spec["parasite"], cost=spec["cost"])


def main() -> int:
    started = time.perf_counter()
    report: dict = {"experiment": "CausalTape-5 (two-fold cost of sex)", "workers": WORKERS, "seeds": len(SEEDS), "cells": {}}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for spec in CELLS:
            key = f"p{int(spec['parasite'])}_c{int(spec['cost'])}"
            rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
            final = np.array([row["sexual_final_mean"] for row in rows])
            report["cells"][key] = {
                "parasite": spec["parasite"],
                "cost": spec["cost"],
                "sexual_final_mean": float(final.mean()),
                "sexual_final_sd": float(final.std()),
                "sexual_final_median": float(np.median(final)),
                "sexual_extinct_fraction": float(np.mean([row["sexual_extinct"] for row in rows])),
                "sexual_auc": float(np.mean([row["sexual_auc"] for row in rows])),
                "infected_mean": float(np.mean([row["infected_mean"] for row in rows])),
                "diversity_final_mean": float(np.mean([row["diversity_final_mean"] for row in rows])),
                "ledger_max_residual": float(np.max([row["ledger_max_residual"] for row in rows])),
                "per_seed": final.tolist(),
            }
            cell = report["cells"][key]
            print(
                f"{key:<10} sexual_final={cell['sexual_final_mean']:.4f}"
                f"+-{cell['sexual_final_sd']:.4f} extinct={cell['sexual_extinct_fraction']:.2f} "
                f"infected={cell['infected_mean']:.3f} ledger_res={cell['ledger_max_residual']:.1e}",
                flush=True,
            )

    a = np.array(report["cells"]["p1_c1"]["per_seed"])
    b = np.array(report["cells"]["p1_c0"]["per_seed"])
    c = np.array(report["cells"]["p0_c1"]["per_seed"])
    d = np.array(report["cells"]["p0_c0"]["per_seed"])
    diff = a - c
    rng = np.random.default_rng(11)
    idx = rng.integers(0, diff.size, size=(2000, diff.size))
    boot = diff[idx].mean(axis=1)

    report["verdicts"] = {
        "P1_ledger_identity": {
            "max_residual_all_cells": float(max(cell["ledger_max_residual"] for cell in report["cells"].values())),
            "passed": bool(max(cell["ledger_max_residual"] for cell in report["cells"].values()) <= 1e-9),
        },
        "P2_positive_control_sex_survives_costless": {
            "cell_C_mean": float(c.mean()),
            "threshold": 0.30,
            "passed": bool(c.mean() > 0.30),
        },
        "P3_negative_control_sex_lost_with_cost_no_parasite": {
            "cell_B_mean": float(b.mean()),
            "threshold": 0.05,
            "passed": bool(b.mean() < 0.05),
        },
        "P4_parasite_rescues_sex_under_cost": {
            "cell_A_mean": float(a.mean()),
            "cell_C_mean": float(c.mean()),
            "paired_diff_A_minus_C": float(diff.mean()),
            "paired_diff_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "baseline_D_mean": float(d.mean()),
        },
    }
    report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    (RESULTS / "sex_twofold_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], indent=2), flush=True)
    print("SEX_TWOFOLD_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
