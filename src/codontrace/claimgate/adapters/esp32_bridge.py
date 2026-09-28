"""ESP32 Moj-ه thin execute+sense bridge (ClaimGate adapter style).

Literature (cite briefly; no overclaim):
- Koos, Mouret & Doncieux, IEEE TEC 17(1):122–145, 2013 — transferability /
  reality gap; few targeted real tests beat mass sim-only evals.
- ESP32 as thin execute+sense bridge (MQTT/UART patterns); evolution stays on
  the host — never on the device.
- OMNI-EPIC arXiv:2405.15568 — bounded interesting archive lesson.
- ARE 2024 heterogeneous reality gap — document STR-disparity honestly.

This module is an **engineering stub only** (not a scientific research surface).
It does **not** claim that physical robots ran. ``SimEsp32Bridge`` is for tests. Serial/MQTT transports fail closed without a device and hold no
secrets. ClaimGate ceiling stays honest; no AGI / collective intelligence.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError
except ImportError:  # pragma: no cover - optional at install time
    BaseModel = None  # type: ignore[misc, assignment]
    ConfigDict = None  # type: ignore[misc, assignment]
    Field = None  # type: ignore[misc, assignment]
    ValidationError = Exception  # type: ignore[misc, assignment]


# ---------------------------------------------------------------------------
# Untrusted-boundary Pydantic models (raw device payloads)
# ---------------------------------------------------------------------------


if BaseModel is not None:

    class Esp32SensorPayloadModel(BaseModel):
        """Raw sensor JSON from device / MQTT / UART — untrusted boundary."""

        model_config = ConfigDict(extra="forbid")

        distance: float = Field(ge=0.0)
        light: float = Field(ge=0.0)
        bump: bool = False

    class Esp32MoveAckModel(BaseModel):
        """Optional move acknowledgement payload from device."""

        model_config = ConfigDict(extra="forbid")

        ok: bool = True
        left: float | None = None
        right: float | None = None
        duration: float | None = None
        message: str = ""

else:  # pragma: no cover

    class Esp32SensorPayloadModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: object) -> None:
            raise ConfigurationError(
                "pydantic is required to parse untrusted ESP32 payloads. "
                "Install codontrace[dev] or pydantic>=2."
            )

    class Esp32MoveAckModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: object) -> None:
            raise ConfigurationError(
                "pydantic is required to parse untrusted ESP32 payloads. "
                "Install codontrace[dev] or pydantic>=2."
            )


# ---------------------------------------------------------------------------
# Trusted internal frozen records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SensorReading:
    """Trusted sensor snapshot after Pydantic validation."""

    distance: float
    light: float
    bump: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.distance, bool) or not isinstance(self.distance, int | float):
            raise ConfigurationError("SensorReading.distance must be numeric.")
        if isinstance(self.light, bool) or not isinstance(self.light, int | float):
            raise ConfigurationError("SensorReading.light must be numeric.")
        if not math.isfinite(float(self.distance)) or float(self.distance) < 0:
            raise ConfigurationError("SensorReading.distance must be finite and >= 0.")
        if not math.isfinite(float(self.light)) or float(self.light) < 0:
            raise ConfigurationError("SensorReading.light must be finite and >= 0.")
        object.__setattr__(self, "distance", float(self.distance))
        object.__setattr__(self, "light", float(self.light))
        object.__setattr__(self, "bump", bool(self.bump))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "distance": self.distance,
            "light": self.light,
            "bump": self.bump,
        }


@dataclass(frozen=True, slots=True)
class MoveCommand:
    """Trusted differential-drive command (host → device)."""

    left: float
    right: float
    duration: float

    def __post_init__(self) -> None:
        for name in ("left", "right", "duration"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ConfigurationError(f"MoveCommand.{name} must be numeric.")
            if not math.isfinite(float(value)):
                raise ConfigurationError(f"MoveCommand.{name} must be finite.")
        if float(self.duration) < 0:
            raise ConfigurationError("MoveCommand.duration must be >= 0.")
        # Soft clamp advice only — firmware must still enforce physical limits.
        object.__setattr__(self, "left", float(self.left))
        object.__setattr__(self, "right", float(self.right))
        object.__setattr__(self, "duration", float(self.duration))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "left": self.left,
            "right": self.right,
            "duration": self.duration,
        }


def parse_sensor_payload(raw: Mapping[str, object]) -> SensorReading:
    """Validate untrusted mapping via Pydantic, then freeze as SensorReading."""

    if BaseModel is None:
        raise ConfigurationError(
            "pydantic is required to parse untrusted ESP32 payloads. "
            "Install codontrace[dev] or pydantic>=2."
        )
    try:
        model = Esp32SensorPayloadModel.model_validate(dict(raw))
    except ValidationError as exc:
        raise ConfigurationError(f"ESP32 sensor payload failed validation: {exc}") from exc
    payload = model.model_dump()
    return SensorReading(
        distance=float(payload["distance"]),
        light=float(payload["light"]),
        bump=bool(payload["bump"]),
    )


# ---------------------------------------------------------------------------
# Bridge protocol + simulations / fail-closed transports
# ---------------------------------------------------------------------------


@runtime_checkable
class Esp32Bridge(Protocol):
    """Thin execute+sense bridge. Evolution stays on the host."""

    def move(self, left: float, right: float, duration: float) -> None: ...

    def read_sensor(self) -> SensorReading: ...


@dataclass
class SimEsp32Bridge:
    """Deterministic in-process bridge for tests (no hardware).

    Tracks a trivial 1-D pose so unit tests can exercise move/read without a
    device. Does **not** claim physical fidelity.
    """

    distance: float = 1.0
    light: float = 0.5
    bump: bool = False
    pose_x: float = 0.0
    history: list[MoveCommand] = field(default_factory=list)

    def move(self, left: float, right: float, duration: float) -> None:
        cmd = MoveCommand(left=left, right=right, duration=duration)
        self.history.append(cmd)
        # Crude differential proxy: average wheel * duration advances pose.
        advance = 0.5 * (cmd.left + cmd.right) * cmd.duration
        self.pose_x += advance
        # Distance decreases as we "approach" a wall at x=2.0 (synthetic).
        self.distance = max(0.0, 2.0 - abs(self.pose_x))
        if self.distance <= 0.05:
            self.bump = True

    def read_sensor(self) -> SensorReading:
        return SensorReading(
            distance=self.distance, light=self.light, bump=self.bump
        )


@runtime_checkable
class Esp32LineTransport(Protocol):
    """JSON-line transport used by ``TransportEsp32Bridge``.

    ``transact`` sends one request line and returns one response line.
    Serial/MQTT implementations fail closed without a live device.
    """

    def connect(self) -> None: ...

    def transact(self, request_line: str) -> str: ...


def _load_firmware_session():
    """Import ``firmware/esp32/main.py`` for in-process loopback (CI only)."""

    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    firmware_path = root / "firmware" / "esp32" / "main.py"
    if not firmware_path.is_file():
        raise ConfigurationError(
            f"LoopbackEsp32Transport: firmware not found at {firmware_path}"
        )
    spec = importlib.util.spec_from_file_location(
        "codontrace_esp32_firmware_loopback", firmware_path
    )
    if spec is None or spec.loader is None:
        raise ConfigurationError("LoopbackEsp32Transport: cannot load firmware module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class LoopbackEsp32Transport:
    """In-process JSON-line transport bound to firmware ``handle_line``.

    Used for CI / host sim only. Does not open UART or MQTT and does not
    claim a physical robot session.
    """

    _firmware: object | None = field(default=None, repr=False, compare=False)

    def _session(self):
        if self._firmware is None:
            self._firmware = _load_firmware_session()
        return self._firmware

    def connect(self) -> None:
        session = self._session()
        disarm = getattr(session, "disarm_motors", None)
        if callable(disarm):
            disarm()

    def reset(self) -> None:
        """Reload firmware module state (disarmed, zero PWM, sim sensors)."""
        self._firmware = _load_firmware_session()
        self.connect()

    def set_sim_sensors(
        self, distance: float, light: float, bump: bool = False
    ) -> None:
        session = self._session()
        sensors = getattr(session, "SENSORS", None)
        if sensors is None or not hasattr(sensors, "set_sim"):
            raise ConfigurationError(
                "LoopbackEsp32Transport: firmware SensorHal.set_sim unavailable."
            )
        sensors.set_sim(distance, light, bump)

    def transact(self, request_line: str) -> str:
        session = self._session()
        handle = getattr(session, "handle_line", None)
        if not callable(handle):
            raise ConfigurationError(
                "LoopbackEsp32Transport: firmware handle_line unavailable."
            )
        reply = handle(request_line)
        if reply is None or not str(reply).strip():
            raise ConfigurationError(
                "LoopbackEsp32Transport: empty device reply (fail closed)."
            )
        return str(reply).strip()


@dataclass
class SerialEsp32Transport:
    """UART transport — fails closed without a connected device.

    No baud secrets, no credentials. Does not open ports unless explicitly
    constructed with ``port`` and ``allow_open=True`` (still raises without
    pyserial / device). ``transact`` speaks the same JSON-line protocol as
    the MicroPython firmware once a live port is open.
    """

    port: str = ""
    baudrate: int = 115200
    allow_open: bool = False
    timeout_s: float = 1.0
    _io: object | None = field(default=None, repr=False, compare=False)

    def connect(self) -> None:
        if not self.allow_open or not self.port:
            raise ConfigurationError(
                "SerialEsp32Transport fails closed: no device configured "
                "(set port and allow_open=True only for real hardware sessions)."
            )
        if self._io is not None:
            return
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise ConfigurationError(
                f"SerialEsp32Transport: pyserial not available for "
                f"port={self.port!r} (fail closed; no fabricated hardware session)."
            ) from exc
        try:
            self._io = serial.Serial(
                self.port, self.baudrate, timeout=float(self.timeout_s)
            )
        except Exception as exc:
            self._io = None
            raise ConfigurationError(
                f"SerialEsp32Transport: device open failed for "
                f"port={self.port!r} (fail closed; no fabricated hardware session): {exc}"
            ) from exc

    def transact(self, request_line: str) -> str:
        self.connect()
        io = self._io
        if io is None:
            raise ConfigurationError(
                "SerialEsp32Transport fails closed: serial port not open."
            )
        payload = (request_line.strip() + "\n").encode("utf-8")
        try:
            io.write(payload)
            io.flush()
            raw = io.readline()
        except Exception as exc:
            raise ConfigurationError(
                f"SerialEsp32Transport: UART exchange failed (fail closed): {exc}"
            ) from exc
        if not raw:
            raise ConfigurationError(
                "SerialEsp32Transport: empty UART reply (fail closed)."
            )
        try:
            return raw.decode("utf-8").strip()
        except Exception as exc:
            raise ConfigurationError(
                f"SerialEsp32Transport: invalid UART reply encoding (fail closed): {exc}"
            ) from exc


@dataclass
class MqttEsp32Transport:
    """MQTT transport — fails closed; holds no broker secrets.

    ``transact`` publishes the command line on ``topic_cmd`` and waits for one
    payload on ``topic_sense``. Without ``broker_url`` + ``allow_connect`` (and
    a live client), connect/transact raise — CI stays fail-closed.
    """

    topic_cmd: str = "codontrace/esp32/cmd"
    topic_sense: str = "codontrace/esp32/sense"
    broker_url: str = ""
    allow_connect: bool = False
    timeout_s: float = 2.0
    _client: object | None = field(default=None, repr=False, compare=False)
    _pending: list[str] = field(default_factory=list, repr=False, compare=False)

    def connect(self) -> None:
        if not self.allow_connect or not self.broker_url:
            raise ConfigurationError(
                "MqttEsp32Transport fails closed: no broker configured "
                "(set broker_url and allow_connect=True only for real sessions)."
            )
        if self._client is not None:
            return
        import importlib.util

        if importlib.util.find_spec("paho.mqtt.client") is None:
            raise ConfigurationError(
                f"MqttEsp32Transport: paho-mqtt not available for "
                f"broker_url={self.broker_url!r} (fail closed; no secrets stored)."
            )
        # Fail closed: do not invent a session. Real campaigns must supply a
        # working broker; this stub refuses to pretend connectivity succeeded.
        raise ConfigurationError(
            f"MqttEsp32Transport: broker connect not available for "
            f"broker_url={self.broker_url!r} (fail closed; no secrets stored)."
        )

    def transact(self, request_line: str) -> str:
        _ = request_line
        self.connect()
        raise ConfigurationError("unreachable")  # pragma: no cover


@dataclass
class TransportEsp32Bridge:
    """Host execute+sense bridge over a JSON-line transport.

    Default transport is Serial (fail closed). Pass ``LoopbackEsp32Transport``
    for CI. Motors stay disarmed until ``arm(token)``. Evolution / selection /
    mutation stay on the host (``codontrace.engine.GenesisEngine``) — this
    class only forwards move/sense.
    """

    transport: Esp32LineTransport = field(default_factory=SerialEsp32Transport)
    host_armed: bool = False
    arm_token: str = ""
    history: list[MoveCommand] = field(default_factory=list)

    def arm(self, token: str) -> None:
        token = str(token or "").strip()
        if not token:
            raise ConfigurationError(
                "TransportEsp32Bridge.arm requires a non-empty token."
            )
        reply = self._transact_json({"cmd": "arm", "token": token})
        if not bool(reply.get("ok")):
            self.host_armed = False
            raise ConfigurationError(
                f"TransportEsp32Bridge arm rejected: {reply.get('message', reply)}"
            )
        self.host_armed = True
        self.arm_token = token

    def disarm(self) -> None:
        try:
            self._transact_json({"cmd": "disarm"})
        finally:
            self.host_armed = False
            self.arm_token = ""

    def move(self, left: float, right: float, duration: float) -> None:
        cmd = MoveCommand(left=left, right=right, duration=duration)
        if not self.host_armed:
            raise ConfigurationError(
                "TransportEsp32Bridge.move refused: host is DISARMED "
                "(call arm(token) first; fail closed)."
            )
        reply = self._transact_json(
            {
                "cmd": "move",
                "left": cmd.left,
                "right": cmd.right,
                "duration": cmd.duration,
            }
        )
        if "ok" in reply and not bool(reply.get("ok")):
            raise ConfigurationError(
                f"TransportEsp32Bridge move rejected: {reply.get('message', reply)}"
            )
        self.history.append(cmd)
        # Firmware auto-disarms after each move during bring-up; mirror on host.
        self.host_armed = False

    def read_sensor(self) -> SensorReading:
        reply = self._transact_json({"cmd": "sense"})
        return parse_sensor_payload(reply)

    def _transact_json(self, payload: Mapping[str, object]) -> dict[str, object]:
        line = json.dumps(dict(payload), separators=(",", ":"))
        try:
            raw = self.transport.transact(line)
        except ConfigurationError:
            raise
        except Exception as exc:
            raise ConfigurationError(
                f"TransportEsp32Bridge transport failed (fail closed): {exc}"
            ) from exc
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            raise ConfigurationError(
                f"TransportEsp32Bridge: device reply is not JSON (fail closed): {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ConfigurationError(
                "TransportEsp32Bridge: device reply must be a JSON object."
            )
        return parsed


def execute_sense(
    bridge: Esp32Bridge,
    left: float,
    right: float,
    duration: float,
) -> SensorReading:
    """Host-side execute+sense step (evolution stays on GenesisEngine).

    Convenience for wiring a thin device arm beside ``codontrace.engine``
    without moving selection/mutation onto the microcontroller.
    """

    bridge.move(left, right, duration)
    return bridge.read_sensor()


# ---------------------------------------------------------------------------
# STR-disparity helper (sim vs reported physical metrics)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class STRDisparityResult:
    """Honest sim-vs-physical disparity (Koos/Mouret/Doncieux; ARE 2024).

    ``disparity`` is mean absolute relative error across paired metrics.
    Digests identify the comparison record; they do **not** grant a hardware
    campaign claim. Stop criterion (goal §11): after 20 real tests, if STR is
    not better than the no-transfer baseline, stop / redesign.
    """

    metric_names: tuple[str, ...]
    sim_values: tuple[float, ...]
    physical_values: tuple[float, ...]
    per_metric_abs_rel_error: tuple[float, ...]
    mean_abs_rel_error: float
    n_pairs: int
    transfer_method: str
    notes: tuple[str, ...] = ()
    record_digest: str = ""

    def __post_init__(self) -> None:
        payload = self._payload()
        computed = _digest(payload)
        if self.record_digest and self.record_digest != computed:
            raise ConfigurationError("STRDisparityResult record_digest mismatch.")
        object.__setattr__(self, "record_digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "metric_names": list(self.metric_names),
            "sim_values": list(self.sim_values),
            "physical_values": list(self.physical_values),
            "per_metric_abs_rel_error": list(self.per_metric_abs_rel_error),
            "mean_abs_rel_error": self.mean_abs_rel_error,
            "n_pairs": self.n_pairs,
            "transfer_method": self.transfer_method,
            "notes": list(self.notes),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest


def compute_str_disparity(
    sim_metrics: Mapping[str, float],
    physical_metrics: Mapping[str, float],
    *,
    transfer_method: str = "none",
    notes: Sequence[str] = (),
    epsilon: float = 1e-9,
) -> STRDisparityResult:
    """Compare sim vs reported physical metrics (synthetic or real).

    Relative error uses ``|sim - phys| / max(|sim|, |phys|, epsilon)``.
    Does not fabricate hardware results — callers supply both sides.
    """

    if isinstance(epsilon, bool) or not isinstance(epsilon, int | float) or epsilon <= 0:
        raise ConfigurationError("epsilon must be a positive finite number.")
    names = tuple(sorted(set(sim_metrics) & set(physical_metrics)))
    if not names:
        raise ConfigurationError(
            "compute_str_disparity requires at least one shared metric name."
        )
    sim_vals: list[float] = []
    phys_vals: list[float] = []
    errors: list[float] = []
    for name in names:
        sim_v = float(sim_metrics[name])
        phys_v = float(physical_metrics[name])
        if not math.isfinite(sim_v) or not math.isfinite(phys_v):
            raise ConfigurationError(f"metric {name!r} must be finite.")
        denom = max(abs(sim_v), abs(phys_v), float(epsilon))
        err = abs(sim_v - phys_v) / denom
        sim_vals.append(sim_v)
        phys_vals.append(phys_v)
        errors.append(round(err, 12))
    mean_err = round(sum(errors) / len(errors), 12)
    return STRDisparityResult(
        metric_names=names,
        sim_values=tuple(sim_vals),
        physical_values=tuple(phys_vals),
        per_metric_abs_rel_error=tuple(errors),
        mean_abs_rel_error=mean_err,
        n_pairs=len(names),
        transfer_method=str(transfer_method),
        notes=tuple(str(item) for item in notes),
    )


def str_stop_criterion_met(
    *,
    n_real_tests: int,
    disparity_with_transfer: float,
    disparity_without_transfer: float,
    real_test_budget: int = 20,
) -> bool:
    """Goal §11: after ``real_test_budget`` real tests, stop if STR not better.

    Returns True when the program should stop/redesign (honesty gate).
    """

    if n_real_tests < real_test_budget:
        return False
    if not math.isfinite(disparity_with_transfer) or not math.isfinite(
        disparity_without_transfer
    ):
        raise ConfigurationError("disparity values must be finite.")
    # "Not better" = transfer disparity is not strictly lower than baseline.
    return disparity_with_transfer >= disparity_without_transfer


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
