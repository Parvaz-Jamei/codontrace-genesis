"""Review repros (round 4, tester-v5) updated for the bounded bridge.

Ported from patch-review/tester-v5/tests/test_review_r4.py. The outage and
persistent-session repros are unchanged; the transient-retry monkeypatch now
accepts the bound keywords; the lock-contention and unexpected-exception
repros assert the fixed behaviour (bounded wait, contained error) instead of
documenting the old one."""
from __future__ import annotations

import fcntl
import os
import shutil
import socket
import subprocess
import time

import pytest

from codontrace.swarm import SwarmCoordinator
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.protocol import canonical

mqtt = pytest.importorskip('paho.mqtt.client')
MOSQUITTO = shutil.which('mosquitto') or ('/usr/sbin/mosquitto' if os.path.exists('/usr/sbin/mosquitto') else None)
broker_only = pytest.mark.skipif(MOSQUITTO is None, reason='mosquitto not installed')


def _port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture
def broker(tmp_path):
    port = _port()
    conf = tmp_path / 'm.conf'; conf.write_text(f'listener {port} 127.0.0.1\nallow_anonymous true\n')
    log = tmp_path / 'mosq.log'
    proc = subprocess.Popen([MOSQUITTO, '-c', str(conf), '-v'], stdout=log.open('w'), stderr=subprocess.STDOUT)
    for _ in range(50):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.1).close(); break
        except OSError:
            time.sleep(0.05)
    yield port, log
    proc.terminate(); proc.wait(5)


def _wait(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def _bridge(monkeypatch, path, port, *, client_id='bridge1', **kw):
    from codontrace.swarm.mqtt import MqttSwarmBridge
    monkeypatch.setattr(mqtt.Client, 'tls_set', lambda self, *a, **k: None)
    swarm = SwarmCoordinator('lab', journal=path)
    bridge = MqttSwarmBridge(swarm, client_id=client_id)
    client = bridge.connect('127.0.0.1', port=port, username='u', password='p', **kw)
    client.loop_start()
    return swarm, bridge, client


def _pub(port):
    pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='node-a', protocol=mqtt.MQTTv5)
    pub.connect('127.0.0.1', port); pub.loop_start(); time.sleep(0.3)
    return pub


def _send(pub, msg, qos=1):
    pub.publish('genesis/swarm/lab/a/up', canonical(msg), qos=qos).wait_for_publish(5)


def _now():
    return int(time.time() * 1000)


@broker_only
def test_r3_finding_outage_then_recovery_resumes_delivery(broker, monkeypatch, tmp_path):
    port, _ = broker
    swarm, bridge, client = _bridge(monkeypatch, tmp_path / 'e.jsonl', port)
    pub = _pub(port)
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: bridge.counters['journaled'] == 1)
        swarm._write_failed = True
        now = _now()
        start = time.monotonic()
        for seq in range(1, 61):
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        assert _wait(lambda: bridge.counters['lost'] == 60, 10), bridge.health()
        outage_s = time.monotonic() - start
        h = bridge.health()
        assert h['state'] == 'degraded' and h['journal_ok'] is False and len(h['recent_losses']) == 60
        assert all('value' not in e for e in h['recent_losses']) and h['recent_losses'][0]['seq'] == 1
        assert bridge.counters['journal_failures'] == 4 + 59  # 4 attempts once, then one each
        assert outage_s < 5, outage_s
        swarm.recover()
        now = _now()
        for seq in range(100, 110):
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        assert _wait(lambda: bridge.counters['journaled'] == 11), bridge.health()
        assert bridge.health()['state'] == 'ok'
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


@broker_only
def test_transient_failure_is_absorbed_by_retry(broker, monkeypatch, tmp_path):
    port, _ = broker
    swarm, bridge, client = _bridge(monkeypatch, tmp_path / 'e.jsonl', port)
    pub = _pub(port)
    real = SwarmCoordinator.ingest
    fails = {'n': 2}

    def flaky(self, message, *, now_ms, **bounds):
        if fails['n']:
            fails['n'] -= 1
            raise OSError('transient')
        return real(self, message, now_ms=now_ms, **bounds)
    monkeypatch.setattr(SwarmCoordinator, 'ingest', flaky)
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: bridge.counters['journaled'] == 1)
        assert bridge.counters['lost'] == 0 and bridge.counters['journal_failures'] == 2
        assert bridge.health()['state'] == 'ok'
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


@broker_only
def test_lock_contention_is_bounded_and_keeps_the_connection(broker, monkeypatch, tmp_path):
    """A foreign file-lock holder costs each message one wait of at most
    lock_timeout_s (0.25 s), no retries; the connection stays up."""
    port, log = broker
    path = tmp_path / 'e.jsonl'
    swarm, bridge, client = _bridge(monkeypatch, path, port)
    pub = _pub(port)
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: bridge.counters['journaled'] == 1)
        holder = open(str(path) + '.lock', 'a+b'); fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
        now = _now(); t0 = time.monotonic()
        try:
            for seq in range(1, 6):
                _send(pub, reading('lab', 'a', seq, now, 1.0))
            assert _wait(lambda: bridge.counters['lost'] == 5, 30), bridge.health()
            elapsed = time.monotonic() - t0
        finally:
            fcntl.flock(holder.fileno(), fcntl.LOCK_UN); holder.close()
        assert client.is_connected()
        assert bridge.loss_reasons == {'JournalBusyError': 5}
        assert elapsed < 5 * 2.0, elapsed  # previously about 8.5 s for the first message alone
        _send(pub, reading('lab', 'a', 50, _now(), 1.0))
        assert _wait(lambda: bridge.counters['journaled'] == 2, 10)
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


@broker_only
def test_persistent_session_queues_fresh_and_rejects_stale_after_ttl(broker, monkeypatch, tmp_path):
    port, _ = broker
    path = tmp_path / 'e.jsonl'
    swarm, bridge, client = _bridge(monkeypatch, path, port, client_id='stable1', session_expiry_s=60)
    pub = _pub(port)
    _send(pub, hello('lab', 'a'))
    assert _wait(lambda: bridge.counters['journaled'] == 1)
    client.loop_stop(); client.disconnect()
    now = _now()
    for seq in range(1, 6):
        _send(pub, reading('lab', 'a', seq, now, float(seq)))
    _send(pub, reading('lab', 'a', 6, now - 60000, 6.0))  # stale sample (> ttl)
    from codontrace.swarm.mqtt import MqttSwarmBridge
    bridge2 = MqttSwarmBridge(swarm, client_id='stable1')
    client2 = bridge2.connect('127.0.0.1', port=port, username='u', password='p', session_expiry_s=60)
    client2.loop_start()
    try:
        assert _wait(lambda: bridge2.counters['journaled'] + bridge2.counters['rejected'] == 6, 8), bridge2.health()
        assert bridge2.counters['journaled'] == 5 and bridge2.counters['rejected'] == 1
        assert swarm.snapshot(now_ms=_now())['state']['nodes']['a']['seq'] == 5
    finally:
        client2.loop_stop(); client2.disconnect(); pub.loop_stop(); pub.disconnect()
    with pytest.raises(ValueError):
        MqttSwarmBridge(swarm).connect('127.0.0.1', port=port, username='u', password='p', session_expiry_s=60)


def test_unexpected_exception_in_on_message_is_contained():
    """A dispatch error after journaling no longer escapes into paho's loop thread."""
    from codontrace.swarm.mqtt import MqttSwarmBridge
    swarm = SwarmCoordinator('lab')
    bridge = MqttSwarmBridge(swarm)

    class Msg:
        topic = 'genesis/swarm/lab/a/up'; payload = canonical(hello('lab', 'a')).encode(); retain = False; mid = 1; qos = 1

    class C:
        def __init__(self): self.acked = []
        def ack(self, mid, qos): self.acked.append(mid)
        def publish(self, *a, **k): raise RuntimeError('client not connected')
    swarm.ingest(hello('lab', 'b'), now_ms=_now())
    swarm.command('b', 'sample', {'channel': 's'}, now_ms=_now())
    c = C()
    assert bridge.on_message(c, Msg()) is True
    assert c.acked == [1]
    assert bridge.counters['journaled'] == 1 and bridge.counters['dispatch_failures'] == 1
    assert bridge.counters['unexpected_errors'] == 0 and bridge.counters['lost'] == 0
