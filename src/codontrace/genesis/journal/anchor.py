"""Journal head anchors: an external record against tail truncation.

A hash chain detects edits but not a truncated tail, because a shorter chain
is still valid. Recording the head digest somewhere else (a run manifest, a
transparency log; cf. RFC 9162 Certificate Transparency 2.0, signed tree
heads) lets a later reader check that the anchored head is still in the
journal. ``verify_anchor`` replays nothing; it walks record digests only.

Statuses: ``current_head``, ``earlier_record``, ``pruned`` (the anchored head
was in a segment that retention deleted from the archive: normal pruning, not
evidence of truncation) and ``not_found`` (truncation or another history).
Segment numbers never repeat, so an anchor whose segment (one past its
``journal_checkpoint_index``) is older than the oldest kept segment, in a
journal whose oldest kept record links to a non-zero ``previous``, is pruned.
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
    head = anchor['journal_head']
    with journal._lock:
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
            return {'status': 'pruned', 'journal_head': journal._chain}
        return {'status': 'not_found', 'journal_head': journal._chain}


def _pruned_before(journal: HashChainedJournal, anchor: dict[str, Any]) -> bool:
    """Did retention delete the segment that held the anchored head?"""
    assert journal.journal is not None
    rows = journal._segment_rows(journal._archive_dir()) + journal._segment_rows()
    if not rows:
        return False
    oldest_index, oldest_path = min(rows)
    first = next(journal._records(oldest_path), None)
    if first is None or first[0].get('previous') == '0' * 64:
        return False  # the kept history starts at the beginning: nothing was pruned
    checkpoint = anchor.get('journal_checkpoint_index')
    anchored_segment = (checkpoint if type(checkpoint) is int else 0) + 1
    return anchored_segment < oldest_index
