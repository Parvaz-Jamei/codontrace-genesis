"""Phase 10: genome-aware dual digests on Zaman freeze/replay/reciprocal."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_genome_zaman_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_genome_zaman import (
    run_genome_zaman_campaign,
)


def test_genome_zaman_arms_distinct_with_dual_digests() -> None:
    result = run_genome_zaman_campaign(
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
    assert len(set(payload["arm_digests"].values())) == 3
    assert payload["complexity_emergence_proved"] is False
    assert payload["red_queen_proved"] is False
    assert payload["raises_claim_ladder"] is False
    assert payload["repertoire_campaign_digest"]


def test_freeze_vs_replay_vs_reciprocal_genome_semantics() -> None:
    result = run_genome_zaman_campaign(seeds=(3,), steps=4)
    by_arm = {arm.arm: arm for arm in result.arm_results}
    freeze = by_arm["freeze_parasites"].seed_outcomes[0].genomes
    replay = by_arm["replay_parasite_schedule"].seed_outcomes[0].genomes
    recip = by_arm["reciprocal_coevolution"].seed_outcomes[0].genomes
    # Freeze: parasite digest trajectory is a singleton repeated.
    assert len(set(freeze.parasite_digest_trajectory)) == 1
    # Replay: predetermined schedule changes parasite digests without host coupling.
    assert len(set(replay.parasite_digest_trajectory)) > 1
    # Reciprocal: both trajectories change; schedule digests differ across arms.
    assert len(set(recip.parasite_digest_trajectory)) > 1
    assert len(set(recip.host_digest_trajectory)) > 1
    schedule_digests = {
        freeze.parasite_schedule_digest,
        replay.parasite_schedule_digest,
        recip.parasite_schedule_digest,
    }
    assert len(schedule_digests) == 3
    assert freeze.parasite_genome_frozen is True
    assert freeze.parasite_schedule_predetermined is False
    assert replay.parasite_schedule_predetermined is True
    assert recip.reciprocal_genome_update is True
    # Host digests must move under freeze while parasite stays fixed.
    assert len(set(freeze.host_digest_trajectory)) > 1
    # Repertoire continuity still present.
    assert "digest" in freeze.to_dict()
    for arm in result.arm_results:
        body = arm.seed_outcomes[0].repertoire.to_dict()
        assert body["complexity_emergence_proved"] is False
        assert "digest" in body
        g = arm.seed_outcomes[0].genomes.to_dict()
        assert g["primary_digest_surface"] == "semantic_genome"
        assert g["genome_program_identity_is_secondary"] is True
        assert g["complexity_emergence_proved"] is False
        assert g["red_queen_proved"] is False


def test_genome_zaman_deterministic() -> None:
    a = run_genome_zaman_campaign(seeds=(11, 22), steps=3)
    b = run_genome_zaman_campaign(seeds=(11, 22), steps=3)
    assert a.to_dict()["campaign_digest"] == b.to_dict()["campaign_digest"]
    assert a.to_dict()["arm_digests"] == b.to_dict()["arm_digests"]


def test_genome_zaman_refuses_high_ceiling() -> None:
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_genome_zaman_campaign(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )
    with pytest.raises(ConfigurationError, match="distinct"):
        run_genome_zaman_campaign(
            seeds=(1,),
            arms=("freeze_parasites",),
            request_claim_ceiling="candidate_evidence",
        )


def test_attach_genome_zaman_requires_prereg_and_does_not_raise_ladder() -> None:
    campaign = run_genome_zaman_campaign(seeds=(5,), steps=2)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do genome digests differ across Zaman arms?",
        context_of_use="Digital genome Zaman analogue only. Complexity unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_genome_zaman_campaign(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Do genome digests differ across Zaman arms?",
        context_of_use="Digital genome Zaman analogue only. Complexity unproved.",
        arms=("freeze_parasites", "replay_parasite_schedule", "reciprocal_coevolution"),
        success_metrics=("arm_digest_distinctness", "parasite_schedule_digest"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_genome_zaman_campaign(ready, campaign)
    assert "genome_zaman_campaign" in attached.extra
    assert attached.extra["genome_zaman_campaign"]["complexity_emergence_proved"] is False
    assert attached.extra["genome_zaman_campaign"]["red_queen_proved"] is False
    assert attached.extra["genome_zaman_campaign"]["preregistration_digest"] == str(
        prereg.to_dict()["digest"]
    )
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_genome_zaman_campaign(attached, campaign)
