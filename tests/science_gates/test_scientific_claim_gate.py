from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate


def test_scientific_claim_gate_allows_only_light_claims_from_smoke():
    gate = ScientificClaimGate()
    foundation = gate.decide(ClaimRequest("foundation_engine", {}))
    discovery = gate.decide(ClaimRequest("discovery_candidate", {"d0_baseline": False}))
    causal = gate.decide(
        ClaimRequest("causal_prediction_supported", {"causal_intervention": False})
    )
    alife = gate.decide(ClaimRequest("artificial_life_candidate", {"body_boundary": False}))
    full = gate.decide(ClaimRequest("full_GENESIS_engine", {"all_protocols_complete": True}))

    assert foundation.allowed is True
    assert discovery.allowed is False
    assert causal.allowed is False
    assert alife.allowed is False
    assert full.allowed is False
    assert full.level == "not_claimed"
