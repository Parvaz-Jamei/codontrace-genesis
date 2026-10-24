"""codontrace.genesis.journal: domain-free use, crash injection, external writers,
the Windows lock path (fake msvcrt) and pure retention planning.

The swarm journal's byte format is pinned by tests/characterization; these tests
exercise the extracted storage through a non-swarm state machine.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from codontrace.genesis.journal import (
    HashChainedJournal,
    archived_to_delete,
    journal_file_lock,
    locking,
    segments_to_archive,
)


def _load_journal_machine() -> types.ModuleType:
    # Load the helper by path so tests/ is never added to sys.path; otherwise
    # tests/platform would shadow the stdlib platform module for later tests
    # and for any child process that copies this sys.path.
    import importlib.util

    name = "_journal_machine"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("_journal_machine.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


Counter = _load_journal_machine().Counter

PKG = Path(__file__).resolve().parents[1] / 'src' / 'codontrace' / 'genesis' / 'journal'


def _fill(c: Counter, start: int, count: int) -> int:
    for i in range(start, start + count):
        c.add(i, now_ms=1000 + i)
    return sum(range(start, start + count))


def _parts(journal: Path) -> list[str]:
    return sorted(p.name for p in journal.parent.glob(journal.name + '.part.*'))


def test_non_swarm_machine_restores_through_rotation_and_checkpoints(tmp_path):
    journal = tmp_path / 'c.jsonl'
    c = Counter(journal)
    total = _fill(c, 1, 40)
    assert len(_parts(journal)) >= 3
    health = c.journal_health()
    assert health['journal_health'] == 'ready' and health['checkpoint_health'] == 'ok'
    assert health['journal_checkpoint_index'] == len(_parts(journal))
    again = Counter(journal)
    assert again.total() == total and again._chain == c._chain
    assert again._checkpoint_index == c._checkpoint_index
    full = Counter(journal)
    full.recover(full_replay=True)
    assert full.total() == total and full._chain == c._chain


def test_not_recorded_result_writes_nothing(tmp_path):
    journal = tmp_path / 'c.jsonl'
    c = Counter(journal)
    c.add(2, now_ms=1)
    size = journal.stat().st_size
    assert c._transaction('peek', {}, 2) == {'total': 2}
    assert journal.stat().st_size == size


def test_record_header_is_checked_on_restore(tmp_path):
    journal = tmp_path / 'c.jsonl'
    Counter(journal).add(1, now_ms=1)
    with pytest.raises(ValueError, match='^counter journal configuration mismatch$'):
        Counter(journal, name='c2')


def test_failed_apply_leaves_state_and_disk_untouched(tmp_path):
    journal = tmp_path / 'c.jsonl'
    c = Counter(journal)
    c.add(1, now_ms=1)
    size = journal.stat().st_size
    with pytest.raises(ValueError, match='unknown action'):
        c._transaction('nope', {}, 2)
    assert c.total() == 1 and journal.stat().st_size == size
    assert c.journal_health()['journal_health'] == 'ready'


_CRASH = '''
import os, sys
sys.path.insert(0, {tests!r})
from _journal_machine import Counter
c = Counter({journal!r})
def crash(self, index, state, chain):
    os._exit(17)
Counter._write_checkpoint = crash
for i in range(1, 1000):
    c.add(i, now_ms=1000 + i)
'''


def test_crash_between_segment_rename_and_checkpoint(tmp_path):
    """A process killed after rotating the active file but before its checkpoint
    and before the next record: restore replays the closed segment, writes the
    missing checkpoint, and writing continues on the same chain."""
    journal = tmp_path / 'c.jsonl'
    script = _CRASH.format(tests=str(Path(__file__).parent), journal=str(journal))
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(PKG.parents[2])] + sys.path)}
    done = subprocess.run([sys.executable, '-c', script], env=env, timeout=120)
    assert done.returncode == 17
    assert not journal.exists() and _parts(journal) == [journal.name + '.part.00000001']
    assert not list(tmp_path.glob('*.checkpoint.*'))
    rows = (tmp_path / _parts(journal)[0]).read_text().splitlines()
    c = Counter(journal)
    assert c.total() == sum(range(1, len(rows) + 1))
    assert (tmp_path / (journal.name + '.checkpoint.00000001.json')).is_file()
    assert c._checkpoint_index == 1
    c.add(5, now_ms=5000)
    assert Counter(journal).total() == c.total()


def test_torn_final_record_refuses_restore(tmp_path):
    """A torn last line (crash mid-append) is refused, not silently dropped;
    recovery needs an operator decision."""
    journal = tmp_path / 'c.jsonl'
    Counter(journal).add(1, now_ms=1)
    with journal.open('a', encoding='utf-8') as handle:
        handle.write('{"action": "add", "ar')
    with pytest.raises(ValueError, match='^truncated or oversized counter journal$'):
        Counter(journal)
    idle = Counter(journal, restore=False)
    assert idle.journal_health()['journal_health'] == 'recovery_required'
    with pytest.raises(ValueError, match='truncated'):
        idle.recover()
    with pytest.raises(OSError, match='requires recovery'):
        idle.add(1, now_ms=2)


def test_corrupt_newest_checkpoint_falls_back(tmp_path):
    journal = tmp_path / 'c.jsonl'
    c = Counter(journal)
    total = _fill(c, 1, 40)
    newest = sorted(tmp_path.glob('*.checkpoint.*.json'))[-1]
    good = newest.read_text(encoding='utf-8')
    newest.write_text(good[:50], encoding='utf-8')
    again = Counter(journal)
    assert again.total() == total and again._chain == c._chain
    # Restored from the older checkpoint, then the newest one is rebuilt identically.
    assert again._checkpoint_index == c._checkpoint_index
    assert newest.read_text(encoding='utf-8') == good


def test_leftover_checkpoint_temp_file_is_ignored(tmp_path):
    journal = tmp_path / 'c.jsonl'
    c = Counter(journal)
    total = _fill(c, 1, 12)
    (tmp_path / (journal.name + '.checkpoint.00000009.json.1.2.tmp')).write_text('{', encoding='utf-8')
    assert Counter(journal).total() == total


def test_external_writer_is_detected_and_recover_reloads(tmp_path):
    journal = tmp_path / 'c.jsonl'
    a = Counter(journal)
    a.add(1, now_ms=1)
    b = Counter(journal)
    b.add(10, now_ms=2)
    with pytest.raises(OSError, match='^journal changed externally'):
        a.add(100, now_ms=3)
    # Refused before anything is written, so not a write failure.
    assert a.journal_health()['journal_health'] == 'ready' and a.total() == 1
    a.recover()
    assert a.total() == 11
    a.add(100, now_ms=3)
    assert Counter(journal).total() == 111


class _FakeMsvcrt(types.ModuleType):
    LK_NBLCK, LK_UNLCK = 2, 0

    def __init__(self) -> None:
        super().__init__('msvcrt')
        self.held: dict[int, int] = {}
        self.calls: list[tuple[int, int, int]] = []

    def locking(self, fd: int, mode: int, nbytes: int) -> None:
        inode = os.fstat(fd).st_ino
        offset = os.lseek(fd, 0, os.SEEK_CUR)
        self.calls.append((mode, nbytes, offset))
        if mode == self.LK_NBLCK:
            if inode in self.held and self.held[inode] != fd:
                raise OSError(36, 'Resource deadlock avoided')
            self.held[inode] = fd
        elif mode == self.LK_UNLCK:
            assert self.held.pop(inode) == fd


def test_windows_lock_path_with_fake_msvcrt(tmp_path, monkeypatch):
    fake = _FakeMsvcrt()
    monkeypatch.setitem(sys.modules, 'msvcrt', fake)
    monkeypatch.setattr(locking, 'os', types.SimpleNamespace(name='nt'))
    lock = tmp_path / 'j.lock'
    with journal_file_lock(lock, 1.0, 'busy'):
        assert lock.read_bytes() == b'0'
        with pytest.raises(BlockingIOError, match='^busy$'):
            with journal_file_lock(lock, 0.02, 'busy'):
                pass
    assert fake.held == {}
    with journal_file_lock(lock, 0.02, 'busy'):
        pass
    assert lock.read_bytes() == b'0'
    assert all(nbytes == 1 and offset == 0 for _, nbytes, offset in fake.calls)
    assert [m for m, _, _ in fake.calls].count(fake.LK_UNLCK) == 2


def test_windows_lock_path_drives_a_journal(tmp_path, monkeypatch):
    fake = _FakeMsvcrt()
    monkeypatch.setitem(sys.modules, 'msvcrt', fake)
    monkeypatch.setattr(locking, 'os', types.SimpleNamespace(name='nt'))
    journal = tmp_path / 'c.jsonl'
    c = Counter(journal)
    total = _fill(c, 1, 12)
    assert Counter(journal).total() == total and fake.held == {}


@pytest.mark.parametrize(('rows', 'live', 'cap', 'covered', 'expected'), [
    ([(1, 100), (2, 100), (3, 100)], 400, 400, 3, []),          # fits exactly: nothing moves
    ([(1, 100), (2, 100), (3, 100)], 401, 400, 3, [1]),
    ([(1, 100), (2, 100), (3, 100)], 900, 100, 3, [1, 2]),      # never the covered segment
    ([(1, 100), (2, 100), (3, 100)], 900, 100, 1, []),
])
def test_segments_to_archive(rows, live, cap, covered, expected):
    assert segments_to_archive(rows, live, cap, covered) == expected


@pytest.mark.parametrize(('rows', 'cap', 'expected'), [
    ([(1, 100), (2, 100)], 200, []),                            # at the cap: kept
    ([(1, 100), (2, 100)], 199, [1]),
    ([(1, 100), (2, 100), (3, 50)], 0, [1, 2, 3]),
])
def test_archived_to_delete(rows, cap, expected):
    assert archived_to_delete(rows, cap) == expected


def test_journal_package_is_domain_free():
    allowed = ('codontrace.contracts', 'codontrace.genesis.journal')
    for path in PKG.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for name in names:
                assert not name.startswith('codontrace') or name.startswith(allowed), (path.name, name)


def test_swarm_coordinator_is_a_hash_chained_journal():
    from codontrace.genesis.journal import NotRecorded
    from codontrace.swarm.runtime import SwarmCoordinator, _NotRecorded
    assert issubclass(SwarmCoordinator, HashChainedJournal) and _NotRecorded is NotRecorded


def test_journal_docs_do_not_point_at_module_classes():
    """Review F8: the journal documents its own rules instead of referring to a module class."""
    from pathlib import Path

    import codontrace.genesis.journal as package
    for path in Path(package.__file__).parent.glob('*.py'):
        assert 'SwarmCoordinator' not in path.read_text(encoding='utf-8'), path.name
