"""CausalTape-4 -- scaled replication of the estimator benchmark.

Fixes the two instrument problems found in the first pass and reruns at a size
that can actually resolve effects:

  * the innovation indicator saturated (rate 0.997-1.000 above depth 20), so the
    threshold is calibrated per environment to the pilot median fitness at the
    reference configuration, which puts the binary outcome near 0.5;
  * focal mutations are chosen from pilot seeds only, and the estimator
    comparison is now reported with the sign hypothesis that the measured
    mechanism implies (naive conditioning UNDER-estimates), rather than the
    first pass's incorrect positive-direction prediction.

Run with 4 worker processes.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

from run_benchmark import PILOT_SEEDS, TOP_K, top_mutations
from harness import build_env, run_tape
from workers import WORKERS, Cfg, ORDER_PERMUTATIONS, confirm_task, pilot_task

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

ENV_SEEDS = (20260927, 20260928)
EPS_GRID = (0.0, 0.05, 0.1, 0.2, 0.4, 0.8)
DEPTHS = (20, 40, 80)
CONFIRM_SEEDS = tuple(range(1000, 1600))  # n = 600
REFERENCE = (0.2, 40)
ORDER_SEEDS_PER_CONFIG = 200


def pilot(cfg: Cfg) -> tuple[list[str], float]:
    env = build_env(cfg.eps, env_seed=cfg.env_seed)
    tapes = [run_tape(seed=seed, generations=cfg.depth, env=env) for seed in PILOT_SEEDS]
    return top_mutations(tapes), float(np.median([tape.fitness for tape in tapes]))


def run_config(pool: ProcessPoolExecutor, cfg: Cfg, threshold: float) -> dict:
    started = time.perf_counter()
    mutations, _ = pilot(cfg)

    args = [
        (cfg, seed, tuple(mutations), ORDER_PERMUTATIONS if cfg.depth == 40 else 0)
        for seed in CONFIRM_SEEDS
    ]
    rows = list(pool.map(confirm_task, args, chunksize=4))

    fitness = np.array([row["fitness"] for row in rows])
    y = (fitness >= threshold).astype(float)
    bits = np.array([row["bits"] for row in rows], dtype=float)
    design = np.hstack([np.ones((bits.shape[0], 1)), bits])
    pinv = np.linalg.pinv(design)
    beta_fit = (pinv @ fitness)[1:]
    beta_y = (pinv @ y)[1:]

    order_array = np.array([np.mean(row["order_effects"]) if row["order_effects"] else 0.0 for row in rows])
    local_array = np.array([np.mean(row["local_effects"]) if row["local_effects"] else 0.0 for row in rows])

    per_mutation = []
    for index, mid in enumerate(mutations):
        bit = int(mid.split(":")[0])
        counter = np.array([row["counterfactual"][mid] for row in rows])
        has = np.array([mid in row["present"] for row in rows], dtype=bool)
        delta = fitness - counter
        delta_y = y - (counter >= threshold).astype(float)

        att = float(np.mean(delta[has]))
        att_sd = float(np.std(delta[has]))
        naive = float(np.mean(fitness[has]) - np.mean(fitness[~has]))
        selection = float(np.mean(counter[has]) - np.mean(counter[~has]))
        tau_direct = None  # filled by the caller for the synthetic substrate
        att_y = float(np.mean(delta_y[has]))
        naive_y = float(np.mean(y[has]) - np.mean(y[~has]))

        # paired bootstrap over the exposed seeds
        exposed = delta[has]
        if exposed.size:
            rng = np.random.default_rng(7 + index)
            idx = rng.integers(0, exposed.size, size=(1000, exposed.size))
            boot_att = exposed[idx].mean(axis=1)
            ci = [float(np.percentile(boot_att, 2.5)), float(np.percentile(boot_att, 97.5))]
        else:
            ci = [float("nan"), float("nan")]
        per_mutation.append(
            {
                "mutation": mid,
                "bit": bit,
                "frequency": float(np.mean(has)),
                "n_exposed": int(has.sum()),
                "att_fitness": att,
                "att_fitness_sd": att_sd,
                "att_fitness_ci": ci,
                "ate_fitness": float(np.mean(delta)),
                "naive_fitness": naive,
                "adjusted_fitness": float(beta_fit[bit]),
                "selection_bias_fitness": naive - att,
                "identity_residual_fitness": abs((naive - att) - selection),
                "specification_bias_fitness": float(beta_fit[bit]) - att,
                "att_binary": att_y,
                "naive_binary": naive_y,
                "adjusted_binary": float(beta_y[bit]),
                "selection_bias_binary": naive_y - att_y,
                "specification_bias_binary": float(beta_y[bit]) - att_y,
            }
        )

    env = build_env(cfg.eps, env_seed=cfg.env_seed)
    for row in per_mutation:
        direct = float(env.weights[row["bit"]])
        row["tau_direct_fitness"] = direct
        row["tau_epi_fitness"] = row["att_fitness"] - direct

    return {
        "env_seed": cfg.env_seed,
        "eps": cfg.eps,
        "depth": cfg.depth,
        "threshold": threshold,
        "n_confirm": len(CONFIRM_SEEDS),
        "innovation_rate": float(np.mean(y)),
        "fitness_mean": float(np.mean(fitness)),
        "fitness_sd": float(np.std(fitness)),
        "order_tau_mean": float(np.mean(order_array)),
        "order_tau_median_abs": float(np.median(np.abs(order_array))),
        "order_fraction_nonzero": float(np.mean(order_array != 0.0)),
        "local_tau_median_abs": float(np.median(np.abs(local_array))),
        "local_fraction_nonzero": float(np.mean(local_array != 0.0)),
        "seconds": round(time.perf_counter() - started, 2),
        "per_mutation": per_mutation,
    }


def main() -> int:
    report: dict = {
        "experiment": "CausalTape-4 (scaled)",
        "workers": WORKERS,
        "confirm_seeds": [CONFIRM_SEEDS[0], CONFIRM_SEEDS[-1], len(CONFIRM_SEEDS)],
        "configs": {},
    }
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        # Threshold calibration: at every depth the innovation target is the
        # phenotype typical of that depth under the reference landscape
        # (eps = 0.2), measured on pilot seeds only. A single global threshold
        # saturated by depth in the previous pass (rate 0.000 at depth 20,
        # 1.000 at depth 80), which made the binary outcome uninformative.
        thresholds: dict[tuple[int, int], float] = {}
        for env_seed in ENV_SEEDS:
            depths = DEPTHS if env_seed == ENV_SEEDS[0] else (40,)
            for depth in depths:
                ref = Cfg(env_seed=env_seed, eps=REFERENCE[0], depth=depth)
                values = list(pool.map(partial(pilot_task, ref), PILOT_SEEDS, chunksize=8))
                thresholds[(env_seed, depth)] = float(np.median(values))
            print(
                f"env_seed {env_seed}: thresholds "
                + ", ".join(f"G{d}={thresholds[(env_seed, d)]:.3f}" for d in depths),
                flush=True,
            )

        for env_seed in ENV_SEEDS:
            depths = DEPTHS if env_seed == ENV_SEEDS[0] else (40,)
            for depth in depths:
                for eps in EPS_GRID:
                    cfg = Cfg(env_seed=env_seed, eps=eps, depth=depth)
                    key = f"e{env_seed}_eps{eps}_G{depth}"
                    report["configs"][key] = run_config(pool, cfg, thresholds[(env_seed, depth)])
                    row = report["configs"][key]
                    print(
                        f"{key:<28} innov={row['innovation_rate']:.3f} "
                        f"order|tau|={row['order_tau_median_abs']:.4f} "
                        f"local|tau|={row['local_tau_median_abs']:.4f} ({row['seconds']}s)",
                        flush=True,
                    )

    report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    report["verdicts"] = verdicts(report)
    (RESULTS / "scale1_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], indent=2), flush=True)
    print("SCALE1_DONE", flush=True)
    return 0


def verdicts(report: dict) -> dict:
    def col(key: str, field: str) -> np.ndarray:
        return np.array([row[field] for row in report["configs"][key]["per_mutation"]])

    out: dict = {}
    for env_seed in ENV_SEEDS:
        k0 = f"e{env_seed}_eps0.0_G40"
        kmax = f"e{env_seed}_eps0.8_G40"
        trend = [float(np.median(np.abs(col(f"e{env_seed}_eps{eps}_G40", "specification_bias_fitness")))) for eps in EPS_GRID]
        out[f"env{env_seed}"] = {
            "spec_bias_zero_at_eps0": float(np.max(np.abs(col(k0, "specification_bias_fitness")))) <= 1e-9,
            "spec_bias_monotone": all(b >= a - 1e-12 for a, b in zip(trend, trend[1:])),
            "spec_bias_trend": trend,
            "naive_bias_negative_at_eps0": float(np.median(col(k0, "selection_bias_fitness"))) < 0.0,
            "naive_underestimates": bool(
                np.all(col(k0, "naive_fitness") < col(k0, "att_fitness"))
            ),
            "att_sd_zero_at_eps0": bool(np.all(col(k0, "att_fitness_sd") <= 1e-12)),
            "att_sd_positive_at_max": bool(np.median(col(kmax, "att_fitness_sd")) > 0.0),
            "tau_epi_zero_at_eps0": float(np.max(np.abs(col(k0, "tau_epi_fitness")))) <= 1e-9,
            "innovation_rate_reference": report["configs"][f"e{env_seed}_eps0.2_G40"]["innovation_rate"],
            "order_nonzero_above_eps": [
                eps
                for eps in EPS_GRID
                if report["configs"][f"e{env_seed}_eps{eps}_G40"]["order_fraction_nonzero"] > 0.0
            ],
            "local_order_nonzero_above_eps": [
                eps
                for eps in EPS_GRID
                if report["configs"][f"e{env_seed}_eps{eps}_G40"]["local_fraction_nonzero"] > 0.0
            ],
        }
    return out


if __name__ == "__main__":
    raise SystemExit(main())
