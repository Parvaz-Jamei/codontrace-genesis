"""Optional MQTT 5 bridge. Broker ACL/TLS bind identities; no firmware code."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import deque
from typing import Any

from codontrace.swarm.protocol import canonical, decode, identifier
from codontrace.swarm.runtime import SwarmCoordinator
from codontrace.swarm.transport.mqtt_session import mqtt_v5_client, session_expiry_properties

_LOG = logging.getLogger(__name__)


class MqttSwarmBridge:
    """MQTT 5 bridge for one swarm.

    Delivery semantics (MQTT 5 section 4.4: a broker resends an unacknowledged
    QoS 1 message only when the client reconnects with Clean Start 0 to a
    session that still exists, never on the same connection). The bridge
    therefore never holds messages unacknowledged:

    * journaled -> acknowledged and counted as ``journaled``;
    * duplicate/reordered sequence -> acknowledged, counted as ``duplicates``,
      nothing journaled;
    * permanently invalid -> acknowledged, counted as ``rejected``;
    * journal error -> retried in the bridge with short backoff
      (``retry_delays``); if it still fails the message is acknowledged and
      recorded as LOST (counter plus a bounded log of node/boot/seq, no
      payload values) and ``health()['state']`` becomes ``degraded``. While
      degraded, each message gets one attempt so the broker's in-flight window
      keeps draining; the first success clears the stall.

    ``connect(session_expiry_s=...)`` opts in to a persistent broker session
    (Clean Start 0 + Session Expiry) so messages published while the bridge is
    disconnected are queued by the broker; it does not change the rules above.
    Use ``service.coordinator()`` so the coordinator is pinned and shared with
    console requests.
    """
    LOSS_LOG_SIZE = 256

    def __init__(self, swarm: SwarmCoordinator, *, client_id: str | None = None,
                 retry_delays: tuple[float, ...] = (0.02, 0.1, 0.4)) -> None:
        self.swarm = swarm
        self.client_id = identifier(client_id) if client_id is not None else "genesis-" + uuid.uuid4().hex
        if (not isinstance(retry_delays, tuple) or len(retry_delays) > 8
                or any(type(d) not in (int, float) or not 0 <= d <= 5 for d in retry_delays)):
            raise ValueError('retry_delays must be a tuple of at most 8 delays between 0 and 5 s')
        self.retry_delays = retry_delays
        self.last_error: str | None = None
        self.counters = {'journaled': 0, 'duplicates': 0, 'rejected': 0, 'journal_failures': 0, 'lost': 0}
        self.losses: deque[dict[str, Any]] = deque(maxlen=self.LOSS_LOG_SIZE)
        self._stalled = False
        self._published: set[str] = set()
        self._dispatch_lock = threading.RLock()

    def handle(self, topic: str, payload: bytes, *, now_ms: int, retained: bool = False) -> dict[str, Any]:
        if retained:
            raise ValueError('retained telemetry rejected; do not replay old sensor values')
        parts = topic.split('/')
        if len(parts) != 5 or parts[:3] != ['genesis', 'swarm', self.swarm.swarm_id] or parts[4] != 'up':
            raise ValueError('invalid swarm topic')
        node = identifier(parts[3]); message = decode(payload)
        if message['node_id'] != node:
            raise ValueError('topic/payload identity mismatch')
        return self.swarm.ingest(message, now_ms=now_ms)

    def connect(self, host: str, *, port: int = 8883, username: str, password: str,
                ca_file: str | None = None, session_expiry_s: int | None = None) -> Any:
        """Opt-in network connection. Never called during imports or engine creation.

        ``session_expiry_s`` (opt-in) requests a persistent session; it needs a
        stable ``client_id`` so the broker can match the session on reconnect.
        """
        properties = session_expiry_properties(session_expiry_s, self.client_id)
        client = mqtt_v5_client(self.client_id, username=username, password=password, ca_file=ca_file)

        def on_connect(c: Any, userdata: Any, flags: Any, reason: Any, properties: Any) -> None:
            if reason.is_failure:
                self.last_error = 'broker_connection_rejected'
                return
            with self._dispatch_lock:
                self._published.clear()
            c.subscribe(f'genesis/swarm/{self.swarm.swarm_id}/+/up', qos=1)

        client.on_message = lambda c, userdata, message: self.on_message(c, message)
        client.on_connect = on_connect
        if properties is None:
            client.connect(host, port, keepalive=30)
        else:
            client.connect(host, port, keepalive=30, clean_start=False, properties=properties)
        return client

    def on_message(self, client: Any, message: Any) -> bool:
        """Process one telemetry message and always acknowledge it (see class docstring)."""
        delays = () if self._stalled else self.retry_delays
        try:
            for attempt in range(len(delays) + 1):
                try:
                    result = self.handle(message.topic, message.payload, now_ms=int(time.time()*1000),
                                         retained=message.retain)
                    break
                except OSError:
                    self.counters['journal_failures'] += 1
                    if attempt == len(delays):
                        raise
                    time.sleep(delays[attempt])
        except OSError as error:
            self._record_loss(message, type(error).__name__)
            client.ack(message.mid, message.qos)
            return False
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, json.JSONDecodeError):
            self.counters['rejected'] += 1
            self.last_error = 'invalid_swarm_message'  # no secrets/payload in logs
            client.ack(message.mid, message.qos)
            return False
        client.ack(message.mid, message.qos)
        self._stalled = False
        if result.get('accepted') is False:
            self.counters['duplicates'] += 1
            return False
        self.counters['journaled'] += 1
        self.last_error = None
        try:
            self.drain(client, now_ms=int(time.time()*1000))
        except (ValueError, OSError):
            self.last_error = 'command_dispatch_failed'
        return True

    def _record_loss(self, message: Any, reason: str) -> None:
        entry: dict[str, Any] = {'at_ms': int(time.time()*1000), 'reason': reason, 'topic_node': None,
                                 'node_id': None, 'boot_id': None, 'seq': None, 'kind': None}
        parts = str(message.topic).split('/')
        entry['topic_node'] = parts[3] if len(parts) == 5 else None
        try:
            decoded = decode(message.payload)
            entry.update(node_id=decoded['node_id'], boot_id=decoded['boot_id'], seq=decoded['seq'], kind=decoded['kind'])
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, json.JSONDecodeError):
            pass
        self.losses.append(entry)
        self.counters['lost'] += 1
        self._stalled = True
        self.last_error = 'telemetry_lost_journal_unavailable'
        _LOG.error('swarm %s: telemetry LOST after journal failure (%s) node=%s boot=%s seq=%s',
                   self.swarm.swarm_id, reason, entry['node_id'], entry['boot_id'], entry['seq'])

    def health(self) -> dict[str, Any]:
        journal_ok = not self.swarm._write_failed and not self._stalled
        return {'state': 'ok' if journal_ok else 'degraded', 'journal_ok': journal_ok,
                'last_error': self.last_error, **self.counters, 'recent_losses': list(self.losses)}

    def publish_command(self, client: Any, command: dict[str, Any]) -> Any:
        if command['swarm_id'] != self.swarm.swarm_id or command['status'] != 'pending':
            raise ValueError('invalid command scope or state')
        if command['expires_ms'] <= int(time.time()*1000):
            raise ValueError('expired command')
        topic = f"genesis/swarm/{self.swarm.swarm_id}/{identifier(command['node_id'])}/down"
        return client.publish(topic, canonical(command), qos=1, retain=False)

    def drain(self, client: Any, *, now_ms: int) -> int:
        with self._dispatch_lock:
            return self._drain(client, now_ms=now_ms)

    def _drain(self, client: Any, *, now_ms: int) -> int:
        commands = self.swarm.snapshot(now_ms=now_ms)['state']['commands']
        self._published.intersection_update(commands)
        count = 0
        for command_id, command in commands.items():
            if command['status'] == 'pending' and command_id not in self._published:
                info = self.publish_command(client, command)
                if getattr(info, 'rc', 0) == 0:
                    self._published.add(command_id); count += 1
        return count
