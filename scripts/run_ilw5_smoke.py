#!/usr/bin/env python3
"""ILW-5 confirmatory smoke (requires pilot artifact gates PASS)."""

from __future__ import annotations

import json
import sys

from codontrace.genesis.ilw.campaign import run_ilw5_smoke


def main() -> int:
    payload = run_ilw5_smoke(seeds=(4100,), write_artifact=True)
    print(json.dumps({
        "status": payload["status"],
        "executed": [c["cell"]["cell_id"] for c in payload["executed_cells"]],
        "remaining_for_colab": payload["remaining_for_colab"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
