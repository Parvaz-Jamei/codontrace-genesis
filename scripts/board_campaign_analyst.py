#!/usr/bin/env python3
"""Score a campaign directory from its raw files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codontrace.campaigns.analyst import analyse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="board_campaign_analyst")
    parser.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args(argv)
    report = analyse(args.campaign)
    out = args.campaign / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "hypothesis_assessment.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["scientific_status"] != "INVALID_MEASUREMENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
