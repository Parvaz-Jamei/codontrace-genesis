"""Snapshot the scored-cell outputs of the five discovery campaign modules.

Used by the CI-repair workstream to measure whether an RNG migration changes
recorded numbers. Prints one JSON object per (module, cell) plus the ledger
digest of each scaffold builder, so a before/after diff is exact.

Usage:
    PYTHONPATH=<repo>/src python -B snapshot_campaigns.py <output.json> [seed]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from codontrace.genesis.campaigns import discovery_q_20260928_idea1 as i1
from codontrace.genesis.campaigns import discovery_q_20260928_idea2 as i2
from codontrace.genesis.campaigns import discovery_q_20260928_idea3 as i3
from codontrace.genesis.campaigns import discovery_q_20260928_idea5 as i5
from codontrace.genesis.campaigns import discovery_q_20260928_idea6 as i6

MODULES = {
    "idea1": (i1, i1.IDEA1_SCORED_CELLS),
    "idea2": (i2, i2.IDEA2_SCORED_CELLS),
    "idea3": (i3, i3.IDEA3_SCORED_CELLS),
    "idea5": (i5, i5.IDEA5_SCORED_CELLS),
    "idea6": (i6, i6.IDEA6_SCORED_CELLS),
}


def _runner(module, prefix):
    return getattr(module, f"run_{prefix}_scored_cell")


def snapshot(seed: int) -> dict[str, object]:
    out: dict[str, object] = {"seed": seed, "cells": {}, "ledgers": {}}
    for name, (module, cells) in MODULES.items():
        run = _runner(module, name)
        for cell in cells:
            key = f"{name}:{cell}"
            try:
                out["cells"][key] = run(seed=seed, cell=cell)
            except TypeError:
                out["cells"][key] = run(seed=seed, cell=cell, generations=4)
    from codontrace.life_loop import contact_atp_ledger as cal

    for builder in (
        "build_engine_scaffold_ledger",
        "build_idea1_scaffold_ledger",
        "build_idea2_engine_scaffold_ledger",
        "build_idea3_scaffold_ledger",
        "build_idea5_scaffold_ledger",
        "build_idea6_scaffold_ledger",
    ):
        fn = getattr(cal, builder, None)
        if fn is None:
            continue
        out["ledgers"][builder] = fn(seed=seed).digest()
    return out


def main() -> int:
    target = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 401
    payload = snapshot(seed)
    target.write_text(
        json.dumps(payload, sort_keys=True, indent=1, default=str), encoding="utf-8"
    )
    print(f"wrote {target} with {len(payload['cells'])} cells")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
