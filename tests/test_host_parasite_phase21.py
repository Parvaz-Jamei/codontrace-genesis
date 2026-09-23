"""Phase 21: multi-seed contingency / repeatability under parasitism (S1)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_multi_seed_contingency,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_contingency import (
    HYPOTHESIS,
    run_multi_seed_contingency_campaign,
)


def test_contingency_falsifies_parasites_always_raise_complexity() -> None:
    result = run_multi_seed_contingency_campaign(
        seeds=(1, 2, 3, 4, 5),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert result.failure_reason
    assert result.complexity_emergence_proved is False
    assert result.red_queen_proved is False
    assert result.seed_digests_are_distinct is True
    assert result.cross_seed_variance >= 0.0
    present = [o for o in result.seed_outcomes if o.arm == "parasite_present"]
    assert any(o.richness_delta <= 0 for o in present)
    assert any(o.contingent_seed for o in present)


def test_requires_at_least_three_seeds() -> None:
    with pytest.raises(ConfigurationError, match="at least 3 seeds"):
        run_multi_seed_contingency_campaign(seeds=(1, 2))


def test_attach_contingency_requires_prereg() -> None:
    campaign = run_multi_seed_contingency_campaign(seeds=(10, 11, 12))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Is complexity rise under parasitism seed-contingent?",
        context_of_use="S1 multi-seed contingency; complexity emergence unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_multi_seed_contingency(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Is complexity rise under parasitism seed-contingent?",
        context_of_use="S1 multi-seed contingency; complexity emergence unproved.",
        arms=("parasite_present", "parasite_absent"),
        success_metrics=("seed_digests_are_distinct", "cross_seed_variance"),
        forbidden_claims=("red_queen_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_multi_seed_contingency(ready, campaign)
    record = attached.extra["multi_seed_contingency"]
    assert record["complexity_emergence_proved"] is False
    assert record["raises_claim_ladder"] is False
    assert audit_bundle(attached).achieved_level == before
