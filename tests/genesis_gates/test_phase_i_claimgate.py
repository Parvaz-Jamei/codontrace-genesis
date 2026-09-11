"""CI-visible Phase I honesty gate: RAG cites + ClaimGate ceilings.

Fast: smoke-scale harnesses only. Does not claim intelligence.
"""

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_i import (
    build_export_of_fitness_observation,
    earn_collective_intelligence_candidate_flags,
    run_evolved_division_of_labor_experiment,
    run_heldout_unfamiliar_partner_experiment,
    run_mls_evolutionary_outcome_experiment,
)
from codontrace.genesis.rag import load_default_corpus, search_corpus


def test_phase_i_smoke_never_earns_flags_and_claimgate_stays_honest() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 14
    assert any(
        "okasha" in hit.document.doc_id
        for hit in search_corpus("Okasha MLS2 evolutionary outcome", k=5).hits
    )
    heldout = run_heldout_unfamiliar_partner_experiment(smoke=True)
    dol = run_evolved_division_of_labor_experiment(smoke=True)
    mls = run_mls_evolutionary_outcome_experiment(smoke=True)
    eof = build_export_of_fitness_observation(mls)
    earned = earn_collective_intelligence_candidate_flags(
        heldout=heldout, evolved_dol=dol, mls=mls, export_of_fitness=eof, smoke=True
    )
    assert all(value is False for value in earned.as_mapping().values())
    assert eof.major_transition_in_individuality is False
    gate = ScientificClaimGate()
    payload = heldout.to_dict()
    for label in ("intelligence", "collective_intelligence", "agi", "tokyo_type1_passed"):
        assert gate.decide(ClaimRequest(label, payload)).allowed is False
    assert gate.decide(ClaimRequest("collective_intelligence_candidate", payload)).allowed is False
