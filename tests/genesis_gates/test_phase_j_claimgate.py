"""CI-visible Phase J honesty gate: replay never faked; ClaimGate ceilings.

Fast: smoke-scale pack only. Does not claim intelligence.
"""

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_j import build_replay_verified_ci_candidate_pack
from codontrace.genesis.rag import load_default_corpus, search_corpus


def test_phase_j_smoke_replay_never_earns_and_claimgate_stays_honest() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 15
    assert any(
        "price" in hit.document.doc_id
        for hit in search_corpus("Price equation covariance selection", k=5).hits
    )
    pack = build_replay_verified_ci_candidate_pack(
        smoke=True, re_execute_replay=True, include_price_equation=False
    )
    assert pack.replay.matched is True
    assert pack.replay.re_executed is True
    flags = pack.as_mapping()
    assert all(value is False for value in flags.values())
    assert pack.candidate_allowed is False
    gate = ScientificClaimGate()
    payload = pack.to_dict()
    for label in (
        "intelligence",
        "collective_intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
    ):
        assert gate.decide(ClaimRequest(label, payload)).allowed is False
    assert gate.decide(ClaimRequest("collective_intelligence_candidate", flags)).allowed is False
