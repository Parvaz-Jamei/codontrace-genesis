"""Idea3 phase-2 harness smoke tests."""

from __future__ import annotations

from codontrace.genesis.campaigns.discovery_q_20260928_idea3 import (
    CLAIM_CEILING,
    LAW_ID,
    OPS,
    UNREACH_ID,
    idea3_constants,
    run_idea3_smoke,
)


def test_idea3_constants_locked() -> None:
    c = idea3_constants()
    assert c["law_id"] == "LAW-LEDGER-CONTACT-ATP-PARENT-V1" == LAW_ID
    assert c["unreach_id"] == "UNREACH-L-SINGLE-LIFETIME-V1" == UNREACH_ID
    assert c["ops"] == list(OPS)
    assert "cut_failed_and_bounds" in c["ops"]
    assert c["discovery_margin"] == 0.15
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert c["n_unit"] == "run"


def test_idea3_smoke_pack() -> None:
    pack = run_idea3_smoke(seed=42)
    assert pack["engineering_green"] is True
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["soft_pass_claimed"] is False
    assert pack["freeze_reopen"] is False
    assert pack["claim_ceiling"] == "phase2_design"
    assert pack["law_id"] == LAW_ID and pack["law_id"]
    assert pack["unreach_id"] == UNREACH_ID and pack["unreach_id"]
    assert pack["package_cut_applied"] is True
    assert pack["distinction_locks"]["cut_failed_and_bounds_required"] is True
    assert pack["distinction_locks"]["unreachability_criterion_in_run"] is True
    assert pack["distinction_locks"]["identity_ids_nonempty"] is True
    assert isinstance(pack["pack_digest"], str) and pack["pack_digest"]
