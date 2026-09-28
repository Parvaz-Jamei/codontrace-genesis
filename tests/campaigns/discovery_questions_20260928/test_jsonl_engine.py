"""Engine closed-loop JSONL campaign tests for Ideas 4 and 2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea2_engine import (
    SHAM_ID,
    run_idea2_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    HORIZON_T,
    run_idea4_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_engine import (
    CLAIM_CEILING,
    SCHEMA,
    jsonl_engine_constants,
    run_jsonl_engine_campaign,
    validate_engine_seeds,
)


def test_engine_constants_locked() -> None:
    c = jsonl_engine_constants()
    assert c["schema"] == SCHEMA
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert c["output_subdir"] == "jsonl_engine"
    assert len(c["pilot_t_intervene"]) >= 3
    for seed in c["default_pilot_seeds"]:
        assert not (801 <= int(seed) <= 816)


def test_refuses_sealed_seeds() -> None:
    with pytest.raises(ConfigurationError, match="sealed"):
        validate_engine_seeds([801])
    with pytest.raises(ConfigurationError, match="sealed"):
        validate_engine_seeds([301, 816])


def test_idea4_engine_observer_fires_and_honesty() -> None:
    rec = run_idea4_engine_cell(
        seed=301, ops_cell="control", t_intervene=10, t_horizon=HORIZON_T
    )
    assert rec["claim_ceiling"] == "phase2_design"
    assert rec["hypothesis_supported"] is False
    assert rec["red_queen_proved"] is False
    assert rec["engine_path"] == "genesis_life_loop_observer_coupled"
    assert rec["recovery_progress_multiplier_used"] is False
    assert int(rec["observer_fire_count"]) == int(rec["tick_count"]) == 50
    assert rec["T_horizon"] == 40
    assert isinstance(rec["recover"], bool)
    assert rec["checkpoint_id"] == "CKPT-RELOCATE-RECOVERY-TOKEN-V1"
    assert "engine_result_digest" in rec


def test_idea4_engine_seed_variance_on_baseline_yield() -> None:
    a = run_idea4_engine_cell(
        seed=301, ops_cell="control", t_intervene=10, t_horizon=HORIZON_T
    )
    b = run_idea4_engine_cell(
        seed=305, ops_cell="control", t_intervene=10, t_horizon=HORIZON_T
    )
    assert a["observer_fire_count"] == b["observer_fire_count"] == 50
    assert a["engine_result_digest"] != b["engine_result_digest"]
    # Key metric must show closed-loop seed variance (not harness-zero).
    assert a["baseline_mean_rare_yield"] != b["baseline_mean_rare_yield"]


def test_idea4_engine_refuses_smoke_horizon() -> None:
    with pytest.raises(ConfigurationError, match="smoke"):
        run_idea4_engine_cell(seed=301, ops_cell="control", t_intervene=2, t_horizon=4)


def test_idea2_engine_observer_and_fields() -> None:
    rows = run_idea2_engine_cell(seed=301, cell="pi_deception")
    assert len(rows) == 3
    arms = {r["arm"] for r in rows}
    assert arms == {"gene", "pattern", "causal"}
    for r in rows:
        assert r["cell"] == "pi_deception"
        assert r["claim_ceiling"] == "phase2_design"
        assert r["hypothesis_supported"] is False
        assert r["red_queen_proved"] is False
        assert r["sham_id"] == SHAM_ID == "SHAM-CUE-PREDPHASE-V1"
        assert r["engine_path"] == "genesis_life_loop_observer_coupled"
        assert int(r["observer_fire_count"]) == int(r["T_horizon"])
        assert isinstance(r["survival_to_T"], float)
        assert isinstance(r["margin_vs_best_rival"], float)


def test_idea2_engine_sham_not_nc() -> None:
    rows = run_idea2_engine_cell(seed=302, cell="sham_predphase")
    for r in rows:
        assert r["sham_id"] == "SHAM-CUE-PREDPHASE-V1"
        assert r.get("sham_targets_nc") is False


def test_idea2_engine_seed_variance_survival() -> None:
    a = run_idea2_engine_cell(seed=301, cell="baseline")
    b = run_idea2_engine_cell(seed=305, cell="baseline")
    assert a[0]["engine_result_digest"] != b[0]["engine_result_digest"]
    surv_a = {r["arm"]: r["survival_to_T"] for r in a}
    surv_b = {r["arm"]: r["survival_to_T"] for r in b}
    assert surv_a != surv_b


def test_mini_engine_campaign_writes_jsonl_engine(tmp_path: Path) -> None:
    summary = run_jsonl_engine_campaign(
        seeds=(301, 302),
        idea_ids=(4,),
        out_dir=tmp_path,
        max_workers=2,
        parallel=True,
        pilot=True,
        ops_cells=("control", "scramble_contacts"),
        t_intervene=(10, 20, 30),
    )
    assert summary["claim_ceiling"] == "phase2_design"
    assert summary["hypothesis_supported"] is False
    assert summary["n_records_idea4"] == 2 * 2 * 3
    assert summary["variance_proof"]["ok"] is True
    assert summary["wall_time_s"] > 0.5  # not sub-second harness theater
    jsonl = Path(summary["jsonl_path"])
    assert jsonl.parent.name == tmp_path.name or "jsonl_engine" in str(jsonl)
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == summary["n_records"]
    rec = json.loads(lines[0])
    assert rec["engine_path"] == "genesis_life_loop_observer_coupled"
    assert rec["hypothesis_supported"] is False
