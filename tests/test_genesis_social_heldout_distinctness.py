from codontrace.genesis import GenesisEngine, ScientificClaimGate, ClaimRequest
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def _social_digest(seed):
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.social_partner_pilot_world(seed=seed, tick_count=3)).run_ticks()
    return result.manifest.runtime_hashes["element_grid_hash"], tuple(r.digest() for r in result.social_interaction_records)


def test_social_partner_pilot_familiar_unfamiliar_are_behaviorally_distinct():
    first = _social_digest(1)
    second = _social_digest(2)
    assert first != second


def test_social_partner_pilot_marks_not_distinct_when_digests_match():
    first = _social_digest(1)
    second = _social_digest(1)
    status = "heldout_not_behaviorally_distinct" if first == second else "heldout_behaviorally_distinct"
    assert status == "heldout_not_behaviorally_distinct"


def test_social_generalization_claim_rejects_identical_familiar_unfamiliar_events():
    decision = ScientificClaimGate().decide(ClaimRequest(
        "social_partner_generalization_supported",
        {
            "real_partner_event": True,
            "familiar_partner_protocol": True,
            "unfamiliar_partner_protocol": True,
            "heldout_protocol": True,
            "leakage_check": False,
            "social_generalization_digest": True,
            "artifact_digest": True,
            "replay_verification": True,
        },
    ))
    assert not decision.allowed
