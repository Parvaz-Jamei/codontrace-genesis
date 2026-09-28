"""Distinction locks for discovery phase-2 harness (ideas 4 and 2)."""

from __future__ import annotations

import math

import pytest

from codontrace.errors import ConfigurationError
from codontrace.life_loop.contact_atp_ledger import (
    CONTACT_TAG_RARE,
    NAMED_CONTACT_EDGE_IDS,
    SHAM_CUE_PREDPHASE,
    build_idea2_smoke_ledger,
    build_smoke_ledger,
)


def test_relocate_recovery_token_does_not_remove_pred_fail_or_cut_scaffold() -> None:
    ledger = build_smoke_ledger(seed=7)
    digest_key = "digest:pred_fail:smoke_v1"
    token_key = "token:recovery:FI-RARECLASS-CONTACT-YIELD-V1"
    assert digest_key in ledger.failed_prediction_digests
    assert token_key in ledger.recovery_tokens
    before_scaffold = {
        eid: ledger.edges[eid].present for eid in ledger.scaffold_edge_sets[
            "scaffold_edges:SCAF-CONTACT-SRC-PATH-V1"
        ]
    }

    ledger.relocate_recovery_token(token_key, remove=False, new_payload="moved")

    assert digest_key in ledger.failed_prediction_digests
    assert token_key in ledger.recovery_tokens
    assert ledger.recovery_tokens[token_key] == "moved"
    for eid, present in before_scaffold.items():
        assert ledger.edges[eid].present is present


def test_ablate_knowledge_digest_does_not_remove_token_or_cut_scaffold() -> None:
    ledger = build_smoke_ledger(seed=7)
    digest_key = "digest:pred_fail:smoke_v1"
    token_key = "token:recovery:FI-RARECLASS-CONTACT-YIELD-V1"
    scaffold_ids = set(ledger.scaffold_edge_sets["scaffold_edges:SCAF-CONTACT-SRC-PATH-V1"])

    ledger.ablate_knowledge_digest(digest_key)

    assert digest_key not in ledger.failed_prediction_digests
    assert token_key in ledger.recovery_tokens
    for eid in scaffold_ids:
        assert ledger.edges[eid].present is True


def test_cut_named_scaffold_does_not_remove_token_or_digests() -> None:
    ledger = build_smoke_ledger(seed=7)
    digest_key = "digest:pred_fail:smoke_v1"
    token_key = "token:recovery:FI-RARECLASS-CONTACT-YIELD-V1"

    ledger.cut_named_scaffold("SCAF-CONTACT-SRC-PATH-V1")

    assert digest_key in ledger.failed_prediction_digests
    assert token_key in ledger.recovery_tokens
    assert ledger.edges["E0"].present is False
    assert ledger.edges["E1"].present is False


def test_sham_cue_predphase_changes_phase_leaves_nc_edges() -> None:
    ledger = build_idea2_smoke_ledger(seed=11)
    ledger.realised_pressure_phase = 0.1
    ledger.predicted_pressure_phase = 0.1
    before_nc = {
        eid: (ledger.edges[eid].present, ledger.edges[eid].masked)
        for eid in NAMED_CONTACT_EDGE_IDS
    }

    out = ledger.sham_cue_predphase(offset=math.pi)

    assert out["sham_id"] == SHAM_CUE_PREDPHASE
    assert abs(ledger.predicted_pressure_phase - (0.1 + math.pi)) < 1e-12
    assert ledger.realised_pressure_phase == 0.1
    for eid, state in before_nc.items():
        assert (ledger.edges[eid].present, ledger.edges[eid].masked) == state


def test_mask_named_contacts_rejects_genotype_class_targeting() -> None:
    ledger = build_idea2_smoke_ledger(seed=11)
    with pytest.raises(ConfigurationError, match="genotype-class"):
        ledger.mask_named_contacts(["genotype:rare"], one_generation=True)
    with pytest.raises(ConfigurationError, match="genotype-class"):
        ledger.mask_named_contacts(["class:rare"], one_generation=True)
    # Valid edge-ID mask still works.
    ledger.mask_named_contacts(["NC-H0-A0"], one_generation=True)
    assert ledger.edges["NC-H0-A0"].masked is True


def test_class_rare_is_tag_only_helper() -> None:
    ledger = build_smoke_ledger(seed=3)
    assert ledger.tag_is_ledger_only(CONTACT_TAG_RARE) is True
    rare_ids = ledger.edges_with_tag(CONTACT_TAG_RARE)
    assert "E0" in rare_ids and "E1" in rare_ids
    # No genotype mapping API on the ledger.
    assert not hasattr(ledger, "genotype_class_for_tag")
    assert not hasattr(ledger, "map_tag_to_genotype")
    assert not hasattr(ledger, "class_to_genotype")


def test_rejected_checkpoint_aliases_not_live_ops() -> None:
    ledger = build_smoke_ledger(seed=1)
    with pytest.raises(ConfigurationError):
        ledger.relocate_recovery_token("CKPT-REMOVE-PREDFAIL-DIGEST-MID-V1")
    with pytest.raises(ConfigurationError):
        ledger.ablate_knowledge_digest("CKPT-CUT-SCAF-MEMBERSHIP-FREEZE-V1")
    with pytest.raises(ConfigurationError):
        ledger.ablate_knowledge_digest("token:recovery:FI-RARECLASS-CONTACT-YIELD-V1")
    with pytest.raises(ConfigurationError):
        ledger.relocate_recovery_token("digest:pred_fail:smoke_v1")
