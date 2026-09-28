"""Measurement definitions required before a discovery claim.

Genotype identity is the set of genome digests. Class sizes can swap without
changing that set. The locked synthetic Red Queen score stays below 0.20;
this module does not raise it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

RQ_SYNTHETIC_SCORE = -0.148
RQ_ACCEPT_THRESHOLD = 0.20


def genotype_set(digests: Iterable[str]) -> frozenset[str]:
    """Genome-digest set. Multiplicity is not part of the set."""

    return frozenset(str(item) for item in digests)


def same_genotype_set(
    left: Iterable[str],
    right: Iterable[str],
) -> bool:
    return genotype_set(left) == genotype_set(right)


def rq_barrier_holds(score: float = RQ_SYNTHETIC_SCORE) -> bool:
    """True while the score has not reached the accept threshold."""

    return float(score) < float(RQ_ACCEPT_THRESHOLD)


def process_cycle_complete(record: Mapping[str, object]) -> bool:
    """A phase record is auditable only when every required trail is present.

    Five pre-build rounds must differ from each other. Two post-build notes,
    one test note, and two result notes are required. Missing any of these
    keeps the phase incomplete.
    """

    rounds = record.get("pre_rounds")
    if not isinstance(rounds, Sequence) or isinstance(rounds, (str, bytes)):
        return False
    texts = [str(item).strip() for item in rounds]
    if len(texts) < 5 or any(not text for text in texts):
        return False
    if len(set(texts)) < 5:
        return False
    for key in ("post_build", "test_note", "result_notes"):
        if key not in record:
            return False
    post = record["post_build"]
    results = record["result_notes"]
    if not isinstance(post, Sequence) or isinstance(post, (str, bytes)) or len(post) < 2:
        return False
    if not isinstance(results, Sequence) or isinstance(results, (str, bytes)) or len(results) < 2:
        return False
    if not str(record.get("test_note", "")).strip():
        return False
    return True
