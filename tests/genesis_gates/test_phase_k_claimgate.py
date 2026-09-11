"""CI-visible Phase K honesty gate: new surfaces never unlock CI.

Fast: smoke-scale campaigns only. Does not claim intelligence.
"""

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_k import (
    build_conflict_suppression_observation,
    run_evolved_coordination_instruction_experiment,
    run_goldsby_cpu_delay_specialist_campaign,
    run_multi_generation_price_analysis,
)
from codontrace.genesis.rag import load_default_corpus, search_corpus


def test_phase_k_smoke_never_earns_and_claimgate_stays_honest() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 16
    assert any(
        "goldsby" in hit.document.doc_id
        for hit in search_corpus("send retrieve broadcast coordination that pays", k=6).hits
    )
    coord = run_evolved_coordination_instruction_experiment(smoke=True)
    goldsby = run_goldsby_cpu_delay_specialist_campaign(smoke=True, delays=(0, 50))
    price = run_multi_generation_price_analysis(smoke=True)
    hooks = build_conflict_suppression_observation()
    gate = ScientificClaimGate()
    for payload in (coord.to_dict(), goldsby.to_dict(), price.to_dict(), hooks.to_dict()):
        assert payload["collective_intelligence"] is False
        for label in (
            "intelligence",
            "collective_intelligence",
            "agi",
            "tokyo_type1_passed",
            "avida_replacement",
        ):
            assert gate.decide(ClaimRequest(label, payload)).allowed is False
        assert (
            gate.decide(ClaimRequest("collective_intelligence_candidate", payload)).allowed
            is False
        )
    assert goldsby.is_goldsby_2012_pnas_experiment is False
    assert price.price_equation_complete is False
    assert hooks.conflict_suppression_endogenous is False
    assert hooks.major_transition_in_individuality is False
