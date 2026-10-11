"""Optional MQTT 5 bridge. Broker ACL/TLS bind identities; no firmware code."""
from __future__ import annotations

import json
import logging
import ssl
import threading
import time
import uuid
from collections import deque
from typing import Any

from codontrace.swarm.protocol import canonical, decode, identifier
from codontrace.swarm.runtime import JournalBusyError, SwarmCoordinator

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
    * busy journal lock (another writer holds it) -> one attempt that waits at
      most ``lock_timeout_s`` (default 0.25 s), no retries, then recorded as
      lost like a journal error. Callbacks run on paho's network thread, so a
      message must never block it for the coordinator's full lock wait.
    * any other unexpected error -> acknowledged (if not yet), counted as
      ``unexpected_errors``, logged and kept in ``last_error``; it never
      propagates into paho's loop thread.

    Loss logging is rate limited: the first loss of an outage is logged at
    ERROR, later losses at most once per ``LOSS_LOG_INTERVAL_S`` as a summary
    with the count, and the first success after an outage logs the total.

    ``connect(session_expiry_s=...)`` opts in to a persistent broker session
    (Clean Start 0 + Session Expiry) so messages published while the bridge is
    disconnected are queued by the broker; it does not change the rules above.
    It only recovers outages shorter than the coordinator's sample TTL
    (``SwarmCoordinator(ttl_ms=...)``, default 10 s): a queued reading whose
    ``sample_ms`` is older than ``ttl_ms`` when it finally arrives is refused
    as a stale sample and counted as ``rejected``, not journaled. Longer
    outages need device-side buffering with fresh re-sampling, or a larger
    ``ttl_ms``.
    Use ``service.coordinator()`` so the coordinator is pinned and shared with
    console requests.
    """
    LOSS_LOG_SIZE = 256
    LOSS_LOG_INTERVAL_S = 30.0

    def __init__(self, swarm: SwarmCoordinator, *, client_id: str | None = None,
                 retry_delays: tuple[float, ...] = (0.02, 0.1, 0.4), lock_timeout_s: float = 0.25) -> None:
        self.swarm = swarm
        self._generated_client_id = client_id is None
        self.client_id = identifier(client_id) if client_id is not None else "genesis-" + uuid.uuid4().hex
        if type(lock_timeout_s) not in (int, float) or not 0 <= lock_timeout_s <= 5:
            raise ValueError('lock_timeout_s must be between 0 and 5 s')
        self.lock_timeout_s = float(lock_timeout_s)
        if (not isinstance(retry_delays, tuple) or len(retry_delays) > 8
                or any(type(d) not in (int, float) or not 0 <= d <= 5 for d in retry_delays)):
            raise ValueError('retry_delays must be a tuple of at most 8 delays between 0 and 5 s')
        self.retry_delays = retry_delays
        self.last_error: str | None = None
        self.counters = {'journaled': 0, 'duplicates': 0, 'rejected': 0, 'journal_failures': 0, 'lost': 0,
                         'unexpected_errors': 0}
        self.losses: deque[dict[str, Any]] = deque(maxlen=self.LOSS_LOG_SIZE)
        self._stalled = False
        self._outage_losses = 0  # losses in the current outage
        self._unlogged_losses = 0  # losses since the last loss log line
        self._last_loss_log: float | None = None
        self._clock = time.monotonic  # injectable for tests
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
        return self.swarm.ingest(message, now_ms=now_ms, lock_timeout_s=self.lock_timeout_s)

    def connect(self, host: str, *, port: int = 8883, username: str, password: str,
                ca_file: str | None = None, session_expiry_s: int | None = None) -> Any:
        """Opt-in network connection. Never called during imports or engine creation.

        ``session_expiry_s`` (opt-in) requests a persistent session; it needs a
        stable ``client_id`` so the broker can match the session on reconnect.
        """
        import paho.mqtt.client as mqtt
        properties = None
        if session_expiry_s is not None:
            if type(session_expiry_s) is not int or not 1 <= session_expiry_s <= 7 * 24 * 3600:
                raise ValueError('session_expiry_s must be 1..604800 seconds')
            if self._generated_client_id:
                raise ValueError('a persistent session needs an explicit stable client_id')
            from paho.mqtt.packettypes import PacketTypes
            from paho.mqtt.properties import Properties
            properties = Properties(PacketTypes.CONNECT)
            properties.SessionExpiryInterval = session_expiry_s
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=self.client_id, protocol=mqtt.MQTTv5, manual_ack=True)
        # Defence in depth: on_message already contains its errors; a callback
        # error must never stop the network loop thread.
        client.suppress_exceptions = True
        client.reconnect_delay_set(min_delay=1, max_delay=60)
        client.username_pw_set(username, password)
        client.tls_set(ca_certs=ca_file, tls_version=ssl.PROTOCOL_TLS_CLIENT)

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
        acked = False

        def ack() -> None:
            nonlocal acked
            if not acked:
                acked = True
                client.ack(message.mid, message.qos)
        try:
            return self._on_message(message, ack, client)
        except Exception as error:  # noqa: BLE001 - must not escape into paho's loop thread
            self.counters['unexpected_errors'] += 1
            self.last_error = f'unexpected_bridge_error: {type(error).__name__}'
            _LOG.exception('swarm %s: unexpected error while handling a telemetry message', self.swarm.swarm_id)
            try:
                ack()
            except Exception:  # noqa: BLE001
                _LOG.exception('swarm %s: acknowledging a message failed', self.swarm.swarm_id)
            return False

    def _on_message(self, message: Any, ack: Any, client: Any) -> bool:
        delays = () if self._stalled else self.retry_delays
        try:
            for attempt in range(len(delays) + 1):
                try:
                    result = self.handle(message.topic, message.payload, now_ms=int(time.time()*1000),
                                         retained=message.retain)
                    break
                except JournalBusyError:
                    # Another writer holds the journal: waiting longer would block
                    # paho's network thread, so give up after the bounded wait.
                    self.counters['journal_failures'] += 1
                    raise
                except OSError:
                    self.counters['journal_failures'] += 1
                    if attempt == len(delays):
                        raise
                    time.sleep(delays[attempt])
        except OSError as error:
            self._record_loss(message, type(error).__name__)
            ack()
            return False
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, json.JSONDecodeError):
            self.counters['rejected'] += 1
            self.last_error = 'invalid_swarm_message'  # no secrets/payload in logs
            ack()
            return False
        ack()
        if self._stalled:
            _LOG.warning('swarm %s: journal writes resumed after %d lost telemetry messages',
                         self.swarm.swarm_id, self._outage_losses)
        self._stalled = False
        self._outage_losses = self._unlogged_losses = 0
        self._last_loss_log = None
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
        self._outage_losses += 1
        self._unlogged_losses += 1
        now = self._clock()
        if self._last_loss_log is None:
            _LOG.error('swarm %s: telemetry LOST after journal failure (%s) node=%s boot=%s seq=%s; '
                       'further losses are summarized every %.0f s',
                       self.swarm.swarm_id, reason, entry['node_id'], entry['boot_id'], entry['seq'],
                       self.LOSS_LOG_INTERVAL_S)
        elif now - self._last_loss_log >= self.LOSS_LOG_INTERVAL_S:
            _LOG.error('swarm %s: %d more telemetry messages LOST (%d in this outage, last: %s node=%s seq=%s)',
                       self.swarm.swarm_id, self._unlogged_losses, self._outage_losses, reason,
                       entry['node_id'], entry['seq'])
        else:
            return
        self._last_loss_log = now
        self._unlogged_losses = 0

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
