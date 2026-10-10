#!/usr/bin/env python3
"""Run implemented REFERENCE pilots locally, with live console artifacts."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from codontrace.experiments import (
    CampaignOrchestrator,
    T01OEERunner,
    T02MLSPriceRunner,
    T03MutualismRunner,
    T04ContingencyRunner,
    T05RedQueenRunner,
)

RUNNERS = {
    "T01": T01OEERunner,
    "T02": T02MLSPriceRunner,
    "T03": T03MutualismRunner,
    "T04": T04ContingencyRunner,
    "T05": T05RedQueenRunner,
}
ARMS = {
    "T01": ("REAL_SELECTION_WITH_QD", "REAL_SELECTION_NO_QD", "QD_RANDOM_DESCRIPTOR", "NEUTRAL_DRIFT_CONTROL"),
    "T02": ("GROUP_SELECTION", "NO_GROUP_SELECTION", "HIGH_MIGRATION"),
    "T03": ("VERTICAL", "HORIZONTAL", "LOW_VERTICAL"),
    "T04": ("CONTINGENCY_REPLAY",),
    "T05": ("COEVOLUTION", "NO_SELECTION", "FIXED_HOST", "FIXED_PARASITE"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", default="genesis_reference_pilot")
    parser.add_argument("--base-dir", default="campaign_runs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generations", type=int, default=50)
    parser.add_argument("--population", type=int, default=96)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--experiment", choices=(*RUNNERS, "all"), default="all")
    parser.add_argument("--arm", default=None)
    parser.add_argument("--num-demes", type=int, default=8)
    parser.add_argument("--replay-branches", type=int, default=8)
    parser.add_argument("--replay-generations", type=int, default=None)
    parser.add_argument("--history-count", type=int, default=2)
    parser.add_argument("--snapshot-generations", default=None)
    parser.add_argument("--group-selection", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--high-migration", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--vertical-transmission-rate", type=float, default=None)
    parser.add_argument("--cooperation-cost", type=float, default=0.20)
    parser.add_argument("--console-run-id", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0):
        parser.error("max-seconds must be finite and positive")
    if args.seed < 0:
        parser.error("seed must be nonnegative")
    if args.generations < 1 or args.population < 2:
        parser.error("generations >= 1 and population >= 2 required")
    if args.experiment == "all" and (args.arm or args.console_run_id):
        parser.error("--arm and --console-run-id require a single experiment")
    targets = list(RUNNERS) if args.experiment == "all" else [args.experiment]
    orchestrator = CampaignOrchestrator(
        Path(args.base_dir).resolve(),
        args.campaign_id,
        console_run_id=args.console_run_id,
        max_seconds=args.max_seconds,
    )
    for exp_id in targets:
        arm = args.arm or ARMS[exp_id][0]
        if arm not in ARMS[exp_id]:
            parser.error(f"{exp_id} arm must be one of {ARMS[exp_id]}")
        kwargs = {"seed": args.seed, "generations": args.generations}
        if exp_id == "T02":
            if args.num_demes < 1 or args.population % args.num_demes:
                parser.error("T02 population must be divisible by positive num-demes")
            kwargs.update(
                num_demes=args.num_demes,
                deme_capacity=args.population // args.num_demes,
                group_selection=arm != "NO_GROUP_SELECTION" if args.group_selection is None else args.group_selection,
                high_migration=arm == "HIGH_MIGRATION" if args.high_migration is None else args.high_migration,
            )
        elif exp_id == "T03":
            kwargs.update(
                population_size=args.population,
                cooperation_cost=args.cooperation_cost,
                vertical_transmission_rate={"VERTICAL": 0.75, "HORIZONTAL": 0.0, "LOW_VERTICAL": 0.25}[arm]
                if args.vertical_transmission_rate is None
                else args.vertical_transmission_rate,
            )
        else:
            kwargs.update(population_size=args.population, arm=arm)
        if exp_id == "T04":
            kwargs.update(
                replay_branches=args.replay_branches,
                replay_generations=args.replay_generations,
                history_count=args.history_count,
            )
            if args.snapshot_generations is not None:
                try:
                    kwargs["snapshot_generations"] = tuple(int(g) for g in args.snapshot_generations.split(","))
                except ValueError:
                    parser.error("snapshot-generations must contain comma-separated integers")
        try:
            runner = RUNNERS[exp_id](**kwargs)
        except ValueError as exc:
            parser.error(str(exc))
        runner.experiment_id = exp_id
        runner.arm = arm
        result = orchestrator.run_experiment(runner)
        print(f"{exp_id}: status={result.status}, assessment={result.scientific_assessment.value}", flush=True)
        if result.status == "FAILED":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
