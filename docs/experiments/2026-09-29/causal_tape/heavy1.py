"""Heavy TEST 1 -- exact-ground-truth estimator benchmark at publishable scale.

Scale-up of `scale1.py`: more seeds, both environments on the full grid, extra
epistasis levels, and full telemetry (live JSONL + per-generation snapshots for a
logged subset, summaries for all runs). Resumable: a killed run restarts from the
last completed configuration.

Usage:  python heavy1.py [--seeds N] [--workers K]
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

from harness import build_env, run_tape
from run_benchmark import PILOT_SEEDS
from telemetry import Telemetry, completed_keys, iter_missing
from workers import Cfg, confirm_task, pilot_task
from run_benchmark import top_mutations

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TELEM = HERE / "runs"
RESULTS.mkdir(exist_ok=True)

EPS_GRID = (0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8)
DEPTHS = (20, 40, 80)
ENV_SEEDS = (20260927, 20260928, 20260929)
REFERENCE_EPS = 0.2
ORDER_PERMUTATIONS = 6
LOGGED_RUNS_PER_CONFIG = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=1500)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def config_key(env_seed: int, eps: float, depth: int) -> str:
    return f"e{env_seed}_eps{eps}_G{depth}"


def analyse(rows: list[dict], env, mutations: list[str], threshold: float) -> dict:
    fitness = np.array([r["fitness"] for r in rows])
    y = (fitness >= threshold).astype(float)
    bits = np.array([r["bits"] for r in rows], dtype=float)
    design = np.hstack([np.ones((bits.shape[0], 1)), bits])
    pinv = np.linalg.pinv(design)
    beta_fit = (pinv @ fitness)[1:]
    beta_y = (pinv @ y)[1:]
    order = np.array([np.mean(r["order_effects"]) if r["order_effects"] else 0.0 for r in rows])
    local = np.array([np.mean(r["local_effects"]) if r["local_effects"] else 0.0 for r in rows])
    per_mutation = []
    for index, mid in enumerate(mutations):
        bit = int(mid.split(":")[0])
        counter = np.array([r["counterfactual"][mid] for r in rows])
        has = np.array([mid in r["present"] for r in rows], dtype=bool)
        delta = fitness - counter
        exposed = delta[has]
        if exposed.size:
            rng = np.random.default_rng(101 + index)
            idx = rng.integers(0, exposed.size, size=(1000, exposed.size))
            ci = [float(np.percentile(exposed[idx].mean(axis=1), 2.5)), float(np.percentile(exposed[idx].mean(axis=1), 97.5))]
        else:
            ci = [float("nan"), float("nan")]
        att = float(np.mean(exposed)) if exposed.size else float("nan")
        naive = float(np.mean(fitness[has]) - np.mean(fitness[~has])) if has.any() and (~has).any() else float("nan")
        direct = float(env.weights[bit])
        per_mutation.append(
            {
                "mutation": mid,
                "bit": bit,
                "frequency": float(np.mean(has)),
                "att": att,
                "att_sd": float(np.std(exposed)) if exposed.size else float("nan"),
                "att_ci": ci,
                "ate": float(np.mean(delta)),
                "naive": naive,
                "adjusted": float(beta_fit[bit]),
                "selection_bias": naive - att,
                "specification_bias": float(beta_fit[bit]) - att,
                "tau_direct": direct,
                "tau_epi": att - direct,
                "att_binary": float(np.mean((y - (counter >= threshold).astype(float))[has])) if exposed.size else float("nan"),
                "naive_binary": float(np.mean(y[has]) - np.mean(y[~has])) if has.any() and (~has).any() else float("nan"),
                "adjusted_binary": float(beta_y[bit]),
            }
        )
    return {
        "n": len(rows),
        "innovation_rate": float(np.mean(y)),
        "fitness_mean": float(np.mean(fitness)),
        "fitness_sd": float(np.std(fitness)),
        "order_tau_mean": float(np.mean(order)),
        "order_tau_median_abs": float(np.median(np.abs(order))),
        "order_fraction_nonzero": float(np.mean(order != 0.0)),
        "local_tau_median_abs": float(np.median(np.abs(local))),
        "per_mutation": per_mutation,
    }


def main() -> int:
    args = parse_args()
    confirm_seeds = tuple(range(1000, 1000 + args.seeds))
    started = time.time()
    report: dict = {
        "experiment": "heavy1",
        "workers": args.workers,
        "seeds_per_config": args.seeds,
        "eps_grid": list(EPS_GRID),
        "depths": list(DEPTHS),
        "env_seeds": list(ENV_SEEDS),
        "configs": {},
    }

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for env_seed in ENV_SEEDS:
            thresholds: dict[int, float] = {}
            for depth in DEPTHS:
                ref = Cfg(env_seed=env_seed, eps=REFERENCE_EPS, depth=depth)
                values = list(pool.map(partial(pilot_task, ref), PILOT_SEEDS, chunksize=8))
                thresholds[depth] = float(np.median(values))
            for depth in DEPTHS:
                for eps in EPS_GRID:
                    key = config_key(env_seed, eps, depth)
                    done = completed_keys(TELEM, "heavy1")
                    if key in done:
                        print(f"{key}: already done, skipped", flush=True)
                        continue
                    cfg = Cfg(env_seed=env_seed, eps=eps, depth=depth)
                    env = build_env(eps, env_seed=env_seed)
                    mutations, _ = None, None
                    env_obj = build_env(eps, env_seed=env_seed)
                    pilot_tapes = [run_tape(seed=s, generations=depth, env=env_obj) for s in PILOT_SEEDS]
                    mutations = top_mutations(pilot_tapes)

                    tele = Telemetry(
                        TELEM,
                        "heavy1",
                        key,
                        {"env_seed": env_seed, "eps": eps, "depth": depth, "seeds": args.seeds,
                         "mutations": mutations, "threshold": thresholds[depth]},
                        snapshot_every=5,
                    )
                    tele.event(event="config_start", key=key, mutations=mutations,
                               threshold=thresholds[depth], seeds=args.seeds)
                    t0 = time.time()
                    order_count = ORDER_PERMUTATIONS if depth == 40 else 0
                    todo = [(cfg, s, tuple(mutations), order_count) for s in confirm_seeds]
                    rows: list[dict] = []
                    logged = 0
                    for row in pool.map(confirm_task, todo, chunksize=4):
                        rows.append(row)
                        if logged < LOGGED_RUNS_PER_CONFIG:
                            tele.event(event="run", seed=row["seed"], fitness=row["fitness"],
                                       present=len(row["present"]),
                                       counterfactual=row["counterfactual"])
                            logged += 1
                        if len(rows) % 100 == 0:
                            tele.event(event="progress", completed=len(rows),
                                       elapsed=round(time.time() - t0, 1))
                    summary = analyse(rows, env, mutations, thresholds[depth])
                    report["configs"][key] = summary
                    tele.close(summary)
                    print(
                        f"{key:<24} n={summary['n']} innov={summary['innovation_rate']:.3f} "
                        f"spec_bias={np.median([abs(m['specification_bias']) for m in summary['per_mutation']]):.4f} "
                        f"order={summary['order_tau_median_abs']:.4f} ({round(time.time()-t0,1)}s)",
                        flush=True,
                    )
                    (RESULTS / "heavy1_results.json").write_text(
                        json.dumps(report, indent=2), encoding="utf-8"
                    )

    report["elapsed_seconds"] = round(time.time() - started, 1)
    report["verdicts"] = verdicts(report)
    (RESULTS / "heavy1_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], indent=2), flush=True)
    print("HEAVY1_DONE", flush=True)
    return 0


def verdicts(report: dict) -> dict:
    out = {}
    for env_seed in ENV_SEEDS:
        keys = [k for k in report["configs"] if k.startswith(f"e{env_seed}_") and k.endswith("_G40")]
        if not keys:
            continue
        keys.sort(key=lambda k: float(k.split("_eps")[1].split("_")[0]))
        trend = [float(np.median([abs(m["specification_bias"]) for m in report["configs"][k]["per_mutation"]])) for k in keys]
        k0 = f"e{env_seed}_eps0.0_G40"
        kmax = keys[-1]
        out[f"env{env_seed}"] = {
            "spec_bias_trend": trend,
            "spec_bias_zero_at_eps0": max(abs(m["specification_bias"]) for m in report["configs"][k0]["per_mutation"]) <= 1e-9,
            "spec_bias_monotone": all(b >= a - 1e-9 for a, b in zip(trend, trend[1:])),
            "naive_underestimates_at_eps0": all(m["naive"] < m["att"] for m in report["configs"][k0]["per_mutation"]),
            "att_sd_zero_at_eps0": all(m["att_sd"] <= 1e-12 for m in report["configs"][k0]["per_mutation"]),
            "att_sd_positive_at_max_eps": float(np.median([m["att_sd"] for m in report["configs"][kmax]["per_mutation"]])) > 0.0,
            "tau_epi_zero_at_eps0": max(abs(m["tau_epi"]) for m in report["configs"][k0]["per_mutation"]) <= 1e-9,
            "order_nonzero_configs": [k for k in sorted(keys) if report["configs"][k]["order_fraction_nonzero"] > 0.0],
        }
    return out


if __name__ == "__main__":
    raise SystemExit(main())
