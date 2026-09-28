#!/usr/bin/env python3
"""CLI: scored JSONL campaign for discovery Ideas 4 and 2 (phase2_design)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_campaign import (
    DEFAULT_CAMPAIGN_SEEDS,
    run_jsonl_campaign,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write scored Idea4+Idea2 JSONL campaign under claim ceiling "
            "phase2_design. Volume ≠ discovery; hypothesis_supported stays false."
        )
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(DEFAULT_CAMPAIGN_SEEDS),
        help=f"campaign seeds (default {DEFAULT_CAMPAIGN_SEEDS[0]}–{DEFAULT_CAMPAIGN_SEEDS[-1]}; not 801–816)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="output directory (default outputs/campaigns/.../jsonl_campaign)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="thread workers (capped at 8)",
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="force serial execution",
    )
    parser.add_argument(
        "--ideas",
        type=int,
        nargs="+",
        default=[4, 2],
        help="idea ids to run (default 4 2)",
    )
    args = parser.parse_args(argv)

    summary = run_jsonl_campaign(
        seeds=args.seeds,
        idea_ids=args.ideas,
        out_dir=args.out_dir,
        max_workers=args.max_workers,
        parallel=not args.no_parallel,
    )
    print(
        json.dumps(
            {
                "schema": summary["schema"],
                "claim_ceiling": summary["claim_ceiling"],
                "seeds": [summary["seed_lo"], summary["seed_hi"]],
                "n_runs_seeds": summary["n_runs_seeds"],
                "idea_ids": summary["idea_ids"],
                "n_records": summary["n_records"],
                "n_records_idea4": summary["n_records_idea4"],
                "n_records_idea2": summary["n_records_idea2"],
                "jsonl_path": summary["jsonl_path"],
                "manifest_path": summary["manifest_path"],
                "nproc_reported": summary["nproc_reported"],
                "max_workers": summary["max_workers"],
                "wall_time_s": summary["wall_time_s"],
                "hypothesis_supported": summary["hypothesis_supported"],
                "red_queen_proved": summary["red_queen_proved"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
