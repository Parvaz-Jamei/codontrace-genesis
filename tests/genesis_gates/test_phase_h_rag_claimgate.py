"""CI-visible Phase H honesty gate: RAG corpus + ClaimGate ceilings.

Fast: no multi-seed engine campaigns. Does not claim intelligence.
"""

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_h import collective_intelligence_candidate_checklist
from codontrace.genesis.rag import load_default_corpus, search_corpus


def test_phase_h_rag_corpus_and_claimgate_stay_honest() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 11
    goldsby = search_corpus("Goldsby Avida messaging division of labor", k=5)
    channon = search_corpus("Channon Tokyo Type 1", k=5)
    assert any("goldsby" in hit.document.doc_id for hit in goldsby.hits)
    assert any("channon" in hit.document.doc_id for hit in channon.hits)
    gate = ScientificClaimGate()
    for label in ("intelligence", "collective_intelligence", "agi"):
        assert gate.decide(ClaimRequest(label, goldsby.to_dict())).allowed is False
    checklist = collective_intelligence_candidate_checklist()
    assert checklist.claim_allowed is False
    assert checklist.auto_set_flags is False
    assert "ablation_result" in checklist.missing_flags
