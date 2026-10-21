"""Journal head anchors: an external record against tail truncation.

A hash chain detects edits but not a truncated tail, because a shorter chain
is still valid. Recording the head digest somewhere else (a run manifest, a
transparency log; cf. RFC 9162 Certificate Transparency 2.0, signed tree
heads) lets a later reader check that the anchored head is still in the
journal. ``verify_anchor`` replays nothing; it walks record digests only.
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
    """Is the anchored head the current head, an earlier record, or missing (truncation or another history)?"""
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
        return {'status': 'not_found', 'journal_head': journal._chain}
