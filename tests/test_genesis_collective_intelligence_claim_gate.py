from codontrace.genesis import ClaimRequest, ScientificClaimGate
from codontrace.genesis.collective_intelligence import (
    CollectiveAblationRecord,
    CollectiveCoordinationRecord,
    CollectiveTaskSpec,
    RoleComplementarityRecord,
    build_collective_evidence_report,
)
from codontrace.genesis.social import SocialInteractionEvent, score_social_interactions


def test_capsule_learning_increases_transfer_score_not_full_cooperation_score():
    scores = score_social_interactions((SocialInteractionEvent("a", "b", "capsule_learning", capsule_delta=1.0, cooperation_score_delta=1.0),))
    assert scores.capsule_social_transfer_score > 0
    assert scores.non_capsule_cooperation_score == 0
    assert not scores.social_intelligence_claim_eligible


def test_collective_coordination_requires_non_capsule_joint_progress():
    task = CollectiveTaskSpec("t", True, ("collector", "depositor"))
    event = SocialInteractionEvent("a", "b", "cooperative_task_progress", cooperation_score_delta=1.0)
    report = build_collective_evidence_report(
        task,
        (event,),
        coordination_records=(CollectiveCoordinationRecord("t", 1, ("a", "b"), 1.0),),
        role_records=(RoleComplementarityRecord("t", "collector", "depositor", 1.0, "e"),),
        ablation_records=(CollectiveAblationRecord("a", "base", "abl", 1.0, "partner"),),
        familiar_partner_digest="fam",
        unfamiliar_partner_digest="unfam",
        replay_digest="replay",
    )
    assert report.claim_eligible


def test_social_intelligence_claim_rejects_capsule_only_evidence():
    decision = ScientificClaimGate().decide(ClaimRequest(
        "collective_intelligence_candidate",
        {
            "real_partner_event": True,
            "non_capsule_cooperation": False,
            "role_complementarity": True,
            "collective_coordination": True,
            "heldout_protocol": True,
            "familiar_partner_protocol": True,
            "unfamiliar_partner_protocol": True,
            "ablation_result": True,
            "collective_report_digest": True,
            "replay_verification": True,
        },
    ))
    assert not decision.allowed
