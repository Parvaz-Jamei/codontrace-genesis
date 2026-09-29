"""CausalTape-3 -- environment replication.

Everything above was measured against one coupling draw (ENV_SEED 20260927).
This reruns the depth-40 grid against a second, independent draw and asks the
only question that matters for robustness: do the pre-registered patterns
survive a different landscape, or were they a property of that one draw?

Patterns under test (from PREREG.md R2/R5/R8):
  * specification bias is machine-zero at eps = 0,
  * specification bias rises monotonically with eps,
  * the exact per-lineage effect has zero spread at eps = 0 and positive spread
    at eps = 0.8,
  * the order effect is exactly zero below a threshold and positive above it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from harness import build_env
from order_arm import DEPTH as ORDER_DEPTH
from order_arm import PERMUTATIONS, permute
from run_benchmark import EPS_GRID, run_config
from harness import record_schedule, run_scheduled_tape, run_tape

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

ENV_SEEDS = (20260927, 20260928)
DEPTH = 40
ORDER_SEEDS = tuple(range(4000, 4080))


def order_threshold(env_seed: int) -> dict:
    """First eps at which the order effect is non-zero for any seed."""

    curve = {}
    for eps in EPS_GRID:
        env = build_env(eps, env_seed=env_seed)
        effects = []
        for seed in ORDER_SEEDS[:40]:
            natural = run_tape(seed=seed, generations=ORDER_DEPTH, env=env)
            schedule = record_schedule(natural)
            values = [
                run_scheduled_tape(
                    seed=seed, schedule=permute(schedule, seed * 100 + k), env=env
                ).fitness
                for k in range(PERMUTATIONS)
            ]
            effects.append(natural.fitness - float(np.mean(values)))
        array = np.array(effects)
        curve[str(eps)] = {
            "mean": float(np.mean(array)),
            "median_abs": float(np.median(np.abs(array))),
            "fraction_nonzero": float(np.mean(array != 0.0)),
        }
    threshold = next(
        (float(eps) for eps in EPS_GRID if curve[str(eps)]["fraction_nonzero"] > 0.0),
        None,
    )
    return {"curve": curve, "first_nonzero_eps": threshold}


def summary_for(env_seed: int) -> dict:
    print(f"--- env_seed {env_seed} ---", flush=True)
    configs = {}
    for eps in EPS_GRID:
        cfg = run_config(eps, DEPTH, env_seed=env_seed, verbose=False)
        rows = cfg["per_mutation"]
        configs[str(eps)] = {
            "spec_bias_median_abs": float(np.median([abs(r["specification_bias_fitness"]) for r in rows])),
            "spec_bias_max_abs": float(np.max([abs(r["specification_bias_fitness"]) for r in rows])),
            "att_sd_median": float(np.median([r["att_fitness_sd"] for r in rows])),
            "tau_epi_median_abs": float(np.median([abs(r["tau_epi_fitness"]) for r in rows])),
            "selection_bias_median": float(np.median([r["selection_bias_fitness"] for r in rows])),
            "null_band_p95": cfg["null_band_across_loci_p95"],
        }
        print(
            f"  eps={eps:<4} spec_bias={configs[str(eps)]['spec_bias_median_abs']:.4f} "
            f"att_sd={configs[str(eps)]['att_sd_median']:.4f}",
            flush=True,
        )
    trend = [configs[str(eps)]["spec_bias_median_abs"] for eps in EPS_GRID]
    checks = {
        "spec_bias_zero_at_eps0": bool(configs["0.0"]["spec_bias_max_abs"] <= 1e-9),
        "spec_bias_monotone": bool(all(b >= a - 1e-12 for a, b in zip(trend, trend[1:]))),
        "spec_bias_grows": bool(trend[-1] > trend[0] + 1e-3),
        "att_sd_zero_at_eps0": bool(configs["0.0"]["att_sd_median"] <= 1e-12),
        "att_sd_positive_at_max": bool(configs["0.8"]["att_sd_median"] > 0.0),
        "selection_bias_nonzero_at_eps0": bool(abs(configs["0.0"]["selection_bias_median"]) > 1e-3),
    }
    return {
        "env_seed": env_seed,
        "configs": configs,
        "checks": checks,
        "order": order_threshold(env_seed),
    }


def main() -> int:
    report = {"experiment": "CausalTape-3 (environment replication)", "depth": DEPTH, "env_seeds": list(ENV_SEEDS)}
    report["runs"] = [summary_for(seed) for seed in ENV_SEEDS]

    thresholds = [run["order"]["first_nonzero_eps"] for run in report["runs"]]
    report["replication_verdict"] = {
        "spec_bias_zero_at_eps0_both": all(r["checks"]["spec_bias_zero_at_eps0"] for r in report["runs"]),
        "spec_bias_monotone_both": all(r["checks"]["spec_bias_monotone"] for r in report["runs"]),
        "att_sd_pattern_both": all(
            r["checks"]["att_sd_zero_at_eps0"] and r["checks"]["att_sd_positive_at_max"] for r in report["runs"]
        ),
        "selection_bias_nonzero_both": all(
            r["checks"]["selection_bias_nonzero_at_eps0"] for r in report["runs"]
        ),
        "order_first_nonzero_eps": thresholds,
        "order_threshold_agrees": len({t for t in thresholds if t is not None}) <= 1,
    }
    (RESULTS / "replication_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["replication_verdict"], indent=2), flush=True)
    print("REPLICATION_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
