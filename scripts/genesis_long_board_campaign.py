#!/usr/bin/env python3
"""Genesis Long Board Campaign Runner.

CLI script to run experiments on Windows and the Orange Pi board.
"""

import argparse
from pathlib import Path

from codontrace.experiments import (
    CampaignOrchestrator,
    T01OEERunner,
    T02MLSPriceRunner,
    T03MutualismRunner,
    T04ContingencyRunner,
    T05RedQueenRunner,
    T06CausalLedgerRunner,
    T07CapsuleTransferRunner,
    T08SkillCompressionRunner,
    T09FunctionalInfoRunner,
    T10EcologicalResilienceRunner,
    T11EnduranceRunner,
    T12SwarmControlRunner,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Genesis Long Board Campaign")
    parser.add_argument("--campaign-id", type=str, default="genesis_board_long_v1", help="Campaign ID")
    parser.add_argument("--base-dir", type=str, default="campaign_runs", help="Base directory for runs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--generations", type=int, default=50, help="Number of generations for iterative experiments")
    parser.add_argument("--experiment", type=str, default="all", help="Target experiment: T01..T12 or 'all'")
    args = parser.parse_args()

    base_path = Path(args.base_dir).resolve()
    orchestrator = CampaignOrchestrator(base_path, args.campaign_id)

    print(f"Starting campaign {args.campaign_id} at {base_path}")
    print(f"Allowed CPUs: {orchestrator.get_allowed_cpus()}")

    all_runners = {
        "T01": T01OEERunner(seed=args.seed, generations=args.generations),
        "T02": T02MLSPriceRunner(seed=args.seed, generations=args.generations),
        "T03": T03MutualismRunner(seed=args.seed, generations=args.generations),
        "T04": T04ContingencyRunner(seed=args.seed),
        "T05": T05RedQueenRunner(seed=args.seed),
        "T06": T06CausalLedgerRunner(seed=args.seed),
        "T07": T07CapsuleTransferRunner(seed=args.seed),
        "T08": T08SkillCompressionRunner(seed=args.seed),
        "T09": T09FunctionalInfoRunner(seed=args.seed),
        "T10": T10EcologicalResilienceRunner(seed=args.seed),
        "T11": T11EnduranceRunner(seed=args.seed),
        "T12": T12SwarmControlRunner(seed=args.seed),
    }

    target = args.experiment.upper()
    if target != "ALL":
        if target not in all_runners:
            print(f"Unknown experiment '{target}'. Available: {list(all_runners.keys())}")
            return
        selected = {target: all_runners[target]}
    else:
        selected = all_runners

    for exp_id, runner in selected.items():
        print(f"Running {exp_id} ({runner.__class__.__name__})...")
        summary = orchestrator.run_experiment(runner)
        print(f"Completed {exp_id}: status={summary.status}, assessment={summary.scientific_assessment.value}")

if __name__ == "__main__":
    main()
