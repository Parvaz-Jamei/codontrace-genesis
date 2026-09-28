# ESP32 Moj-ه bring-up checklist

**Status:** host↔device execute+sense software path is complete in-repo.
**Honesty:** this checklist separates what CI verifies in simulation from what
still requires physical hardware. No physical robot campaign is claimed here.

Evolution, selection, and mutation stay on the host (`codontrace.engine`
`GenesisEngine`). The device only accepts `arm` / `disarm` / `move` /
`sense`.

## Verified in simulation (CI)

| Item | Where |
|---|---|
| Firmware JSON-line protocol (`arm`, `disarm`, `move`, `sense`) | `firmware/esp32/main.py` via `LoopbackEsp32Transport` |
| PWM duties start at 0; `disarm_motors` zeros outputs | firmware unit tests |
| Move while DISARMED is a no-op (fail closed) | firmware + host tests |
| Move after host `arm(token)` drives then auto-disarms | loopback bridge tests |
| ADC / GPIO sense path returns `{distance, light, bump}` | firmware `SensorHal` + loopback |
| Host `TransportEsp32Bridge` refuses move until armed | adapter tests |
| Serial transport fails closed without port / `allow_open` | adapter tests |
| MQTT transport fails closed without broker / `allow_connect` | adapter tests |
| `SimEsp32Bridge` move/sense for pure in-process tests | existing discovery-wire tests |
| STR-disparity helper uses caller-supplied metrics only | existing tests |
| GenesisEngine life-loop digests unchanged by this arm | discovery-wire digest pin |

## Not verified on physical hardware (still required before any robot claim)

| Item | Notes |
|---|---|
| Real ESP32 flash of `firmware/esp32/main.py` or `sketch_arduino.ino` | Board-specific |
| UART wiring host↔ESP32 at 115200 | Confirm TX/RX/GND; no fabricated session in CI |
| MQTT broker + device topics | Optional alternate transport; no secrets in repo |
| Separate motor PSU from ESP32 logic rail | Mandatory safety — not a software check |
| Physical e-stop (hardware cut) | Mandatory safety — not a software check |
| Enclosed / fixed test area | Reality-gap practice (Koos, Mouret & Doncieux 2013) |
| Pin map calibration (PWM / ADC / bump polarity) | Placeholders in firmware; measure on bench |
| Closed-loop host arming token procedural control | Lab SOP — token must be intentional |
| STR-disparity on real vs sim metrics | Requires ≥1 honest physical trial; stop rule at 20 |

## Bench bring-up order (physical)

1. Logic power only. Confirm Serial JSON `sense` replies. Motors disconnected.
2. Confirm `arm` without token is rejected; `disarm` zeros PWM lines on a scope/meter.
3. Attach **separate** motor PSU behind a physical e-stop. Enclosed area.
4. Arm with an explicit host token; single short `move` at low wheel caps; expect auto-disarm.
5. Record sim vs physical metrics with `compute_str_disparity` — do not invent physical numbers.

## ClaimGate ceiling

Observational / engineering only until ClaimGate grants more. Do not claim a
completed physical campaign from CI greens alone.
