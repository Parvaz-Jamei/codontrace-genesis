"""Compare the raw (individual, task) traces across HE03 arms for one seed.

Answers the question the aggregate d_sym cannot: do the cost arms actually
produce a different activity trace from the ablated arm, or are the samples
the same and only the cost bookkeeping differs?

One engine run per arm; the metrics are recomputed here from the same samples
the campaign uses, so the printed d_sym can be checked against the campaign.

Usage: python tools/probe_he03_traces.py --seed 1001 --ticks 8 --population 4
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codontrace.genesis.engine import GenesisEngine  # noqa: E402
from codontrace.genesis.hard_experiment_03 import (  # noqa: E402
    ARMS,
    _extract_switch_stats,
    _extract_task_samples,
    _task_switch_for_arm,
    build_hard_experiment_03_spec,
)
from codontrace.genesis.metrics.division_of_labor import gorelick_nmi  # noqa: E402


def _run_once(seed: int, arm: str, ticks: int, population: int):
    spec = build_hard_experiment_03_spec(
        seed=seed, arm=arm, tick_count=ticks, population=population
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    config = _task_switch_for_arm(arm)
    samples = _extract_task_samples(result, config)
    n_switches, realized = _extract_switch_stats(result)
    nmi = gorelick_nmi(samples)
    return samples, n_switches, realized, nmi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--ticks", type=int, default=8)
    ap.add_argument("--population", type=int, default=4)
    args = ap.parse_args()

    samples_by_arm: dict[str, tuple[tuple[str, str], ...]] = {}
    print(f"seed={args.seed} ticks={args.ticks} population={args.population}")
    print()
    for arm in ARMS:
        samples, n_switches, realized, nmi = _run_once(
            args.seed, arm, args.ticks, args.population
        )
        samples_by_arm[arm] = samples
        print(
            f"{arm:16s} n_samples={len(samples):4d} n_switches={n_switches:3d} "
            f"cost_realized={realized:8.4f} d_sym={nmi.d_sym:.10f} "
            f"n_indiv={nmi.n_individuals} n_tasks={nmi.n_tasks} "
            f"degenerate={nmi.matrix_degenerate}"
        )

    print()
    print("=== per-arm sample multiset ===")
    for arm in ARMS:
        counts = collections.Counter(samples_by_arm[arm])
        pretty = ", ".join(f"{k[0]}:{k[1]}={v}" for k, v in sorted(counts.items()))
        print(f"{arm:16s} {pretty}")

    print()
    print("=== pairwise sample-multiset equality ===")
    for i, a in enumerate(ARMS):
        for b in ARMS[i + 1 :]:
            ca = collections.Counter(samples_by_arm[a])
            cb = collections.Counter(samples_by_arm[b])
            print(
                f"{a:16s} vs {b:16s} identical={ca == cb}  "
                f"n=({sum(ca.values())},{sum(cb.values())})"
            )

    print()
    print("=== entropy/bias inputs per arm (for the sample-size confound) ===")
    for arm in ARMS:
        nmi = gorelick_nmi(samples_by_arm[arm])
        print(
            f"{arm:16s} n={nmi.n_observations:4d} H_indiv={nmi.h_individual:.6f} "
            f"H_task={nmi.h_task:.6f} MI={nmi.mutual_information:.6f} "
            f"d_sym={nmi.d_sym:.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
