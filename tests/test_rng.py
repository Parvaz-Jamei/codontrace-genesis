from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace import RNGManager


def test_rng_manager_is_deterministic_and_forkable() -> None:
    left = RNGManager(seed=42)
    right = RNGManager(seed=42)
    assert [left.randrange(100) for _ in range(5)] == [right.randrange(100) for _ in range(5)]
    assert left.fork("mutation").snapshot() == {
        "seed": 42,
        "namespace": "root/mutation",
        "draw_count": 0,
    }


def test_rng_snapshot_restore_resumes_exact_stream_without_pickle() -> None:
    rng = RNGManager(seed=7)
    _ = [rng.randrange(10) for _ in range(5)]
    snapshot = rng.snapshot(include_state=True)
    json.dumps(snapshot)
    restored = RNGManager.restore(snapshot)
    assert rng.randrange(10) == restored.randrange(10)
    assert rng.draw_count == restored.draw_count
    assert rng.state_digest() == restored.state_digest()


def test_rng_restore_rejects_invalid_snapshot() -> None:
    with pytest.raises(ValueError, match="Invalid RNG snapshot"):
        RNGManager.restore({"seed": 1})


def test_no_direct_random_usage_outside_rng_module() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "codontrace"
    forbidden = ("import random", "from random", "random.", "Random(", "pickle")
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        if path.name == "rng.py":
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                offenders.append(f"{path.relative_to(src)}:{marker}")
    assert offenders == []
