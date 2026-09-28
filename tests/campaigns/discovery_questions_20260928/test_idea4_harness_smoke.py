"""Idea4 phase-2 harness smoke tests."""

from __future__ import annotations

from pathlib import Path

from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    CHECKPOINT_ID,
    CLAIM_CEILING,
    COMPETENCE_ID,
    HORIZON_T,
    REJECTED_CHECKPOINT_ALIASES,
    SCAFFOLD_ID,
    idea4_constants,
    run_idea4_smoke,
)

REPO = Path(__file__).resolve().parents[3]
LEDGER_SRC = REPO / "src" / "codontrace" / "life_loop" / "contact_atp_ledger.py"
ENGINE_SRC = REPO / "src" / "codontrace" / "engine.py"
HOOKS_SRC = REPO / "src" / "codontrace" / "life_loop" / "discovery_boundary_hooks.py"


def test_idea4_constants_locked() -> None:
    c = idea4_constants()
    assert c["competence_id"] == "FI-RARECLASS-CONTACT-YIELD-V1" == COMPETENCE_ID
    assert c["checkpoint_id"] == "CKPT-RELOCATE-RECOVERY-TOKEN-V1" == CHECKPOINT_ID
    assert c["scaffold_id"] == "SCAF-CONTACT-SRC-PATH-V1" == SCAFFOLD_ID
    assert c["horizon_T"] == 40 == HORIZON_T
    assert c["slope_threshold"] == 0.15
    assert c["delta_p_threshold"] == 0.20
    assert c["claim_ceiling"] == "phase2_design" == CLAIM_CEILING
    assert c["red_queen_proved"] is False
    assert "CKPT-REMOVE-PREDFAIL-DIGEST-MID-V1" in REJECTED_CHECKPOINT_ALIASES
    assert "CKPT-CUT-SCAF-MEMBERSHIP-FREEZE-V1" in REJECTED_CHECKPOINT_ALIASES


def test_idea4_smoke_pack() -> None:
    pack = run_idea4_smoke(seed=42)
    assert pack["engineering_green"] is True
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["claim_ceiling"] == "phase2_design"
    assert pack["checkpoint_id"] == "CKPT-RELOCATE-RECOVERY-TOKEN-V1"
    assert pack["competence_id"] == "FI-RARECLASS-CONTACT-YIELD-V1"
    assert len(pack["t_tilde_grid"]) >= 3
    assert pack["distinction_locks"]["checkpoint_is_relocate_recovery_token"] is True
    assert isinstance(pack["pack_digest"], str) and pack["pack_digest"]
    assert "recover_rule_shape" in pack
    assert pack["recover_rule_shape"]["horizon_T"] == 40


def test_ledger_and_hooks_have_no_banned_domain_tokens() -> None:
    for path in (LEDGER_SRC, HOOKS_SRC):
        text = path.read_text(encoding="utf-8").casefold()
        for tok in BANNED_DOMAIN_TOKENS:
            assert tok.casefold() not in text, f"{path.name} contains banned {tok!r}"


def test_engine_py_has_no_new_infection_physics_keywords_from_harness() -> None:
    """Harness must not edit engine.py; infection physics stay out of the kernel."""

    text = ENGINE_SRC.read_text(encoding="utf-8")
    # Sanity: engine may mention domain-free observers, but harness must not
    # have introduced match-allele / virulence / steal infection physics there.
    # We only assert the engine file still lacks virulence/steal infection APIs
    # as callable surface names commonly used in domain modules.
    lowered = text.casefold()
    for needle in ("def infect", "class infection", "virulence_physics", "match_allele_engine"):
        assert needle not in lowered
