"""Bias probe for the DoL metric: is the arm-to-arm d_sym difference real or sampling?

Compares for the same trace data:
  - `gorelick_nmi(...).d_sym`  : the repo's plug-in estimator (no chance correction)
  - sklearn `normalized_mutual_info_score(average_method='sqrt')` : same normaliser
  - sklearn `adjusted_mutual_info_score(average_method='sqrt')`   : chance-corrected (Vinh 2010)

and runs a seeded equal-n rarefaction so the two arms are compared at the same
sample size.

Usage:
  python tools/probe_nmi_bias.py --seed 1001 --ticks 24 --population 8
"""

from __future__ import annotations

import argparse
import collections
import random
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sklearn.metrics import (  # noqa: E402
    adjusted_mutual_info_score,
    normalized_mutual_info_score,
)

from codontrace.genesis.engine import GenesisEngine  # noqa: E402
from codontrace.genesis.hard_experiment_03 import (  # noqa: E402
    ARMS,
    _extract_task_samples,
    _task_switch_for_arm,
    build_hard_experiment_03_spec,
)
from codontrace.genesis.metrics.division_of_labor import gorelick_nmi  # noqa: E402


def _samples_for(seed: int, arm: str, ticks: int, population: int):
    spec = build_hard_experiment_03_spec(
        seed=seed, arm=arm, tick_count=ticks, population=population
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    return _extract_task_samples(result, _task_switch_for_arm(arm))


def _sklearn_scores(samples):
    indiv = [s[0] for s in samples]
    task = [s[1] for s in samples]
    return (
        round(normalized_mutual_info_score(indiv, task, average_method="geometric"), 10),
        round(adjusted_mutual_info_score(indiv, task, average_method="geometric"), 10),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--ticks", type=int, default=24)
    ap.add_argument("--population", type=int, default=8)
    ap.add_argument("--draws", type=int, default=400)
    ap.add_argument("--rarefy-seed", type=int, default=20260924)
    args = ap.parse_args()

    by_arm = {}
    print(f"seed={args.seed} ticks={args.ticks} pop={args.population}")
    print(f"{'arm':16s} {'n':>4s} {'plug_in_d_sym':>14s} {'sk_sqrt_nmi':>12s} {'adjusted_mi':>12s}")
    for arm in ARMS:
        samples = _samples_for(args.seed, arm, args.ticks, args.population)
        by_arm[arm] = samples
        plug = gorelick_nmi(samples).d_sym
        sk_nmi, ami = _sklearn_scores(samples)
        print(f"{arm:16s} {len(samples):4d} {plug:14.10f} {sk_nmi:12.10f} {ami:12.10f}")

    print()
    print("=== equal-n rarefaction: cost_high vs channel_off ===")
    a = by_arm["cost_high"]
    b = by_arm["channel_off"]
    n_common = min(len(a), len(b))
    if n_common == 0:
        print("no samples; cannot rarefy")
        return 0
    rng = random.Random(args.rarefy_seed)
    deltas_plug, deltas_ami, wins_plug, wins_ami = [], [], 0, 0
    for _ in range(args.draws):
        sa = rng.sample(a, n_common)
        sb = rng.sample(b, n_common)
        da = gorelick_nmi(sa).d_sym
        db = gorelick_nmi(sb).d_sym
        deltas_plug.append(da - db)
        aa = _sklearn_scores(sa)[1]
        ab = _sklearn_scores(sb)[1]
        deltas_ami.append(aa - ab)
        wins_plug += 1 if da > db else 0
        wins_ami += 1 if aa > ab else 0
    print(f"rarefied n = {n_common} per arm, {args.draws} draws, seed {args.rarefy_seed}")
    print(f"  plug-in  d_sym delta: mean={statistics.mean(deltas_plug):+.10f} "
          f"frac(cost_high > channel_off)={wins_plug / args.draws:.3f}")
    print(f"  adjusted MI  delta  : mean={statistics.mean(deltas_ami):+.10f} "
          f"frac(cost_high > channel_off)={wins_ami / args.draws:.3f}")
    print()
    print("=== unrarefied (full samples, unequal n) ===")
    full_plug = gorelick_nmi(a).d_sym - gorelick_nmi(b).d_sym
    full_ami = _sklearn_scores(a)[1] - _sklearn_scores(b)[1]
    print(f"  plug-in  d_sym delta: {full_plug:+.10f}   (n = {len(a)} vs {len(b)})")
    print(f"  adjusted MI  delta  : {full_ami:+.10f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
