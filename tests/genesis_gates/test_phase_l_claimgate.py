"""CI-visible Phase L honesty gate: Avida analogs never unlock CI.

Fast: smoke-scale campaigns only. Does not claim intelligence.
"""

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_k import run_evolved_coordination_instruction_experiment
from codontrace.genesis.phase_l import (
    feed_phase_k_coordination_ablation_evidence,
    run_goldsby_aligned_specialist_campaign,
    run_organism_messaging_fidelity_experiment,
)
from codontrace.genesis.rag import load_default_corpus, search_corpus


def test_phase_l_smoke_never_earns_and_claimgate_stays_honest() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 18
    assert any(
        "organism_messaging" in hit.document.doc_id
        for hit in search_corpus("ORGANISM_MESSAGING send-msg retrieve-msg FIFO", k=6).hits
    )
    messaging = run_organism_messaging_fidelity_experiment(smoke=True)
    goldsby = run_goldsby_aligned_specialist_campaign(smoke=True, delays=(0, 50))
    feed = feed_phase_k_coordination_ablation_evidence(
        run_evolved_coordination_instruction_experiment(smoke=True)
    )
    gate = ScientificClaimGate()
    for payload in (messaging.to_dict(), goldsby.to_dict(), feed.to_dict()):
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
    assert messaging.is_avida_cpp_port is False
    assert goldsby.is_goldsby_2012_pnas_experiment is False
    assert feed.claim_gate_ablation_result_set is False
    assert all(value is False for value in feed.as_mapping().values())
