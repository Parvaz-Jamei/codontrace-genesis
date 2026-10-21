"""ESP32 Moj-ه bridge for ClaimGate callers (re-export shim).

The device implementation lives in ``codontrace.swarm.devices.esp32`` and the STR
disparity record and stop rule in ``codontrace.genesis.transferability``. The
names here are the same objects, kept for existing imports.
"""

from __future__ import annotations

from codontrace.errors import ConfigurationError as ConfigurationError  # was a module attribute
from codontrace.genesis.transferability import (
    STRDisparityResult as STRDisparityResult,
)
from codontrace.genesis.transferability import (
    compute_str_disparity as compute_str_disparity,
)
from codontrace.genesis.transferability import (
    str_stop_criterion_met as str_stop_criterion_met,
)
from codontrace.swarm.devices.esp32 import Esp32Bridge as Esp32Bridge
from codontrace.swarm.devices.esp32 import Esp32LineTransport as Esp32LineTransport
from codontrace.swarm.devices.esp32 import Esp32MoveAckModel as Esp32MoveAckModel
from codontrace.swarm.devices.esp32 import Esp32SensorPayloadModel as Esp32SensorPayloadModel
from codontrace.swarm.devices.esp32 import LoopbackEsp32Transport as LoopbackEsp32Transport
from codontrace.swarm.devices.esp32 import MoveCommand as MoveCommand
from codontrace.swarm.devices.esp32 import MqttEsp32Transport as MqttEsp32Transport
from codontrace.swarm.devices.esp32 import SensorReading as SensorReading
from codontrace.swarm.devices.esp32 import SerialEsp32Transport as SerialEsp32Transport
from codontrace.swarm.devices.esp32 import SimEsp32Bridge as SimEsp32Bridge
from codontrace.swarm.devices.esp32 import TransportEsp32Bridge as TransportEsp32Bridge
from codontrace.swarm.devices.esp32 import execute_sense as execute_sense
from codontrace.swarm.devices.esp32 import parse_sensor_payload as parse_sensor_payload

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
    "STRDisparityResult",
    "TransportEsp32Bridge",
    "compute_str_disparity",
    "execute_sense",
    "parse_sensor_payload",
    "str_stop_criterion_met",
]
