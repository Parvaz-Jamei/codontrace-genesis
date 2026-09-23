"""Phase 23: Scanlan mutator / abiotic-constraint dual-null (earn-in)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_scanlan_mutator_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_mutator import (
    HYPOTHESIS,
    run_scanlan_mutator_campaign,
)


def test_mutator_falsifies_elevated_mutation_always_improves_abiotic() -> None:
    result = run_scanlan_mutator_campaign(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert result.failure_reason
    assert result.gene_identity_proved is False
    assert result.red_queen_proved is False
    assert result.arms_are_distinct is True
    payload = result.to_dict()
    assert payload["wet_mutator_gene_identity"] is False
    assert payload["crispr_identity_proved"] is False
    by_arm = {}
    for o in result.arm_outcomes:
        by_arm.setdefault(o.arm, []).append(o.abiotic_fitness)
    coevo = sum(by_arm["coevolution_elevated_mutation"]) / len(by_arm["coevolution_elevated_mutation"])
    abiotic = sum(by_arm["abiotic_elevated_mutation"]) / len(by_arm["abiotic_elevated_mutation"])
    assert coevo < abiotic


def test_crispr_and_gene_identity_stay_refused() -> None:
    with pytest.raises(ConfigurationError, match="crispr_identity_proved"):
        assert_claim_allowed("crispr_identity_proved")
    result = run_scanlan_mutator_campaign(seeds=(7,))
    assert result.gene_identity_proved is False


def test_attach_mutator_requires_prereg() -> None:
    campaign = run_scanlan_mutator_campaign(seeds=(3, 4))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does elevated mutation under coevolution always improve abiotic?",
        context_of_use="Scanlan mutator dual-null; gene identity unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_scanlan_mutator_campaign(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Does elevated mutation under coevolution always improve abiotic?",
        context_of_use="Scanlan mutator dual-null; gene identity unproved.",
        arms=list(campaign.arms),
        success_metrics=("campaign_digest", "arms_are_distinct"),
        forbidden_claims=("crispr_identity_proved", "red_queen_proved"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_scanlan_mutator_campaign(ready, campaign)
    record = attached.extra["scanlan_mutator_campaign"]
    assert record["gene_identity_proved"] is False
    assert record["crispr_identity_proved"] is False
    assert record["raises_claim_ladder"] is False
    assert audit_bundle(attached).achieved_level == before
