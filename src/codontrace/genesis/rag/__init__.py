"""Literature RAG substrate for CodonTrace Genesis (Phase H).

Dependency-light research corpus + retriever. No vector database, no forced
ML dependencies. Claim ceiling remains documentation / measurement design:
retrieving a paper does **not** unlock ``collective_intelligence``,
``intelligence``, or AGI.
"""

from codontrace.genesis.rag.retriever import (
    CITE_SCHEMA_VERSION,
    CORPUS_SCHEMA_VERSION,
    DEFAULT_CORPUS_ID,
    RankedHit,
    ResearchCorpus,
    ResearchDocument,
    SearchResult,
    cite_sources,
    default_corpus_digest,
    ingest_document,
    load_default_corpus,
    load_default_documents,
    search_corpus,
)

__all__ = [
    "CITE_SCHEMA_VERSION",
    "CORPUS_SCHEMA_VERSION",
    "DEFAULT_CORPUS_ID",
    "RankedHit",
    "ResearchCorpus",
    "ResearchDocument",
    "SearchResult",
    "cite_sources",
    "default_corpus_digest",
    "ingest_document",
    "load_default_corpus",
    "load_default_documents",
    "search_corpus",
]
