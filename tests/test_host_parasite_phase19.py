"""Phase 19: ARD→FSD transition + cost-of-generalism digests."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_ard_fsd_transition,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_ard_fsd_transition import (
    HYPOTHESIS,
    run_ard_fsd_transition_campaign,
)


def test_transition_falsifies_always_ard_and_keeps_red_queen_false() -> None:
    result = run_ard_fsd_transition_campaign(
        seeds=(1, 2),
        n_slices=6,
        request_claim_ceiling="candidate_evidence",
    )
    assert result.red_queen_proved is False
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert result.transition_observed is True or result.failure_reason
    assert result.slices_are_distinct is True
    payload = result.to_dict()
    assert payload["wet_ard_fsd_identity"] is False
    assert payload["red_queen_proved"] is False
    costs = [s.mean_cost_of_generalism for s in result.slices if s.arm == "parasite_coevolution"]
    assert costs and all(c >= 0.0 for c in costs)
    assert len(set(payload["arm_digests"].values())) == 3


def test_red_queen_claim_stays_blocked() -> None:
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")


def test_attach_ard_fsd_transition_requires_prereg() -> None:
    campaign = run_ard_fsd_transition_campaign(seeds=(3,), n_slices=6)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do range slices transition ARD→FSD digitally?",
        context_of_use="Digital ARD→FSD transition + cost-of-generalism only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_ard_fsd_transition(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Do range slices transition ARD→FSD digitally?",
        context_of_use="Digital ARD→FSD transition + cost-of-generalism only.",
        arms=("parasite_coevolution", "structure_null_shuffled", "abiotic_only"),
        success_metrics=("transition_observed", "campaign_digest"),
        forbidden_claims=("red_queen_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_ard_fsd_transition(ready, campaign)
    record = attached.extra["ard_fsd_transition"]
    assert record["red_queen_proved"] is False
    assert record["wet_ard_fsd_identity"] is False
    assert record["raises_claim_ladder"] is False
    assert audit_bundle(attached).achieved_level == before


def test_dual_null_not_universally_ard() -> None:
    result = run_ard_fsd_transition_campaign(seeds=(1, 2), n_slices=6)
    null_labels = [
        s.label
        for s in result.slices
        if s.arm in {"structure_null_shuffled", "abiotic_only"}
    ]
    assert null_labels
    assert any(label != "ard_like" for label in null_labels)

