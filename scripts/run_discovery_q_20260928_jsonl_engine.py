#!/usr/bin/env python3
"""CLI: engine closed-loop JSONL campaign for discovery Ideas 4 and 2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_engine import (
    DEFAULT_PILOT_SEEDS,
    run_jsonl_engine_campaign,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write engine closed-loop Idea4+Idea2 JSONL under claim ceiling "
            "phase2_design. Distinct from harness jsonl_campaign. "
            "hypothesis_supported stays false."
        )
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=None,
        help="campaign seeds (default pilot 301–312; not 801–816)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="output directory (default outputs/campaigns/.../jsonl_engine)",
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
    parser.add_argument(
        "--full",
        action="store_true",
        help="use full cell grid / larger default seed set (not pilot)",
    )
    args = parser.parse_args(argv)

    summary = run_jsonl_engine_campaign(
        seeds=args.seeds if args.seeds is not None else DEFAULT_PILOT_SEEDS,
        idea_ids=args.ideas,
        out_dir=args.out_dir,
        max_workers=args.max_workers,
        parallel=not args.no_parallel,
        pilot=not args.full,
    )
    print(
        json.dumps(
            {
                "schema": summary["schema"],
                "claim_ceiling": summary["claim_ceiling"],
                "pilot": summary["pilot"],
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
                "variance_proof": summary["variance_proof"],
                "hypothesis_supported": summary["hypothesis_supported"],
                "red_queen_proved": summary["red_queen_proved"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
