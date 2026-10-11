"""Journal hardening: retention health, directory fsync, lock wait, recovery path, LRU cache,
fusion input validation and the exact conformal rank."""
from __future__ import annotations

import fcntl
import os
import shutil
import threading
import time

import pytest

from codontrace.swarm import SwarmCoordinator, service
from codontrace.swarm.decision_support import residual_interval
from codontrace.swarm.experiments import hello, reading

SEG = 1024


def _fill(path, n=40, **kw):
    s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG, **kw)
    s.ingest(hello('lab', 'a'), now_ms=1000)
    for seq in range(1, n):
        s.ingest(reading('lab', 'a', seq, 1000 + seq, float(seq)), now_ms=1000 + seq)
    return s


def test_retention_errors_are_reported_separately_and_never_block_writes(tmp_path, monkeypatch):
    real = os.replace

    def no_archive(a, b):
        if '.archive' in str(b):
            raise OSError('archive volume full')
        return real(a, b)

    monkeypatch.setattr(os, 'replace', no_archive)
    s = _fill(tmp_path / 'events.jsonl', n=60, journal_retention_bytes=SEG)
    snap = s.snapshot(now_ms=5000)
    assert snap['journal_health'] == 'ready' and snap['checkpoint_health'] == 'ok'
    assert snap['retention_health'].startswith('retention: OSError')
    monkeypatch.undo()
    s.ingest(reading('lab', 'a', 200, 1200, 1.0), now_ms=1200)
    assert s.snapshot(now_ms=5000)['retention_health'] == 'ok'


def test_directory_is_fsynced_after_create_and_archive_moves(tmp_path, monkeypatch):
    calls = []
    real = SwarmCoordinator._fsync_dir
    monkeypatch.setattr(SwarmCoordinator, '_fsync_dir', staticmethod(lambda folder: (calls.append(folder.name), real(folder))))
    s = SwarmCoordinator('lab', journal=tmp_path / 'events.jsonl', journal_segment_bytes=SEG, journal_retention_bytes=SEG)
    s.ingest(hello('lab', 'a'), now_ms=1000)
    assert calls == [tmp_path.name]  # active journal created
    for seq in range(1, 60):
        s.ingest(reading('lab', 'a', seq, 1000 + seq, 1.0), now_ms=1000 + seq)
    assert 'events.jsonl.archive' in calls
    assert (tmp_path / 'events.jsonl.archive').is_dir()


def _hold_lock(path, seconds):
    handle = path.with_suffix(path.suffix + '.lock').open('a+b')
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def release():
        time.sleep(seconds)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN); handle.close()

    thread = threading.Thread(target=release); thread.start()
    return thread


@pytest.mark.skipif(os.name == 'nt', reason='flock semantics')
def test_lock_contention_waits_briefly_then_fails_cleanly(tmp_path):
    path = tmp_path / 'events.jsonl'
    s = SwarmCoordinator('lab', journal=path, lock_timeout_s=2.0)
    holder = _hold_lock(path, 0.2)
    assert s.ingest(hello('lab', 'a'), now_ms=1000)['accepted'] is True  # waited
    holder.join()
    quick = SwarmCoordinator('lab', journal=path, lock_timeout_s=0.05)
    holder = _hold_lock(path, 0.5)
    with pytest.raises(BlockingIOError):
        quick.ingest(reading('lab', 'a', 1, 1000, 1.0), now_ms=1000)
    holder.join()
    assert quick.snapshot(now_ms=1000)['journal_health'] == 'ready'  # contention is not a write failure
    assert quick.ingest(reading('lab', 'a', 1, 1000, 1.0), now_ms=1000)['accepted'] is True


def test_stale_in_process_instance_refuses_then_recover_reloads(tmp_path):
    path = tmp_path / 'events.jsonl'
    first = SwarmCoordinator('lab', journal=path)
    second = SwarmCoordinator('lab', journal=path)
    first.ingest(hello('lab', 'a'), now_ms=1000)
    with pytest.raises(OSError, match='recover'):
        second.ingest(hello('lab', 'b'), now_ms=1000)
    second.recover()
    second.ingest(hello('lab', 'b'), now_ms=1001)
    assert sorted(second.snapshot(now_ms=1001)['state']['nodes']) == ['a', 'b']


def test_journal_recover_reaches_a_swarm_that_cannot_open_and_heals_after_repair(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path)); service._SWARMS.clear()
    folder = tmp_path / 'lab'; folder.mkdir()
    expected = _fill(folder / 'events.jsonl', n=60, journal_retention_bytes=2 * SEG).snapshot(now_ms=10**7)
    for cp in folder.glob('events.jsonl.checkpoint.*.json'):
        cp.write_text('{}')
    first_archived = folder / 'events.jsonl.archive' / 'events.jsonl.part.00000001'
    backup = tmp_path / 'backup.part'
    shutil.move(first_archived, backup)
    try:
        with pytest.raises(ValueError):
            SwarmCoordinator('lab', journal=folder / 'events.jsonl')
        with pytest.raises(ValueError, match='full replay unavailable'):
            service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
        with pytest.raises(service.SwarmRecoveryRequired, match='recovery_required'):
            service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)
        with pytest.raises(service.SwarmRecoveryRequired):
            service.invoke('status', {'swarm_id': 'lab', 'status': 'paused'}, now_ms=10**7)
        assert 'lab' not in service._SWARMS
        shutil.move(backup, first_archived)  # operator restores the archived segment
        result = service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
        assert result['result']['journal_digest'] == expected['journal_digest']
        service.invoke('status', {'swarm_id': 'lab', 'status': 'paused'}, now_ms=10**7)
    finally:
        service._SWARMS.clear()


def test_service_cache_evicts_idle_swarms_lru_and_reopens_from_disk(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path)); service._SWARMS.clear()
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 2)
    try:
        for sid in ('s1', 's2', 's3'):
            service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1000)
        assert list(service._SWARMS) == ['s2', 's3']
        snap = service.invoke('snapshot', {'swarm_id': 's1'}, now_ms=1000)
        assert snap['swarm_recorded'] is True and 'a' in snap['result']['state']['nodes']
        assert list(service._SWARMS) == ['s3', 's1']
        # A leased (in-flight) swarm and one needing recovery are never evicted.
        service._LEASES['s3'] = 1
        service._SWARMS['s1']._write_failed = True
        with pytest.raises(ValueError, match='busy'):
            service.coordinator('s4')
        del service._LEASES['s3']
        service.coordinator('s4')
        assert list(service._SWARMS) == ['s1', 's4']
    finally:
        service._SWARMS.clear(); service._LEASES.clear(); service._PINS.clear()


def test_fusion_rejects_non_text_quantity_and_unit():
    s = SwarmCoordinator('lab')
    for bad in ([], {}, '', 5, 'x' * 500):
        with pytest.raises(ValueError):
            s.fuse(bad, 'arb', now_ms=1000)
        with pytest.raises(ValueError):
            s.fuse('signal', bad, now_ms=1000)
        with pytest.raises(ValueError):
            s.plan(bad, 'arb', now_ms=1000)
        with pytest.raises(ValueError):
            s.freshness_plan({}, 'signal', bad, now_ms=1000, byte_budget=10)


def test_conformal_rank_is_exact_rational():
    n, alpha = 999, 0.059
    references = [float(i) for i in range(n)]
    result = residual_interval([0.0] * n, references, estimate=0.0, training_id='t',
                               calibration_id='c', model_id='m', alpha=alpha)
    assert result['quantile_rank'] == 941  # ceil(1000 * 0.941); float arithmetic gives 942
    assert result['radius'] == 940.0
