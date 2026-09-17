# ESP32 Moj-ه firmware (thin execute+sense only)

Evolution, selection, and mutation run **on the host** — never on this device.
The ESP32 only executes `move(left, right, duration)` and reports
`read_sensor() -> {distance, light, bump}` over UART or MQTT.

## Safety (mandatory — comments are not optional)

- **Separate motor PSU** from the ESP32 logic supply. Do not power DC/servo
  motors from the ESP32 5 V pin (brown-outs / damage).
- **Physical e-stop** on every experimental robot (hardware cut, not software).
- **Enclosed / fixed test area** for early trials — reality gap can produce
  unexpected motion (Koos, Mouret & Doncieux, IEEE TEC 2013).
- Default sketch keeps motor outputs **disabled** until an explicit host
  arming command is received; there are **no dangerous defaults**.

## Sketches

- `main.py` — MicroPython stub (UART JSON lines).
- `sketch_arduino.ino` — Arduino-style stub with the same protocol notes.

Neither sketch claims a completed hardware campaign. Wire to
`codontrace.claimgate.adapters.esp32_bridge` on the host.
