# MicroPython ESP32 thin bridge — execute + sense ONLY.
# Evolution stays on the host. No mutation / selection on device.
#
# SAFETY (mandatory):
# - Separate motor PSU from ESP32 logic rail. Never power motors from ESP32 5V.
# - Physical e-stop required on every experimental robot.
# - Enclosed / fixed test area for initial trials (reality gap).
# - Motors stay DISARMED until host sends {"cmd":"arm","token":"..."}.
# - No dangerous defaults: PWM duty starts at 0; duration capped in firmware.
#
# Protocol (UART JSON lines, one object per line):
#   host -> device: {"cmd":"arm","token":"..."}
#   host -> device: {"cmd":"disarm"}
#   host -> device: {"cmd":"move","left":0.0,"right":0.0,"duration":0.0}
#   host -> device: {"cmd":"sense"}
#   device -> host: {"ok": true/false, "message": "..."}  (arm/disarm/move ack)
#   device -> host: {"distance":1.0,"light":0.5,"bump":false}  (sense)
#
# This sketch does NOT claim physical robots ran in CodonTrace campaigns.
# CPython can import this module for loopback / CI (SimHal). MicroPython
# binds real pins when machine.Pin / PWM / ADC are available.

try:
    import ujson as json  # type: ignore
except ImportError:  # CPython smoke / host loopback
    import json

try:
    import utime as time  # type: ignore
except ImportError:
    import time

# --- Pin map placeholders (adjust per board; left disconnected by default) ---
LEFT_PWM_PIN = 25
RIGHT_PWM_PIN = 26
DISTANCE_ADC_PIN = 34
LIGHT_ADC_PIN = 35
BUMP_GPIO_PIN = 14

ARMED = False
MAX_DURATION_S = 0.5  # hard cap — no long open-loop runs by default
MAX_WHEEL = 0.3  # soft magnitude cap while validating
PWM_FREQ_HZ = 1000
PWM_DUTY_MAX = 1023  # ESP32 ledc 10-bit scale used by common MicroPython builds


def _clamp(value: float, limit: float) -> float:
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


class MotorHal:
    """Left/right PWM outputs. Starts at duty 0 (disarmed / safe)."""

    def __init__(self) -> None:
        self.left_duty = 0.0
        self.right_duty = 0.0
        self._left_pwm = None
        self._right_pwm = None
        self._bind_hardware()

    def _bind_hardware(self) -> None:
        """Attach real PWM when MicroPython machine is present; else sim-only."""
        try:
            from machine import PWM, Pin  # type: ignore
        except ImportError:
            return
        try:
            self._left_pwm = PWM(Pin(LEFT_PWM_PIN), freq=PWM_FREQ_HZ, duty=0)
            self._right_pwm = PWM(Pin(RIGHT_PWM_PIN), freq=PWM_FREQ_HZ, duty=0)
        except Exception:
            # Pin conflict / unsupported board → stay on software duties only.
            self._left_pwm = None
            self._right_pwm = None

    def _apply(self, left: float, right: float) -> None:
        self.left_duty = float(left)
        self.right_duty = float(right)
        if self._left_pwm is not None:
            self._left_pwm.duty(int(abs(left) * PWM_DUTY_MAX))
        if self._right_pwm is not None:
            self._right_pwm.duty(int(abs(right) * PWM_DUTY_MAX))

    def zero(self) -> None:
        """Force both channels to PWM duty 0."""
        self._apply(0.0, 0.0)

    def drive(self, left: float, right: float, duration: float) -> None:
        """Drive PWM for ``duration`` seconds, then zero outputs."""
        self._apply(left, right)
        if duration > 0.0:
            time.sleep(duration)
        self.zero()


class SensorHal:
    """Distance / light / bump facade. Sim values are host-settable for CI."""

    def __init__(self) -> None:
        self.distance = 0.0
        self.light = 0.0
        self.bump = False
        self._distance_adc = None
        self._light_adc = None
        self._bump_pin = None
        self._bind_hardware()

    def _bind_hardware(self) -> None:
        try:
            from machine import ADC, Pin  # type: ignore
        except ImportError:
            return
        try:
            self._distance_adc = ADC(Pin(DISTANCE_ADC_PIN))
            self._light_adc = ADC(Pin(LIGHT_ADC_PIN))
            self._bump_pin = Pin(BUMP_GPIO_PIN, Pin.IN, Pin.PULL_UP)
            # Full-range atten on ESP32 when available.
            if hasattr(self._distance_adc, "atten"):
                self._distance_adc.atten(ADC.ATTN_11DB)  # type: ignore[attr-defined]
            if hasattr(self._light_adc, "atten"):
                self._light_adc.atten(ADC.ATTN_11DB)  # type: ignore[attr-defined]
        except Exception:
            self._distance_adc = None
            self._light_adc = None
            self._bump_pin = None

    def set_sim(self, distance: float, light: float, bump: bool = False) -> None:
        """Host/CI loopback: inject synthetic readings (no fabricated hardware)."""
        self.distance = max(0.0, float(distance))
        self.light = max(0.0, float(light))
        self.bump = bool(bump)

    def read(self) -> dict:
        if self._distance_adc is not None and self._light_adc is not None:
            # 12-bit ADC → [0, 1] normalised proxies (board-specific calibration later).
            dist_raw = self._distance_adc.read()
            light_raw = self._light_adc.read()
            distance = dist_raw / 4095.0
            light = light_raw / 4095.0
            bump = False
            if self._bump_pin is not None:
                bump = self._bump_pin.value() == 0  # active-low contact
            return {"distance": float(distance), "light": float(light), "bump": bool(bump)}
        return {
            "distance": float(self.distance),
            "light": float(self.light),
            "bump": bool(self.bump),
        }


MOTORS = MotorHal()
SENSORS = SensorHal()


def disarm_motors() -> None:
    """Force zero PWM. Call on boot, e-stop, and parse errors."""
    global ARMED
    MOTORS.zero()
    ARMED = False


def apply_move(left: float, right: float, duration: float) -> None:
    global ARMED
    if not ARMED:
        return  # fail closed — refuse motion while disarmed
    left = _clamp(float(left), MAX_WHEEL)
    right = _clamp(float(right), MAX_WHEEL)
    duration = min(max(float(duration), 0.0), MAX_DURATION_S)
    MOTORS.drive(left, right, duration)
    disarm_motors()  # auto-disarm after each short move during bring-up


def read_sensors() -> dict:
    return SENSORS.read()


def handle_line(line: str):
    global ARMED
    line = line.strip()
    if not line:
        return None
    try:
        msg = json.loads(line)
    except Exception:
        disarm_motors()
        return json.dumps({"ok": False, "message": "bad_json"})
    cmd = msg.get("cmd")
    if cmd == "arm":
        # Require an explicit non-empty token from the host session.
        if msg.get("token"):
            ARMED = True
            return json.dumps({"ok": True, "message": "armed"})
        disarm_motors()
        return json.dumps({"ok": False, "message": "arm_token_required"})
    if cmd == "disarm":
        disarm_motors()
        return json.dumps({"ok": True, "message": "disarmed"})
    if cmd == "move":
        apply_move(msg.get("left", 0.0), msg.get("right", 0.0), msg.get("duration", 0.0))
        return json.dumps(
            {
                "ok": True,
                "left": msg.get("left"),
                "right": msg.get("right"),
                "duration": msg.get("duration"),
            }
        )
    if cmd == "sense":
        return json.dumps(read_sensors())
    disarm_motors()
    return json.dumps({"ok": False, "message": "unknown_cmd"})


def main() -> None:
    disarm_motors()
    # UART loop — wire to machine.UART in real deployments.
    try:
        from machine import UART  # type: ignore
    except ImportError:
        return
    try:
        uart = UART(1, baudrate=115200, tx=17, rx=16)
    except Exception:
        return
    while True:
        line = uart.readline()
        if line:
            try:
                text = line.decode("utf-8") if isinstance(line, (bytes, bytearray)) else str(line)
            except Exception:
                disarm_motors()
                continue
            reply = handle_line(text)
            if reply:
                uart.write(reply + "\n")


if __name__ == "__main__":
    main()
