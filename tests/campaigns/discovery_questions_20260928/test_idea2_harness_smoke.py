"""Idea2 phase-2 harness smoke tests."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import (
    CLAIM_CEILING,
    DECEPTION_PHASE,
    KAPPA_SMOKE,
    NAMED_CONTACT_SET,
    SHAM_ID,
    idea2_constants,
    require_kappa,
    run_idea2_smoke,
)
from codontrace.life_loop.contact_atp_ledger import NAMED_CONTACT_EDGE_IDS


def test_idea2_constants_locked() -> None:
    c = idea2_constants()
    assert set(c["named_contact_edge_ids"]) == set(NAMED_CONTACT_EDGE_IDS)
    assert tuple(c["named_contact_edge_ids"]) == NAMED_CONTACT_SET or set(
        c["named_contact_edge_ids"]
    ) == set(NAMED_CONTACT_SET)
    assert c["decision_budget"] == 1.0
    assert c["causal_spend"] == [0.5, 0.5]
    assert abs(c["deception_phase"] - DECEPTION_PHASE) < 1e-12
    assert c["kappa_smoke"] == KAPPA_SMOKE == 1.0
    assert c["sham_id"] == "SHAM-CUE-PREDPHASE-V1" == SHAM_ID
    assert c["claim_ceiling"] == "phase2_harness" == CLAIM_CEILING
    assert c["red_queen_proved"] is False


def test_kappa_required() -> None:
    with pytest.raises(ConfigurationError, match="kappa"):
        require_kappa(None)
    assert require_kappa(1.0) == 1.0
    with pytest.raises(ConfigurationError):
        run_idea2_smoke(kappa=None)


def test_idea2_smoke_pack() -> None:
    pack = run_idea2_smoke(seed=42)
    assert pack["engineering_green"] is True
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["claim_ceiling"] == "phase2_harness"
    assert pack["sham_id"] == "SHAM-CUE-PREDPHASE-V1"
    assert set(pack["named_contact_edge_ids"]) == set(NAMED_CONTACT_EDGE_IDS)
    assert pack["kappa"] == 1.0
    assert pack["distinction_locks"]["sham_is_predphase_only"] is True
    assert "gene" in pack["arms"] and "pattern" in pack["arms"] and "causal" in pack["arms"]
    assert pack["arms"]["causal"]["spend"]["sham_control"] == SHAM_ID
    assert isinstance(pack["pack_digest"], str) and pack["pack_digest"]


def test_nc_edge_ids_are_ledger_edges() -> None:
    expected = {
        "NC-H0-A0",
        "NC-H0-A1",
        "NC-H1-A0",
        "NC-H1-A1",
        "NC-H2-A0",
        "NC-H2-A1",
    }
    assert set(NAMED_CONTACT_SET) == expected
