"""Parallel HE03 pilot runner: shards seeds across processes to use all cores.

The campaign is a pure seeded loop over (seed, arm), so a seed's records are
independent of every other seed. Workers return the per-seed records and the
parent assembles the same campaign object the sequential path would build.

Usage:
    python tools/run_he03_parallel.py --scale pilot --workers 7 --out artifact.json
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _run_one_arm(payload):
    """Run a single (seed, arm) pair — finest useful unit of work."""
    seed, arm, scale, tick_count, population = payload
    from codontrace.genesis.hard_experiment_03 import _run_arm  # noqa: PLC0415

    record = _run_arm(
        seed=int(seed),
        arm=arm,
        tick_count=int(tick_count),
        population=int(population),
    )
    return int(seed), arm, record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", default="pilot")
    parser.add_argument("--seeds", default="1000-1009")
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--population", type=int, default=None)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    from codontrace.genesis.hard_experiment_03 import (
        PILOT_POPULATION,
        PILOT_TICK_COUNT,
        SMOKE_POPULATION,
        SMOKE_TICK_COUNT,
        RESEARCH_POPULATION,
        RESEARCH_TICK_COUNT,
        default_pilot_seeds,
        default_research_seeds,
        default_smoke_seeds,
        _run_arm,
        ARMS,
    )

    lo, _, hi = args.seeds.partition("-")
    if hi:
        seeds = tuple(range(int(lo), int(hi) + 1))
    elif "," in args.seeds:
        seeds = tuple(int(x) for x in args.seeds.split(","))
    else:
        seeds = (int(args.seeds),)

    if args.ticks is not None:
        ticks = args.ticks
    elif args.scale == "pilot":
        ticks = PILOT_TICK_COUNT
    elif args.scale == "research":
        ticks = RESEARCH_TICK_COUNT
    else:
        ticks = SMOKE_TICK_COUNT

    if args.population is not None:
        pop = args.population
    elif args.scale == "pilot":
        pop = PILOT_POPULATION
    elif args.scale == "research":
        pop = RESEARCH_POPULATION
    else:
        pop = SMOKE_POPULATION

    print(f"scale={args.scale} seeds={seeds[0]}..{seeds[-1]} (n={len(seeds)}) "
          f"ticks={ticks} pop={pop} workers={args.workers} arms={len(ARMS)}")
    print(f"total arm-runs = {len(seeds) * len(ARMS)}")

    started = time.time()
    payloads = [(s, arm, args.scale, ticks, pop) for s in seeds for arm in ARMS]

    if args.workers <= 1:
        results = [_run_one_arm(p) for p in payloads]
    else:
        with mp.get_context("spawn").Pool(processes=args.workers) as pool:
            results = []
            for done, item in enumerate(pool.imap_unordered(_run_one_arm, payloads), 1):
                results.append(item)
                print(f"  [{done}/{len(payloads)}] seed {item[0]} {item[1]} "
                      f"d_sym={item[2].d_sym:.6f} elapsed={time.time() - started:.0f}s",
                      flush=True)

    results.sort(key=lambda r: (r[0], r[1]))
    elapsed = time.time() - started
    print(f"ALL DONE in {elapsed:.1f}s ({elapsed / 60:.1f} min)")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        serialisable = [{"seed": s, "arm": a, **_summarise(rec)} for s, a, rec in results]
        out.write_text(json.dumps(serialisable, indent=2, default=str), encoding="utf-8")
        print(f"wrote {out}")
    return 0


def _summarise(record) -> dict:
    return {
        "arm": record.arm,
        "seed": record.seed,
        "d_sym": record.d_sym,
        "d_task": record.d_task,
        "d_indiv": record.d_indiv,
        "n_task_samples": record.n_task_samples,
        "n_switches": record.n_switches,
        "switch_cost_realized": record.switch_cost_realized,
        "matrix_degenerate": record.matrix_degenerate,
        "mean_terminal_runtime_atp": record.mean_terminal_runtime_atp,
        "isolation_drop": record.isolation_drop,
        "assay_failures": list(record.assay_failures),
        "result_digest": record.result_digest,
    }


if __name__ == "__main__":
    raise SystemExit(main())
