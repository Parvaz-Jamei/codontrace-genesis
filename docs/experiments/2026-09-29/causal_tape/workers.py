"""Worker functions for the 4-process scaled runs.

Windows uses spawn, so every callable passed to the pool must live at module
level. Each task builds its own environment object (cheap, deterministic) and
returns plain JSON-able values.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from harness import build_env, record_schedule, run_scheduled_tape, run_tape

WORKERS = 4
ORDER_PERMUTATIONS = 6
LOCAL_SWAPS = 12


@dataclass(frozen=True)
class Cfg:
    env_seed: int
    eps: float
    depth: int


def _env(cfg: Cfg):
    return build_env(cfg.eps, env_seed=cfg.env_seed)


def pilot_task(cfg: Cfg, seed: int) -> float:
    """Natural tape fitness, used only to pick focal mutations and the threshold."""

    return run_tape(seed=seed, generations=cfg.depth, env=_env(cfg)).fitness


def confirm_task(args: tuple[Cfg, int, tuple[str, ...], int]) -> dict:
    """One confirmatory seed: natural tape, every suppressed arm, order arms."""

    cfg, seed, mutation_ids, order_count = args
    env = _env(cfg)
    natural = run_tape(seed=seed, generations=cfg.depth, env=env)

    counterfactual: dict[str, float] = {}
    for mid in mutation_ids:
        counterfactual[mid] = run_tape(
            seed=seed, generations=cfg.depth, env=env, suppress=frozenset({mid})
        ).fitness

    order_effects: list[float] = []
    local_effects: list[float] = []
    if order_count > 0:
        schedule = record_schedule(natural)
        for k in range(order_count):
            permuted = permute_schedule(schedule, seed * 100 + k)
            order_effects.append(
                natural.fitness
                - run_scheduled_tape(seed=seed, schedule=permuted, env=env).fitness
            )
        if len(schedule) > 1:
            step = max(1, len(schedule) // LOCAL_SWAPS)
            for index in range(0, len(schedule) - 1, step):
                swapped = list(schedule)
                swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
                local_effects.append(
                    natural.fitness
                    - run_scheduled_tape(seed=seed, schedule=tuple(swapped), env=env).fitness
                )

    return {
        "seed": seed,
        "fitness": natural.fitness,
        "bits": natural.final_bits,
        "present": tuple(sorted(natural.mutation_ids())),
        "counterfactual": counterfactual,
        "order_effects": order_effects,
        "local_effects": local_effects,
    }


def permute_schedule(schedule: tuple[tuple[int, str], ...], seed: int) -> tuple[tuple[int, str], ...]:
    from codontrace.rng import RNGManager

    stream = RNGManager(seed=seed).fork("order")
    items = list(schedule)
    for index in range(len(items) - 1, 0, -1):
        swap = stream.randrange(index + 1)
        items[index], items[swap] = items[swap], items[index]
    return tuple(items)


def chunked(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def median_threshold(fitness: np.ndarray) -> float:
    return float(np.median(fitness))
