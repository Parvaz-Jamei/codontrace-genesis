"""MQTT v5 client setup for ``swarm.mqtt`` (its only caller).

``MqttEsp32Transport`` in ``swarm.devices.esp32`` does not use it: that transport
fails closed and never opens a broker connection.

paho-mqtt is imported only inside these functions, never at module import.
Settings follow paho-mqtt 2.x (checked against 2.1.0, the current PyPI release;
``CallbackAPIVersion.VERSION2``, ``manual_ack``) and MQTT 5.0
(OASIS standard, 2019): ``Session Expiry Interval`` on CONNECT with
``clean_start=False`` for a persistent session, TLS client context, and
bounded reconnect backoff (1..60 s).
"""
from __future__ import annotations

import importlib.util
import ssl
from typing import Any

__all__ = ['MAX_SESSION_EXPIRY_S', 'mqtt_v5_client', 'paho_available', 'session_expiry_properties']

MAX_SESSION_EXPIRY_S = 7 * 24 * 3600


def paho_available() -> bool:
    try:
        return importlib.util.find_spec("paho.mqtt.client") is not None
    except ModuleNotFoundError:  # find_spec imports the parent package ``paho``
        return False


def session_expiry_properties(session_expiry_s: int | None, client_id: str) -> Any:
    """CONNECT properties for a persistent session, or None for a clean session."""
    import paho.mqtt.client  # noqa: F401  (same import order and failure as a direct connect)
    if session_expiry_s is None:
        return None
    if type(session_expiry_s) is not int or not 1 <= session_expiry_s <= MAX_SESSION_EXPIRY_S:
        raise ValueError('session_expiry_s must be 1..604800 seconds')
    if client_id.startswith('genesis-'):
        raise ValueError('a persistent session needs an explicit stable client_id')
    from paho.mqtt.packettypes import PacketTypes
    from paho.mqtt.properties import Properties
    properties = Properties(PacketTypes.CONNECT)  # type: ignore[no-untyped-call, unused-ignore]
    properties.SessionExpiryInterval = session_expiry_s
    return properties


def mqtt_v5_client(client_id: str, *, username: str, password: str, ca_file: str | None,
                   manual_ack: bool = True) -> Any:
    """paho v5 client with TLS, credentials and reconnect backoff; not connected."""
    import paho.mqtt.client as mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,  # type: ignore[attr-defined, unused-ignore]
                         client_id=client_id, protocol=mqtt.MQTTv5, manual_ack=manual_ack)
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.username_pw_set(username, password)
    client.tls_set(ca_certs=ca_file, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    return client
