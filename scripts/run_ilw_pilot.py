#!/usr/bin/env python3
"""Run locked S2 ILW pilot (seeds 3100–3107) and write outputs/ilw_pilot_s2.json."""

from __future__ import annotations

import json
import sys

from codontrace.genesis.ilw.pilot import run_s2_pilot


def main() -> int:
    report = run_s2_pilot(write_artifact=True)
    print(json.dumps({"status": report.status, "gates": report.gates.to_dict()}, indent=2))
    return 0 if report.gates.all_passed else 2


if __name__ == "__main__":
    sys.exit(main())
