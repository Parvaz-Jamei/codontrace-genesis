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
#   host -> device: {"cmd":"move","left":0.0,"right":0.0,"duration":0.0}
#   host -> device: {"cmd":"sense"}
#   device -> host: {"distance":1.0,"light":0.5,"bump":false}
#
# This sketch does NOT claim physical robots ran in CodonTrace campaigns.

try:
    import ujson as json  # type: ignore
except ImportError:  # CPython smoke
    import json

# --- Pin map placeholders (adjust per board; left disconnected by default) ---
# LEFT_PWM_PIN = 25
# RIGHT_PWM_PIN = 26
# DISTANCE_ADC = 34
# LIGHT_ADC = 35
# BUMP_GPIO = 14

ARMED = False
MAX_DURATION_S = 0.5  # hard cap — no long open-loop runs by default
MAX_WHEEL = 0.3  # soft magnitude cap while validating


def _clamp(value: float, limit: float) -> float:
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


def disarm_motors() -> None:
    """Force zero PWM. Call on boot, e-stop, and parse errors."""
    # TODO: set LEFT/RIGHT PWM duty to 0 when pins are wired.
    global ARMED
    ARMED = False


def apply_move(left: float, right: float, duration: float) -> None:
    global ARMED
    if not ARMED:
        return  # fail closed — refuse motion while disarmed
    left = _clamp(float(left), MAX_WHEEL)
    right = _clamp(float(right), MAX_WHEEL)
    duration = min(max(float(duration), 0.0), MAX_DURATION_S)
    # TODO: drive PWM for `duration` seconds, then zero outputs.
    _ = (left, right, duration)
    disarm_motors()  # auto-disarm after each short move during bring-up


def read_sensors() -> dict:
    # TODO: replace with ADC / GPIO reads. Synthetic zeros are intentional.
    return {"distance": 0.0, "light": 0.0, "bump": False}


def handle_line(line: str) -> str | None:
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
        return json.dumps({"ok": True, "left": msg.get("left"), "right": msg.get("right"),
                           "duration": msg.get("duration")})
    if cmd == "sense":
        return json.dumps(read_sensors())
    disarm_motors()
    return json.dumps({"ok": False, "message": "unknown_cmd"})


def main() -> None:
    disarm_motors()
    # UART loop placeholder — wire to machine.UART in real deployments.
    # while True:
    #     line = uart.readline()
    #     if line:
    #         reply = handle_line(line.decode("utf-8"))
    #         if reply:
    #             uart.write(reply + "\n")


if __name__ == "__main__":
    main()
