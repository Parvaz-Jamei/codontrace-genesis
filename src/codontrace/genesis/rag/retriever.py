"""Keyword + TF-IDF (with optional feature-hash) retriever for literature digests.

Public functions: ingest a document, ``search(query, k)``, and cite sources.
Ranking is deterministic for a fixed corpus so replay digests stay stable.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

CORPUS_SCHEMA_VERSION = "codontrace_genesis_rag_corpus_v1"
CITE_SCHEMA_VERSION = "codontrace_genesis_rag_cite_v1"
DEFAULT_CORPUS_ID = "codontrace_genesis_phase_h_literature_seed"
_PACKAGE_CORPUS = "corpus/seed.jsonl"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HASH_DIM = 64
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "not",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "its",
        "into",
        "than",
        "then",
        "via",
        "vs",
    }
)


def tokenize(text: str) -> tuple[str, ...]:
    """Lowercase alphanumeric tokens with a tiny stopword list."""

    return tuple(
        token
        for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOPWORDS and len(token) >= 2
    )


def _hash_embedding(tokens: Sequence[str]) -> tuple[float, ...]:
    """Signed feature-hash embedding. No learned weights; replay-stable."""

    vec = [0.0] * _HASH_DIM
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % _HASH_DIM
        sign = 1.0 if digest[2] & 1 else -1.0
        vec[index] += sign
    norm = math.sqrt(sum(item * item for item in vec))
    if norm <= 0.0:
        return tuple(vec)
    return tuple(round(item / norm, 12) for item in vec)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return round(float(dot), 12)


def _tfidf_vector(
    tokens: Sequence[str],
    idf: Mapping[str, float],
    vocabulary: Sequence[str],
) -> tuple[float, ...]:
    counts = Counter(tokens)
    length = max(1, len(tokens))
    raw: list[float] = []
    for term in vocabulary:
        tf = counts.get(term, 0) / length
        weight = (1.0 + math.log(counts[term])) * idf.get(term, 0.0) if counts.get(term) else 0.0
        raw.append(weight if counts.get(term) else tf * idf.get(term, 0.0))
    norm = math.sqrt(sum(item * item for item in raw))
    if norm <= 0.0:
        return tuple(raw)
    return tuple(round(item / norm, 12) for item in raw)


@dataclass(frozen=True, slots=True)
class ResearchDocument:
    """One citable literature digest mapped onto CodonTrace Genesis gaps."""

    doc_id: str
    title: str
    authors: tuple[str, ...]
    year: int
    venue: str
    doi: str = ""
    arxiv: str = ""
    tags: tuple[str, ...] = ()
    summary: str = ""
    key_claims: tuple[str, ...] = ()
    codontrace_has: str = ""
    codontrace_lacks: str = ""
    next_experiment: str = ""
    claim_ceiling: str = "runtime_observation"
    schema_version: str = CORPUS_SCHEMA_VERSION
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.doc_id or not self.title:
            raise ConfigurationError("ResearchDocument requires doc_id and title.")
        object.__setattr__(self, "authors", tuple(str(item) for item in self.authors))
        object.__setattr__(self, "tags", tuple(str(item) for item in self.tags))
        object.__setattr__(self, "key_claims", tuple(str(item) for item in self.key_claims))
        if self.year < 1800 or self.year > 2100:
            raise ConfigurationError("ResearchDocument.year is out of range.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("ResearchDocument digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def searchable_text(self) -> str:
        parts = (
            self.doc_id,
            self.title,
            " ".join(self.authors),
            self.venue,
            self.doi,
            self.arxiv,
            " ".join(self.tags),
            self.summary,
            " ".join(self.key_claims),
            self.codontrace_has,
            self.codontrace_lacks,
            self.next_experiment,
        )
        return " ".join(part for part in parts if part)

    def citation(self) -> str:
        authors = ", ".join(self.authors) if self.authors else "Unknown"
        ident = self.doi or (f"arXiv:{self.arxiv}" if self.arxiv else "")
        suffix = f" {ident}." if ident else ""
        return f"{authors} ({self.year}). {self.title}. {self.venue}.{suffix}"

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "doc_id": self.doc_id,
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "arxiv": self.arxiv,
            "tags": list(self.tags),
            "summary": self.summary,
            "key_claims": list(self.key_claims),
            "codontrace_has": self.codontrace_has,
            "codontrace_lacks": self.codontrace_lacks,
            "next_experiment": self.next_experiment,
            "claim_ceiling": self.claim_ceiling,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> ResearchDocument:
        authors = data.get("authors", ())
        tags = data.get("tags", ())
        claims = data.get("key_claims", ())
        return cls(
            doc_id=str(data.get("doc_id", "")),
            title=str(data.get("title", "")),
            authors=tuple(str(item) for item in authors) if isinstance(authors, Sequence) else (),
            year=int(str(data.get("year", 0) or 0)),
            venue=str(data.get("venue", "")),
            doi=str(data.get("doi", "") or ""),
            arxiv=str(data.get("arxiv", "") or ""),
            tags=tuple(str(item) for item in tags) if isinstance(tags, Sequence) else (),
            summary=str(data.get("summary", "") or ""),
            key_claims=tuple(str(item) for item in claims) if isinstance(claims, Sequence) else (),
            codontrace_has=str(data.get("codontrace_has", "") or ""),
            codontrace_lacks=str(data.get("codontrace_lacks", "") or ""),
            next_experiment=str(data.get("next_experiment", "") or ""),
            claim_ceiling=str(
                data.get("claim_ceiling", "runtime_observation") or "runtime_observation"
            ),
        )


@dataclass(frozen=True, slots=True)
class RankedHit:
    """One ranked retrieval hit with a deterministic cite string."""

    rank: int
    score: float
    tfidf_score: float
    hash_score: float
    document: ResearchDocument

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", round(require_finite_float("score", self.score), 10))
        object.__setattr__(
            self, "tfidf_score", round(require_finite_float("tfidf_score", self.tfidf_score), 10)
        )
        object.__setattr__(
            self, "hash_score", round(require_finite_float("hash_score", self.hash_score), 10)
        )
        if self.rank < 1:
            raise ConfigurationError("RankedHit.rank must be >= 1.")

    def citation(self) -> str:
        return self.document.citation()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "rank": self.rank,
            "score": self.score,
            "tfidf_score": self.tfidf_score,
            "hash_score": self.hash_score,
            "doc_id": self.document.doc_id,
            "title": self.document.title,
            "citation": self.citation(),
            "document_digest": self.document.digest,
            "codontrace_lacks": self.document.codontrace_lacks,
            "next_experiment": self.document.next_experiment,
            "claim_ceiling": self.document.claim_ceiling,
        }


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Ranked hits plus a replay digest of the query and ordered cites."""

    query: str
    k: int
    hits: tuple[RankedHit, ...]
    corpus_digest: str
    schema_version: str = CITE_SCHEMA_VERSION
    digest: str = ""

    def __post_init__(self) -> None:
        if self.k < 1:
            raise ConfigurationError("SearchResult.k must be >= 1.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("SearchResult digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def citations(self) -> tuple[str, ...]:
        return tuple(hit.citation() for hit in self.hits)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "query": self.query,
            "k": self.k,
            "hits": [hit.to_dict() for hit in self.hits],
            "corpus_digest": self.corpus_digest,
            "collective_intelligence": False,
            "intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


class ResearchCorpus:
    """In-memory literature corpus with deterministic TF-IDF + hash search."""

    def __init__(
        self,
        documents: Sequence[ResearchDocument] = (),
        *,
        corpus_id: str = DEFAULT_CORPUS_ID,
    ) -> None:
        self.corpus_id = corpus_id
        self._documents: list[ResearchDocument] = []
        self._by_id: dict[str, ResearchDocument] = {}
        self._token_cache: dict[str, tuple[str, ...]] = {}
        self._idf: dict[str, float] = {}
        self._vocabulary: tuple[str, ...] = ()
        self._tfidf: dict[str, tuple[float, ...]] = {}
        self._hashes: dict[str, tuple[float, ...]] = {}
        for document in documents:
            self.ingest(document, rebuild=False)
        if self._documents:
            self._rebuild_index()

    def __len__(self) -> int:
        return len(self._documents)

    def documents(self) -> tuple[ResearchDocument, ...]:
        return tuple(self._documents)

    def digest(self) -> str:
        return canonical_digest(
            {
                "corpus_id": self.corpus_id,
                "schema_version": CORPUS_SCHEMA_VERSION,
                "documents": [item.digest for item in self._documents],
            }
        )

    def ingest(self, document: ResearchDocument, *, rebuild: bool = True) -> ResearchDocument:
        """Insert or replace a digest. Rebuilds the index unless ``rebuild=False``."""

        if document.doc_id in self._by_id:
            self._documents = [item for item in self._documents if item.doc_id != document.doc_id]
        self._documents.append(document)
        self._documents.sort(key=lambda item: item.doc_id)
        self._by_id[document.doc_id] = document
        if rebuild:
            self._rebuild_index()
        return document

    def _rebuild_index(self) -> None:
        self._token_cache = {
            item.doc_id: tokenize(item.searchable_text()) for item in self._documents
        }
        document_count = max(1, len(self._documents))
        df: Counter[str] = Counter()
        for tokens in self._token_cache.values():
            df.update(set(tokens))
        self._idf = {
            term: math.log((1.0 + document_count) / (1.0 + count)) + 1.0
            for term, count in df.items()
        }
        self._vocabulary = tuple(sorted(self._idf))
        self._tfidf = {
            doc_id: _tfidf_vector(tokens, self._idf, self._vocabulary)
            for doc_id, tokens in self._token_cache.items()
        }
        self._hashes = {
            doc_id: _hash_embedding(tokens) for doc_id, tokens in self._token_cache.items()
        }

    def search(self, query: str, k: int = 5) -> SearchResult:
        """Rank documents for ``query``. Deterministic: score desc, then ``doc_id``."""

        if k < 1:
            raise ConfigurationError("search k must be >= 1.")
        if not self._documents:
            raise ConfigurationError("ResearchCorpus is empty.")
        query_tokens = tokenize(query)
        query_tfidf = _tfidf_vector(query_tokens, self._idf, self._vocabulary)
        query_hash = _hash_embedding(query_tokens)
        query_set = set(query_tokens)
        scored: list[tuple[float, float, float, str]] = []
        for document in self._documents:
            tfidf = _cosine(query_tfidf, self._tfidf[document.doc_id])
            hashed = _cosine(query_hash, self._hashes[document.doc_id])
            overlap = len(query_set & set(self._token_cache[document.doc_id]))
            title_hits = len(
                query_set & set(tokenize(document.title + " " + " ".join(document.tags)))
            )
            haystack = document.searchable_text().lower()
            phrase_hits = 0
            query_tokens_seq = list(query_tokens)
            for index in range(len(query_tokens_seq) - 1):
                phrase = f"{query_tokens_seq[index]} {query_tokens_seq[index + 1]}"
                if phrase in haystack:
                    phrase_hits += 1
            score = (
                0.62 * tfidf
                + 0.14 * hashed
                + 0.08 * overlap
                + 0.06 * title_hits
                + 0.10 * phrase_hits
            )
            scored.append((round(score, 10), round(tfidf, 10), round(hashed, 10), document.doc_id))
        scored.sort(key=lambda item: (-item[0], item[3]))
        hits = tuple(
            RankedHit(
                rank=index + 1,
                score=row[0],
                tfidf_score=row[1],
                hash_score=row[2],
                document=self._by_id[row[3]],
            )
            for index, row in enumerate(scored[:k])
        )
        return SearchResult(query=query, k=k, hits=hits, corpus_digest=self.digest())


def ingest_document(
    document: ResearchDocument | Mapping[str, object],
    corpus: ResearchCorpus | None = None,
) -> ResearchCorpus:
    """Public ingest: accept a document or mapping and return the corpus."""

    resolved = corpus or ResearchCorpus()
    payload = (
        document
        if isinstance(document, ResearchDocument)
        else ResearchDocument.from_mapping(document)
    )
    resolved.ingest(payload)
    return resolved


def search_corpus(
    query: str,
    k: int = 5,
    *,
    corpus: ResearchCorpus | None = None,
) -> SearchResult:
    """Search the default literature seed unless a corpus is supplied."""

    resolved = corpus or load_default_corpus()
    return resolved.search(query, k=k)


def cite_sources(
    hits: SearchResult | Sequence[RankedHit] | Sequence[ResearchDocument],
) -> tuple[str, ...]:
    """Return ordered citation strings for a search result or document list."""

    if isinstance(hits, SearchResult):
        return hits.citations()
    citations: list[str] = []
    for item in hits:
        if isinstance(item, (RankedHit, ResearchDocument)):
            citations.append(item.citation())
        else:
            raise ConfigurationError(
                "cite_sources expects RankedHit, ResearchDocument, or SearchResult."
            )
    return tuple(citations)


def _package_jsonl_text() -> str:
    package = resources.files("codontrace.genesis.rag")
    target = package.joinpath(_PACKAGE_CORPUS)
    return target.read_text(encoding="utf-8")


def load_default_documents() -> tuple[ResearchDocument, ...]:
    """Load the shipped Phase H literature seed (JSONL package data)."""

    documents: list[ResearchDocument] = []
    for line in _package_jsonl_text().splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ConfigurationError("corpus JSONL rows must be objects.")
        documents.append(ResearchDocument.from_mapping(payload))
    if not documents:
        raise ConfigurationError("default RAG corpus is empty.")
    documents.sort(key=lambda item: item.doc_id)
    return tuple(documents)


def load_default_corpus() -> ResearchCorpus:
    return ResearchCorpus(load_default_documents())


def default_corpus_digest() -> str:
    return load_default_corpus().digest()


def ingest_markdown_dir(
    path: str | Path, *, corpus: ResearchCorpus | None = None
) -> ResearchCorpus:
    """Optional extra ingest from a markdown directory (repo ``docs/rag/corpus``)."""

    resolved = corpus or load_default_corpus()
    root = Path(path)
    if not root.is_dir():
        raise ConfigurationError(f"markdown corpus directory not found: {root}")
    for file_path in sorted(root.glob("*.md")):
        text = file_path.read_text(encoding="utf-8")
        doc_id = file_path.stem
        title = doc_id.replace("_", " ")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        resolved.ingest(
            ResearchDocument(
                doc_id=f"markdown:{doc_id}",
                title=title,
                authors=("CodonTrace Genesis literature digest",),
                year=2026,
                venue="docs/rag/corpus",
                tags=("markdown_overlay",),
                summary=text[:4000],
                codontrace_has="see shipped JSONL seed for structured has/lacks fields",
                codontrace_lacks="markdown overlay is a human-readable copy, not extra evidence",
                next_experiment="use the JSONL seed next_experiment fields",
                claim_ceiling="runtime_observation",
            )
        )
    return resolved


def iter_seed_mappings() -> Iterable[dict[str, JsonValue]]:
    for document in load_default_documents():
        yield document.to_dict()
