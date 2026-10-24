"""Review probes (round 6, patch-review/b-mqtt-scratch/tests/test_review_r6_probes.py), kept verbatim.

A pass means the reviewed fix holds; the last group covers failing acks (F1)."""
from __future__ import annotations

import fcntl
import logging
import os
import threading
import time

import pytest

from codontrace.swarm import SwarmCoordinator
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.mqtt import MqttSwarmBridge
from codontrace.swarm.protocol import canonical

TOPIC = 'genesis/swarm/lab/a/up'


def _now():
    return int(time.time() * 1000)


class _Msg:
    def __init__(self, payload, mid=1, raw=None):
        self.topic, self.mid, self.qos, self.retain = TOPIC, mid, 1, False
        self.payload = raw if raw is not None else canonical(payload).encode()


class _Client:
    def __init__(self, publish_error=None):
        self.acks = []; self.publish_error = publish_error

    def ack(self, mid, qos):
        self.acks.append(mid)

    def publish(self, *a, **k):
        if self.publish_error:
            raise self.publish_error
        return type('I', (), {'rc': 0})()


class _BrokenAck(_Client):
    def ack(self, mid, qos):
        raise RuntimeError('socket closed')


@pytest.fixture
def bridge(tmp_path):
    b = MqttSwarmBridge(SwarmCoordinator('lab', journal=tmp_path / 'events.jsonl'), client_id='bridge1')
    assert b.on_message(_Client(), _Msg(hello('lab', 'a')))
    return b


def _hold_flock(path):
    h = open(str(path) + '.lock', 'a+b'); fcntl.flock(h.fileno(), fcntl.LOCK_EX); return h


# F1
def test_f1_unexpected_before_journal_is_loss(bridge, monkeypatch):
    monkeypatch.setattr(bridge.swarm, 'ingest', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('x')))
    c = _Client()
    assert bridge.on_message(c, _Msg(reading('lab', 'a', 1, _now(), 1.0), mid=4)) is False
    h = bridge.health()
    assert c.acks == [4] and h['lost'] == 1 and h['state'] == 'degraded'
    assert h['loss_reasons'] == {'unexpected:RuntimeError': 1}


# F2
def test_f2_same_process_slow_write_loses_nothing(bridge, monkeypatch):
    s = bridge.swarm; real = os.fsync; started = threading.Event()

    def slow(fd):
        time.sleep(0.5); return real(fd)

    def console_write():
        started.set(); s.boundary({'generation': 1, 'world_digest': 'f' * 64}, now_ms=_now())
    monkeypatch.setattr(os, 'fsync', slow)
    t = threading.Thread(target=console_write); t.start(); started.wait(5); time.sleep(0.05)
    c = _Client()
    try:
        ok = bridge.on_message(c, _Msg(reading('lab', 'a', 1, _now(), 1.0), mid=5))
    finally:
        t.join(10); monkeypatch.setattr(os, 'fsync', real)
    assert ok is True and bridge.counters['lost'] == 0


def test_f2_in_process_wait_bound_still_applies(bridge):
    b2 = MqttSwarmBridge(bridge.swarm, client_id='b2', coordinator_wait_s=0.2)
    taken, release = threading.Event(), threading.Event()
    t = threading.Thread(target=lambda: (bridge.swarm._lock.acquire(), taken.set(), release.wait(5),
                                         bridge.swarm._lock.release())); t.start(); taken.wait(5)
    try:
        t0 = time.monotonic()
        assert b2.on_message(_Client(), _Msg(reading('lab', 'a', 1, _now(), 1.0))) is False
        el = time.monotonic() - t0
    finally:
        release.set(); t.join(5)
    assert 0.15 < el < 0.6 and b2.loss_reasons == {'CoordinatorBusy': 1}


# F3
def test_f3_drain_bounded_and_deferred(bridge, tmp_path):
    s = bridge.swarm; h = _hold_flock(tmp_path / 'events.jsonl'); started = threading.Event()

    def console_write():
        started.set()
        try:
            s.set_status('paused', now_ms=_now())
        except BlockingIOError:
            pass
    t = threading.Thread(target=console_write); t.start(); started.wait(5); time.sleep(0.05)
    try:
        t0 = time.monotonic()
        from codontrace.swarm.runtime import JournalBusyError
        with pytest.raises(JournalBusyError):
            bridge.drain(_Client(), now_ms=_now(), lock_timeout_s=bridge.lock_timeout_s)
        el = time.monotonic() - t0
    finally:
        t.join(5); fcntl.flock(h.fileno(), fcntl.LOCK_UN); h.close()
    assert el < 0.6


# F4
def test_f4_unexpected_error_log_rate_limited(bridge, monkeypatch, caplog):
    monkeypatch.setattr(bridge.swarm, 'ingest', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('x')))
    with caplog.at_level(logging.ERROR):
        for i in range(50):
            bridge.on_message(_Client(), _Msg(reading('lab', 'a', i + 1, _now(), 1.0), mid=i))
    tb = sum(1 for r in caplog.records if r.exc_info)
    n = sum(1 for r in caplog.records if r.levelno >= logging.ERROR)
    print('error records', n, 'with traceback', tb)
    assert tb <= 1 and n <= 3


# F5
def test_f5_dispatch_error_counted_as_dispatch_failure_only(bridge):
    bridge.swarm.ingest(hello('lab', 'b'), now_ms=_now())
    bridge.swarm.command('b', 'sample', {'channel': 's'}, now_ms=_now())
    c = _Client(publish_error=RuntimeError('not connected'))
    assert bridge.on_message(c, _Msg(reading('lab', 'a', 1, _now(), 1.0), mid=7)) is True
    assert bridge.counters['unexpected_errors'] == 0 and bridge.counters['dispatch_failures'] == 1
    assert bridge.counters['journaled'] == 2 and bridge.counters['lost'] == 0


# F8
def test_f8_client_id_read_only():
    b = MqttSwarmBridge(SwarmCoordinator('lab'))
    with pytest.raises(AttributeError):
        b.client_id = 'x'


# New-code probes: a failing ack on a non-success path must not double count
def test_new_failing_ack_on_busy_path_counts_one_loss(bridge, tmp_path):
    h = _hold_flock(tmp_path / 'events.jsonl')
    try:
        bridge.on_message(_BrokenAck(), _Msg(reading('lab', 'a', 1, _now(), 1.0)))
    finally:
        fcntl.flock(h.fileno(), fcntl.LOCK_UN); h.close()
    print(bridge.counters, bridge.loss_reasons)
    assert bridge.counters['lost'] == 1, (bridge.counters, bridge.loss_reasons)


def test_new_failing_ack_on_rejected_path_is_not_a_loss(bridge):
    bridge.on_message(_BrokenAck(), _Msg(None, raw=b'{"not": "valid"}'))
    print(bridge.counters, bridge.loss_reasons)
    assert bridge.counters['rejected'] == 1 and bridge.counters['lost'] == 0, (bridge.counters, bridge.loss_reasons)


def test_new_base_exceptions_still_propagate(bridge, monkeypatch):
    monkeypatch.setattr(bridge, 'handle', lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        bridge.on_message(_Client(), _Msg(reading('lab', 'a', 1, _now(), 1.0)))


def test_new_failing_ack_after_journal_is_still_counted_journaled(bridge):
    before = dict(bridge.counters)
    r = bridge.on_message(_BrokenAck(), _Msg(reading('lab', 'a', 1, _now(), 1.0)))
    bridge.swarm.snapshot(now_ms=_now())
    print(r, bridge.counters, bridge.loss_reasons, bridge.last_error)
    assert bridge.counters['journaled'] == before['journaled'] + 1, (bridge.counters, bridge.last_error)


def test_failing_ack_is_counted_once_as_ack_failure(bridge):
    bridge.on_message(_BrokenAck(), _Msg(reading('lab', 'a', 1, _now(), 1.0)))
    assert bridge.counters['ack_failures'] == 1 and bridge.counters['unexpected_errors'] == 0
    assert bridge.counters['lost'] == 0 and bridge.health()['state'] == 'ok'
