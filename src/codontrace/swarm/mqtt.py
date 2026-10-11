"""Optional MQTT 5 bridge. Broker ACL/TLS bind identities; no firmware code."""
from __future__ import annotations

import json
import ssl
import threading
import time
import uuid
from typing import Any

from codontrace.swarm.protocol import canonical, decode, identifier
from codontrace.swarm.runtime import SwarmCoordinator


class MqttSwarmBridge:
    def __init__(self, swarm: SwarmCoordinator, *, client_id: str | None = None) -> None:
        self.swarm = swarm
        self.client_id = identifier(client_id) if client_id is not None else "genesis-" + uuid.uuid4().hex
        self.last_error: str | None = None
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
                ca_file: str | None = None) -> Any:
        """Opt-in network connection. Never called during imports or engine creation."""
        import paho.mqtt.client as mqtt
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=self.client_id, protocol=mqtt.MQTTv5)
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

        def on_message(c: Any, userdata: Any, message: Any) -> None:
            try:
                self.handle(message.topic, message.payload, now_ms=int(time.time()*1000), retained=message.retain)
                self.drain(c, now_ms=int(time.time()*1000))
                self.last_error = None
            except OSError:
                self.last_error = 'swarm_journal_unavailable'
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, json.JSONDecodeError):
                self.last_error = 'invalid_swarm_message'  # no secrets/payload in logs
        client.on_connect = on_connect; client.on_message = on_message
        client.connect(host, port, keepalive=30)
        return client

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
