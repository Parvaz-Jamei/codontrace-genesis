#!/usr/bin/env python3
"""Thin CLI: honest JSONL smoke for discovery Ideas 4 and 2 (phase2_design)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_smoke import (
    DEFAULT_SMOKE_SEEDS,
    run_jsonl_smoke,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write honest Idea4+Idea2 JSONL smoke under claim ceiling "
            "phase2_design. Not recovery-window or G2 evidence."
        )
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(DEFAULT_SMOKE_SEEDS),
        help=f"smoke seeds (default {list(DEFAULT_SMOKE_SEEDS)}; not 801–816)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="output directory (default outputs/campaigns/.../jsonl_smoke)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="thread workers (default min(8, n_seeds, nproc))",
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="force serial execution",
    )
    args = parser.parse_args(argv)

    summary = run_jsonl_smoke(
        seeds=args.seeds,
        out_dir=args.out_dir,
        max_workers=args.max_workers,
        parallel=not args.no_parallel,
    )
    print(
        json.dumps(
            {
                "schema": summary["schema"],
                "claim_ceiling": summary["claim_ceiling"],
                "seeds": summary["seeds"],
                "idea_ids": summary["idea_ids"],
                "n_records": summary["n_records"],
                "jsonl_path": summary["jsonl_path"],
                "nproc_reported": summary["nproc_reported"],
                "max_workers": summary["max_workers"],
                "hypothesis_supported": summary["hypothesis_supported"],
                "red_queen_proved": summary["red_queen_proved"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
