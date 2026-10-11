"""ESP32 Moj-ه device I/O for swarm code (re-export of ``claimgate.adapters.esp32_bridge``).

The implementation stays in ``claimgate.adapters.esp32_bridge`` because the
engine core reaches the ``claimgate.adapters`` package through the
host-parasite drivers, and the import contract forbids that path from loading
``codontrace.swarm``. Swarm code imports device I/O from here.
"""
from __future__ import annotations

from codontrace.claimgate.adapters.esp32_bridge import (
    Esp32Bridge,
    Esp32LineTransport,
    Esp32MoveAckModel,
    Esp32SensorPayloadModel,
    LoopbackEsp32Transport,
    MoveCommand,
    MqttEsp32Transport,
    SensorReading,
    SerialEsp32Transport,
    SimEsp32Bridge,
    TransportEsp32Bridge,
    execute_sense,
    parse_sensor_payload,
)

__all__ = [
    "Esp32Bridge",
    "Esp32LineTransport",
    "Esp32MoveAckModel",
    "Esp32SensorPayloadModel",
    "LoopbackEsp32Transport",
    "MqttEsp32Transport",
    "MoveCommand",
    "SensorReading",
    "SerialEsp32Transport",
    "SimEsp32Bridge",
    "TransportEsp32Bridge",
    "execute_sense",
    "parse_sensor_payload",
]
