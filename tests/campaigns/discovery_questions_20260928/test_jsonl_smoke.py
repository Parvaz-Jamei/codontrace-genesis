"""Honest JSONL smoke path tests for Ideas 4 and 2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_smoke import (
    CLAIM_CEILING,
    DEFAULT_SMOKE_SEEDS,
    SCHEMA,
    jsonl_smoke_constants,
    run_jsonl_smoke,
    validate_smoke_seeds,
)


def test_constants_locked() -> None:
    c = jsonl_smoke_constants()
    assert c["schema"] == SCHEMA
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert 32 <= len(c["default_smoke_seeds"]) <= 64
    for seed in c["default_smoke_seeds"]:
        assert not (801 <= int(seed) <= 816)


def test_refuses_sealed_seeds() -> None:
    with pytest.raises(ConfigurationError, match="sealed"):
        validate_smoke_seeds([801])
    with pytest.raises(ConfigurationError, match="sealed"):
        validate_smoke_seeds([42, 816])
    assert validate_smoke_seeds([41, 42, 41]) == (41, 42)


def test_jsonl_smoke_writes_honest_records(tmp_path: Path) -> None:
    seeds = (41, 42, 43, 44)
    summary = run_jsonl_smoke(
        seeds=seeds,
        out_dir=tmp_path,
        parallel=False,
    )
    jsonl_path = Path(summary["jsonl_path"])
    assert jsonl_path.is_file()
    assert (tmp_path / "README.md").is_file()

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(seeds) * 2  # idea 4 and 2 per seed

    parsed = [json.loads(line) for line in lines]
    # Deterministic order: by seed, then idea_id order (4 then 2).
    assert [r["seed"] for r in parsed] == sorted(
        [s for s in seeds for _ in (4, 2)]
    )
    idea_cycle = [4, 2] * len(seeds)
    assert [r["idea_id"] for r in parsed] == idea_cycle

    for rec in parsed:
        assert rec["schema"] == SCHEMA
        assert rec["claim_ceiling"] == "phase2_design"
        assert rec["hypothesis_supported"] is False
        assert rec["red_queen_proved"] is False
        assert isinstance(rec["engineering_green"], bool)
        assert isinstance(rec["pack_digest"], str) and rec["pack_digest"]
        assert isinstance(rec["nproc_reported"], int) and rec["nproc_reported"] >= 1
        assert "honesty" in rec and "recovery-window" in rec["honesty"]
        assert "G2" in rec["honesty"]
        assert not (801 <= int(rec["seed"]) <= 816)

    assert summary["hypothesis_supported"] is False
    assert all(s not in range(801, 817) for s in summary["seeds"])


def test_default_seeds_avoid_sealed_range() -> None:
    assert DEFAULT_SMOKE_SEEDS
    assert 32 <= len(DEFAULT_SMOKE_SEEDS) <= 64
    for seed in DEFAULT_SMOKE_SEEDS:
        assert not (801 <= seed <= 816)
