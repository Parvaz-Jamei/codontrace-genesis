from __future__ import annotations

import runpy
from pathlib import Path


def test_examples_run_without_exception() -> None:
    root = Path(__file__).resolve().parents[1]
    for script in ("quickstart.py", "causal_replay_demo.py", "quick_factory.py"):
        runpy.run_path(str(root / "examples" / script), run_name="__main__")
