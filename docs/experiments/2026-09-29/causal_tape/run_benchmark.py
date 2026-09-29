"""CausalTape-1 -- exact-ground-truth benchmark of mutation-effect estimators.

Treatment is the occurrence of one point mutation m during a deterministic
mutation-accumulation tape. The RNG stream advances identically in every
counterfactual (harness gates B/C), so the intervention is exact and the
counterfactual outcome carries no simulation noise.

Target estimand (ground truth, exact):

    ATT_m = E[ Y(1) - Y(0) | m occurs ]        "effect of the mutation on the
                                                lineages that actually carry it"

Two population quantities are reported next to it:
    ATE_m = E[ Y(1) - Y(0) ]                   never-taker convention (0 if the
                                                mutation never appears)
    naive_m = E[Y | m] - E[Y | not m]           what people compute from data

Exact identities available only because Y(0) is computable for every seed:

    naive_m = ATT_m + selection_bias_m,
    selection_bias_m = E[Y(0) | m] - E[Y(0) | not m]

Estimators compared:
    E1 naive conditioning (naive_m)          -> selection bias
    E2 OLS on the full final bit vector       -> specification bias
    E3 exact paired replay                     -> ground truth

Pre-registered rules (PREREG.md):
    R2  eps = 0: |specification bias| <= 1e-9 (OLS must recover the additive
        per-unit effect exactly). If it fails the estimator comparison is void.
    R3  eps = 0: |selection bias| > 0 (conditioning is confounded even with no
        epistasis, because the mutation is not randomised across lineages).
    R4  eps = 0: the exact per-lineage effect has zero variance; at the largest
        eps the median per-lineage effect variance is > 0 (contingency).
    R5  the specification bias increases with epistasis strength.
    R6  seed heterogeneity is reported, never assumed away.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from harness import Env, build_env, run_tape

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

PILOT_SEEDS = tuple(range(0, 150))
CONFIRM_SEEDS = tuple(range(1000, 1300))
EPS_GRID = (0.0, 0.05, 0.1, 0.2, 0.4, 0.8)
DEPTHS = (20, 40, 80)
TOP_K = 8
BOOTSTRAP = 1000
RNG = np.random.default_rng(20260927)


def binary(env: Env, fitness: float) -> int:
    return 1 if fitness >= env.theta else 0


def top_mutations(pilot_tapes, k: int = TOP_K) -> list[str]:
    counts: dict[str, int] = {}
    for tape in pilot_tapes:
        for mutation_id in tape.mutation_ids():
            counts[mutation_id] = counts.get(mutation_id, 0) + 1
    gain = [(mid, n) for mid, n in counts.items() if mid.split(":")[1] == "0>1"]
    gain.sort(key=lambda item: (-item[1], item[0]))
    return [mid for mid, _ in gain[:k]]


def ols(bits: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.hstack([np.ones((bits.shape[0], 1)), bits])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coef[1:]


def run_config(eps: float, depth: int, *, env_seed: int = 20260927, verbose: bool = True) -> dict:
    env = build_env(eps, env_seed=env_seed)
    started = time.perf_counter()

    pilot = [run_tape(seed=seed, generations=depth, env=env) for seed in PILOT_SEEDS]
    mutations = top_mutations(pilot)

    natural = {seed: run_tape(seed=seed, generations=depth, env=env) for seed in CONFIRM_SEEDS}
    fit = np.array([natural[seed].fitness for seed in CONFIRM_SEEDS])
    y = np.array([binary(env, value) for value in fit])
    bits_matrix = np.array([natural[seed].final_bits for seed in CONFIRM_SEEDS], dtype=float)

    design = np.hstack([np.ones((bits_matrix.shape[0], 1)), bits_matrix])
    pinv = np.linalg.pinv(design)
    idx_matrix = RNG.integers(0, len(CONFIRM_SEEDS), size=(BOOTSTRAP, len(CONFIRM_SEEDS)))

    def boot_mean_ci(values: np.ndarray, mask: np.ndarray) -> list[float]:
        """Bootstrap CI of the mean of ``values`` over the masked (exposed) seeds."""

        mask_matrix = mask[idx_matrix]
        counts = mask_matrix.sum(axis=1)
        totals = np.where(mask_matrix, values[idx_matrix], 0.0).sum(axis=1)
        means = np.where(counts > 0, totals / np.maximum(counts, 1), np.nan)
        return [float(np.nanpercentile(means, 2.5)), float(np.nanpercentile(means, 97.5))]

    rows = []
    for mid in mutations:
        bit = int(mid.split(":")[0])
        counter_fit = np.array(
            [
                run_tape(seed=seed, generations=depth, env=env, suppress=frozenset({mid})).fitness
                for seed in CONFIRM_SEEDS
            ]
        )
        counter_y = np.array([binary(env, value) for value in counter_fit])
        has = np.array([natural[seed].present(mid) for seed in CONFIRM_SEEDS], dtype=bool)

        delta_fit = fit - counter_fit
        delta_y = y - counter_y

        att_fit = float(np.mean(delta_fit[has]))
        att_sd_fit = float(np.std(delta_fit[has]))
        ate_fit = float(np.mean(delta_fit))
        naive_fit = float(np.mean(fit[has]) - np.mean(fit[~has]))
        selection_fit = float(np.mean(counter_fit[has]) - np.mean(counter_fit[~has]))
        beta_fit = float(ols(bits_matrix, fit)[bit])

        att_y = float(np.mean(delta_y[has]))
        att_sd_y = float(np.std(delta_y[has]))
        ate_y = float(np.mean(delta_y))
        naive_y = float(np.mean(y[has]) - np.mean(y[~has]))
        selection_y = float(np.mean(counter_y[has]) - np.mean(counter_y[~has]))
        beta_y = float(ols(bits_matrix, y)[bit])

        tau_direct = float(env.weights[bit])  # isolated mutation on the ancestor background

        rows.append(
            {
                "mutation": mid,
                "bit": bit,
                "frequency": float(np.mean(has)),
                "n_exposed": int(has.sum()),
                # --- exact ground truth
                "att_fitness": att_fit,
                "att_fitness_sd": att_sd_fit,
                "att_fitness_ci": boot_mean_ci(delta_fit, has),
                "ate_fitness": ate_fit,
                # --- direct / epistatic split (red-team correction: the reference
                #     is the ancestor contrast, never an average over backgrounds)
                "tau_direct_fitness": tau_direct,
                "tau_epi_fitness": att_fit - tau_direct,
                "tau_epi_fitness_sd": att_sd_fit,
                # --- estimators
                "naive_fitness": naive_fit,
                "adjusted_fitness": beta_fit,
                "selection_bias_fitness": naive_fit - att_fit,
                "identity_residual_fitness": abs((naive_fit - att_fit) - selection_fit),
                "specification_bias_fitness": beta_fit - att_fit,
                "adjusted_fitness_ci": [
                    float(np.percentile((pinv[:, idx_matrix] * fit[idx_matrix]).sum(axis=2)[bit], 2.5)),
                    float(np.percentile((pinv[:, idx_matrix] * fit[idx_matrix]).sum(axis=2)[bit], 97.5)),
                ],
                # --- binary outcome
                "att_binary": att_y,
                "att_binary_sd": att_sd_y,
                "ate_binary": ate_y,
                "naive_binary": naive_y,
                "adjusted_binary": beta_y,
                "selection_bias_binary": naive_y - att_y,
                "specification_bias_binary": beta_y - att_y,
            }
        )

    tau = np.array([row["att_fitness"] for row in rows])
    pair_gaps = np.abs(tau[:, None] - tau[None, :])[np.triu_indices(len(tau), k=1)] if len(tau) > 1 else np.array([0.0])
    null_band = float(np.percentile(pair_gaps, 95)) if pair_gaps.size else float("nan")

    return {
        "eps": eps,
        "env_seed": env_seed,
        "depth": depth,
        "mutations": mutations,
        "null_band_across_loci_p95": null_band,
        "n_confirm": len(CONFIRM_SEEDS),
        "fitness_mean": float(np.mean(fit)),
        "fitness_sd": float(np.std(fit)),
        "innovation_rate": float(np.mean(y)),
        "seconds": round(time.perf_counter() - started, 2),
        "per_mutation": rows,
    }


def run_agent_instance(depth: int = 20, n_seeds: int = 100, k: int = 4) -> dict:
    """Engine-native substrate: outcome is the closed ATP ledger after a run."""

    seeds = tuple(range(2000, 2000 + n_seeds))
    natural = {seed: run_tape(seed=seed, generations=depth, substrate="agent") for seed in seeds}
    fit = np.array([natural[seed].fitness for seed in seeds])
    counts: dict[str, int] = {}
    for tape in natural.values():
        for mid in tape.mutation_ids():
            counts[mid] = counts.get(mid, 0) + 1
    mutations = [mid for mid, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:k]]
    bits_matrix = np.array([natural[seed].final_bits for seed in seeds], dtype=float)
    beta = ols(bits_matrix, fit)
    rows = []
    for mid in mutations:
        bit = int(mid.split(":")[0])
        counter = np.array(
            [
                run_tape(seed=seed, generations=depth, substrate="agent", suppress=frozenset({mid})).fitness
                for seed in seeds
            ]
        )
        has = np.array([natural[seed].present(mid) for seed in seeds], dtype=bool)
        delta = fit - counter
        att = float(np.mean(delta[has]))
        naive = float(np.mean(fit[has]) - np.mean(fit[~has]))
        rows.append(
            {
                "mutation": mid,
                "frequency": float(np.mean(has)),
                "att": att,
                "att_sd": float(np.std(delta[has])),
                "ate": float(np.mean(delta)),
                "naive": naive,
                "adjusted": float(beta[bit]),
                "selection_bias": naive - att,
                "specification_bias": float(beta[bit]) - att,
            }
        )
    return {
        "substrate": "agent",
        "depth": depth,
        "n_seeds": n_seeds,
        "outcome": "remaining ATP after 8 deterministic engine steps",
        "fitness_mean": float(np.mean(fit)),
        "fitness_sd": float(np.std(fit)),
        "per_mutation": rows,
    }


def main() -> int:
    report: dict = {
        "experiment": "CausalTape-1",
        "env_seed": 20260927,
        "pilot_seeds": [PILOT_SEEDS[0], PILOT_SEEDS[-1], len(PILOT_SEEDS)],
        "confirm_seeds": [CONFIRM_SEEDS[0], CONFIRM_SEEDS[-1], len(CONFIRM_SEEDS)],
        "configs": {},
    }
    for depth in DEPTHS:
        for eps in EPS_GRID:
            key = f"eps{eps}_G{depth}"
            report["configs"][key] = run_config(eps, depth)
            cfg = report["configs"][key]
            print(
                f"{key:<16} innov={cfg['innovation_rate']:.3f} F={cfg['fitness_mean']:.2f}"
                f"+-{cfg['fitness_sd']:.2f} ({cfg['seconds']}s)",
                flush=True,
            )

    report["agent_instance"] = run_agent_instance()

    def col(key: str, field: str) -> np.ndarray:
        return np.array([row[field] for row in report["configs"][key]["per_mutation"]])

    k0 = "eps0.0_G40"
    k_max = "eps0.8_G40"
    trend = [float(np.median(np.abs(col(f"eps{eps}_G40", "specification_bias_fitness")))) for eps in EPS_GRID]
    sd_trend = [float(np.median(col(f"eps{eps}_G40", "att_fitness_sd"))) for eps in EPS_GRID]

    verdicts = {
        "R2_additive_pipeline_null": {
            "max_abs_specification_bias_at_eps0": float(np.max(np.abs(col(k0, "specification_bias_fitness")))),
            "threshold": 1e-9,
            "passed": bool(np.max(np.abs(col(k0, "specification_bias_fitness"))) <= 1e-9),
        },
        "R3_conditioning_confounded_without_epistasis": {
            "median_selection_bias_at_eps0": float(np.median(col(k0, "selection_bias_fitness"))),
            "identity_residual_max": float(np.max(col(k0, "identity_residual_fitness"))),
            "passed": bool(np.median(col(k0, "selection_bias_fitness")) > 1e-3),
        },
        "R4_exact_contingency_of_single_mutation_effect": {
            "median_att_sd_by_eps": sd_trend,
            "zero_variance_at_eps0": bool(np.all(col(k0, "att_fitness_sd") == 0.0)),
            "positive_variance_at_max_eps": bool(np.median(col(k_max, "att_fitness_sd")) > 0.0),
            "passed": bool(
                np.all(col(k0, "att_fitness_sd") == 0.0)
                and np.median(col(k_max, "att_fitness_sd")) > 0.0
            ),
        },
        "R5_specification_bias_increases_with_epistasis": {
            "median_abs_specification_bias_by_eps": trend,
            "monotone": bool(all(b >= a - 1e-12 for a, b in zip(trend, trend[1:]))),
            "passed": bool(
                all(b >= a - 1e-12 for a, b in zip(trend, trend[1:])) and trend[-1] > trend[0] + 1e-3
            ),
        },
        "R6_seed_heterogeneity_reported": {
            "median_att_sd_by_eps": sd_trend,
            "note": "sd is the exact spread of the per-lineage causal effect, not sampling error",
        },
        "R7_additive_direct_equals_lineage": {
            "max_abs_tau_epi_at_eps0": float(np.max(np.abs(col(k0, "tau_epi_fitness")))),
            "threshold": 1e-9,
            "passed": bool(np.max(np.abs(col(k0, "tau_epi_fitness"))) <= 1e-9),
        },
        "R8_epistatic_excess_exceeds_null_band": {
            "median_abs_tau_epi_at_max_eps": float(np.median(np.abs(col(k_max, "tau_epi_fitness")))),
            "null_band_p95_at_max_eps": float(report["configs"][k_max]["null_band_across_loci_p95"]),
            "passed": bool(
                np.median(np.abs(col(k_max, "tau_epi_fitness")))
                > report["configs"][k_max]["null_band_across_loci_p95"]
            ),
        },
    }
    report["verdicts"] = verdicts

    (RESULTS / "benchmark_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(verdicts, indent=2), flush=True)
    print("BENCHMARK_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
