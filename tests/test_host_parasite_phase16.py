"""Phase 16: virulence / resistance quality proxies (Challenge S7)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_virulence_resistance_quality,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_virulence_quality import (
    HYPOTHESIS,
    run_virulence_resistance_quality_campaign,
)


def test_virulence_quality_can_falsify_universal_cost_claim() -> None:
    result = run_virulence_resistance_quality_campaign(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert result.failure_reason
    assert result.arms_are_distinct is True
    assert result.virulence_optimized_for_humans is False
    assert result.red_queen_proved is False
    payload = result.to_dict()
    assert len(set(payload["arm_digests"].values())) == 4
    by_arm = {arm: [] for arm in result.arms}
    for item in result.arm_outcomes:
        by_arm[item.arm].append(item.host_cost)
        assert item.to_dict()["virulence_optimized_for_humans"] is False
    assert sum(by_arm["qualitative_resistance_gate"]) / len(by_arm["qualitative_resistance_gate"]) <= 0
    assert sum(by_arm["quantitative_steal_gradient"]) / len(by_arm["quantitative_steal_gradient"]) > 0


def test_human_virulence_claim_stays_blocked() -> None:
    with pytest.raises(ConfigurationError, match="virulence_optimized_for_humans"):
        assert_claim_allowed("virulence_optimized_for_humans")


def test_attach_virulence_quality_requires_prereg_and_keeps_block() -> None:
    campaign = run_virulence_resistance_quality_campaign(seeds=(3,))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do qualitative and quantitative resistance proxies differ?",
        context_of_use="Digital virulence-quality proxies only. No human virulence claim.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.4,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_virulence_resistance_quality(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Do qualitative and quantitative resistance proxies differ?",
        context_of_use="Digital virulence-quality proxies only. No human virulence claim.",
        arms=tuple(campaign.arms),
        success_metrics=("host_cost", "arm_digest"),
        forbidden_claims=("virulence_optimized_for_humans",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_virulence_resistance_quality(ready, campaign)
    record = attached.extra["virulence_resistance_quality"]
    assert record["virulence_optimized_for_humans"] is False
    assert record["hypothesis_supported"] is False
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_virulence_resistance_quality(attached, campaign)
