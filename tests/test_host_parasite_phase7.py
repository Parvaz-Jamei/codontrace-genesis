"""Phase 7: Zaman freeze / replay / reciprocal + repertoire richness."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_zaman_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_zaman import (
    ZAMAN_ARMS,
    run_zaman_three_arm_campaign,
)


def test_zaman_arms_are_three_distinct() -> None:
    assert ZAMAN_ARMS == frozenset(
        {
            "freeze_parasites",
            "replay_parasite_schedule",
            "reciprocal_coevolution",
        }
    )
    result = run_zaman_three_arm_campaign(
        seeds=(7, 8),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    payload = result.to_dict()
    assert payload["arms"] == [
        "freeze_parasites",
        "replay_parasite_schedule",
        "reciprocal_coevolution",
    ]
    assert payload["arms_are_distinct"] is True
    digests = list(payload["arm_digests"].values())
    assert len(set(digests)) == 3
    assert payload["complexity_emergence_proved"] is False
    assert payload["red_queen_proved"] is False
    assert payload["raises_claim_ladder"] is False


def test_repertoire_richness_analogue_present() -> None:
    result = run_zaman_three_arm_campaign(seeds=(3,), steps=4)
    by_arm = {arm.arm: arm for arm in result.arm_results}
    # Replay without parasite pressure keeps cardinality; freeze expands under
    # fixed pressure; reciprocal expands faster (budget 2) — Zaman-style order.
    assert (
        by_arm["replay_parasite_schedule"].mean_final_richness
        < by_arm["freeze_parasites"].mean_final_richness
    )
    assert (
        by_arm["freeze_parasites"].mean_final_richness
        <= by_arm["reciprocal_coevolution"].mean_final_richness
    )
    for arm in result.arm_results:
        body = arm.seed_outcomes[0].repertoire.to_dict()
        assert body["complexity_emergence_proved"] is False
        assert len(body["richness_trajectory"]) >= 2
        assert body["final_richness"] >= 1
        assert "digest" in body


def test_zaman_deterministic_digests() -> None:
    a = run_zaman_three_arm_campaign(seeds=(11, 22), steps=3)
    b = run_zaman_three_arm_campaign(seeds=(11, 22), steps=3)
    assert a.to_dict()["campaign_digest"] == b.to_dict()["campaign_digest"]
    assert a.to_dict()["arm_digests"] == b.to_dict()["arm_digests"]


def test_zaman_refuses_high_ceiling_and_proved_complexity_language() -> None:
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_zaman_three_arm_campaign(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )
    result = run_zaman_three_arm_campaign(seeds=(1,), steps=2)
    assert result.complexity_emergence_proved is False
    text = str(result.to_dict()).lower()
    assert "proved complexity" not in text
    assert "complexity_emergence_proved': true" not in text
    assert "complexity_emergence_proved': True" not in text


def test_attach_zaman_requires_prereg_and_does_not_raise_ladder() -> None:
    campaign = run_zaman_three_arm_campaign(seeds=(5,), steps=2)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do freeze, replay, and reciprocal digests differ?",
        context_of_use="Digital Zaman analogue only. Complexity unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_zaman_campaign(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Do freeze, replay, and reciprocal digests differ?",
        context_of_use="Digital Zaman analogue only. Complexity unproved.",
        arms=("freeze_parasites", "replay_parasite_schedule", "reciprocal_coevolution"),
        success_metrics=("arm_digest_distinctness", "mean_final_richness"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_zaman_campaign(ready, campaign)
    assert "zaman_three_arm_campaign" in attached.extra
    assert attached.extra["zaman_three_arm_campaign"]["complexity_emergence_proved"] is False
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_zaman_campaign(attached, campaign)


def test_single_arm_candidate_evidence_refused_when_not_distinct() -> None:
    # One arm alone cannot satisfy arms_are_distinct for candidate_evidence.
    with pytest.raises(ConfigurationError, match="distinct"):
        run_zaman_three_arm_campaign(
            seeds=(1,),
            arms=("freeze_parasites",),
            request_claim_ceiling="candidate_evidence",
        )
