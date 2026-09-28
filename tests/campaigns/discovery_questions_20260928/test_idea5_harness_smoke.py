"""Idea5 phase-2 harness smoke tests."""

from __future__ import annotations

from codontrace.genesis.campaigns.discovery_q_20260928_idea5 import (
    CLAIM_CEILING,
    LAW_ID,
    OPS,
    PROBE_ID,
    THETA,
    WORLD_FAMILY_ID,
    idea5_constants,
    run_idea5_smoke,
)


def test_idea5_constants_locked() -> None:
    c = idea5_constants()
    assert c["world_family_id"] == "WORLD-FAMILY-CONTACT-ATP-V1" == WORLD_FAMILY_ID
    assert c["law_id"] == "LAW-SHORT-COMPOSABLE-V1" == LAW_ID
    assert c["probe_id"] == "PROBE-PRIVATE-VS-SKELETON-V1" == PROBE_ID
    assert c["ops"] == list(OPS)
    assert c["theta"] == 0.80 == THETA
    assert c["transfer_margin"] == 0.15
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert c["dreamcoder_status"] == "DEFER"
    assert c["n_unit"] == "run"


def test_idea5_smoke_pack() -> None:
    pack = run_idea5_smoke(seed=42)
    assert pack["engineering_green"] is True
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["soft_pass_claimed"] is False
    assert pack["freeze_reopen"] is False
    assert pack["claim_ceiling"] == "phase2_design"
    assert pack["world_family_id"] and pack["law_id"] and pack["probe_id"]
    assert pack["held_out_split"]["held_out"]
    assert pack["distinction_locks"]["held_out_split_present"] is True
    assert pack["distinction_locks"]["shortcut_pair_present"] is True
    assert pack["distinction_locks"]["train_fit_alone_is_fail"] is True
    assert pack["distinction_locks"]["survival_only_neq_teach"] is True
    assert pack["shortcut_probe_pass"] is True
    assert isinstance(pack["pack_digest"], str) and pack["pack_digest"]
