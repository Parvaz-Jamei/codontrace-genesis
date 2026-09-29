"""CausalTape-7 -- phase diagram for the maintenance of costly sex.

The single-cell factorial said the two-fold cost is not recovered by an
antagonist that turns over once per host generation. The published mechanisms
that actually drive pro-recombination outcomes are a short antagonist generation
time and a severe cost to the antagonist of failing to infect. Both are knobs
here, so the question becomes a phase diagram rather than a yes/no:

    for which (antagonist generations per host generation, infection cost,
    cost ratio) is sexual reproduction maintained?

Axes
    turnover       antagonist generations per host generation: 1, 2, 4
    infection_cost 0.4, 0.9, 1.4
    cost_ratio     1.0, 1.5, 2.0, 3.0
    plus a costless reference and an antagonist-free reference per turnover

Outcome
    mean sexual frequency over the last quarter of the run, and the fraction of
    seeds in which sex is extinct, at 200 paired seeds per cell.

Runtime, measured: about 1.1-1.9 s per 400-generation run at four workers.
"""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

import sex_arms as S
from telemetry import Telemetry, _jsonable

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TELEM = HERE / "runs"
RESULTS.mkdir(exist_ok=True)

WORKERS = 4
TURNOVERS = (1, 3, 6, 12)
INFECTION_COSTS = (0.4, 0.9, 1.6, 2.4)
COST_RATIOS = (1.0, 1.25, 1.5, 1.75, 2.0, 3.0)
SEEDS = tuple(range(8000, 8200))
GENERATIONS = 400
FAIL_DEATH = 0.9  # probability an antagonist that infects nobody dies this generation
PARASITE_MUTATION = 0.02  # 0.08 at six loci puts ~38% of offspring two matches away


def run_phase(
    seed: int,
    *,
    turnover: int,
    infection_cost: float,
    cost_ratio: float,
    antagonist: bool = True,
    fail_death: float = FAIL_DEATH,
    parasite_mutation: float = PARASITE_MUTATION,
    generations: int = GENERATIONS,
) -> dict:
    """One run with antagonist generations nested inside each host generation."""

    import numpy as np

    from codontrace.rng import RNGManager

    root = RNGManager(seed=seed).fork("phase")
    host_stream = root.fork("host")
    par_stream = root.fork("parasite")
    rng = np.random.default_rng(seed)

    loci = S.LOCI
    host_genome = np.zeros((S.HOST_CAP, loci), dtype=np.int8)
    host_energy = np.zeros(S.HOST_CAP, dtype=float)
    host_sexual = np.zeros(S.HOST_CAP, dtype=bool)
    host_alive = np.zeros(S.HOST_CAP, dtype=bool)
    slots = rng.permutation(S.HOST_CAP)[: S.INITIAL_HOSTS]
    host_alive[slots] = True
    host_energy[slots] = S.BIRTH_COST * 0.6
    host_genome[slots] = rng.integers(0, 2, size=(S.INITIAL_HOSTS, loci)).astype(np.int8)
    for row in rng.choice(slots, size=S.INVADERS, replace=False):
        host_sexual[row] = True

    par_genome = rng.integers(0, 2, size=(S.PARASITE_CAP, loci)).astype(np.int8)
    par_alive = np.zeros(S.PARASITE_CAP, dtype=bool)
    par_alive[: S.PARASITE_POOL] = True

    ledger = S.Ledger(float(host_energy[host_alive].sum()))
    sexual_series: list[float] = []
    infected_series: list[float] = []
    extinction = -1

    for generation in range(generations):
        alive = np.flatnonzero(host_alive)
        if alive.size == 0:
            sexual_series.append(0.0)
            infected_series.append(0.0)
            continue

        host_energy[host_alive] += S.INTAKE
        ledger.intake += S.INTAKE * alive.size
        host_energy[host_alive] -= S.METABOLISM
        ledger.metabolism += S.METABOLISM * alive.size

        infected = np.zeros(S.HOST_CAP, dtype=bool)
        if antagonist:
            for _ in range(turnover):
                par = np.flatnonzero(par_alive)
                if par.size and alive.size:
                    distances = (
                        host_genome[alive, None, :] != par_genome[None, par, :]
                    ).sum(axis=2)
                    hits = distances <= S.MATCH_TOLERANCE
                    if _ == 0:
                        infected[alive] = hits.any(axis=1)
                    success = hits.sum(axis=0)
                    survivors = par[success > 0]
                    failed = par[success == 0]
                    if failed.size:
                        dies = rng.random(failed.size) < fail_death
                        par_alive[failed[dies]] = False
                    if survivors.size:
                        if survivors.size >= S.PARASITE_CAP:
                            # Never truncate the surviving genotypes: a plain
                            # tile-and-slice drops infecting antagonists whenever
                            # more than PARASITE_CAP of them survive.
                            children = rng.permutation(survivors)[: S.PARASITE_CAP]
                        else:
                            children = np.tile(
                                survivors, int(math.ceil(S.PARASITE_CAP / survivors.size))
                            )[: S.PARASITE_CAP]
                        par_genome = S._mutate(
                            par_genome[children].copy(),
                            par_stream,
                            np.arange(S.PARASITE_CAP),
                            parasite_mutation,
                        )
                        par_alive[:] = True
                    elif not par_alive.any():
                        revive = rng.permutation(S.PARASITE_CAP)[: S.PARASITE_POOL]
                        par_genome[revive] = rng.integers(0, 2, size=(revive.size, loci))
                        par_alive[revive] = True
        if infected.any():
            host_energy[infected] -= infection_cost
            ledger.infection += infection_cost * int(infected.sum())

        unit = np.where(
            host_sexual, S.BIRTH_COST * cost_ratio * 1.0, S.BIRTH_COST
        )
        eligible = host_alive & (host_energy >= unit)
        if eligible.any():
            eligible_idx = np.flatnonzero(eligible)
            ranked = eligible_idx[np.argsort(-host_energy[eligible_idx], kind="stable")]
            free = np.flatnonzero(~host_alive)
            n_births = min(ranked.size, free.size)
            parents = ranked[:n_births]
            child_slots = free[:n_births]
            children = host_genome[parents].copy()
            sexual_parents = parents[host_sexual[parents]]
            if sexual_parents.size:
                for offset, parent in enumerate(parents):
                    if not host_sexual[parent]:
                        continue
                    mate = sexual_parents[int(host_stream.randrange(sexual_parents.size))]
                    picks = np.array([host_stream.randrange(2) for _ in range(loci)])
                    children[offset] = np.where(picks == 0, host_genome[parent], host_genome[mate])
            children = S._mutate(children, host_stream, np.arange(n_births), S.MUTATION_RATE)
            paid = unit[parents]
            host_energy[parents] -= paid
            ledger.births += float(paid.sum())
            host_genome[child_slots] = children
            host_energy[child_slots] = S.START_ENERGY
            host_sexual[child_slots] = host_sexual[parents]
            host_alive[child_slots] = True
            ledger.offspring += S.START_ENERGY * n_births

        bankrupt = host_alive & (host_energy < 0.0)
        ledger.deaths += float(host_energy[bankrupt].sum())
        host_energy[bankrupt] = 0.0
        host_alive[bankrupt] = False
        mortal = host_alive & (rng.random(S.HOST_CAP) < S.MORTALITY)
        ledger.deaths += float(host_energy[mortal].sum())
        host_energy[mortal] = 0.0
        host_alive[mortal] = False
        ledger.check(float(host_energy[host_alive].sum()))

        alive_now = np.flatnonzero(host_alive)
        freq = float(host_sexual[alive_now].mean()) if alive_now.size else 0.0
        sexual_series.append(freq)
        infected_series.append(float(infected[alive_now].mean()) if alive_now.size else 0.0)
        if extinction < 0 and freq == 0.0:
            extinction = generation

    tail = int(generations * 0.25)
    return {
        "seed": seed,
        "turnover": turnover,
        "infection_cost": infection_cost,
        "cost_ratio": cost_ratio,
        "antagonist": antagonist,
        "sexual_final": float(np.mean(sexual_series[-tail:])),
        "sexual_auc": float(np.mean(sexual_series)),
        "extinct": extinction >= 0,
        "extinction_generation": extinction,
        "infected_mean": float(np.mean(infected_series)),
        "ledger_residual": ledger.max_residual,
    }


def _task(spec: dict, seed: int) -> dict:
    return run_phase(seed, **spec)


def cell_key(spec: dict) -> str:
    tag = "ant" if spec["antagonist"] else "noant"
    return f"t{spec['turnover']}_ic{spec['infection_cost']}_c{spec['cost_ratio']}_{tag}"


def main() -> int:
    started = time.time()
    cells: list[dict] = []
    for turnover in TURNOVERS:
        for infection_cost in INFECTION_COSTS:
            for cost_ratio in COST_RATIOS:
                cells.append(
                    {
                        "turnover": turnover,
                        "infection_cost": infection_cost,
                        "cost_ratio": cost_ratio,
                        "antagonist": True,
                    }
                )
            cells.append(
                {
                    "turnover": turnover,
                    "infection_cost": infection_cost,
                    "cost_ratio": 2.0,
                    "antagonist": False,
                }
            )

    report: dict = {
        "experiment": "CausalTape-7 phase diagram",
        "workers": WORKERS,
        "seeds_per_cell": len(SEEDS),
        "generations": GENERATIONS,
        "axes": {"turnover": TURNOVERS, "infection_cost": INFECTION_COSTS, "cost_ratio": COST_RATIOS},
        "cells": {},
    }
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for spec in cells:
            key = cell_key(spec)
            tele = Telemetry(TELEM, "phase", key, spec)
            tele.event(event="cell_start", **spec, seeds=len(SEEDS))
            t0 = time.time()
            rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
            final = np.array([r["sexual_final"] for r in rows])
            summary = {
                **spec,
                "sexual_final_mean": float(final.mean()),
                "sexual_final_sd": float(final.std()),
                "extinct_fraction": float(np.mean([r["extinct"] for r in rows])),
                "infected_mean": float(np.mean([r["infected_mean"] for r in rows])),
                "ledger_max_residual": float(np.max([r["ledger_residual"] for r in rows])),
                "seconds": round(time.time() - t0, 1),
                "per_seed": final.tolist(),
            }
            report["cells"][key] = summary
            tele.close(_jsonable(summary))
            print(
                f"{key:<26} sexual={summary['sexual_final_mean']:.4f} "
                f"extinct={summary['extinct_fraction']:.2f} infected={summary['infected_mean']:.2f} "
                f"({summary['seconds']}s)",
                flush=True,
            )
            (RESULTS / "phase_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    antagonist_cells = {k: v for k, v in report["cells"].items() if v["antagonist"]}
    survivors = {
        k: v["sexual_final_mean"]
        for k, v in antagonist_cells.items()
        if v["sexual_final_mean"] > 0.05 and v["cost_ratio"] > 1.0
    }
    report["verdicts"] = {
        "cells_where_costly_sex_persists": survivors,
        "any_rescue": bool(survivors),
        "max_cost_ratio_with_rescue": max(
            [v["cost_ratio"] for k, v in antagonist_cells.items() if v["sexual_final_mean"] > 0.05 and v["cost_ratio"] > 1.0],
            default=None,
        ),
        "costless_reference": {
            k: v["sexual_final_mean"] for k, v in antagonist_cells.items() if v["cost_ratio"] == 1.0
        },
        "no_antagonist_reference": {
            k: v["sexual_final_mean"] for k, v in report["cells"].items() if not v["antagonist"]
        },
        "best_rescue_ratio": max(
            [
                v["sexual_final_mean"]
                for v in antagonist_cells.values()
                if v["cost_ratio"] > 1.0
            ],
            default=0.0,
        ),
    }
    report["elapsed_seconds"] = round(time.time() - started, 1)
    (RESULTS / "phase_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], indent=2), flush=True)
    print("PHASE_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

