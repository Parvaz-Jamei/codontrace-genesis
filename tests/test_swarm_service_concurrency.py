"""Swarm service: recovery-required reads, pins, per-swarm open lock, HTTP 409 and storms."""
from __future__ import annotations

import fcntl
import json
import os
import random
import threading
import time

import pytest

from codontrace.swarm import SwarmCoordinator, service
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.mqtt import MqttSwarmBridge
from codontrace.swarm.protocol import canonical

SEG = 1024
UI = {'predictions': [0, 0, 0], 'references': [1, 2, 3], 'estimate': 0, 'training_id': 't',
      'calibration_id': 'c', 'model_id': 'm'}


def _fill(path, n=60, **kw):
    s = SwarmCoordinator(path.parent.name, journal=path, journal_segment_bytes=SEG, **kw)
    sid = path.parent.name
    s.ingest(hello(sid, 'a'), now_ms=1000)
    for seq in range(1, n):
        s.ingest(reading(sid, 'a', seq, 1000 + seq, float(seq)), now_ms=1000 + seq)
    return s


def _unrecoverable(folder):
    _fill(folder / 'events.jsonl', journal_retention_bytes=2 * SEG)
    for cp in folder.glob('events.jsonl.checkpoint.*.json'):
        cp.write_text('{}')
    first = folder / 'events.jsonl.archive' / 'events.jsonl.part.00000001'
    backup = folder.parent / (folder.name + '.bak')
    first.rename(backup)
    return first, backup


def _clear():
    service._SWARMS.clear(); service._LEASES.clear(); service._PINS.clear(); service._OPENING.clear()


@pytest.fixture
def swarm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path)); _clear()
    yield tmp_path
    _clear()


def _tables_empty():
    return not service._LEASES and not service._OPENING


# --- r2 finding 1: failed recovery must not serve placeholder state -------------------------

def test_r2_1_failed_recovery_reads_refuse(swarm_dir):
    folder = swarm_dir / 'lab'; folder.mkdir()
    first, backup = _unrecoverable(folder)
    with pytest.raises(service.SwarmRecoveryRequired):
        service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)
    with pytest.raises(ValueError):
        service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
    assert 'lab' not in service._SWARMS
    for action, extra in (('snapshot', {}), ('fusion', {'quantity': 'signal', 'unit': 'arb'}),
                          ('diagnosis', {'quantity': 'signal', 'unit': 'arb'}),
                          ('freshness_plan', {'models': {}, 'quantity': 'signal', 'unit': 'arb', 'byte_budget': 1})):
        with pytest.raises(service.SwarmRecoveryRequired):
            service.invoke(action, {'swarm_id': 'lab', **extra}, now_ms=10**7)
    with pytest.raises((service.SwarmRecoveryRequired, OSError)):
        service.invoke('status', {'swarm_id': 'lab', 'status': 'paused'}, now_ms=10**7)
    from codontrace.console.science_tools import invoke_tool
    out = invoke_tool('swarm_inspect', {'swarm_id': 'lab'})
    assert out['ok'] is False and 'recovery_required' in out['error']
    backup.rename(first)
    assert service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)['ok']
    assert 'a' in service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)['result']['state']['nodes']
    assert _tables_empty() and not service._PINS


# --- r2 finding 2: bridge instance must be shared and never evicted ---------------------------

def test_r2_2_pinned_bridge_shares_instance(swarm_dir, monkeypatch):
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 2)
    swarm = service.coordinator('lab')
    bridge = MqttSwarmBridge(swarm)
    bridge.handle('genesis/swarm/lab/a/up', canonical(hello('lab', 'a')).encode(), now_ms=1000)
    service.invoke('ingest', {'swarm_id': 'x1', 'message': hello('x1', 'a')}, now_ms=1000)
    service.invoke('ingest', {'swarm_id': 'x2', 'message': hello('x2', 'a')}, now_ms=1000)
    assert list(service._SWARMS) == ['lab', 'x2'] and service._SWARMS['lab'] is swarm  # unpinned x1 evicted
    service.invoke('status', {'swarm_id': 'lab', 'status': 'running'}, now_ms=1001)
    bridge.handle('genesis/swarm/lab/a/up', canonical(reading('lab', 'a', 1, 1002, 1.0)).encode(), now_ms=1002)
    service.release('lab')
    with pytest.raises(ValueError):
        service.release('lab')


# --- r2 finding 3: slow open must not stall other swarms -------------------------------------

def test_r2_3_slow_open_does_not_block_others(swarm_dir):
    folder = swarm_dir / 'lab'; folder.mkdir()
    _fill(folder / 'events.jsonl', n=5)
    holder = open(folder / 'events.jsonl.lock', 'a+b'); fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
    errs = []
    try:
        t = threading.Thread(target=lambda: errs.append(pytest.raises(OSError, service.invoke, 'snapshot',
                                                                       {'swarm_id': 'lab'}, now_ms=10**7)))
        t.start(); time.sleep(0.1)
        start = time.monotonic()
        service.invoke('uncertainty_interval', {'swarm_id': 'other', **UI}, now_ms=1000)
        service.invoke('ingest', {'swarm_id': 'other2', 'message': hello('other2', 'a')}, now_ms=1000)
        waited = time.monotonic() - start
        t.join()
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN); holder.close()
    assert waited < 0.5, waited
    assert _tables_empty()


# --- adversarial: pins ------------------------------------------------------------------------

def test_no_pin_or_lease_leak_through_service_tools_and_http_paths(swarm_dir, monkeypatch):
    from codontrace.console.science_tools import invoke_tool
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 3)
    for i in range(20):
        sid = f's{i}'
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1000)
        service.invoke('snapshot', {'swarm_id': sid}, now_ms=1000)
        invoke_tool('swarm_inspect', {'swarm_id': sid})
        service.invoke('journal_recover', {'swarm_id': sid}, now_ms=1000)
        for bad in ({'swarm_id': sid, 'quantity': [], 'unit': 'x'},):
            with pytest.raises(ValueError):
                service.invoke('fusion', bad, now_ms=1000)
        with pytest.raises(ValueError):
            service.invoke('nope', {'swarm_id': sid}, now_ms=1000)
    assert not service._PINS and _tables_empty() and len(service._SWARMS) <= 3


def test_pinned_instance_with_journal_failure_refuses_reads_and_heals_in_place(swarm_dir, monkeypatch):
    swarm = service.coordinator('lab')
    bridge = MqttSwarmBridge(swarm)
    bridge.handle('genesis/swarm/lab/a/up', canonical(hello('lab', 'a')).encode(), now_ms=1000)
    real = os.fsync
    monkeypatch.setattr(os, 'fsync', lambda fd: (_ for _ in ()).throw(OSError('disk')))
    with pytest.raises(OSError):
        service.invoke('status', {'swarm_id': 'lab', 'status': 'running'}, now_ms=1001)
    monkeypatch.setattr(os, 'fsync', real)
    with pytest.raises(service.SwarmRecoveryRequired):
        service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=1002)
    with pytest.raises(OSError):
        bridge.handle('genesis/swarm/lab/a/up', canonical(reading('lab', 'a', 1, 1002, 1.0)).encode(), now_ms=1002)
    service.invoke('journal_recover', {'swarm_id': 'lab'}, now_ms=1003)
    assert service._SWARMS['lab'] is swarm  # healed in place, bridge keeps working
    bridge.handle('genesis/swarm/lab/a/up', canonical(reading('lab', 'a', 2, 1004, 2.0)).encode(), now_ms=1004)
    snap = service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=1004)['result']
    assert snap['state']['frames']['a/s']['value'] == 2.0
    service.release('lab')


def test_pinned_unrecoverable_swarm_stays_refusing_then_heals(swarm_dir):
    folder = swarm_dir / 'lab'; folder.mkdir()
    _fill(folder / 'events.jsonl', n=60, journal_retention_bytes=2 * SEG)
    swarm = service.coordinator('lab')  # pinned, opened fine
    for cp in folder.glob('events.jsonl.checkpoint.*.json'):
        cp.write_text('{}')
    first = folder / 'events.jsonl.archive' / 'events.jsonl.part.00000001'
    backup = swarm_dir / 'b'; first.rename(backup)
    with pytest.raises(ValueError):
        service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
    assert service._SWARMS['lab'] is swarm
    with pytest.raises(service.SwarmRecoveryRequired):
        service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)
    backup.rename(first)
    service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
    assert service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)['result']['journal_health'] == 'ready'
    service.release('lab')


# --- adversarial: concurrency of open / evict / recover --------------------------------------

def test_open_evict_recover_storm(swarm_dir, monkeypatch):
    monkeypatch.setattr(service, 'MAX_CACHED_SWARMS', 3)
    sids = [f'z{i}' for i in range(6)]
    for sid in sids:
        service.invoke('ingest', {'swarm_id': sid, 'message': hello(sid, 'a')}, now_ms=1000)
    constructed = {}
    real_init = SwarmCoordinator.__init__

    def counting(self, swarm_id, **kw):
        real_init(self, swarm_id, **kw)
        if kw.get('journal') is not None:
            constructed.setdefault(swarm_id, []).append(self)
    monkeypatch.setattr(SwarmCoordinator, '__init__', counting)
    stop = threading.Event(); unexpected = []; seqs = {sid: 0 for sid in sids}; seq_lock = threading.Lock()

    def worker(k):
        rng = random.Random(k)
        while not stop.is_set():
            sid = rng.choice(sids); op = rng.random()
            try:
                if op < 0.5:
                    with seq_lock:
                        seqs[sid] += 1; seq = seqs[sid]
                    service.invoke('ingest', {'swarm_id': sid, 'message': reading(sid, 'a', seq, 10**6 + seq, 1.0)},
                                   now_ms=10**6 + seq)
                elif op < 0.8:
                    service.invoke('snapshot', {'swarm_id': sid}, now_ms=2 * 10**6)
                else:
                    service.invoke('journal_recover', {'swarm_id': sid}, now_ms=2 * 10**6)
            except service.SwarmCapacityError:
                pass
            except ValueError as e:
                if 'reordered' not in str(e) and 'host clock' not in str(e):
                    unexpected.append(repr(e))
            except OSError as e:
                unexpected.append(repr(e))
    threads = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
    for t in threads: t.start()
    time.sleep(4); stop.set()
    for t in threads: t.join()
    assert not unexpected, unexpected[:5]
    assert _tables_empty() and not service._PINS
    for sid in sids:
        s = SwarmCoordinator(sid, journal=swarm_dir / sid / 'events.jsonl')
        f = SwarmCoordinator(sid, journal=swarm_dir / sid / 'events.jsonl'); f.recover(full_replay=True)
        assert s.snapshot(now_ms=3 * 10**6)['state'] == f.snapshot(now_ms=3 * 10**6)['state']


def test_opening_table_does_not_grow_for_many_ids(swarm_dir):
    for i in range(500):
        service.invoke('snapshot', {'swarm_id': f'ghost{i}'}, now_ms=1000)
        service.invoke('uncertainty_interval', {'swarm_id': f'u{i}', **UI}, now_ms=1000)
    assert _tables_empty() and not service._SWARMS and not list(swarm_dir.iterdir())


def test_recovery_required_is_a_distinct_409_over_http(swarm_dir, monkeypatch):
    """POST and GET /api/swarm answer 409 {"error": "recovery_required"}, not the generic 400."""
    import urllib.request
    from urllib.error import HTTPError

    from codontrace.console.server import make_server
    folder = swarm_dir / 'lab'; folder.mkdir(); _unrecoverable(folder)
    srv = make_server('127.0.0.1', 0); t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{srv.server_address[1]}/api/swarm',
                                     data=json.dumps({'action': 'snapshot', 'args': {'swarm_id': 'lab'}}).encode(),
                                     headers={'Content-Type': 'application/json'})
        with pytest.raises(HTTPError) as err:
            urllib.request.urlopen(req)
        body = json.loads(err.value.read())
        assert err.value.code == 409 and body['ok'] is False and body['error'] == 'recovery_required', body
        with pytest.raises(HTTPError) as err:
            urllib.request.urlopen(f'http://127.0.0.1:{srv.server_address[1]}/api/swarm?swarm_id=lab')
        assert err.value.code == 409 and json.loads(err.value.read())['error'] == 'recovery_required'
        bad = urllib.request.Request(f'http://127.0.0.1:{srv.server_address[1]}/api/swarm',
                                     data=json.dumps({'action': 'nope', 'args': {'swarm_id': 'lab'}}).encode(),
                                     headers={'Content-Type': 'application/json'})
        with pytest.raises(HTTPError) as err:
            urllib.request.urlopen(bad)
        assert err.value.code == 400  # ordinary invalid requests keep the generic 400
    finally:
        srv.shutdown(); srv.server_close()
