"""Phase 18: soft-complete journal ClaimGate attach-registry packet."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    BLOCKED_HOST_PARASITE_CLAIMS,
    assert_claim_allowed,
    attach_journal_attach_registry,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_attach_registry import (
    BLOCKED_CLAIM_MATRIX,
    REQUIRED_ATTACH_KEYS,
    WAVE5_ATTACH_CALLABLES,
    WAVE5_ATTACH_KEYS,
    assert_registry_covers_phases_1_to_17,
    assert_wave5_attach_surface_wired,
    build_journal_attach_registry_packet,
)
from codontrace.genesis.text_digest import sha256_text_file

ROOT = Path(__file__).resolve().parents[1]
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)


def test_registry_covers_phases_1_to_17_keys() -> None:
    packet = build_journal_attach_registry_packet()
    assert_registry_covers_phases_1_to_17(packet)
    assert set(REQUIRED_ATTACH_KEYS) <= set(packet.required_attach_keys)
    assert packet.soft_complete is True
    assert packet.raises_claim_ladder is False
    assert packet.red_queen_proved is False
    assert packet.major_transition_proved is False
    assert packet.phases_covered == tuple(range(1, 18))
    assert "transmission_mode_contrast" in packet.required_attach_keys
    assert "price_causality_caution" in packet.required_attach_keys
    assert {
        "journal_attach_registry",
        "ard_fsd_transition",
        "resource_dynamics_factorial",
        "multi_seed_contingency",
        "cornish_sequential_campaign",
        "scanlan_mutator_campaign",
    } <= set(WAVE5_ATTACH_KEYS)


def test_blocked_claim_matrix_covers_profile_and_refuse_list() -> None:
    for claim in BLOCKED_HOST_PARASITE_CLAIMS:
        assert claim in BLOCKED_CLAIM_MATRIX
        with pytest.raises(ConfigurationError):
            assert_claim_allowed(claim)
    for claim in (
        "gene_identity_proved",
        "complexity_emergence_proved",
        "oee_type1_proved",
        "modes_passed_proved",
        "phage_therapy_cleared",
        "red_queen_proved",
        "intelligence_proved",
        "intervention_supported",
    ):
        assert claim in BLOCKED_CLAIM_MATRIX
        assert claim in BLOCKED_HOST_PARASITE_CLAIMS
        with pytest.raises(ConfigurationError):
            assert_claim_allowed(claim)


def test_attach_journal_registry_requires_prereg_and_keeps_ladder() -> None:
    packet = build_journal_attach_registry_packet(
        request_claim_ceiling="candidate_evidence",
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Is the Phase 1–17 attach surface documented?",
        context_of_use="Journal soft-complete registry hygiene only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.1,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_journal_attach_registry(bundle, packet)
    prereg = host_parasite_preregistration(
        question_of_interest="Is the Phase 1–17 attach surface documented?",
        context_of_use="Journal soft-complete registry hygiene only.",
        arms=("journal_registry",),
        success_metrics=("registry_digest", "soft_complete"),
        forbidden_claims=("red_queen_proved", "major_transition_proved"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_journal_attach_registry(ready, packet)
    record = attached.extra["journal_attach_registry"]
    assert record["soft_complete"] is True
    assert record["raises_claim_ladder"] is False
    assert record["red_queen_proved"] is False
    assert "price_causality_caution" in record["required_attach_keys"]
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_journal_attach_registry(attached, packet)




def test_wave5_attach_surface_wired_to_adapter_callables() -> None:
    """Completeness hygiene: Wave-5 keys map to real attach_* callables."""

    assert_wave5_attach_surface_wired()
    assert set(WAVE5_ATTACH_KEYS) == set(WAVE5_ATTACH_CALLABLES)
    assert set(WAVE5_ATTACH_CALLABLES.values()) == {
        "attach_journal_attach_registry",
        "attach_ard_fsd_transition",
        "attach_resource_dynamics_factorial",
        "attach_multi_seed_contingency",
        "attach_sequential_cornish_campaign",
        "attach_scanlan_mutator_campaign",
    }

def test_baic_pins_byte_identical() -> None:
    for rel, expected in PIN_SPECS:
        digest = sha256_text_file(ROOT / rel)
        assert digest == expected, rel
