"""Phase 22: sequential Cornish multi-intervention deepening."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_sequential_cornish_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_cornish_sequential import (
    default_sequential_schedule,
    run_sequential_cornish_campaign,
)


def _prereg_digest() -> str:
    prereg = host_parasite_preregistration(
        question_of_interest="Does observational match grant intervention support?",
        context_of_use="Sequential Cornish deepening; digital only.",
        arms=("obs_baseline", "int_remove_parasites", "int_content_null", "int_steal_ablation"),
        success_metrics=("campaign_digest", "intervention_supported"),
        forbidden_claims=("red_queen_proved",),
    )
    return prereg.to_dict()["digest"]


def test_observational_match_never_grants_intervention_supported() -> None:
    result = run_sequential_cornish_campaign(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
        preregistration_digest=_prereg_digest(),
    )
    assert result.observational_match is True
    assert result.interventions_executed is True
    assert result.intervention_supported is False
    assert result.red_queen_proved is False
    payload = result.to_dict()
    assert payload["intervention_supported"] is False
    assert payload["clinical_decision_support"] is False
    assert payload["cornish_rule"] == (
        "observational_match_alone_never_grants_intervention_supported"
    )
    assert len(result.step_outcomes) == len(default_sequential_schedule())
    assert result.step_outcomes[0].kind == "observational"
    assert any(o.kind == "intervention" for o in result.step_outcomes)
    # Digests pairwise distinct across ordered steps.
    digests = [o.step_digest for o in result.step_outcomes]
    assert len(set(digests)) == len(digests)


def test_schedule_requires_observational_first() -> None:
    bad = (
        {
            "step_id": "int_first",
            "kind": "intervention",
            "intervention_kind": "remove_parasites",
            "description": "Intervention before observational.",
        },
        {
            "step_id": "obs_late",
            "kind": "observational",
            "description": "Late observational.",
        },
    )
    with pytest.raises(ConfigurationError, match="first step"):
        run_sequential_cornish_campaign(
            seeds=(1,),
            schedule=bad,
            preregistration_digest=_prereg_digest(),
        )


def test_attach_sequential_cornish_requires_prereg_and_matching_digest() -> None:
    prereg = host_parasite_preregistration(
        question_of_interest="Does observational match grant intervention support?",
        context_of_use="Sequential Cornish deepening; digital only.",
        arms=("obs_baseline", "int_remove_parasites", "int_content_null", "int_steal_ablation"),
        success_metrics=("campaign_digest", "intervention_supported"),
        forbidden_claims=("red_queen_proved",),
    )
    digest = prereg.to_dict()["digest"]
    campaign = run_sequential_cornish_campaign(
        seeds=(3,),
        preregistration_digest=digest,
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does observational match grant intervention support?",
        context_of_use="Sequential Cornish deepening; digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_sequential_cornish_campaign(bundle, campaign)
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_sequential_cornish_campaign(ready, campaign)
    record = attached.extra["cornish_sequential_campaign"]
    assert record["intervention_supported"] is False
    assert record["clinical_decision_support"] is False
    assert record["raises_claim_ladder"] is False
    assert audit_bundle(attached).achieved_level == before
