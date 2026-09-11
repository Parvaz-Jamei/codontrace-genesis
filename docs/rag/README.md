# CodonTrace Genesis literature RAG (Phase H)

Dependency-light research corpus + retriever for **CodonTrace Genesis**.
No vector database. No forced ML dependencies. Retrieving a paper does
**not** unlock `collective_intelligence`, `intelligence`, or AGI.

Machine seed: [`src/codontrace/genesis/rag/corpus/seed.jsonl`](../../src/codontrace/genesis/rag/corpus/seed.jsonl)
(shipped as package data). Human digests in [`corpus/`](corpus/).

## Query

```python
from codontrace.genesis import search_corpus, cite_sources, ingest_document

hits = search_corpus("how to get collective intelligence evidence", k=8)
for cite in cite_sources(hits):
    print(cite)
```

`examples/genesis_rag_query.py` prints ranked cites plus the
`collective_intelligence_candidate` gap checklist (flags are listed, never
auto-set).

Public API: `ingest_document`, `search_corpus(query, k)`, `cite_sources`.
Search ranking is deterministic for a fixed corpus (TF-IDF + feature-hash +
keyword overlap). Each `SearchResult` has a replay digest.

## Papers in the seed

See [`PHASE_H_CI_AI_PATH.md`](../PHASE_H_CI_AI_PATH.md) for the has / lacks /
next-experiment map. Seed `doc_id`s:

- `miikkulainen_forrest_2021_nature_mi`
- `goldsby_2012_pnas_task_switching`
- `goldsby_ofria_avida_messaging_germline`
- `channon_2024_tokyo_type1`
- `soros_stanley_2014_chromaria`
- `stanley_2017_open_endedness_creative_intelligence`
- `szathmary_maynard_smith_michod_transitions`
- `jaxlife_2024`
- `cao_yang_2026_vocabulary_verifier_gaps`
- `chaturvedi_2026_role_mls`
- `conlin_2023_dol_multicellularity_avida`

## Claim ceiling

Documentation / `runtime_observation`. ClaimGate unchanged in the strict
direction.
