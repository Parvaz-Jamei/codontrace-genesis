"""MqttSwarmBridge against a real mosquitto broker (skips when paho-mqtt or mosquitto is absent)."""
from __future__ import annotations

import shutil
import socket
import subprocess
import time

import pytest

from codontrace.swarm import SwarmCoordinator
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.protocol import canonical

mqtt = pytest.importorskip('paho.mqtt.client')
MOSQUITTO = shutil.which('mosquitto') or ('/usr/sbin/mosquitto' if shutil.os.path.exists('/usr/sbin/mosquitto') else None)
pytestmark = pytest.mark.skipif(MOSQUITTO is None, reason='mosquitto not installed')


def _port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture
def broker(tmp_path):
    port = _port()
    conf = tmp_path / 'm.conf'; conf.write_text(f'listener {port} 127.0.0.1\nallow_anonymous true\n')
    proc = subprocess.Popen([MOSQUITTO, '-c', str(conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.1).close(); break
        except OSError:
            time.sleep(0.05)
    yield port
    proc.terminate(); proc.wait(5)


def _wait(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def _bridge(monkeypatch, tmp_path, port):
    from codontrace.swarm.mqtt import MqttSwarmBridge
    monkeypatch.setattr(mqtt.Client, 'tls_set', lambda self, *a, **k: None)  # plain TCP test broker
    swarm = SwarmCoordinator('lab', journal=tmp_path / 'events.jsonl')
    bridge = MqttSwarmBridge(swarm, client_id='bridge1')
    client = bridge.connect('127.0.0.1', port=port, username='u', password='p')
    client.loop_start()
    pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='node-a', protocol=mqtt.MQTTv5)
    pub.connect('127.0.0.1', port); pub.loop_start()
    time.sleep(0.5)
    return swarm, bridge, client, pub


def _send(pub, msg, qos=1):
    pub.publish('genesis/swarm/lab/a/up', canonical(msg), qos=qos).wait_for_publish(5)


def test_happy_path_acks_and_journals(broker, monkeypatch, tmp_path):
    swarm, bridge, client, pub = _bridge(monkeypatch, tmp_path, broker)
    try:
        now = int(time.time() * 1000)
        _send(pub, hello('lab', 'a'))
        for seq in range(1, 6):
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        _send(pub, {'garbage': True})  # permanently invalid: acked
        _send(pub, reading('lab', 'a', 6, now, 6.0), qos=0)
        assert _wait(lambda: bridge.counters['journaled'] == 7 and bridge.counters['rejected'] == 1), bridge.health()
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


def test_journal_outage_records_losses_and_never_wedges_delivery(broker, monkeypatch, tmp_path):
    """During a journal outage every message is still acknowledged (MQTT 5 never resends on
    the same connection), so mosquitto's in-flight window (20) never fills; losses are
    recorded explicitly and health() is degraded until the first success after recovery."""
    swarm, bridge, client, pub = _bridge(monkeypatch, tmp_path, broker)
    try:
        now = int(time.time() * 1000)
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: bridge.counters['journaled'] == 1)
        swarm._write_failed = True  # e.g. ENOSPC / fsync failure on the journal
        for seq in range(1, 31):
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        assert _wait(lambda: bridge.counters['lost'] == 30, 10), bridge.health()
        health = bridge.health()
        assert health['state'] == 'degraded' and health['journal_ok'] is False
        assert [e['seq'] for e in health['recent_losses']] == list(range(1, 31))
        assert all(e['node_id'] == 'a' and e['boot_id'] and e['kind'] == 'reading' for e in health['recent_losses'])
        assert 'value' not in health['recent_losses'][0]  # no payload values
        swarm.recover()  # operator heals the journal via journal_recover
        now = int(time.time() * 1000)
        for seq in range(100, 110):
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        assert _wait(lambda: bridge.counters['journaled'] == 11, 5), bridge.health()
        assert bridge.health()['state'] == 'ok'
        assert SwarmCoordinator('lab', journal=tmp_path / 'events.jsonl').snapshot(now_ms=now)['state']['frames']['a/s']['value'] == 109.0
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


def test_duplicates_are_acked_counted_and_not_journaled(broker, monkeypatch, tmp_path):
    swarm, bridge, client, pub = _bridge(monkeypatch, tmp_path, broker)
    try:
        now = int(time.time() * 1000)
        _send(pub, hello('lab', 'a'))
        _send(pub, reading('lab', 'a', 1, now, 1.0))
        assert _wait(lambda: bridge.counters['journaled'] == 2)
        size = (tmp_path / 'events.jsonl').stat().st_size
        for _ in range(25):  # more than the in-flight window
            _send(pub, reading('lab', 'a', 1, now, 1.0))
        assert _wait(lambda: bridge.counters['duplicates'] == 25), bridge.health()
        assert (tmp_path / 'events.jsonl').stat().st_size == size
        assert bridge.counters['journaled'] == 2 and bridge.health()['state'] == 'ok'
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()


def test_opt_in_persistent_session_queues_while_bridge_is_offline(broker, monkeypatch, tmp_path):
    from codontrace.swarm.mqtt import MqttSwarmBridge
    monkeypatch.setattr(mqtt.Client, 'tls_set', lambda self, *a, **k: None)
    swarm = SwarmCoordinator('lab', journal=tmp_path / 'events.jsonl')

    def start():
        bridge = MqttSwarmBridge(swarm, client_id='bridge-persistent')
        client = bridge.connect('127.0.0.1', port=broker, username='u', password='p', session_expiry_s=300)
        client.loop_start(); time.sleep(0.5)
        return bridge, client

    bridge, client = start()
    pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='node-a', protocol=mqtt.MQTTv5)
    pub.connect('127.0.0.1', broker); pub.loop_start()
    try:
        _send(pub, hello('lab', 'a'))
        assert _wait(lambda: bridge.counters['journaled'] == 1)
        client.loop_stop(); client.disconnect(); time.sleep(0.3)
        now = int(time.time() * 1000)
        for seq in range(1, 4):  # published while the bridge is offline
            _send(pub, reading('lab', 'a', seq, now, float(seq)))
        bridge, client = start()
        assert _wait(lambda: bridge.counters['journaled'] == 3), bridge.health()
    finally:
        client.loop_stop(); client.disconnect(); pub.loop_stop(); pub.disconnect()
    with pytest.raises(ValueError):
        MqttSwarmBridge(swarm).connect('127.0.0.1', port=broker, username='u', password='p', session_expiry_s=60)
