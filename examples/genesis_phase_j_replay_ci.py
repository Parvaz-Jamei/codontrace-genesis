"""CodonTrace Genesis Phase J replay-verified CI candidate smoke.

Print-only. Builds a smoke-scale replay-verified pack (independent digest
re-execution), prints Price-equation covariance bookkeeping, and shows that
ClaimGate candidate flags are still unearned at smoke scale even when
digests match. Does not write files, start a UI, set ClaimGate flags, or
claim intelligence, collective intelligence, Tokyo Type 1 passed, or Avida
replacement.
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
from codontrace.genesis.phase_j import build_replay_verified_ci_candidate_pack
from codontrace.genesis.rag import cite_sources, search_corpus


def main() -> None:
    gate = ScientificClaimGate()
    print("product", "CodonTrace Genesis")
    print("phase", "J")
    hits = search_corpus("Price equation covariance Okasha MLS1 replay verification", k=6)
    print("ranked_cites")
    for index, citation in enumerate(cite_sources(hits), start=1):
        print(f"  {index}. {citation}")
    pack = build_replay_verified_ci_candidate_pack(
        smoke=True, re_execute_replay=True, include_price_equation=True
    )
    flags = pack.as_mapping()
    print("replay_matched", pack.replay.matched)
    print("replay_re_executed", pack.replay.re_executed)
    print("replay_earns", pack.replay.earns_replay_verification())
    print("smoke_earned_any", any(flags.values()))
    print("candidate_allowed", pack.candidate_allowed)
    print("missing_flags", ",".join(pack.candidate_missing_flags))
    if pack.price is not None:
        print("price_status", pack.price.price_equation_status)
        print("price_mls1_identity_holds", pack.price.mls1_identity_holds)
        print("price_mean_mls_between", pack.price.mean_mls_between_mls1)
        print("major_transition_in_individuality", pack.price.major_transition_in_individuality)
    payload = pack.to_dict()
    print(
        "collective_intelligence_allowed",
        gate.decide(ClaimRequest("collective_intelligence", payload)).allowed,
    )
    print("intelligence_allowed", gate.decide(ClaimRequest("intelligence", payload)).allowed)
    print(
        "candidate_from_smoke_payload_allowed",
        gate.decide(ClaimRequest("collective_intelligence_candidate", flags)).allowed,
    )
    print("agi_allowed", gate.decide(ClaimRequest("agi", {})).allowed)
    print("tokyo_type1_passed_allowed", gate.decide(ClaimRequest("tokyo_type1_passed", {})).allowed)
    print("avida_replacement_allowed", gate.decide(ClaimRequest("avida_replacement", {})).allowed)


if __name__ == "__main__":
    main()
