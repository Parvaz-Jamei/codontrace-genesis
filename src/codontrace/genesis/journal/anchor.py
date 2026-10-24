"""Journal head anchors: an external record against tail truncation.

A hash chain detects edits but not a truncated tail, because a shorter chain
is still valid. Recording the head digest somewhere else (a run manifest, a
transparency log; cf. RFC 9162 Certificate Transparency 2.0, signed tree
heads) lets a later reader check that the anchored head is still in the
journal. ``verify_anchor`` replays nothing; it walks record digests only.

Statuses: ``current_head``, ``earlier_record``, ``pruned`` (retention deleted
the segment that held the anchored head, and the head digest is listed in the
``<journal>.pruned`` ledger under that same segment, which retention writes
before each delete: normal pruning, not evidence of truncation), ``forged``
(the anchor names a segment that retention deleted, but its head is not among
that segment's ledger digests, so the anchor belongs to another history, was
fabricated, or names the wrong segment) and ``not_found`` (truncation, another
history, or a pruned segment with no ledger entry). The ledger is plain and
unkeyed: anyone who can write the journal directory can add a head to it, so
``pruned`` is as strong as the hash chain itself, no stronger.
An anchor whose header fields (``swarm_id`` and the rest of
``_record_header()``) differ from the journal's is ``forged``: it does not
belong to this journal. ``verify_anchor`` raises ``ValueError`` only for a
malformed anchor: wrong schema, a ``journal_head`` that is not 64 lowercase
hex digits, a header field that is missing or of the wrong type, or a
``journal_checkpoint_index`` that is missing or not ``None`` / a
non-negative int. ``journal_checkpoint_index`` is ``None`` when the anchor
was taken before the first checkpoint; the anchored segment is then
segment 1.
Segment numbers never repeat, so an anchor whose segment (one past its
``journal_checkpoint_index``) is older than the oldest kept segment, in a
journal whose oldest kept record links to a non-zero ``previous``, claims
pruned history.
"""
from __future__ import annotations

from typing import Any

from codontrace.genesis.journal.store import HashChainedJournal

__all__ = ['ANCHOR_SCHEMA', 'journal_anchor', 'verify_anchor']

ANCHOR_SCHEMA = 'genesis_journal_anchor_v1'


def journal_anchor(journal: HashChainedJournal) -> dict[str, Any]:
    """Head digest plus enough context to find it again."""
    with journal._lock:
        health = journal.journal_health()
        return {'schema': ANCHOR_SCHEMA, 'journal_head': journal._chain, **dict(journal._record_header()),
                'journal_segment_count': health['journal_segment_count'],
                'journal_checkpoint_index': health['journal_checkpoint_index'],
                'journal_path': None if journal.journal is None else str(journal.journal)}


def verify_anchor(journal: HashChainedJournal, anchor: dict[str, Any]) -> dict[str, Any]:
    """Is the anchored head the current head, an earlier record, pruned by retention,
    or missing (truncation or another history)?"""
    if anchor.get('schema') != ANCHOR_SCHEMA:
        raise ValueError('not a journal anchor')
    head = anchor.get('journal_head')
    if type(head) is not str or len(head) != 64 or any(c not in '0123456789abcdef' for c in head):
        raise ValueError(f'invalid journal_head {head!r}')
    segment = _anchored_segment(anchor)
    with journal._lock:
        for key, value in journal._record_header().items():
            if key not in anchor or type(anchor[key]) is not type(value):
                raise ValueError(f'invalid anchor {key} {anchor.get(key)!r}')
        if any(anchor[key] != value for key, value in journal._record_header().items()):
            return {'status': 'forged', 'journal_head': journal._chain}
        if head == journal._chain:
            return {'status': 'current_head', 'journal_head': journal._chain}
        if head == '0' * 64:
            return {'status': 'earlier_record', 'journal_head': journal._chain}
        if journal.journal is None:
            return {'status': 'not_found', 'journal_head': journal._chain}
        files = [p for _, p in journal._segment_rows(journal._archive_dir())] + \
                [p for _, p in journal._segment_rows()] + ([journal.journal] if journal.journal.exists() else [])
        for path in files:
            for _, digest in journal._records(path):
                if digest == head:
                    return {'status': 'earlier_record', 'journal_head': journal._chain}
        if _pruned_before(journal, anchor):
            ledger = _pruned_ledger(journal)
            if head in ledger.get(segment, set()):
                return {'status': 'pruned', 'journal_head': journal._chain}
            if segment in ledger:
                return {'status': 'forged', 'journal_head': journal._chain}
        return {'status': 'not_found', 'journal_head': journal._chain}


def _pruned_before(journal: HashChainedJournal, anchor: dict[str, Any]) -> bool:
    """Did retention delete the segment that held the anchored head?"""
    if journal.journal is None:
        raise ValueError('journal has no file: pruning cannot be checked')
    rows = journal._segment_rows(journal._archive_dir()) + journal._segment_rows()
    if not rows:
        return False
    oldest_index, oldest_path = min(rows)
    first = next(journal._records(oldest_path), None)
    if first is None or first[0].get('previous') == '0' * 64:
        return False  # the kept history starts at the beginning: nothing was pruned
    return _anchored_segment(anchor) < oldest_index


def _anchored_segment(anchor: dict[str, Any]) -> int:
    """Segment that held the anchored head: one past the checkpoint index.

    ``None`` is the documented value for "no checkpoint written yet" (``journal_anchor``
    copies ``journal_health()['journal_checkpoint_index']``, typed ``int | None``), so it
    means segment 1. The key itself is required."""
    if 'journal_checkpoint_index' not in anchor:
        raise ValueError('anchor has no journal_checkpoint_index')
    checkpoint = anchor['journal_checkpoint_index']
    if checkpoint is None:
        return 1
    if type(checkpoint) is not int or checkpoint < 0:
        raise ValueError(f'invalid journal_checkpoint_index {checkpoint!r}')
    return checkpoint + 1


def _pruned_ledger(journal: HashChainedJournal) -> dict[int, set[str]]:
    """``segment index -> record digests`` of segments retention deleted."""
    path = journal._pruned_ledger_path()
    out: dict[int, set[str]] = {}
    if not path.is_file():
        return out
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            index, _, digest = line.rstrip('\n').partition(' ')
            if len(index) == 8 and index.isdigit() and len(digest) == 64:
                out.setdefault(int(index), set()).add(digest)
    return out
