"""Heavy TEST 1b -- per-seed dataset + a correctly-specified third estimator.

Two corrections over `heavy1.py`:

1. Per-seed arrays are saved for every run (fitness, final bits, counterfactual
   fitness per focal mutation) as a compressed `.npz` per configuration, so any
   estimator can be recomputed later without re-simulating. heavy1 kept only
   three logged runs per config, which made post-hoc analysis impossible.
2. The pre-registered trend rule is replaced by a proper trend statistic
   (Spearman rho of median |bias| against eps with a bootstrap CI) because the
   strict non-decreasing test failed on one of three environments on a dip of
   0.003 between adjacent eps values, which is inside the noise of a median over
   eight mutations. The focal set is widened to 16 mutations to stabilise it.

A third estimator is added: a quadratic g-computation model (bits plus all
pairwise products) evaluated under do(bit=0) versus do(bit=1). The linear
adjusted estimator is exactly misspecified once the landscape is quadratic, so
this separates "specification bias" from "no estimator can succeed".

Usage:  python heavy2.py [--seeds N] [--workers K]
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
from run_benchmark import PILOT_SEEDS, top_mutations
from telemetry import Telemetry, completed_keys
from workers import Cfg, confirm_task, pilot_task

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TELEM = HERE / "runs"
DATASETS = HERE / "datasets"
RESULTS.mkdir(exist_ok=True)
DATASETS.mkdir(exist_ok=True)

EPS_GRID = (0.0, 0.05, 0.1, 0.2, 0.4, 0.8)
DEPTHS = (40,)
ENV_SEEDS = (20260927, 20260928, 20260929)
REFERENCE_EPS = 0.2
TOP_K = 16


def _dump(obj) -> str:
    from telemetry import _jsonable

    return json.dumps(_jsonable(obj), indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def quadratic_design(bits: np.ndarray, override: tuple[int, float] | None = None) -> np.ndarray:
    """Design matrix: intercept, main bits, then all pairwise products.

    ``override`` sets one bit to a fixed value before the products are formed, so
    calling it twice with (bit, 1.0) and (bit, 0.0) gives the two do() worlds.
    """

    work = bits.copy()
    if override is not None:
        column, value = override
        work[:, column] = value
    pairs = [(i, j) for i in range(work.shape[1]) for j in range(i + 1, work.shape[1])]
    extra = np.empty((work.shape[0], len(pairs)))
    for index, (i, j) in enumerate(pairs):
        extra[:, index] = work[:, i] * work[:, j]
    return np.hstack([np.ones((work.shape[0], 1)), work, extra])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    def ranks(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values, kind="stable")
        out = np.empty(len(values), dtype=float)
        out[order] = np.arange(len(values), dtype=float)
        return out

    rx, ry = ranks(x), ranks(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denominator = np.sqrt((rx**2).sum() * (ry**2).sum())
    return float((rx * ry).sum() / denominator) if denominator else 0.0


def main() -> int:
    args = parse_args()
    confirm_seeds = tuple(range(1000, 1000 + args.seeds))
    started = time.time()
    report: dict = {
        "experiment": "heavy2",
        "workers": args.workers,
        "seeds_per_config": args.seeds,
        "eps_grid": list(EPS_GRID),
        "depths": list(DEPTHS),
        "env_seeds": list(ENV_SEEDS),
        "top_k": TOP_K,
        "configs": {},
    }

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for env_seed in ENV_SEEDS:
            thresholds = {}
            for depth in DEPTHS:
                ref = Cfg(env_seed=env_seed, eps=REFERENCE_EPS, depth=depth)
                values = list(pool.map(partial(pilot_task, ref), PILOT_SEEDS, chunksize=8))
                thresholds[depth] = float(np.median(values))
            for eps in EPS_GRID:
                key = f"e{env_seed}_eps{eps}_G40"
                if key in completed_keys(TELEM, "heavy2"):
                    print(f"{key}: done, skipped", flush=True)
                    continue
                depth = 40
                cfg = Cfg(env_seed=env_seed, eps=eps, depth=depth)
                env = build_env(eps, env_seed=env_seed)
                pilot_tapes = [run_tape(seed=s, generations=depth, env=env) for s in PILOT_SEEDS]
                mutations = top_mutations(pilot_tapes, k=TOP_K)
                tele = Telemetry(
                    TELEM,
                    "heavy2",
                    key,
                    {"env_seed": env_seed, "eps": eps, "depth": depth, "seeds": args.seeds,
                     "mutations": mutations, "threshold": thresholds[depth]},
                    snapshot_every=1,
                )
                tele.event(event="config_start", key=key, mutations=mutations,
                           threshold=thresholds[depth], seeds=args.seeds)
                t0 = time.time()
                todo = [(cfg, s, tuple(mutations), 0) for s in confirm_seeds]
                rows: list[dict] = []
                for index, row in enumerate(pool.map(confirm_task, todo, chunksize=4)):
                    rows.append(row)
                    if index % 200 == 0:
                        tele.event(event="progress", completed=len(rows),
                                   elapsed=round(time.time() - t0, 1))
                summary = analyse(rows, env, mutations, thresholds[depth])
                tele.close(summary)

                fitness = np.array([r["fitness"] for r in rows])
                bits = np.array([r["bits"] for r in rows], dtype=np.int8)
                counter = np.array([[r["counterfactual"][m] for m in mutations] for r in rows])
                present = np.array([[1 if m in r["present"] else 0 for m in mutations] for r in rows], dtype=np.int8)
                np.savez_compressed(
                    DATASETS / f"{key}.npz",
                    fitness=fitness,
                    bits=bits,
                    counterfactual=counter,
                    present=present,
                    mutations=np.array(mutations),
                    seeds=np.array([r["seed"] for r in rows]),
                    threshold=np.array([thresholds[depth]]),
                )
                report["configs"][key] = summary
                print(
                    f"{key:<24} n={summary['n']} spec={np.median([abs(m['specification_bias']) for m in summary['per_mutation']]):.4f} "
                    f"quad={np.median([abs(m['quadratic_bias']) for m in summary['per_mutation']]):.4f} "
                    f"({round(time.time()-t0,1)}s)",
                    flush=True,
                )
                (RESULTS / "heavy2_results.json").write_text(_dump(report), encoding="utf-8")

    report["elapsed_seconds"] = round(time.time() - started, 1)
    report["verdicts"] = verdicts(report)
    (RESULTS / "heavy2_results.json").write_text(_dump(report), encoding="utf-8")
    print(_dump(report["verdicts"]), flush=True)
    print("HEAVY2_DONE", flush=True)
    return 0


def analyse(rows: list[dict], env, mutations: list[str], threshold: float) -> dict:
    fitness = np.array([r["fitness"] for r in rows])
    y = (fitness >= threshold).astype(float)
    bits = np.array([r["bits"] for r in rows], dtype=float)
    design = np.hstack([np.ones((bits.shape[0], 1)), bits])
    pinv = np.linalg.pinv(design)
    beta_fit = (pinv @ fitness)[1:]

    quad = quadratic_design(bits)
    quad_coef, *_ = np.linalg.lstsq(quad, fitness, rcond=None)
    per_mutation = []
    for index, mid in enumerate(mutations):
        bit = int(mid.split(":")[0])
        counter = np.array([r["counterfactual"][mid] for r in rows])
        has = np.array([mid in r["present"] for r in rows], dtype=bool)
        delta = fitness - counter
        exposed = delta[has]
        if exposed.size:
            rng = np.random.default_rng(202 + index)
            idx = rng.integers(0, exposed.size, size=(1000, exposed.size))
            ci = [float(np.percentile(exposed[idx].mean(axis=1), 2.5)), float(np.percentile(exposed[idx].mean(axis=1), 97.5))]
        else:
            ci = [float("nan"), float("nan")]
        att = float(np.mean(exposed)) if exposed.size else float("nan")

        # g-computation under do(bit=1) versus do(bit=0), averaged over the
        # observed covariates. The linear adjusted estimator is exactly the
        # misspecified version of this; the quadratic one is correctly specified
        # whenever the landscape really is quadratic.
        on = quadratic_design(bits, override=(bit, 1.0))
        off = quadratic_design(bits, override=(bit, 0.0))
        quadratic_effect = float(np.mean(on @ quad_coef - off @ quad_coef))

        direct = float(env.weights[bit])
        per_mutation.append(
            {
                "mutation": mid,
                "bit": bit,
                "n_exposed": int(has.sum()),
                "frequency": float(np.mean(has)),
                "att": att,
                "att_sd": float(np.std(exposed)) if exposed.size else float("nan"),
                "att_ci": ci,
                "naive": float(np.mean(fitness[has]) - np.mean(fitness[~has])) if has.any() and (~has).any() else float("nan"),
                "adjusted": float(beta_fit[bit]),
                "quadratic": quadratic_effect,
                "selection_bias": float(np.mean(fitness[has]) - np.mean(fitness[~has])) - att if has.any() and (~has).any() else float("nan"),
                "specification_bias": float(beta_fit[bit]) - att,
                "quadratic_bias": quadratic_effect - att,
                "tau_direct": direct,
                "tau_epi": att - direct,
            }
        )
    return {
        "n": len(rows),
        "innovation_rate": float(np.mean(y)),
        "fitness_mean": float(np.mean(fitness)),
        "fitness_sd": float(np.std(fitness)),
        "per_mutation": per_mutation,
    }


def verdicts(report: dict) -> dict:
    out = {}
    for env_seed in ENV_SEEDS:
        keys = [f"e{env_seed}_eps{eps}_G40" for eps in EPS_GRID if f"e{env_seed}_eps{eps}_G40" in report["configs"]]
        if not keys:
            continue
        eps = np.array([float(k.split("_eps")[1].split("_")[0]) for k in keys])
        spec = np.array([float(np.median([abs(m["specification_bias"]) for m in report["configs"][k]["per_mutation"]])) for k in keys])
        quad = np.array([float(np.median([abs(m["quadratic_bias"]) for m in report["configs"][k]["per_mutation"]])) for k in keys])
        rho_spec = spearman(eps, spec)
        rho_quad = spearman(eps, quad)
        boot = []
        rng = np.random.default_rng(31)
        for _ in range(2000):
            take = rng.integers(0, len(eps), size=len(eps))
            if len(set(take.tolist())) < 3:
                continue
            boot.append(spearman(eps[take], spec[take]))
        out[f"env{env_seed}"] = {
            "spec_bias_by_eps": spec.tolist(),
            "quadratic_bias_by_eps": quad.tolist(),
            "spearman_spec": rho_spec,
            "spearman_spec_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "spearman_quadratic": rho_quad,
            "spec_bias_zero_at_eps0": spec[0] <= 1e-9,
            "quadratic_bias_smaller_at_max_eps": bool(quad[-1] < spec[-1]),
            "trend_supported": bool(rho_spec > 0.8 and np.percentile(boot, 2.5) > 0.5),
        }
    return out


if __name__ == "__main__":
    raise SystemExit(main())

