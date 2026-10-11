"""Hash-chained, segmented write-ahead journal for an event-sourced state machine.

Domain-free storage shared by modules that journal host decisions. A subclass
(see ``EventSourcedMachine``) supplies the state machine: ``_empty_state()``,
``_apply(action, args, now)`` operating on ``self._state``, the record header
(``_record_header()``, fields repeated in every record and checkpoint, e.g. an
instance id and the configuration that replay depends on), the checkpoint
schema name and a label used in error messages.

Byte format, frozen (existing journals must restore unchanged): one canonical
JSON record per line, ``{<header>, previous, action, args, now_ms, state_digest,
digest}``, where ``digest`` is the SHA-256 of the record without it and
``previous`` links to the prior record (zero digest first). Closed segments are
``<journal>.part.NNNNNNNN``; checkpoints ``<journal>.checkpoint.NNNNNNNN.json``
bind the state at the end of a closed segment to its last record; covered
segments may move to ``<journal>.archive/``. A lock file ``<journal>.lock``
serializes writers across processes.

Lock waits: writes take the journal's in-process ``RLock`` and then the file
lock. ``lock_timeout_s`` (constructor) bounds the file-lock wait by default.
``_transaction(lock_timeout_s=..., in_process_timeout_s=...)`` can bound the two
waits separately for one call: ``lock_timeout_s`` bounds only the file lock and
``in_process_timeout_s`` only the in-process lock (``None`` waits as long as the
other thread needs). An expired bound raises ``JournalBusyError`` with
``scope`` ``'file'`` or ``'in_process'`` and writes nothing.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol

from codontrace.contracts.wire_validation import bounded_int, finite_number, wire_canonical
from codontrace.genesis.journal.checkpoint import (
    MAX_CHECKPOINT_BYTES,
    checkpoint_body,
    state_digest,
    verify_checkpoint_text,
)
from codontrace.genesis.journal.locking import JournalBusyError, fsync_dir, journal_file_lock
from codontrace.genesis.journal.retention import archived_to_delete, segments_to_archive

__all__ = ['EventSourcedMachine', 'HashChainedJournal', 'JournalBusyError', 'JournalHealth', 'NotRecorded']


class NotRecorded(dict):  # type: ignore[type-arg]
    """An _apply result that changes nothing durable (e.g. a duplicate packet):
    live writes discard it without a journal record; replay of older journals
    that contain such records still applies them unchanged."""


class EventSourcedMachine(Protocol):
    """What ``HashChainedJournal`` needs from the state machine it journals."""

    _state: dict[str, Any]

    def _empty_state(self) -> dict[str, Any]: ...

    def _apply(self, action: str, args: dict[str, Any], now: int) -> Any: ...

    def _record_header(self) -> Mapping[str, Any]: ...


class JournalHealth(dict):  # type: ignore[type-arg]
    """Snapshot health fields: ``journal_health``, ``journal_segment_count``,
    ``journal_checkpoint_index``, ``checkpoint_health``, ``retention_health``."""


class HashChainedJournal:
    """Base class: journal storage, restore, checkpoints, retention and transactions.

    Call ``_init_journal(...)`` from the subclass ``__init__`` after the record
    header attributes are set. ``_transaction(action, args, now_ms)`` applies an
    action to a copy of the state, journals it (fsync before the in-memory
    state changes) and returns the result; ``recover()`` reloads from disk.
    """

    _checkpoint_schema: str = 'genesis_journal_checkpoint_v1'
    _journal_label: str = 'event'
    journal: Path | None
    _state: dict[str, Any]

    def _empty_state(self) -> dict[str, Any]:
        raise NotImplementedError

    def _apply(self, action: str, args: dict[str, Any], now: int) -> Any:
        raise NotImplementedError

    def _record_header(self) -> Mapping[str, Any]:
        raise NotImplementedError

    def _init_journal(self, journal: Path | None, *, segment_bytes: int, retention_bytes: int | None,
                      archive_max_bytes: int | None, lock_timeout_s: float, restore: bool) -> None:
        self.journal = None if journal is None else Path(journal).resolve()
        self.journal_segment_bytes = bounded_int(segment_bytes, high=64*1024*1024)
        if self.journal_segment_bytes < 1024:
            raise ValueError("journal segment size must be at least 1024 bytes")
        if retention_bytes is not None:
            bounded_int(retention_bytes, high=2**40)
            if retention_bytes < self.journal_segment_bytes:
                raise ValueError('journal retention must be at least one segment')
        if archive_max_bytes is not None:
            bounded_int(archive_max_bytes, high=2**40)
        self.lock_timeout_s = finite_number(lock_timeout_s, low=0, high=60)
        if type(restore) is not bool:
            raise ValueError('restore must be boolean')
        self.journal_retention_bytes = retention_bytes
        self.archive_max_bytes = archive_max_bytes
        self._checkpoint_index: int | None = None
        self._checkpoint_error: str | None = None
        self._retention_error: str | None = None
        self._pending_checkpoint: tuple[int, dict[str, Any], str] | None = None
        journal = self.journal
        self._lock = threading.RLock()
        self._chain = '0' * 64
        self._write_failed = False
        self._journal_size = 0
        self._journal_token: tuple[Any, ...] = ()
        self._state = self._empty_state()
        if journal is not None:
            with self._journal_guard():
                if not restore:
                    # Opened only to run recover(): no writes until it succeeds.
                    self._write_failed = journal.exists() or bool(self._segment_rows()) or self._archive_dir().is_dir()
                elif journal.exists() or self._segment_rows() or self._archive_dir().is_dir():
                    self._restore()
                    self._write_pending_checkpoint()
                self._refresh_disk_state()

    def journal_health(self) -> JournalHealth:
        """Health fields for snapshots (caller holds ``self._lock``)."""
        return JournalHealth({
            'journal_health': 'recovery_required' if self._write_failed else 'ready',
            'journal_segment_count': len(self._segments()) if self.journal is not None else 0,
            'journal_checkpoint_index': self._checkpoint_index,
            'checkpoint_health': 'ok' if self._checkpoint_error is None else self._checkpoint_error,
            'retention_health': 'ok' if self._retention_error is None else self._retention_error})

    @contextmanager
    def _journal_guard(self, timeout_s: float | None = None) -> Iterator[None]:
        if self.journal is None:
            yield
            return
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        # Cross-process serialization with a bounded wait; a writer that cannot
        # get the lock in time fails instead of forking the chain.
        with journal_file_lock(self.journal.with_suffix(self.journal.suffix + '.lock'),
                               self.lock_timeout_s if timeout_s is None else timeout_s,
                               f'{self._journal_label} journal is locked by another writer'):
            yield

    @contextmanager
    def _in_process_lock(self, timeout_s: float | None) -> Iterator[None]:
        """The journal's own lock, with an optional wait bound (``JournalBusyError``, scope ``'in_process'``)."""
        if timeout_s is None:
            acquired = self._lock.acquire()
        else:
            acquired = self._lock.acquire(timeout=finite_number(timeout_s, low=0, high=60))
        if not acquired:
            raise JournalBusyError(f'{self._journal_label} coordinator is busy in this process', scope='in_process')
        try:
            yield
        finally:
            self._lock.release()

    @contextmanager
    def _write_locks(self, lock_timeout_s: float | None,
                     in_process_timeout_s: float | None = None) -> Iterator[None]:
        """In-process serialization, then the cross-process file lock, each with its own bound."""
        if lock_timeout_s is None and in_process_timeout_s is None:
            with self._lock, self._journal_guard():
                yield
            return
        file_timeout = None if lock_timeout_s is None else finite_number(lock_timeout_s, low=0, high=60)
        with self._in_process_lock(in_process_timeout_s), self._journal_guard(file_timeout):
            yield

    @staticmethod
    def _fsync_dir(folder: Path) -> None:
        """Persist directory entries (create/rename); fsync(2) on a file does not."""
        fsync_dir(folder)

    @staticmethod
    def _numbered(paths: list[Path], prefix: str, suffix: str = '', *, strict: bool = True) -> list[tuple[int, Path]]:
        """Files named exactly ``prefix + 8 digits + suffix``; other names are ignored.

        A matching name that is a symlink or not a regular file is an error when
        strict (journal segments) and skipped otherwise (checkpoint cache files).
        """
        rows = []
        for path in paths:
            name = path.name
            if not name.startswith(prefix) or (suffix and not name.endswith(suffix)):
                continue
            middle = name[len(prefix):len(name)-len(suffix) if suffix else None]
            if len(middle) != 8 or not middle.isdigit():
                continue
            if path.is_symlink() or not path.is_file():
                if strict:
                    raise ValueError('invalid journal file')
                continue
            rows.append((int(middle), path))
        return sorted(rows)

    def _segment_rows(self, directory: Path | None = None) -> list[tuple[int, Path]]:
        assert self.journal is not None
        prefix = self.journal.name + '.part.'
        folder = self.journal.parent if directory is None else directory
        rows = self._numbered(list(folder.glob(prefix + '*')), prefix) if folder.is_dir() else []
        for (a, _), (b, _) in zip(rows, rows[1:], strict=False):
            if b != a + 1:
                raise ValueError('invalid or missing journal segment')
        return rows

    def _segments(self) -> list[Path]:
        return [path for _, path in self._segment_rows()]

    def _archive_dir(self) -> Path:
        assert self.journal is not None
        return self.journal.with_name(self.journal.name + '.archive')

    def _checkpoint_path(self, index: int) -> Path:
        assert self.journal is not None
        return self.journal.with_name(self.journal.name + f'.checkpoint.{index:08d}.json')

    def _checkpoint_rows(self) -> list[tuple[int, Path]]:
        assert self.journal is not None
        prefix = self.journal.name + '.checkpoint.'
        # Checkpoints are a cache: unrecognised names are ignored, not fatal.
        return self._numbered(list(self.journal.parent.glob(prefix + '*.json')), prefix, '.json', strict=False)

    def _disk_token(self) -> tuple[Any, ...]:
        assert self.journal is not None
        paths = [*self._segments(), self.journal]
        return tuple((p.name, p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                     for p in paths if p.exists())

    def _refresh_disk_state(self) -> None:
        """Adopt the current on-disk layout after this instance changed it."""
        if self.journal is not None:
            self._journal_size = self.journal.stat().st_size if self.journal.exists() else 0
            self._journal_token = self._disk_token()

    def _records(self, path: Path) -> Iterator[tuple[dict[str, Any], str]]:
        with path.open(encoding='utf-8') as handle:
            for line in handle:
                if len(line) > 100000 or not line.endswith('\n'):
                    raise ValueError(f'truncated or oversized {self._journal_label} journal')
                record = json.loads(line)
                digest = record.pop('digest', None)
                if hashlib.sha256(wire_canonical(record).encode()).hexdigest() != digest:
                    raise ValueError(f'{self._journal_label} journal integrity failure')
                if any(record.get(key) != value for key, value in self._record_header().items()):
                    raise ValueError(f'{self._journal_label} journal configuration mismatch')
                yield record, digest

    def _replay_file(self, path: Path) -> None:
        for record, digest in self._records(path):
            if record.get('previous') != self._chain:
                raise ValueError(f'{self._journal_label} journal integrity failure')
            self._apply(record['action'], record['args'], record['now_ms'])
            if state_digest(self._state) != record.get('state_digest'):
                raise ValueError(f'{self._journal_label} replay state divergence')
            self._chain = digest

    def _verify_links(self, rows: list[tuple[int, Path]], end_chain: str) -> None:
        """Hash-chain check of covered segments without re-applying their records.

        Starts from the zero digest when segment 1 is live; after archiving, the
        first live record's predecessor is anchored by the archive (full replay).
        """
        chain = '0' * 64 if rows and rows[0][0] == 1 else None
        for _, path in rows:
            for record, digest in self._records(path):
                if chain is None:
                    chain = record.get('previous')
                if record.get('previous') != chain:
                    raise ValueError(f'{self._journal_label} journal integrity failure')
                chain = digest
        if chain != end_chain:
            raise ValueError(f'{self._journal_label} journal integrity failure')

    @staticmethod
    def _last_record(path: Path) -> dict[str, Any]:
        """Read and self-verify the final complete record of a closed segment."""
        with path.open('rb') as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 200002))
            tail = handle.read()
        if not tail.endswith(b'\n'):
            raise ValueError('closed segment has a partial final record')
        line = tail[:-1].rsplit(b'\n', 1)[-1]
        record: dict[str, Any] = json.loads(line)
        digest = record.pop('digest', None)
        if hashlib.sha256(wire_canonical(record).encode()).hexdigest() != digest:
            raise ValueError('closed segment final record fails its digest')
        record['digest'] = digest
        return record

    def _read_checkpoint(self, index: int, path: Path, live: dict[int, Path]) -> tuple[dict[str, Any], str]:
        """Verify one checkpoint against the current journal; raise if unusable."""
        if index not in live:
            raise ValueError('checkpoint position is not in the live journal')
        if path.stat().st_size > MAX_CHECKPOINT_BYTES:
            raise ValueError('oversized checkpoint')
        payload = verify_checkpoint_text(path.read_text(encoding='utf-8'), schema=self._checkpoint_schema,
                                         header=self._record_header(), index=index)
        last = self._last_record(live[index])
        if last['digest'] != payload.get('chain') or last.get('state_digest') != payload['state_digest']:
            raise ValueError('checkpoint is not bound to the closed segment')
        return payload['state'], payload['chain']

    def _checkpoint_valid(self, index: int, live: dict[int, Path] | None = None) -> bool:
        live = dict(self._segment_rows()) if live is None else live
        try:
            self._read_checkpoint(index, self._checkpoint_path(index), live)
            return True
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            return False

    def _load_checkpoint(self, live: dict[int, Path]) -> tuple[int, dict[str, Any], str] | None:
        """Newest checkpoint whose position exists in the live stream and matches it."""
        errors = []
        for index, path in reversed(self._checkpoint_rows()):
            if index not in live:
                continue
            try:
                state, chain = self._read_checkpoint(index, path, live)
                return index, state, chain
            except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
                errors.append(f'{path.name}: {type(error).__name__}')
        self._checkpoint_error = '; '.join(errors) or None
        return None

    def _restore(self, *, full_replay: bool = False) -> None:
        assert self.journal is not None
        live_rows = self._segment_rows()
        live = dict(live_rows)
        start = None if full_replay else self._load_checkpoint(live)
        rows = live_rows
        if start is not None:
            index, state, chain = start
            # Covered live history keeps its hash-chain check; only re-application is skipped.
            self._verify_links([row for row in rows if row[0] <= index], chain)
            self._state, self._chain, self._checkpoint_index = copy.deepcopy(state), chain, index
            rows = [row for row in rows if row[0] > index]
        else:
            # Full replay from the first segment; after archiving that includes the
            # archive, and replaying across it verifies the archive -> live link.
            self._checkpoint_index = None
            if not rows or rows[0][0] != 1 or full_replay:
                archived = self._segment_rows(self._archive_dir())
                if archived and rows and archived[-1][0] >= rows[0][0]:
                    archived = [row for row in archived if row[0] < rows[0][0]]
                rows = archived + rows
                for (a, _), (b, _) in zip(rows, rows[1:], strict=False):
                    if b != a + 1:
                        raise ValueError('archived and live segments are not contiguous')
            if rows and rows[0][0] != 1:
                raise ValueError('earliest archived segments were deleted and no valid checkpoint covers '
                                 'the live journal; full replay unavailable')
        self._pending_checkpoint = None
        last_live = max(live) if live else None
        for index, path in rows:
            self._replay_file(path)
            if index == last_live and index != self._checkpoint_index:
                self._pending_checkpoint = (index, copy.deepcopy(self._state), self._chain)
        if self.journal.exists():
            self._replay_file(self.journal)

    def _write_checkpoint(self, index: int, state: dict[str, Any], chain: str) -> None:
        """Atomic, fsynced checkpoint; failures are reported, never fatal to writes."""
        assert self.journal is not None
        try:
            body = checkpoint_body(self._checkpoint_schema, self._record_header(), index, chain, state)
            target = self._checkpoint_path(index)
            temp = target.with_name(target.name + f'.{os.getpid()}.{threading.get_ident()}.tmp')
            try:
                with temp.open('x', encoding='utf-8') as handle:
                    handle.write(body); handle.flush(); os.fsync(handle.fileno())
                os.replace(temp, target)
            finally:
                temp.unlink(missing_ok=True)
            self._fsync_dir(target.parent)
            self._checkpoint_index, self._checkpoint_error = index, None
            self._prune_checkpoints(index)
            self._enforce_retention()
        except (OSError, ValueError) as error:
            self._checkpoint_error = f'checkpoint {index}: {type(error).__name__}'
        finally:
            self._refresh_disk_state()

    def _prune_checkpoints(self, keep: int) -> None:
        """Keep the just-written checkpoint and one older checkpoint valid for this
        journal; delete stale ones (other history, beyond the live end, unbound)."""
        live = dict(self._segment_rows())
        spare = None
        for index, path in reversed(self._checkpoint_rows()):
            if index == keep:
                continue
            if spare is None and index < keep and self._checkpoint_valid(index, live):
                spare = index
                continue
            path.unlink(missing_ok=True)

    def _write_pending_checkpoint(self) -> None:
        if self._pending_checkpoint is not None:
            index, state, chain = self._pending_checkpoint
            self._pending_checkpoint = None
            self._write_checkpoint(index, state, chain)

    def _enforce_retention(self) -> None:
        """Archive covered closed segments beyond the live cap; delete only past the archive cap.

        Only a checkpoint re-verified against the current journal is trusted.
        Errors are reported in ``retention_health`` and never block journal writes.
        """
        if self.journal_retention_bytes is None or self._checkpoint_index is None:
            return
        try:
            live = dict(self._segment_rows())
            covered = self._checkpoint_index
            if not self._checkpoint_valid(covered, live):
                raise ValueError('current checkpoint does not verify against the journal')
            rows = sorted(live.items())
            sizes = [(index, path.stat().st_size) for index, path in rows]
            live_bytes = sum(size for _, size in sizes)
            journal = self.journal
            assert journal is not None
            live_bytes += journal.stat().st_size if journal.exists() else 0
            archive = self._archive_dir()
            moved = False
            # Keeps the checkpoint's own segment live: its tail binds the checkpoint.
            for index in segments_to_archive(sizes, live_bytes, self.journal_retention_bytes, covered):
                path = live[index]
                if not archive.is_dir():
                    archive.mkdir()
                    self._fsync_dir(archive.parent)
                target = archive / path.name
                if target.exists():
                    raise OSError('archived segment already exists')
                os.replace(path, target)
                moved = True
            if moved:
                self._fsync_dir(archive)
                self._fsync_dir(journal.parent)
            if self.archive_max_bytes is not None and archive.is_dir():
                archived = dict(self._segment_rows(archive))
                doomed = archived_to_delete([(i, p.stat().st_size) for i, p in sorted(archived.items())],
                                            self.archive_max_bytes)
                for index in doomed:
                    archived[index].unlink()
                deleted = bool(doomed)
                if deleted:
                    self._fsync_dir(archive)
            self._retention_error = None
        except (OSError, ValueError) as error:
            self._retention_error = f'retention: {type(error).__name__}: {error}'
        finally:
            self._refresh_disk_state()

    def recover(self, *, full_replay: bool = False) -> dict[str, Any]:
        """Explicit replay of complete records; never truncate a corrupt tail.

        An append that failed during fsync can exist on disk. Recovery adopts
        validated durable records; callers must inspect pending command IDs.
        ``full_replay`` ignores checkpoints and re-verifies the whole chain from
        the first archived or live segment. Also reloads a stale instance.
        """
        if type(full_replay) is not bool:
            raise ValueError('full_replay must be boolean')
        with self._lock, self._journal_guard():
            original, chain = self._state, self._chain
            self._state = self._empty_state()
            self._chain = '0'*64
            try:
                if self.journal is None:
                    self._state, self._chain = original, chain
                else:
                    self._restore(full_replay=full_replay)
                    # Checkpoint (and any retention it triggers) first, then adopt
                    # the resulting on-disk layout so the next write is not refused.
                    self._write_pending_checkpoint()
                    if self.journal.exists():
                        with self.journal.open('ab') as handle:
                            handle.flush(); os.fsync(handle.fileno())
                    self._refresh_disk_state()
                self._write_failed = False
            except BaseException:
                self._state, self._chain = original, chain
                self._write_failed = True
                raise
            return {'recovered': True, 'journal_digest': self._chain,
                    'state_changed': chain != self._chain, 'records_not_truncated': True,
                    'full_replay': full_replay, 'checkpoint_index': self._checkpoint_index}

    def _transaction(self, action: str, args: dict[str, Any], now_ms: int, *,
                     lock_timeout_s: float | None = None, in_process_timeout_s: float | None = None) -> Any:
        now_ms = bounded_int(now_ms)
        with self._write_locks(lock_timeout_s, in_process_timeout_s):
            if self.journal is not None:
                size = self.journal.stat().st_size if self.journal.exists() else 0
                if size != self._journal_size or self._disk_token() != self._journal_token:
                    raise OSError('journal changed externally; recover() reloads this coordinator')
            if self._write_failed:
                raise OSError("journal failure requires recovery before further writes")
            original = self._state
            self._state = copy.deepcopy(original)
            try:
                result = self._apply(action, json.loads(wire_canonical(args)), now_ms)
                if isinstance(result, NotRecorded):
                    self._state = original  # nothing to journal
                    return dict(result)
                record = {**self._record_header(),
                          'previous': self._chain, 'action': action, 'args': args, 'now_ms': now_ms,
                          'state_digest': state_digest(self._state)}
                digest = hashlib.sha256(wire_canonical(record).encode()).hexdigest()
                if self.journal is not None:
                    self.journal.parent.mkdir(parents=True, exist_ok=True)
                    if self._journal_size >= self.journal_segment_bytes:
                        rows = self._segment_rows()
                        index = (rows[-1][0] if rows else 0) + 1
                        target = self.journal.with_name(self.journal.name + f'.part.{index:08d}')
                        if target.exists():
                            raise OSError('journal segment already exists')
                        os.rename(self.journal, target)
                        self._journal_size = 0
                        # State/chain at the end of the closed segment = before this record.
                        self._write_checkpoint(index, original, self._chain)
                    created = not self.journal.exists()
                    with self.journal.open('a', encoding='utf-8') as handle:
                        handle.write(wire_canonical({**record, 'digest': digest}) + '\n'); handle.flush(); os.fsync(handle.fileno())
                    if created:
                        self._fsync_dir(self.journal.parent)
                    self._refresh_disk_state()
                self._chain = digest
                return copy.deepcopy(result)
            except OSError:
                self._write_failed = True
                self._state = original
                raise
            except BaseException:
                self._state = original
                raise
