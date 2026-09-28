"""Idea1 phase-2 harness smoke tests."""

from __future__ import annotations

from codontrace.genesis.campaigns.discovery_q_20260928_idea1 import (
    CHANNEL_MARGIN,
    CLAIM_CEILING,
    OPS,
    RIVAL_PAIR_ID,
    idea1_constants,
    run_idea1_smoke,
)


def test_idea1_constants_locked() -> None:
    c = idea1_constants()
    assert c["rival_pair_id"] == "RP-LEDGER-ATP-DRAIN-V1" == RIVAL_PAIR_ID
    assert c["ops"] == list(OPS)
    assert "do_rival_discriminate" in c["ops"]
    assert "update_reactive_ledger" in c["ops"]
    assert "reward_explore_ε" in c["ops"]
    assert c["decision_budget"] == 1.0
    assert c["channel_margin"] == 0.15 == CHANNEL_MARGIN
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["hypothesis_supported"] is False
    assert c["red_queen_proved"] is False
    assert c["evoscm_status"] == "DEFER"
    assert c["n_unit"] == "run"


def test_idea1_smoke_pack() -> None:
    pack = run_idea1_smoke(seed=42)
    assert pack["engineering_green"] is True
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["soft_pass_claimed"] is False
    assert pack["freeze_reopen"] is False
    assert pack["claim_ceiling"] == "phase2_design"
    assert pack["rival_pair_id"] == "RP-LEDGER-ATP-DRAIN-V1"
    assert pack["rival_pair_id"]
    assert pack["n_unit"] == "run"
    assert pack["distinction_locks"]["assay_separate_from_reward"] is True
    assert pack["distinction_locks"]["margin_without_assay_is_not_h2"] is True
    assert pack["distinction_locks"]["identity_ids_nonempty"] is True
    assert isinstance(pack["pack_digest"], str) and pack["pack_digest"]
