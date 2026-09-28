"""Scored JSONL campaign tests for Ideas 4 and 2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import (
    IDEA2_SCORED_CELLS,
    SHAM_ID,
    run_idea2_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    HORIZON_T,
    OPS_CELLS,
    T_INTERVENE_GRID,
    run_idea4_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_campaign import (
    CLAIM_CEILING,
    DEFAULT_CAMPAIGN_SEEDS,
    SCHEMA,
    jsonl_campaign_constants,
    run_jsonl_campaign,
    validate_campaign_seeds,
)


def test_campaign_constants_locked() -> None:
    c = jsonl_campaign_constants()
    assert c["schema"] == SCHEMA
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert len(c["default_campaign_seeds"]) >= 64
    for seed in c["default_campaign_seeds"]:
        assert not (801 <= int(seed) <= 816)
    assert set(c["idea4_ops_cells"]) == set(OPS_CELLS)
    assert list(c["idea4_t_intervene_grid"]) == list(T_INTERVENE_GRID)
    assert 2 not in c["idea4_t_intervene_grid"]
    assert set(c["idea2_cells"]) == set(IDEA2_SCORED_CELLS)


def test_refuses_sealed_seeds() -> None:
    with pytest.raises(ConfigurationError, match="sealed"):
        validate_campaign_seeds([801])
    with pytest.raises(ConfigurationError, match="sealed"):
        validate_campaign_seeds([201, 816])
    assert validate_campaign_seeds([201, 202, 201]) == (201, 202)


def test_idea4_scored_cell_honesty_and_fields() -> None:
    rec = run_idea4_scored_cell(
        seed=201, ops_cell="control", t_intervene=10, t_horizon=HORIZON_T
    )
    assert rec["claim_ceiling"] == "phase2_design"
    assert rec["hypothesis_supported"] is False
    assert rec["red_queen_proved"] is False
    assert rec["n_unit"] == "run"
    assert rec["T_horizon"] == 40
    assert rec["t_intervene"] == 10
    assert abs(float(rec["t_tilde"]) - 0.25) < 1e-12
    assert isinstance(rec["recover"], bool)
    assert rec["ops_cell"] == "control"
    assert rec["checkpoint_id"] == "CKPT-RELOCATE-RECOVERY-TOKEN-V1"
    assert "run_id" in rec


def test_idea4_refuses_smoke_horizon() -> None:
    with pytest.raises(ConfigurationError, match="smoke"):
        run_idea4_scored_cell(seed=201, ops_cell="control", t_intervene=2, t_horizon=4)


def test_idea2_scored_cell_required_fields() -> None:
    rows = run_idea2_scored_cell(seed=201, cell="pi_deception")
    assert len(rows) == 3
    arms = {r["arm"] for r in rows}
    assert arms == {"gene", "pattern", "causal"}
    for r in rows:
        assert r["cell"] == "pi_deception"
        assert r["claim_ceiling"] == "phase2_design"
        assert r["hypothesis_supported"] is False
        assert r["red_queen_proved"] is False
        assert r["sham_id"] == SHAM_ID == "SHAM-CUE-PREDPHASE-V1"
        assert isinstance(r["survival_to_T"], float)
        assert isinstance(r["margin_vs_best_rival"], float)
        assert isinstance(r["do_on_NC"], bool)
        assert r["n_unit"] == "run"
        assert r["mechanism_label_deferred"] is True
        assert set(r["mechanism_competitors"]) == {"M0", "M1", "M2", "M3"}


def test_idea2_sham_not_nc() -> None:
    rows = run_idea2_scored_cell(seed=202, cell="sham_predphase")
    for r in rows:
        assert r["sham_id"] == "SHAM-CUE-PREDPHASE-V1"
        assert r.get("sham_targets_nc") is False


def test_jsonl_campaign_subset(tmp_path: Path) -> None:
    seeds = (201, 202)
    summary = run_jsonl_campaign(
        seeds=seeds,
        out_dir=tmp_path,
        parallel=False,
        max_workers=1,
    )
    jsonl_path = Path(summary["jsonl_path"])
    assert jsonl_path.is_file()
    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "README.md").is_file()

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    # idea4: 2 seeds × 5 cells × 3 t = 30; idea2: 2 × 4 cells × 3 arms = 24
    assert len(lines) == 30 + 24
    parsed = [json.loads(line) for line in lines]
    assert all(r["hypothesis_supported"] is False for r in parsed)
    assert all(r["red_queen_proved"] is False for r in parsed)
    assert all(r["claim_ceiling"] == "phase2_design" for r in parsed)
    assert all(not (801 <= int(r["seed"]) <= 816) for r in parsed)
    assert summary["hypothesis_supported"] is False
    assert summary["n_records"] == len(parsed)

    idea4 = [r for r in parsed if r["idea_id"] == 4]
    idea2 = [r for r in parsed if r["idea_id"] == 2]
    assert all("t_tilde" in r and "recover" in r and "ops_cell" in r for r in idea4)
    assert all(
        {"cell", "arm", "survival_to_T", "margin_vs_best_rival", "sham_id", "do_on_NC"}
        <= set(r)
        for r in idea2
    )


def test_default_seeds_avoid_sealed_and_large() -> None:
    assert len(DEFAULT_CAMPAIGN_SEEDS) >= 64
    assert DEFAULT_CAMPAIGN_SEEDS[0] == 201
    assert DEFAULT_CAMPAIGN_SEEDS[-1] == 264
    for seed in DEFAULT_CAMPAIGN_SEEDS:
        assert not (801 <= seed <= 816)
