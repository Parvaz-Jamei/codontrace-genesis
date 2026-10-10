#!/usr/bin/env python3
"""Run or resume the T11 calibration. Other experiments are refused."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codontrace.campaigns.board_runner import main

if __name__ == "__main__":
    raise SystemExit(main())
