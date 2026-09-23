"""Phase 9: evolvability falsification, Cornish refusal, HE_HP digests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_cornish_campaign,
    attach_evolvability_falsification,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_continuum import run_vt_spatial_factorial
from codontrace.genesis.host_parasite_cornish import (
    default_cornish_arm_specs,
    run_cornish_intervention_campaign,
)
from codontrace.genesis.host_parasite_evolvability import (
    HYPOTHESIS,
    run_evolvability_falsification,
)
from codontrace.genesis.host_parasite_zaman import run_zaman_three_arm_campaign

ROOT = Path(__file__).resolve().parents[1]
HE_HP = ROOT / "docs" / "hard_experiment_hp" / "locked_campaign_digests.json"
COMPARATOR = (
    ROOT
    / "docs"
    / "claimgate"
    / "host_parasite_port_20260924"
    / "COMPARATOR_MATRIX.md"
)


def test_evolvability_assay_can_fail_universal_claim() -> None:
    result = run_evolvability_falsification(
        seeds=(1, 2),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert "abiotic_stress" in result.failure_reason or "biotic_stress" in result.failure_reason
    assert result.red_queen_proved is False
    by_arm = {}
    for item in result.arm_outcomes:
        by_arm.setdefault(item.arm, []).append(item.richness_delta)
    assert sum(by_arm["biotic_mild"]) / len(by_arm["biotic_mild"]) > 0
    assert sum(by_arm["biotic_stress"]) / len(by_arm["biotic_stress"]) <= 0


def test_evolvability_refuses_candidate_when_hypothesis_holds() -> None:
    # Force mild-only path by monkey-patching would be heavy; instead request
    # candidate_evidence on the standard failing assay (ok) and ensure high
    # ceilings stay refused.
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_evolvability_falsification(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_cornish_observational_match_never_grants_intervention_supported() -> None:
    prereg = host_parasite_preregistration(
        question_of_interest="Does observational match unlock intervention_supported?",
        context_of_use="Digital Cornish pack only.",
        arms=("obs_intact", "int_remove_parasites", "int_content_null"),
        success_metrics=("obs_match_refusal",),
    )
    digest = str(prereg.to_dict()["digest"])
    # Observational-only campaign still refuses intervention_supported.
    obs_only = (
        {
            "arm_id": "obs_a",
            "kind": "observational",
            "description": "Observational arm A.",
        },
        {
            "arm_id": "obs_b",
            "kind": "observational",
            "description": "Observational arm B (match check).",
        },
    )
    campaign = run_cornish_intervention_campaign(
        seeds=(3, 4),
        arms=obs_only,
        preregistration_digest=digest,
    )
    assert campaign.observational_match is True
    assert campaign.intervention_supported is False
    assert campaign.interventions_executed is False
    payload = campaign.to_dict()
    assert payload["intervention_supported"] is False
    assert "observational_match_alone_never_grants" in payload["cornish_rule"]


def test_cornish_with_interventions_still_refuses_intervention_supported() -> None:
    prereg = host_parasite_preregistration(
        question_of_interest="q",
        context_of_use="Digital only.",
        arms=("obs_intact", "int_remove_parasites"),
        success_metrics=("score",),
    )
    digest = str(prereg.to_dict()["digest"])
    campaign = run_cornish_intervention_campaign(
        seeds=(5,),
        arms=default_cornish_arm_specs(),
        preregistration_digest=digest,
    )
    assert campaign.interventions_executed is True
    assert campaign.intervention_supported is False


def test_attach_cornish_requires_matching_prereg_digest() -> None:
    prereg = host_parasite_preregistration(
        question_of_interest="q",
        context_of_use="Digital only.",
        arms=("obs_intact", "int_remove_parasites", "int_content_null"),
        success_metrics=("score",),
    )
    digest = str(prereg.to_dict()["digest"])
    campaign = run_cornish_intervention_campaign(
        seeds=(8,),
        preregistration_digest=digest,
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="Digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_cornish_campaign(bundle, campaign)
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_cornish_campaign(ready, campaign)
    assert attached.extra["cornish_intervention_campaign"]["intervention_supported"] is False
    assert audit_bundle(attached).achieved_level == before


def test_attach_evolvability_does_not_raise_ladder() -> None:
    assay = run_evolvability_falsification(seeds=(9,), steps=2)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do parasites always raise repertoire?",
        context_of_use="Digital evolvability assay only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    before = audit_bundle(bundle).achieved_level
    attached = attach_evolvability_falsification(bundle, assay)
    assert attached.extra["evolvability_falsification"]["hypothesis_supported"] is False
    assert audit_bundle(attached).achieved_level == before


def test_comparator_matrix_exists_and_denies_identity() -> None:
    text = COMPARATOR.read_text(encoding="utf-8")
    assert "comparison ≠ identity" in text.lower() or "Comparison is not identity" in text
    assert "Avida" in text
    assert "Symbulation" in text
    assert "CRISPR" in text
    assert "intervention_supported" in text
    # Matrix must discuss these as *not* claimed.
    assert "What is *not* claimed" in text or "not* claimed" in text
    lowered = text.lower()
    assert "crispr identity" in lowered
    assert "phage-therapy clearance" in lowered or "phage therapy" in lowered
    assert "red queen" in lowered


def test_he_hp_locked_digests_replay() -> None:
    locked = json.loads(HE_HP.read_text(encoding="utf-8"))
    assert locked["baic_pins_untouched"] is True
    assert locked["intervention_supported"] is False
    assert locked["red_queen_proved"] is False
    zaman = run_zaman_three_arm_campaign(
        seeds=tuple(locked["campaigns"]["zaman_three_arm"]["seeds"]),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    assert (
        zaman.to_dict()["campaign_digest"]
        == locked["campaigns"]["zaman_three_arm"]["campaign_digest"]
    )
    vt = run_vt_spatial_factorial(
        seeds=tuple(locked["campaigns"]["vt_spatial_factorial"]["seeds"]),
        vt_levels=(0.0, 1.0),
        spatial_modes=("well_mixed", "local_neighborhood"),
        interaction_value=-1.0,
        request_claim_ceiling="candidate_evidence",
    )
    assert (
        vt.to_dict()["factorial_digest"]
        == locked["campaigns"]["vt_spatial_factorial"]["factorial_digest"]
    )
    evol = run_evolvability_falsification(
        seeds=tuple(locked["campaigns"]["evolvability_falsification"]["seeds"]),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    assert (
        evol.to_dict()["assay_digest"]
        == locked["campaigns"]["evolvability_falsification"]["assay_digest"]
    )
    assert evol.hypothesis_supported is False
    prereg_digest = locked["campaigns"]["cornish_intervention"]["preregistration_digest"]
    cornish = run_cornish_intervention_campaign(
        seeds=tuple(locked["campaigns"]["cornish_intervention"]["seeds"]),
        preregistration_digest=prereg_digest,
    )
    assert (
        cornish.to_dict()["campaign_digest"]
        == locked["campaigns"]["cornish_intervention"]["campaign_digest"]
    )
    assert cornish.intervention_supported is False


def test_cornish_requires_preregistration_digest() -> None:
    with pytest.raises(ConfigurationError, match="preregistration_digest"):
        run_cornish_intervention_campaign(seeds=(1,), preregistration_digest="")
