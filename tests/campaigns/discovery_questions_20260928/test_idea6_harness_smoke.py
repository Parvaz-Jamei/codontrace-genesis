"""Idea6 phase-2 harness smoke tests."""

from __future__ import annotations

from codontrace.genesis.campaigns.discovery_q_20260928_idea6 import (
    CLAIM_CEILING,
    OPS,
    SUPPORT_CUT_CELL_ID,
    USTAR_ID,
    USTAR_SMOKE_VALUE,
    idea6_constants,
    run_idea6_smoke,
)


def test_idea6_constants_locked() -> None:
    c = idea6_constants()
    assert c["ustar_id"] == "USTAR-RESTRAINT-V1" == USTAR_ID
    assert c["ustar_smoke_value"] == 0.55 == USTAR_SMOKE_VALUE
    assert c["support_cut_cell_id"] == "SUPCUT-REMOVE-CHANNELS-V1" == SUPPORT_CUT_CELL_ID
    assert "SUP-VERIFY-CONSULT-V1" in c["support_channel_ids"]
    assert c["ops"] == list(OPS)
    assert "withhold_if_u_below" in c["ops"]
    assert "support_cut" in c["ops"]
    assert c["survival_margin"] == 0.15
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert c["n_unit"] == "run"


def test_idea6_smoke_pack() -> None:
    pack = run_idea6_smoke(seed=42)
    assert pack["engineering_green"] is True
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["soft_pass_claimed"] is False
    assert pack["freeze_reopen"] is False
    assert pack["claim_ceiling"] == "phase2_design"
    assert pack["ustar_id"] == USTAR_ID and pack["ustar_id"]
    assert pack["ustar_value"] == USTAR_SMOKE_VALUE
    assert pack["support_cut_applied"] is True
    assert pack["distinction_locks"]["claimgate_neq_u"] is True
    assert pack["distinction_locks"]["claimgate_neq_trait"] is True
    assert pack["distinction_locks"]["support_on_then_cut"] is True
    assert pack["distinction_locks"]["identity_ids_nonempty"] is True
    assert isinstance(pack["pack_digest"], str) and pack["pack_digest"]
