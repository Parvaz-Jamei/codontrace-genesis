"""CodonTrace Genesis Phase H RAG query + CI-candidate gap checklist.

Print-only. Queries the shipped literature corpus for how to get collective
intelligence evidence, prints ranked cites, and lists missing ClaimGate flags.
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
from codontrace.genesis.phase_h import (
    format_collective_intelligence_candidate_checklist,
)
from codontrace.genesis.rag import cite_sources, load_default_corpus, search_corpus

QUERY = "how to get collective intelligence evidence"


def main() -> None:
    corpus = load_default_corpus()
    result = search_corpus(QUERY, k=8, corpus=corpus)
    gate = ScientificClaimGate()
    payload = result.to_dict()
    print("product", "CodonTrace Genesis")
    print("corpus_size", len(corpus))
    print("corpus_digest_prefix", corpus.digest()[:16])
    print("query", QUERY)
    print("search_digest_prefix", result.digest[:16])
    print("ranked_cites")
    for index, citation in enumerate(cite_sources(result), start=1):
        hit = result.hits[index - 1]
        print(f"  {index}. {citation}")
        print(f"     lacks: {hit.document.codontrace_lacks[:160]}")
        print(f"     next: {hit.document.next_experiment[:160]}")
    print("gap_checklist")
    for line in format_collective_intelligence_candidate_checklist().splitlines():
        print(" ", line)
    print(
        "collective_intelligence_allowed",
        gate.decide(ClaimRequest("collective_intelligence", payload)).allowed,
    )
    print("intelligence_allowed", gate.decide(ClaimRequest("intelligence", payload)).allowed)
    print(
        "candidate_allowed",
        gate.decide(ClaimRequest("collective_intelligence_candidate", payload)).allowed,
    )
    print("agi_allowed", gate.decide(ClaimRequest("agi", {})).allowed)


if __name__ == "__main__":
    main()
