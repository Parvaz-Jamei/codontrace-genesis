"""Inventory closure summaries without reclassifying them as missing old raw.

The existing closure JSONs contain aggregate outputs. No missing trajectories
are reconstructed from aggregates. This tool is read-only and prints JSON.
"""

from __future__ import annotations

import json
from pathlib import Path


def inventory(root: Path) -> dict[str, object]:
    records = []
    base = root / "docs/experiments/2026-09-29"
    for pack, folder, seeds in (
        ("rq1_time_shift", "confirmatory/closure_2026-10-03", (5706, 5707, 5708)),
        ("rq3_adaptation_route", "closure_2026-10-03", (21061, 21062, 21063)),
    ):
        directory = base / pack / folder
        for seed in seeds:
            summary = directory / f"seed_{seed}.json"
            data = json.loads(summary.read_text(encoding="utf-8")) if summary.is_file() else {}
            records.append(
                {
                    "pack": pack,
                    "seed": seed,
                    "summary_present": summary.is_file(),
                    "record_role": "current_engine_aggregate_summary",
                    "summary_commit": data.get("commit"),
                    "trajectory_present": any(directory.glob(f"population_seed{seed}.jsonl*")),
                    "raw_pack_complete": False,
                    "status": "INCOMPLETE_PROVENANCE",
                    "reason": "No complete seed-specific trajectory, initial state, config and replay recipe in this closure directory.",
                    "replaces_historical_raw": False,
                    "hypothesis_supported": False,
                }
            )
    return {
        "schema": "closure_summary_inventory_v1",
        "records": records,
        "historical_verdicts_unchanged": True,
        "claim_eligible": False,
    }


if __name__ == "__main__":
    print(json.dumps(inventory(Path(__file__).resolve().parents[1]), indent=2, sort_keys=True))
