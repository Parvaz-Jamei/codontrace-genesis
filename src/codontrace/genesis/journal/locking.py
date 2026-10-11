"""Cross-process journal lock and directory fsync (POSIX ``flock``, Windows ``msvcrt.locking``)."""
from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

__all__ = ['JournalBusyError', 'fsync_dir', 'journal_file_lock']


class JournalBusyError(BlockingIOError):
    """A journal lock was not obtained within its wait bound.

    ``scope`` is ``'file'`` when the cross-process journal file lock is held by
    another writer (normally another process), or ``'in_process'`` when the
    journal's own lock stayed busy (another thread of this process is writing,
    fsyncing, checkpointing or recovering). Nothing was written and the journal
    stays writable; the caller may retry later.
    """

    def __init__(self, message: str, *, scope: str = 'file') -> None:
        super().__init__(message)
        self.scope = scope


@contextmanager
def journal_file_lock(lock_path: Path, timeout_s: float, busy_message: str) -> Iterator[None]:
    """Exclusive lock on ``lock_path`` with a bounded, backing-off wait.

    A writer that cannot get the lock within ``timeout_s`` raises
    ``JournalBusyError(busy_message, scope='file')`` (a ``BlockingIOError``)
    instead of forking the hash chain. The lock
    file itself carries no data (Windows needs one byte to lock).
    """
    with lock_path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.tell() == 0:
                handle.write(b'0'); handle.flush()
        else:
            import fcntl
        deadline = time.monotonic() + timeout_s
        delay = 0.001
        while True:
            try:
                if os.name == 'nt':
                    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined,unused-ignore]
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise JournalBusyError(busy_message, scope='file') from error
                time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
                delay = min(delay * 2, 0.05)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined,unused-ignore]
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def fsync_dir(folder: Path) -> None:
    """Persist directory entries (create/rename); fsync(2) on a file does not."""
    if os.name == 'nt':
        return
    fd = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
