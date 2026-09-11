"""CodonTrace Genesis Phase L Avida-fidelity smoke.

Print-only. Runs ORGANISM_MESSAGING / DEME_GROUP analog, Goldsby-aligned
specialist measurement, and the optional Phase K coordination-ablation
evidence feed at smoke scale. Shows ClaimGate still blocks bare CI /
intelligence. Does not write files, start a UI, set ClaimGate flags, or
claim intelligence, collective intelligence, Tokyo Type 1 passed, or
Avida replacement.
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
from codontrace.genesis.phase_k import run_evolved_coordination_instruction_experiment
from codontrace.genesis.phase_l import (
    feed_phase_k_coordination_ablation_evidence,
    run_goldsby_aligned_specialist_campaign,
    run_organism_messaging_fidelity_experiment,
)
from codontrace.genesis.rag import cite_sources, search_corpus


def main() -> None:
    gate = ScientificClaimGate()
    print("product", "CodonTrace Genesis")
    print("phase", "L")
    hits = search_corpus(
        "Avida ORGANISM_MESSAGING DEME_GROUP send-msg retrieve-msg "
        "GERMLINE Goldsby CPU delay colony quota",
        k=8,
    )
    print("ranked_cites")
    for index, citation in enumerate(cite_sources(hits), start=1):
        print(f"  {index}. {citation}")
    messaging = run_organism_messaging_fidelity_experiment(smoke=True)
    goldsby = run_goldsby_aligned_specialist_campaign(smoke=True, delays=(0, 50))
    feed = feed_phase_k_coordination_ablation_evidence(
        run_evolved_coordination_instruction_experiment(smoke=True)
    )
    print("messaging_status", messaging.messaging_status)
    print("messaging_is_avida_cpp_port", messaging.is_avida_cpp_port)
    print("messaging_uses_fifo", messaging.uses_per_organism_fifo)
    print("messaging_uses_deme_group_analog", messaging.uses_deme_group_analog)
    print("goldsby_is_pnas_2012", goldsby.is_goldsby_2012_pnas_experiment)
    print("goldsby_treatments", len(goldsby.treatments))
    print("feed_auto_set", feed.claim_gate_flags_auto_set)
    print("feed_ablation_result_set", feed.claim_gate_ablation_result_set)
    print("feed_proposed_ablation_result", feed.as_mapping()["ablation_result"])
    payload = messaging.to_dict()
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
