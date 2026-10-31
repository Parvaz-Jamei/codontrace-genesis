"""Swarm service: recovery-required reads, pinned coordinators vs LRU eviction, open outside the global lock."""
from __future__ import annotations

import fcntl
import json
import shutil
import threading
import time

import pytest

from codontrace.swarm import SwarmCoordinator, service
from codontrace.swarm.decision_support import residual_interval
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.mqtt import MqttSwarmBridge
from codontrace.swarm.protocol import canonical

SEG = 1024


def _fill(path, n=60, **kw):
    s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG, **kw)
    s.ingest(hello('lab', 'a'), now_ms=1000)
    for seq in range(1, n):
        s.ingest(reading('lab', 'a', seq, 1000 + seq, float(seq)), now_ms=1000 + seq)
    return s


@pytest.fixture
def swarm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path)); service._SWARMS.clear(); service._LEASES.clear(); service._PINS.clear()
    yield tmp_path
    service._SWARMS.clear(); service._LEASES.clear(); service._PINS.clear()


def _unrecoverable(folder):
    _fill(folder / 'events.jsonl', journal_retention_bytes=2 * SEG)
    for cp in folder.glob('events.jsonl.checkpoint.*.json'):
        cp.write_text('{}')
    (folder / 'events.jsonl.archive' / 'events.jsonl.part.00000001').unlink()


def test_failed_recovery_never_serves_placeholder_state(swarm_dir):
    """A failed journal_recover caches nothing; every read keeps refusing with
    recovery_required instead of answering from empty placeholder state."""
    folder = swarm_dir / 'lab'; folder.mkdir()
    _unrecoverable(folder)
    with pytest.raises(ValueError):
        service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)  # reads refuse before recovery attempt
    with pytest.raises(ValueError):
        service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
    # Reads must keep refusing (the recorded history exists but cannot be loaded).
    assert 'lab' not in service._SWARMS
    reads = [('snapshot', {}), ('fusion', {'quantity': 'signal', 'unit': 'arb'}),
             ('diagnosis', {'quantity': 'signal', 'unit': 'arb'}),
             ('freshness_plan', {'models': {}, 'quantity': 'signal', 'unit': 'arb', 'byte_budget': 10})]
    for action, extra in reads:
        with pytest.raises(service.SwarmRecoveryRequired, match='recovery_required'):
            service.invoke(action, {'swarm_id': 'lab', **extra}, now_ms=1100)
    from codontrace.console.science_tools import invoke_tool
    out = invoke_tool('swarm_inspect', {'swarm_id': 'lab'})
    assert out['ok'] is False and 'recovery_required' in json.dumps(out) and '0' * 64 not in json.dumps(out)


def test_mqtt_bridge_coordinator_is_pinned_and_never_forks(swarm_dir, monkeypatch):
    """service.coordinator() pins the instance the bridge holds: LRU eviction skips it,
    HTTP requests share it, and every bridged reading is journaled."""
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 2)
    bridge = MqttSwarmBridge(service.coordinator('lab'))
    bridge.handle('genesis/swarm/lab/a/up', canonical(hello('lab', 'a')).encode(), now_ms=1000)
    for sid in ('x1', 'x2'):
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1000)
    assert service._SWARMS.get('lab') is bridge.swarm  # pinned, not evicted
    service.invoke('status', {'swarm_id': 'lab', 'status': 'running'}, now_ms=1001)  # e.g. dashboard button
    bridge.handle('genesis/swarm/lab/a/up', canonical(reading('lab', 'a', 1, 1002, 1.0)).encode(), now_ms=1002)
    reopened = SwarmCoordinator('lab', journal=swarm_dir / 'lab' / 'events.jsonl')
    assert reopened.snapshot(now_ms=1002)['state']['frames']['a/s']['value'] == 1.0
    assert reopened.snapshot(now_ms=1002)['journal_digest'] == bridge.swarm.snapshot(now_ms=1002)['journal_digest']
    service.release('lab')
    for sid in ('x3', 'x4'):
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1003)
    assert 'lab' not in service._SWARMS  # evictable once released


def test_opening_a_locked_swarm_does_not_block_other_requests(swarm_dir):
    """Opening (bounded lock wait, possible full replay) happens outside service._LOCK."""
    folder = swarm_dir / 'lab'; folder.mkdir()
    _fill(folder / 'events.jsonl', n=5)
    holder = open(folder / 'events.jsonl.lock', 'a+b')
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX)  # another process's writer, simulated
    try:
        t = threading.Thread(target=lambda: pytest.raises(OSError, service.invoke, 'snapshot', {'swarm_id': 'lab'}, now_ms=10**7))
        t.start(); time.sleep(0.1)
        start = time.monotonic()
        service.invoke('uncertainty_interval', {'swarm_id': 'other', 'predictions': [0, 0, 0], 'references': [1, 2, 3],
                       'estimate': 0, 'training_id': 't', 'calibration_id': 'c', 'model_id': 'm'}, now_ms=1000)
        waited = time.monotonic() - start
        t.join()
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN); holder.close()
    assert waited < 0.5, f'unrelated stateless request blocked {waited:.2f}s'


def test_restore_false_instance_cannot_write_before_recovery(swarm_dir):
    folder = swarm_dir / 'lab'; folder.mkdir()
    _fill(folder / 'events.jsonl', n=10)
    before = (folder / 'events.jsonl').read_bytes()
    s = SwarmCoordinator('lab', journal=folder / 'events.jsonl', restore=False)
    for call in (lambda: s.ingest(hello('lab', 'b'), now_ms=5000), lambda: s.set_status('paused', now_ms=5000),
                 lambda: s.boundary({'g': 1}, now_ms=5000)):
        with pytest.raises(OSError):
            call()
    assert (folder / 'events.jsonl').read_bytes() == before
    s.recover()
    assert s.set_status('paused', now_ms=5000) == {'status': 'paused'}


WAIT_S = 30  # upper bound for a hang only; no step depends on how fast a thread runs


def _wait_until(predicate, what):
    deadline = time.monotonic() + WAIT_S
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError(f'timed out waiting for {what}')
        time.sleep(0.001)


def _pause_inside(monkeypatch, obj, name):
    """Make ``obj.<name>`` block once (inside the journal lock) until released.

    Returns ``(entered, release, restore)``. ``restore`` puts the real
    method back through ``monkeypatch`` itself, so monkeypatch's own undo at
    teardown stays consistent with the object (deleting the attribute behind
    monkeypatch's back makes its undo fail on pytest 9.2).
    """
    entered, release = threading.Event(), threading.Event()
    real = getattr(obj, name)

    def paused(*args, **kwargs):
        if not entered.is_set():
            entered.set()
            assert release.wait(WAIT_S), 'paused call was never released'
        return real(*args, **kwargs)
    monkeypatch.setattr(obj, name, paused, raising=False)

    def restore():
        monkeypatch.setattr(obj, name, real)
    return entered, release, restore


class _FlockProbe:
    """Records threads whose non-blocking ``flock`` attempt found the lock held."""

    def __init__(self, monkeypatch):
        self.blocked: set[int] = set()
        real = fcntl.flock

        def flock(fd, op):
            try:
                return real(fd, op)
            except OSError:
                self.blocked.add(threading.get_ident())
                raise
        monkeypatch.setattr(fcntl, 'flock', flock)


def test_restore_false_and_normal_instance_race(swarm_dir, monkeypatch):
    """A restore=False instance recovering while another instance writes the same journal.

    Deterministic replacement of a sleep/scheduling race (it starved the
    recovering instance's bounded lock wait under load, ``journal is locked by
    another writer``). The schedule is explicit: interleaved writes and
    recoveries across segment rotations, then real lock contention in both
    directions, forced with events instead of timing.
    """
    folder = swarm_dir / 'lab'; folder.mkdir()
    path = folder / 'events.jsonl'
    _fill(path, n=10)
    opts = {'journal_segment_bytes': SEG, 'lock_timeout_s': WAIT_S}
    normal = SwarmCoordinator('lab', journal=path, **opts)
    rec = SwarmCoordinator('lab', journal=path, restore=False, **opts)
    seq = iter(range(100, 10**6))

    def write():
        i = next(seq)
        return normal.ingest(reading('lab', 'a', i, 10**6 + i, 1.0), now_ms=10**6 + i)

    def in_thread(fn):
        out = {}
        def run():
            try:
                out['result'] = fn()
            except BaseException as error:  # surfaced in the main thread
                out['error'] = error
        t = threading.Thread(target=run, daemon=True); t.start()
        return t, out

    def joined(t, out):
        t.join(WAIT_S)
        assert not t.is_alive(), 'worker thread hung'
        if 'error' in out:
            raise out['error']
        return out['result']

    # 1. Interleaved schedule: 20 recoveries between 200 writes (several rotations).
    for _ in range(20):
        for _ in range(10):
            assert write() == {'accepted': True}
        assert rec.recover()['journal_digest'] == normal.snapshot(now_ms=2 * 10**6)['journal_digest']
    assert normal.snapshot(now_ms=2 * 10**6)['journal_segment_count'] > 1

    probe = _FlockProbe(monkeypatch)

    # 2. Recovery starts while a write holds the journal lock: it waits, then adopts that record.
    entered, release, restore = _pause_inside(monkeypatch, normal, '_apply')
    try:
        writer = in_thread(write)
        assert entered.wait(WAIT_S)
        recovering = in_thread(rec.recover)
        # Blocked on the cross-process file lock, not merely holding its own RLock.
        _wait_until(lambda: recovering[0].ident in probe.blocked, 'recover() to find the journal flock held')
        assert recovering[0].is_alive()
    finally:
        release.set()
    assert joined(*writer) == {'accepted': True}
    assert joined(*recovering)['journal_digest'] == normal.snapshot(now_ms=2 * 10**6)['journal_digest']
    restore()

    # 3. A write starts while recovery holds the lock: it waits, then appends on the same chain.
    entered, release, restore = _pause_inside(monkeypatch, rec, '_restore')
    try:
        recovering = in_thread(rec.recover)
        assert entered.wait(WAIT_S)
        writer = in_thread(write)
        _wait_until(lambda: writer[0].ident in probe.blocked, 'ingest() to find the journal flock held')
        assert writer[0].is_alive()
    finally:
        release.set()
    joined(*recovering)
    assert joined(*writer) == {'accepted': True}
    restore()

    rec.recover()
    final = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    assert final.snapshot(now_ms=2 * 10**6)['journal_digest'] == rec.snapshot(now_ms=2 * 10**6)['journal_digest']
    assert final.snapshot(now_ms=2 * 10**6)['journal_digest'] == normal.snapshot(now_ms=2 * 10**6)['journal_digest']
    full = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    full.recover(full_replay=True)
    assert full.snapshot(now_ms=2 * 10**6)['state'] == final.snapshot(now_ms=2 * 10**6)['state']
    assert full.snapshot(now_ms=2 * 10**6)['state']['nodes']['a']['seq'] == next(seq) - 1


def test_eviction_reload_preserves_pending_commands_and_state(swarm_dir, monkeypatch):
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 2)
    service.invoke('ingest', {'swarm_id': 'lab', 'message': hello('lab', 'a')}, now_ms=1000)
    service.invoke('command', {'swarm_id': 'lab', 'node_id': 'a', 'operation': 'sample', 'params': {'channel': 's'},
                               'timeout_ms': 60000}, now_ms=1001)
    before = service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=1002)['result']
    for sid in ('x1', 'x2', 'x3'):
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1000)
    assert 'lab' not in service._SWARMS
    after = service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=1002)['result']
    assert after['state'] == before['state'] and after['journal_digest'] == before['journal_digest']
    assert after['state']['commands']['cmd-1']['status'] == 'pending'


def test_eviction_never_drops_coordinator_during_request(swarm_dir, monkeypatch):
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 2)
    for sid in ('a1', 'a2', 'a3', 'a4'):
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1000)
    stop = threading.Event(); bad = []

    def hammer(sid):
        seq = 0
        while not stop.is_set():
            seq += 1
            try:
                service.invoke('ingest', {'swarm_id': sid, 'message': reading(sid, 'a', seq, 10**6 + seq, 1.0)}, now_ms=10**6 + seq)
            except OSError as e:
                bad.append((sid, str(e)))
            except ValueError as e:
                if 'busy' not in str(e):
                    bad.append((sid, str(e)))
    threads = [threading.Thread(target=hammer, args=(s,)) for s in ('a1', 'a2', 'a3', 'a4')]
    for t in threads: t.start()
    time.sleep(3); stop.set()
    for t in threads: t.join()
    assert not bad, bad[:5]


@pytest.mark.parametrize('alpha', [0.1, 0.059, 0.5, 0.001, 1 / 3, 0.30000000000000004, 0.1 + 0.2])
def test_exact_rank_with_odd_floats(alpha):
    out = residual_interval([0.0] * 9, [float(i) for i in range(9)], estimate=0, training_id='t',
                            calibration_id='c', model_id='m', alpha=alpha)
    assert 1 <= out['quantile_rank'] <= 10


@pytest.mark.parametrize('alpha', [1e-20, True, False, 0, '0.1', float('nan'), 0.6])
def test_rank_rejects_bad_alpha(alpha):
    with pytest.raises(ValueError):
        residual_interval([0.0] * 9, [float(i) for i in range(9)], estimate=0, training_id='t',
                          calibration_id='c', model_id='m', alpha=alpha)


def test_rank_numpy_float():
    np = pytest.importorskip('numpy')
    out = residual_interval([0.0] * 999, [float(i) for i in range(999)], estimate=0, training_id='t',
                            calibration_id='c', model_id='m', alpha=np.float64(0.059))
    assert out['quantile_rank'] == 941


def test_auto_full_replay_rejects_archive_gap_and_broken_link(tmp_path):
    path = tmp_path / 'events.jsonl'
    _fill(path, n=80, journal_retention_bytes=2 * SEG)
    for cp in tmp_path.glob('events.jsonl.checkpoint.*.json'):
        cp.unlink()
    archived = sorted((tmp_path / 'events.jsonl.archive').glob('events.jsonl.part.*'))
    assert len(archived) >= 3
    ok = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)  # auto full replay works
    digest = ok.snapshot(now_ms=10**7)['journal_digest']
    for cp in tmp_path.glob('events.jsonl.checkpoint.*.json'):
        cp.unlink()
    # gap in the middle of the archive
    mid = archived[1]; keep = tmp_path / 'mid.bak'; shutil.move(mid, keep)
    with pytest.raises(ValueError):
        SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    shutil.move(keep, mid)
    # last archived segment swapped for a self-consistent but different file: link must fail
    last = archived[-1]; orig = last.read_bytes()
    lines = orig.splitlines(keepends=True)
    last.write_bytes(b''.join(lines[:-1]))
    with pytest.raises(ValueError):
        SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    last.write_bytes(orig)
    assert SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG).snapshot(now_ms=10**7)['journal_digest'] == digest


def test_checkpoint_after_archive_still_valid_and_cheap(tmp_path, monkeypatch):
    path = tmp_path / 'events.jsonl'
    _fill(path, n=200, journal_retention_bytes=2 * SEG)
    calls = []
    real = SwarmCoordinator._replay_file
    monkeypatch.setattr(SwarmCoordinator, '_replay_file', lambda self, p: (calls.append(p.name), real(self, p))[1])
    s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG, journal_retention_bytes=2 * SEG)
    assert calls == ['events.jsonl'] and s.snapshot(now_ms=10**7)['checkpoint_health'] == 'ok'


class _Msg:
    def __init__(self, topic, payload, mid):
        self.topic, self.payload, self.mid, self.qos, self.retain = topic, payload, mid, 1, False


class _Client:
    def __init__(self):
        self.acks = []

    def ack(self, mid, qos):
        self.acks.append(mid)

    def publish(self, *args, **kwargs):
        return type('Info', (), {'rc': 0})()


def test_bridge_acks_only_journaled_or_invalid_telemetry_with_cache_of_two(swarm_dir, monkeypatch):
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 2)
    bridge = MqttSwarmBridge(service.coordinator('lab'))
    client = _Client()
    topic = 'genesis/swarm/lab/a/up'
    assert bridge.on_message(client, _Msg(topic, canonical(hello('lab', 'a')).encode(), 1))
    for i, sid in enumerate(('x1', 'x2', 'x3', 'x4')):
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')})
        service.invoke('status', {'swarm_id': 'lab', 'status': 'running'})  # HTTP shares the pinned instance
        now = int(time.time() * 1000)
        assert bridge.on_message(client, _Msg(topic, canonical(reading('lab', 'a', i + 1, now, float(i))).encode(), 10 + i))
    assert not bridge.on_message(client, _Msg(topic, b'not json', 50))  # invalid: acked, counted
    real_open = type(swarm_dir).open

    def broken(self, mode='r', *a, **k):
        if self.name == 'events.jsonl' and mode == 'a':
            raise OSError('disk gone')
        return real_open(self, mode, *a, **k)

    monkeypatch.setattr(type(swarm_dir), 'open', broken)
    assert not bridge.on_message(client, _Msg(topic, canonical(reading('lab', 'a', 9, int(time.time() * 1000), 9.0)).encode(), 60))
    monkeypatch.setattr(type(swarm_dir), 'open', real_open)
    assert client.acks == [1, 10, 11, 12, 13, 50, 60]  # always acknowledged; the loss is recorded
    health = bridge.health()
    assert health['journaled'] == 5 and health['rejected'] == 1 and health['lost'] == 1
    assert health['journal_failures'] == 1 + len(bridge.retry_delays)  # bounded in-bridge retry
    assert health['state'] == 'degraded' and health['last_error'] == 'telemetry_lost_journal_unavailable'
    assert health['recent_losses'][0]['seq'] == 9
    disk = SwarmCoordinator('lab', journal=swarm_dir / 'lab' / 'events.jsonl')
    assert disk.snapshot(now_ms=int(time.time() * 1000))['state']['frames']['a/s']['value'] == 3.0  # every acked reading journaled


def test_concurrent_open_of_one_swarm_constructs_once(swarm_dir, monkeypatch):
    folder = swarm_dir / 'lab'; folder.mkdir()
    _fill(folder / 'events.jsonl', n=5)
    built = []
    real = service.SwarmCoordinator

    def slow(*args, **kwargs):
        built.append(1); time.sleep(0.2)
        return real(*args, **kwargs)

    monkeypatch.setattr(service, 'SwarmCoordinator', slow)
    out = []
    threads = [threading.Thread(target=lambda: out.append(service._cached('lab', create=True))) for _ in range(4)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(built) == 1 and len({id(x) for x in out}) == 1 and not service._OPENING
