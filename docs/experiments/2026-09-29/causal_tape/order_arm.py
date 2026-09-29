"""CausalTape-2 -- the order arm, with matched schedules on every arm.

Intervention: keep the multiset of drawn mutation proposals fixed and change
only the ORDER in which they are applied. Both arms are scheduled tapes, each
carrying its own schedule digest, so a control arm that silently runs a
different schedule is detectable (an earlier design inflated the order effect by
52x exactly that way).

    tau_order(s) = F(natural order, s) - mean_k F(permuted_k, s)

Gates before the measurement:
  E  replaying a recorded schedule in recorded order reproduces the draw-driven
     tape exactly (events, bits, fitness).
  F  on an order-insensitive landscape (eps = 0, where acceptance depends only
     on the sign of w_i) the order effect must be exactly zero.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from harness import (
    build_env,
    record_schedule,
    run_scheduled_tape,
    run_tape,
    schedule_digest,
)

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

DEPTH = 40
PERMUTATIONS = 4
ORDER_SEEDS = tuple(range(3000, 3120))
RNG = np.random.default_rng(20260928)


def permute(schedule: tuple[tuple[int, str], ...], seed: int) -> tuple[tuple[int, str], ...]:
    from codontrace.rng import RNGManager

    stream = RNGManager(seed=seed).fork("order")
    items = list(schedule)
    for index in range(len(items) - 1, 0, -1):
        swap = stream.randrange(index + 1)
        items[index], items[swap] = items[swap], items[index]
    return tuple(items)


def gate_e(depth: int = DEPTH, seeds: tuple[int, ...] = (1000, 1001, 1002)) -> dict:
    env = build_env(0.2)
    checks = []
    for seed in seeds:
        natural = run_tape(seed=seed, generations=depth, env=env)
        replay = run_scheduled_tape(seed=seed, schedule=record_schedule(natural), env=env)
        checks.append(
            {
                "seed": seed,
                "events_equal": natural.events == replay.events,
                "bits_equal": natural.final_bits == replay.final_bits,
                "fitness_equal": natural.fitness == replay.fitness,
                "digest": replay.schedule_digest[:16],
            }
        )
    return {
        "gate": "E_schedule_reproduces_natural_tape",
        "passed": all(c["events_equal"] and c["bits_equal"] and c["fitness_equal"] for c in checks),
        "checks": checks,
    }


def gate_f(depth: int = DEPTH, seeds: tuple[int, ...] = tuple(range(3000, 3040))) -> dict:
    """eps = 0: order must not matter at all."""

    env = build_env(0.0)
    effects = []
    digest_mismatch = 0
    for seed in seeds:
        natural = run_tape(seed=seed, generations=depth, env=env)
        schedule = record_schedule(natural)
        permuted_fitness = []
        for k in range(PERMUTATIONS):
            other = permute(schedule, seed * 100 + k)
            if schedule_digest(other) != schedule_digest(schedule):
                digest_mismatch += 1
            permuted_fitness.append(
                run_scheduled_tape(seed=seed, schedule=other, env=env).fitness
            )
        effects.append(natural.fitness - float(np.mean(permuted_fitness)))

    effects_array = np.array(effects)
    return {
        "gate": "F_order_effect_zero_on_commuting_landscape",
        "passed": bool(np.max(np.abs(effects_array)) == 0.0),
        "max_abs_tau_order": float(np.max(np.abs(effects_array))),
        "n_seeds": len(seeds),
        "permuted_schedules_that_differ": digest_mismatch,
        "permutations_per_seed": PERMUTATIONS,
    }


def gate_g(depth: int = DEPTH, seeds: tuple[int, ...] = tuple(range(3040, 3060))) -> dict:
    """The order intervention must actually change the schedule, and matter when it should."""

    env = build_env(0.8)
    effects = []
    distinct = 0
    for seed in seeds:
        natural = run_tape(seed=seed, generations=depth, env=env)
        schedule = record_schedule(natural)
        permuted_fitness = []
        for k in range(PERMUTATIONS):
            other = permute(schedule, seed * 100 + k)
            if schedule_digest(other) != schedule_digest(schedule):
                distinct += 1
            permuted_fitness.append(run_scheduled_tape(seed=seed, schedule=other, env=env).fitness)
        effects.append(natural.fitness - float(np.mean(permuted_fitness)))
    effects_array = np.array(effects)
    return {
        "gate": "G_order_effect_nonzero_under_epistasis",
        "passed": bool(np.median(np.abs(effects_array)) > 0.0 and distinct > 0),
        "median_abs_tau_order": float(np.median(np.abs(effects_array))),
        "mean_tau_order": float(np.mean(effects_array)),
        "sd_tau_order": float(np.std(effects_array)),
        "distinct_schedules": distinct,
        "n_seeds": len(seeds),
    }


def measure(eps: float, depth: int = DEPTH, seeds: tuple[int, ...] = ORDER_SEEDS) -> dict:
    env = build_env(eps)
    natural_fitness = []
    permuted_fitness = []
    effects = []
    normalized = []
    unmatched = []
    for seed in seeds:
        natural = run_tape(seed=seed, generations=depth, env=env)
        schedule = record_schedule(natural)
        values = []
        for k in range(PERMUTATIONS):
            permuted = run_scheduled_tape(
                seed=seed, schedule=permute(schedule, seed * 100 + k), env=env
            )
            values.append(permuted.fitness)
        mean_permuted = float(np.mean(values))
        natural_fitness.append(natural.fitness)
        permuted_fitness.append(mean_permuted)
        effects.append(natural.fitness - mean_permuted)
        # Bajic et al. 2018 normalise the noncommutativity by the largest
        # endpoint fitness of the pair; mirror that convention.
        fmax = max(abs(natural.fitness), abs(mean_permuted), 1e-9)
        normalized.append((natural.fitness - mean_permuted) / fmax)

    # Naive (unmatched) comparison: compare the natural tapes of one half of the
    # seed set against the permuted outcomes of the other half. Nothing is
    # matched -- not the seed, not the schedule -- which is the design that has
    # no declared schedule digest. The ratio to the matched estimate is the
    # common-random-numbers inflation factor.
    half = len(seeds) // 2
    unmatched_abs = float(abs(np.mean(natural_fitness[:half]) - np.mean(permuted_fitness[half:])))

    effects_array = np.array(effects)
    normalized_array = np.array(normalized)
    boot = RNG.integers(0, effects_array.size, size=(2000, effects_array.size))
    means = effects_array[boot].mean(axis=1)
    matched_abs = float(abs(np.mean(effects_array)))
    return {
        "eps": eps,
        "depth": depth,
        "n_seeds": len(seeds),
        "natural_mean": float(np.mean(natural_fitness)),
        "permuted_mean": float(np.mean(permuted_fitness)),
        "tau_order_mean": float(np.mean(effects_array)),
        "tau_order_median_abs": float(np.median(np.abs(effects_array))),
        "tau_order_sd": float(np.std(effects_array)),
        "tau_order_ci": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
        "fraction_seeds_nonzero": float(np.mean(effects_array != 0.0)),
        "tau_order_over_fmax_median_abs": float(np.median(np.abs(normalized_array))),
        "fraction_above_detection_floor_0p01": float(np.mean(np.abs(normalized_array) > 0.01)),
        "fraction_above_strong_floor_0p1": float(np.mean(np.abs(normalized_array) > 0.1)),
        "unmatched_effect_abs": unmatched_abs,
        "unmatched_over_matched_inflation": (
            float("inf") if matched_abs == 0.0 else unmatched_abs / matched_abs
        ),
    }


def main() -> int:
    report = {
        "experiment": "CausalTape-2 (order arm)",
        "depth": DEPTH,
        "permutations_per_seed": PERMUTATIONS,
        "order_seeds": [ORDER_SEEDS[0], ORDER_SEEDS[-1], len(ORDER_SEEDS)],
        "gate_e": gate_e(),
        "gate_f": gate_f(),
        "gate_g": gate_g(),
        "configs": {},
    }
    for eps in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
        report["configs"][f"eps{eps}"] = measure(eps)
        row = report["configs"][f"eps{eps}"]
        print(
            f"eps={eps:<4} tau_order mean={row['tau_order_mean']:>8.4f} "
            f"median|tau|={row['tau_order_median_abs']:>7.4f} "
            f"|tau|/FMAX={row['tau_order_over_fmax_median_abs']:.4f} "
            f"ci=[{row['tau_order_ci'][0]:.3f}, {row['tau_order_ci'][1]:.3f}] "
            f"nonzero={row['fraction_seeds_nonzero']:.2f} "
            f"inflation={row['unmatched_over_matched_inflation']:.1f}x",
            flush=True,
        )

    (RESULTS / "order_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k]["passed"] for k in ("gate_e", "gate_f", "gate_g")}, indent=2), flush=True)
    print("ORDER_ARM_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
