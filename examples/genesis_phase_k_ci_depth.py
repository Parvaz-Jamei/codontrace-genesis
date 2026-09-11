"""CodonTrace Genesis Phase K CI-depth smoke.

Print-only. Runs evolved coordination-instruction, Goldsby CPU-delay,
multi-generation Price (transmission term), and Michod/Conlin conflict
hooks at smoke scale. Shows ClaimGate still blocks bare CI / intelligence.
Does not write files, start a UI, set ClaimGate flags, or claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_k import (
    GOLDSBY_RESEARCH_REPLICATE_COUNT,
    build_conflict_suppression_observation,
    run_evolved_coordination_instruction_experiment,
    run_goldsby_cpu_delay_specialist_campaign,
    run_multi_generation_price_analysis,
)
from codontrace.genesis.rag import cite_sources, search_corpus


def main() -> None:
    gate = ScientificClaimGate()
    print("product", "CodonTrace Genesis")
    print("phase", "K")
    hits = search_corpus(
        "evolved send retrieve broadcast Goldsby CPU delay Price transmission "
        "Michod conflict suppression Conlin revertant",
        k=8,
    )
    print("ranked_cites")
    for index, citation in enumerate(cite_sources(hits), start=1):
        print(f"  {index}. {citation}")
    coord = run_evolved_coordination_instruction_experiment(smoke=True)
    goldsby = run_goldsby_cpu_delay_specialist_campaign(smoke=True)
    price = run_multi_generation_price_analysis(smoke=True)
    hooks = build_conflict_suppression_observation()
    print("coordination_status", coord.coordination_status)
    print("coordination_mean_ablation_drop", coord.mean_ablation_drop)
    print("coordination_uses_phase_e", coord.uses_phase_e_messaging)
    print("goldsby_research_replicate_default", GOLDSBY_RESEARCH_REPLICATE_COUNT)
    print("goldsby_smoke_replicates", len(goldsby.seeds))
    print("goldsby_is_pnas_2012", goldsby.is_goldsby_2012_pnas_experiment)
    print("price_transmission_estimated", price.transmission_term_estimated)
    print("price_equation_complete", price.price_equation_complete)
    print("price_identity_holds", price.transmission_identity_holds)
    print("conflict_suppression_endogenous", hooks.conflict_suppression_endogenous)
    print("major_transition_in_individuality", hooks.major_transition_in_individuality)
    payload = coord.to_dict()
    print(
        "collective_intelligence_allowed",
        gate.decide(ClaimRequest("collective_intelligence", payload)).allowed,
    )
    print("intelligence_allowed", gate.decide(ClaimRequest("intelligence", payload)).allowed)
    print(
        "candidate_from_smoke_payload_allowed",
        gate.decide(ClaimRequest("collective_intelligence_candidate", payload)).allowed,
    )
    print("agi_allowed", gate.decide(ClaimRequest("agi", {})).allowed)
    print("tokyo_type1_passed_allowed", gate.decide(ClaimRequest("tokyo_type1_passed", {})).allowed)
    print("avida_replacement_allowed", gate.decide(ClaimRequest("avida_replacement", {})).allowed)


if __name__ == "__main__":
    main()
