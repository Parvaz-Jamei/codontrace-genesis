"""Phase 17: Price≠causality refusal assay (Challenge S8)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_price_causality_caution,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_price_caution import run_price_causality_caution_assay


def test_price_summary_never_proves_major_transition() -> None:
    result = run_price_causality_caution_assay(
        seeds=(1, 2, 3),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.refusal_assay_passed is True
    assert result.price_summary_is_causal is False
    assert result.major_transition_proved is False
    assert result.red_queen_proved is False
    assert result.summary_digest
    payload = result.to_dict()
    assert payload["price_summary_is_causal"] is False
    assert payload["major_transition_proved"] is False


def test_major_transition_claim_stays_blocked() -> None:
    with pytest.raises(ConfigurationError, match="major_transition_proved"):
        assert_claim_allowed("major_transition_proved")


def test_attach_price_caution_requires_prereg() -> None:
    assay = run_price_causality_caution_assay(seeds=(4, 5))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does a Price summary prove a major transition?",
        context_of_use="Digital Price≠causality caution only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.1,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_price_causality_caution(bundle, assay)
    prereg = host_parasite_preregistration(
        question_of_interest="Does a Price summary prove a major transition?",
        context_of_use="Digital Price≠causality caution only.",
        arms=("price_caution",),
        success_metrics=("summary_digest", "refusal_assay_passed"),
        forbidden_claims=("major_transition_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_price_causality_caution(ready, assay)
    record = attached.extra["price_causality_caution"]
    assert record["major_transition_proved"] is False
    assert record["price_summary_is_causal"] is False
    assert audit_bundle(attached).achieved_level == before
