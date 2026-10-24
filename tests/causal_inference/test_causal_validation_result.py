"""The committed causal_validation/result.json must be what run_validation.py produces.

The run takes about 40 s, so the test is marked slow (still collected by the
default suite). ``commit`` and ``python`` are provenance, not results: they
are copied from the committed file before the byte comparison.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs" / "experiments" / "2026-10-21" / "causal_validation"


def _load_script():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("run_validation", DIRECTORY / "run_validation.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
def test_committed_result_json_matches_a_fresh_run() -> None:
    committed_bytes = (DIRECTORY / "result.json").read_bytes()
    committed = json.loads(committed_bytes)
    script = _load_script()
    fresh = script.build(commit=committed["commit"])
    fresh["python"] = committed["python"]
    fresh_bytes = script.render(fresh).encode("utf-8")
    assert hashlib.sha256(fresh_bytes).hexdigest() == hashlib.sha256(committed_bytes).hexdigest()
    assert fresh_bytes == committed_bytes
