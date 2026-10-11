"""A minimal non-swarm state machine on HashChainedJournal (used by test_genesis_journal)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from codontrace.genesis.journal import HashChainedJournal, NotRecorded


class Counter(HashChainedJournal):
    _checkpoint_schema = 'test_counter_checkpoint_v1'
    _journal_label = 'counter'

    def __init__(self, journal: Path | None, *, name: str = 'c1', segment_bytes: int = 1024,
                 retention_bytes: int | None = None, archive_max_bytes: int | None = None,
                 lock_timeout_s: float = 2.0, restore: bool = True) -> None:
        self.name = name
        self._init_journal(journal, segment_bytes=segment_bytes, retention_bytes=retention_bytes,
                           archive_max_bytes=archive_max_bytes, lock_timeout_s=lock_timeout_s, restore=restore)

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {'total': 0, 'last_ms': 0}

    def _record_header(self) -> dict[str, Any]:
        return {'counter': self.name}

    def _apply(self, action: str, args: dict[str, Any], now: int) -> Any:
        if action == 'add':
            self._state['total'] += args['n']
            self._state['last_ms'] = now
            return {'total': self._state['total']}
        if action == 'peek':
            return NotRecorded(total=self._state['total'])
        raise ValueError('unknown action')

    def add(self, n: int, now_ms: int) -> Any:
        return self._transaction('add', {'n': n}, now_ms)

    def total(self) -> int:
        with self._lock:
            return int(self._state['total'])
