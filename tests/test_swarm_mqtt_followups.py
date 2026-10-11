"""MQTT bridge follow-ups: bounded lock wait, contained callback errors, rate-limited loss log,
stable 'genesis-' client ids, TTL limit of persistent sessions. Ported from review round 4."""
from __future__ import annotations

import fcntl
import logging
import os
import shutil
import socket
import subprocess
import threading
import time

import pytest

from codontrace.swarm import SwarmCoordinator
from codontrace.swarm import mqtt as bridge_module
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.mqtt import MqttSwarmBridge
from codontrace.swarm.protocol import canonical
from codontrace.swarm.runtime import JournalBusyError

TOPIC = 'genesis/swarm/lab/a/up'


def _now():
    return int(time.time() * 1000)


class _Msg:
    def __init__(self, payload, mid=1, topic=TOPIC):
        self.topic, self.payload, self.mid, self.qos, self.retain = topic, canonical(payload).encode(), mid, 1, False


class _Client:
    def __init__(self, publish_error=None):
        self.acks = []; self.publish_error = publish_error

    def ack(self, mid, qos):
        self.acks.append(mid)

    def publish(self, *args, **kwargs):
        if self.publish_error:
            raise self.publish_error
        return type('Info', (), {'rc': 0})()


@pytest.fixture
def bridge(tmp_path):
    swarm = SwarmCoordinator('lab', journal=tmp_path / 'events.jsonl')
    b = MqttSwarmBridge(swarm, client_id='bridge1')
    assert b.on_message(_Client(), _Msg(hello('lab', 'a')))
    return b


# (1) busy journal lock: bounded wait, no retries, coordinator stays writable

def test_busy_file_lock_waits_once_and_briefly(bridge, tmp_path):
    holder = open(str(tmp_path / 'events.jsonl') + '.lock', 'a+b')
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX)  # another process's writer, simulated
    client = _Client(); now = _now()
    try:
        start = time.monotonic()
        for seq in range(1, 6):
            assert not bridge.on_message(client, _Msg(reading('lab', 'a', seq, now, 1.0), mid=seq))
        elapsed = time.monotonic() - start
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN); holder.close()
    # Before: 4 attempts x 2 s for the first message, then 2 s per message (~16 s).
    assert elapsed < 5 * bridge.lock_timeout_s + 1.0, elapsed
    assert client.acks == [1, 2, 3, 4, 5]
    assert bridge.counters['lost'] == 5 and bridge.counters['journal_failures'] == 5  # no retries
    assert {e['reason'] for e in bridge.health()['recent_losses']} == {'JournalBusyError'}
    assert not bridge.swarm._write_failed  # nothing was written; no recovery needed
    assert bridge.on_message(client, _Msg(reading('lab', 'a', 6, _now(), 6.0), mid=6))
    assert bridge.health()['state'] == 'ok'


def test_busy_in_process_coordinator_is_bounded_too(bridge):
    taken, release = threading.Event(), threading.Event()

    def hold():
        with bridge.swarm._lock:
            taken.set(); release.wait(10)
    t = threading.Thread(target=hold); t.start()
    assert taken.wait(10)
    try:
        start = time.monotonic()
        assert not bridge.on_message(_Client(), _Msg(reading('lab', 'a', 1, _now(), 1.0)))
        assert time.monotonic() - start < bridge.lock_timeout_s + 1.0
    finally:
        release.set(); t.join(10)
    assert bridge.counters['lost'] == 1


def test_default_ingest_keeps_coordinator_lock_timeout(tmp_path):
    path = tmp_path / 'events.jsonl'
    swarm = SwarmCoordinator('lab', journal=path, lock_timeout_s=0.3)
    holder = open(str(path) + '.lock', 'a+b'); fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
    try:
        start = time.monotonic()
        with pytest.raises(BlockingIOError, match='locked by another writer') as info:
            swarm.ingest(hello('lab', 'a'), now_ms=1000)
        assert time.monotonic() - start >= 0.3 and isinstance(info.value, JournalBusyError)
        with pytest.raises(JournalBusyError):
            swarm.ingest(hello('lab', 'a'), now_ms=1000, lock_timeout_s=0)
        with pytest.raises(ValueError):
            swarm.ingest(hello('lab', 'a'), now_ms=1000, lock_timeout_s=-1)
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN); holder.close()
    assert not swarm._write_failed and swarm.ingest(hello('lab', 'a'), now_ms=1000) == {'accepted': True}


def test_bridge_lock_timeout_validated():
    for bad in (-1, 6, '1', True):
        with pytest.raises(ValueError):
            MqttSwarmBridge(SwarmCoordinator('lab'), lock_timeout_s=bad)


# (3) loss log is rate limited and summarized

def test_loss_log_is_rate_limited_and_summarized(bridge, caplog, monkeypatch):
    clock = {'t': 1000.0}
    monkeypatch.setattr(bridge, '_clock', lambda: clock['t'])
    bridge.swarm._write_failed = True
    client = _Client(); now = _now()
    with caplog.at_level(logging.WARNING, logger=bridge_module.__name__):
        for seq in range(1, 51):
            bridge.on_message(client, _Msg(reading('lab', 'a', seq, now, 1.0), mid=seq))
            clock['t'] += 1.0  # 50 s of losses at 1 msg/s
        bridge.swarm.recover()
        assert bridge.on_message(client, _Msg(reading('lab', 'a', 99, _now(), 1.0), mid=99))
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert bridge.counters['lost'] == 50 and len(bridge.losses) == 50
    assert len(errors) == 2, errors  # first loss + one 30 s summary, not 50 lines
    assert 'seq=1' in errors[0] and '30 more' in errors[1] and '(31 in this outage' in errors[1]
    assert any('resumed after 50 lost' in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    assert bridge._last_loss_log is None and bridge._outage_losses == 0


# (4) unexpected errors stay inside the callback; stable 'genesis-' ids allowed

def test_unexpected_exception_is_contained_and_acked_once(bridge, caplog):
    bridge.swarm.ingest(hello('lab', 'b'), now_ms=_now())
    bridge.swarm.command('b', 'sample', {'channel': 's'}, now_ms=_now())
    client = _Client(publish_error=RuntimeError('client not connected'))
    with caplog.at_level(logging.ERROR, logger=bridge_module.__name__):
        assert bridge.on_message(client, _Msg(reading('lab', 'a', 1, _now(), 1.0), mid=7)) is False
    assert client.acks == [7]
    assert bridge.counters['journaled'] == 2 and bridge.counters['unexpected_errors'] == 1
    assert bridge.health()['last_error'] == 'unexpected_bridge_error: RuntimeError'
    assert any(r.exc_info for r in caplog.records)


def test_unexpected_exception_before_ack_still_acks(bridge, monkeypatch):
    monkeypatch.setattr(bridge, 'handle', lambda *a, **k: (_ for _ in ()).throw(LookupError('boom')))
    client = _Client()
    assert bridge.on_message(client, _Msg(reading('lab', 'a', 1, _now(), 1.0), mid=3)) is False
    assert client.acks == [3] and bridge.counters['unexpected_errors'] == 1


def test_failing_ack_does_not_escape(bridge):
    class Broken(_Client):
        def ack(self, mid, qos):
            raise RuntimeError('socket closed')
    assert bridge.on_message(Broken(), _Msg(reading('lab', 'a', 1, _now(), 1.0))) is False
    assert bridge.counters['unexpected_errors'] == 1


paho = pytest.importorskip('paho.mqtt.client')


@pytest.fixture
def offline_paho(monkeypatch):
    calls = []
    monkeypatch.setattr(paho.Client, 'tls_set', lambda self, *a, **k: None)
    monkeypatch.setattr(paho.Client, 'connect', lambda self, *a, **k: calls.append(k))
    return calls


def test_connect_sets_suppress_exceptions(offline_paho):
    client = MqttSwarmBridge(SwarmCoordinator('lab'), client_id='bridge1').connect(
        'broker', username='u', password='p')
    assert client.suppress_exceptions is True


def test_explicit_genesis_prefixed_client_id_allows_persistent_session(offline_paho):
    swarm = SwarmCoordinator('lab')
    MqttSwarmBridge(swarm, client_id='genesis-bridge-1').connect('broker', username='u', password='p',
                                                                 session_expiry_s=60)
    assert offline_paho[-1]['clean_start'] is False
    with pytest.raises(ValueError, match='explicit stable client_id'):
        MqttSwarmBridge(swarm).connect('broker', username='u', password='p', session_expiry_s=60)


def test_docstring_states_session_ttl_limit():
    doc = MqttSwarmBridge.__doc__
    assert 'shorter than the coordinator' in doc and 'default 10 s' in doc


# Real broker (skips without mosquitto)

MOSQUITTO = shutil.which('mosquitto') or ('/usr/sbin/mosquitto' if os.path.exists('/usr/sbin/mosquitto') else None)
broker_only = pytest.mark.skipif(MOSQUITTO is None, reason='mosquitto not installed')


@pytest.fixture
def broker(tmp_path):
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    conf = tmp_path / 'm.conf'; conf.write_text(f'listener {port} 127.0.0.1\nallow_anonymous true\n')
    proc = subprocess.Popen([MOSQUITTO, '-c', str(conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.1).close(); break
        except OSError:
            time.sleep(0.05)
    yield port
    proc.terminate(); proc.wait(5)


def _wait(pred, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def _start(monkeypatch, swarm, port, client_id, **kw):
    monkeypatch.setattr(paho.Client, 'tls_set', lambda self, *a, **k: None)
    b = MqttSwarmBridge(swarm, client_id=client_id)
    connected = threading.Event()
    client = b.connect('127.0.0.1', port=port, username='u', password='p', **kw)
    inner = client.on_connect
    client.on_connect = lambda *a: (inner(*a), connected.set())
    client.loop_start()
    assert connected.wait(10)
    time.sleep(0.2)  # subscription round trip
    return b, client


def _publisher(port):
    pub = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id='node-a', protocol=paho.MQTTv5)
    pub.connect('127.0.0.1', port); pub.loop_start()
    return pub


def _send(pub, msg):
    pub.publish(TOPIC, canonical(msg), qos=1).wait_for_publish(5)


@broker_only
def test_broker_lock_contention_does_not_stall_network_thread(broker, monkeypatch, tmp_path):
    path = tmp_path / 'e.jsonl'
    swarm = SwarmCoordinator('lab', journal=path)
    b, client = _start(monkeypatch, swarm, broker, 'bridge1')
    pub = _publisher(broker)
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: b.counters['journaled'] == 1)
        holder = open(str(path) + '.lock', 'a+b'); fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
        try:
            now = _now(); t0 = time.monotonic()
            for seq in range(1, 6):
                _send(pub, reading('lab', 'a', seq, now, 1.0))
            assert _wait(lambda: b.counters['lost'] == 5), b.health()
            elapsed = time.monotonic() - t0
        finally:
            fcntl.flock(holder.fileno(), fcntl.LOCK_UN); holder.close()
        assert elapsed < 5, elapsed  # was ~16 s with 2 s waits and retries
        assert client.is_connected()
        _send(pub, reading('lab', 'a', 50, _now(), 1.0))  # no recover() needed after a busy lock
        assert _wait(lambda: b.counters['journaled'] == 2), b.health()
        assert b.health()['state'] == 'ok'
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


@broker_only
def test_broker_transient_failure_absorbed_by_retry(broker, monkeypatch, tmp_path):
    swarm = SwarmCoordinator('lab', journal=tmp_path / 'e.jsonl')
    real = SwarmCoordinator.ingest
    fails = {'n': 2}

    def flaky(self, message, **kw):
        if fails['n']:
            fails['n'] -= 1
            raise OSError('transient')
        return real(self, message, **kw)
    monkeypatch.setattr(SwarmCoordinator, 'ingest', flaky)
    b, client = _start(monkeypatch, swarm, broker, 'bridge1')
    pub = _publisher(broker)
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: b.counters['journaled'] == 1)
        assert b.counters['lost'] == 0 and b.counters['journal_failures'] == 2 and b.health()['state'] == 'ok'
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


@broker_only
def test_broker_persistent_session_keeps_fresh_and_rejects_stale(broker, monkeypatch, tmp_path):
    """Queued readings within the sample TTL are journaled; older ones are rejected as stale."""
    swarm = SwarmCoordinator('lab', journal=tmp_path / 'e.jsonl')
    b, client = _start(monkeypatch, swarm, broker, 'genesis-stable1', session_expiry_s=60)
    pub = _publisher(broker)
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: b.counters['journaled'] == 1)
        client.loop_stop(); client.disconnect(); time.sleep(0.3)
        now = _now()
        for seq in range(1, 6):
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        _send(pub, reading('lab', 'a', 6, now - swarm.ttl_ms - 50_000, 6.0))  # older than the TTL
        b2, client = _start(monkeypatch, swarm, broker, 'genesis-stable1', session_expiry_s=60)
        assert _wait(lambda: b2.counters['journaled'] + b2.counters['rejected'] == 6), b2.health()
        assert b2.counters['journaled'] == 5 and b2.counters['rejected'] == 1
        assert swarm.snapshot(now_ms=_now())['state']['nodes']['a']['seq'] == 5
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()
