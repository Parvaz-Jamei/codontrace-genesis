"""Scored JSONL Track C tests for Ideas 1, 3, 5, and 6."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea1 import (
    IDEA1_SCORED_CELLS,
    RIVAL_PAIR_ID,
    run_idea1_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea3 import (
    IDEA3_SCORED_CELLS,
    REVERSAL_CELL_ID,
    run_idea3_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea5 import (
    IDEA5_SCORED_CELLS,
    THETA,
    run_idea5_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea6 import (
    EVIDENCE_MEASURE_ID,
    IDEA6_SCORED_CELLS,
    USTAR_ID,
    run_idea6_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_jsonl_track_c import (
    CLAIM_CEILING,
    DEFAULT_CAMPAIGN_SEEDS,
    SCHEMA,
    jsonl_track_c_constants,
    run_jsonl_track_c,
    validate_campaign_seeds,
)
from codontrace.life_loop.contact_atp_ledger import build_idea3_scaffold_ledger


def test_track_c_constants_locked() -> None:
    c = jsonl_track_c_constants()
    assert c["schema"] == SCHEMA
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert c["soft_pass"] is False
    assert len(c["default_campaign_seeds"]) >= 64
    for seed in c["default_campaign_seeds"]:
        assert not (801 <= int(seed) <= 816)
        assert not (201 <= int(seed) <= 264)
        assert not (301 <= int(seed) <= 364)
    assert set(c["idea1_cells"]) == set(IDEA1_SCORED_CELLS)
    assert set(c["idea3_cells"]) == set(IDEA3_SCORED_CELLS)
    assert set(c["idea5_cells"]) == set(IDEA5_SCORED_CELLS)
    assert set(c["idea6_cells"]) == set(IDEA6_SCORED_CELLS)
    assert c["scaffold_builders"][1] == "build_idea1_scaffold_ledger"
    assert c["scaffold_builders"][3] == "build_idea3_scaffold_ledger"
    assert c["scaffold_builders"][5] == "build_idea5_scaffold_ledger"
    assert c["scaffold_builders"][6] == "build_idea6_scaffold_ledger"


def test_refuses_sealed_and_reserved_seeds() -> None:
    with pytest.raises(ConfigurationError, match="refused|sealed|801"):
        validate_campaign_seeds([801])
    with pytest.raises(ConfigurationError, match="refused"):
        validate_campaign_seeds([201])
    with pytest.raises(ConfigurationError, match="refused"):
        validate_campaign_seeds([301])
    with pytest.raises(ConfigurationError, match="refused"):
        validate_campaign_seeds([401, 816])
    assert validate_campaign_seeds([401, 402, 401]) == (401, 402)


def test_idea1_scored_cell_honesty_and_locks() -> None:
    rec = run_idea1_scored_cell(seed=401, cell="discriminate")
    assert rec["claim_ceiling"] == "phase2_design"
    assert rec["hypothesis_supported"] is False
    assert rec["red_queen_proved"] is False
    assert rec["soft_pass"] is False
    assert rec["soft_pass_claimed"] is False
    assert rec["rival_pair_id"] == RIVAL_PAIR_ID == "RP-LEDGER-ATP-DRAIN-V1"
    assert rec["n_unit"] == "run"
    assert rec["distinction_locks"]["assay_separate_from_reward"] is True
    assert rec["distinction_locks"]["scaffold_builder"] == "build_idea1_scaffold_ledger"
    assert "smoke" not in rec["honesty"].lower() or "scaffold" in rec["honesty"].lower()

    explore = run_idea1_scored_cell(seed=401, cell="reward_explore")
    assert explore["assay_pass"] is False
    assert explore["distinction_locks"]["assay_separate_from_reward"] is True


def test_idea3_scored_cell_cut_and_reversal() -> None:
    cut = run_idea3_scored_cell(seed=401, cell="cut")
    assert cut["hypothesis_supported"] is False
    assert cut["soft_pass"] is False
    assert cut["reversal_cell_id"] == REVERSAL_CELL_ID == "REV-HIGH-NOISE-BLIND-ACCEPT-V1"
    assert cut["cut_applied"] is True
    assert cut["package_cut_applied"] is True
    assert cut["unreach_id"]
    assert cut["distinction_locks"]["empty_cut_reopens"] is True

    rev = run_idea3_scored_cell(seed=402, cell="reversal")
    assert rev["reversal_cell_id"] == "REV-HIGH-NOISE-BLIND-ACCEPT-V1"
    assert rev["discovered"] is False


def test_idea3_empty_cut_reopens() -> None:
    ledger = build_idea3_scaffold_ledger(seed=7)
    ledger.transmit_package(
        package_id="pkg-empty",
        interventional_claim="claim",
        failed_intervention="fail_once",
        validity_bounds="bound_once",
    )
    # Force empty fields after transmit, then cut should raise (empty cut reopen).
    pkg = dict(ledger.causal_packages["pkg-empty"])
    pkg["failed_intervention"] = ""
    pkg["validity_bounds"] = ""
    ledger.causal_packages["pkg-empty"] = pkg
    with pytest.raises(ConfigurationError, match="empty cut|removed nothing"):
        ledger.cut_failed_and_bounds(package_id="pkg-empty")


def test_idea5_scored_cell_theta_and_held_out() -> None:
    rec = run_idea5_scored_cell(seed=401, cell="retain_teach")
    assert rec["theta"] == THETA == 0.80
    assert rec["train_fit_alone_counts"] is False
    assert rec["held_out_split"]["held_out"]
    assert rec["world_family_id"] == "WORLD-FAMILY-CONTACT-ATP-V1"
    assert rec["law_id"] == "LAW-SHORT-COMPOSABLE-V1"
    assert rec["probe_id"] == "PROBE-PRIVATE-VS-SKELETON-V1"
    assert rec["hypothesis_supported"] is False
    assert rec["soft_pass"] is False

    surv = run_idea5_scored_cell(seed=401, cell="survival_only")
    assert surv["survival_only_active"] is True
    assert surv["taught"] is False

    probe = run_idea5_scored_cell(seed=401, cell="shortcut_probe")
    assert isinstance(probe["probe_pass"], bool)
    assert probe["train_fit_alone_counts"] is False


def test_idea5_refuses_smoke_horizon() -> None:
    with pytest.raises(ConfigurationError, match="smoke"):
        run_idea5_scored_cell(seed=401, cell="retain_teach", generations=4)


def test_idea6_scored_cell_ustar_and_support_cut() -> None:
    on = run_idea6_scored_cell(seed=401, cell="support_on")
    assert on["ustar_id"] == USTAR_ID == "USTAR-RESTRAINT-V1"
    assert on["evidence_measure_id"] == EVIDENCE_MEASURE_ID == "U-LEDGER-EVIDENCE-STRENGTH-V1"
    assert on["hypothesis_supported"] is False
    assert on["soft_pass"] is False
    assert on["distinction_locks"]["claimgate_neq_u"] is True
    assert on["support_cut_applied"] is False

    cut = run_idea6_scored_cell(seed=401, cell="support_cut")
    assert cut["support_cut_applied"] is True
    assert not any(cut["support_channels_after"].values())
    assert cut["distinction_locks"]["empty_support_cut_reopens"] is True


def test_jsonl_track_c_smoke_subset(tmp_path: Path) -> None:
    seeds = (401, 402)
    summary = run_jsonl_track_c(
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
    # 2 seeds × (3 + 5 + 3 + 5) cells = 2 × 16 = 32
    assert len(lines) == 32
    parsed = [json.loads(line) for line in lines]
    assert all(r["hypothesis_supported"] is False for r in parsed)
    assert all(r["red_queen_proved"] is False for r in parsed)
    assert all(r["claim_ceiling"] == "phase2_design" for r in parsed)
    assert all(r.get("soft_pass") is False for r in parsed)
    assert all(not (801 <= int(r["seed"]) <= 816) for r in parsed)
    assert summary["hypothesis_supported"] is False
    assert summary["hypothesis_supported_any"] is False
    assert summary["scientific_result"] is False
    assert summary["data_class"] == "scaffold"
    assert summary["closed_loop_unseen_worlds"] is False
    assert summary["n_records"] == len(parsed)
    assert all(r["data_class"] == "scaffold" for r in parsed)
    assert all(r["scientific_result"] is False for r in parsed)
    assert all(r["closed_loop_unseen_worlds"] is False for r in parsed)

    by_idea = {i: [r for r in parsed if r["idea_id"] == i] for i in (1, 3, 5, 6)}
    assert len(by_idea[1]) == 6  # 2 × 3
    assert len(by_idea[3]) == 10  # 2 × 5
    assert len(by_idea[5]) == 6
    assert len(by_idea[6]) == 10
    assert all(r["rival_pair_id"] == "RP-LEDGER-ATP-DRAIN-V1" for r in by_idea[1])
    assert all(
        r["reversal_cell_id"] == "REV-HIGH-NOISE-BLIND-ACCEPT-V1" for r in by_idea[3]
    )
    assert all(r["theta"] == 0.80 for r in by_idea[5])
    assert all(
        r["evidence_measure_id"] == "U-LEDGER-EVIDENCE-STRENGTH-V1" for r in by_idea[6]
    )


def test_default_seeds_avoid_reserved() -> None:
    assert len(DEFAULT_CAMPAIGN_SEEDS) >= 64
    assert DEFAULT_CAMPAIGN_SEEDS[0] == 401
    assert DEFAULT_CAMPAIGN_SEEDS[-1] == 464
    for seed in DEFAULT_CAMPAIGN_SEEDS:
        assert not (801 <= seed <= 816)
        assert not (201 <= seed <= 264)
        assert not (301 <= seed <= 364)


def test_unknown_cell_refused() -> None:
    with pytest.raises(ConfigurationError, match="unknown Idea1"):
        run_idea1_scored_cell(seed=401, cell="not_a_cell")
    with pytest.raises(ConfigurationError, match="unknown Idea3"):
        run_idea3_scored_cell(seed=401, cell="not_a_cell")
    with pytest.raises(ConfigurationError, match="unknown Idea5"):
        run_idea5_scored_cell(seed=401, cell="not_a_cell")
    with pytest.raises(ConfigurationError, match="unknown Idea6"):
        run_idea6_scored_cell(seed=401, cell="not_a_cell")
