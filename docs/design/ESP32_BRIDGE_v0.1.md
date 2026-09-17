# ESP32 Moj-ه bridge v0.1

**Status:** thin software + sim layer only. **Zero claim that physical robots ran.**
**Prerequisite:** Waves الف–د of the open-ended discovery ClaimGate pipeline are Done on `main`.

## Architecture

```
Host (evolution / QD / ClaimGate)  --move/sense-->  ESP32 (execute+sense only)
       ^                                                     |
       +------------- sensor JSON (UART / MQTT) -------------+
```

- Evolution, selection, mutation, and archive admission stay on the **host**.
- ESP32 never mutates genomes or selects parents (design goal §8).
- Python adapter: `codontrace.claimgate.adapters.esp32_bridge`
  - Protocol: `move(left, right, duration)`, `read_sensor() -> {distance, light, bump}`
  - Pydantic models at the untrusted device boundary
  - `SimEsp32Bridge` for unit tests (no hardware)
  - Serial / MQTT transport stubs **fail closed** without a device (no secrets)

## Literature (brief; no overclaim)

| Citation | Lesson used here |
|---|---|
| Koos, Mouret & Doncieux, *IEEE TEC* 17(1):122–145, 2013 | Reality gap / transferability — few targeted real tests beat mass sim-only evals. |
| ESP32 MQTT/UART patterns (common practice) | Device is a thin execute+sense bridge; evolution on host. |
| OMNI-EPIC, arXiv:2405.15568 | Bounded interesting archive — do not grow an unbounded physical trial log. |
| ARE 2024 heterogeneous reality gap | Document **STR-disparity** honestly; do not hide sim–real mismatch. |

## STR-disparity

Helper: `compute_str_disparity(sim_metrics, physical_metrics, *, transfer_method=...)`.

- Mean absolute relative error across shared metric names.
- Digests identify the comparison record; they do **not** grant a hardware claim.
- Callers must supply both sim and physical sides — this library does not fabricate physical numbers.

## Stop criterion (goal §11)

After **20 real tests**, if STR-disparity with the transfer method is **not strictly better** than the no-transfer baseline → **stop / redesign**.

```python
from codontrace.claimgate.adapters.esp32_bridge import str_stop_criterion_met

should_stop = str_stop_criterion_met(
    n_real_tests=20,
    disparity_with_transfer=0.40,
    disparity_without_transfer=0.35,  # transfer not better → stop
)
```

`str_stop_criterion_met` returns `True` when the program should stop.

## Safety (goal §12)

Documented in `firmware/esp32/` comments and README:

1. Separate motor PSU from ESP32 logic supply.
2. Physical e-stop (not software-only).
3. Enclosed / fixed test area for early trials.
4. Firmware defaults: motors **disarmed**, short duration/wheel caps, auto-disarm after move.

## Honesty / ClaimGate

- Ceiling stays observational until ClaimGate grants more.
- No AGI, collective intelligence, or “physical campaign completed” claims.
- No fabricated hardware results in docs or tests (use `SimEsp32Bridge` + synthetic STR numbers only).

## Firmware

Minimal sketches under `firmware/esp32/` (MicroPython + Arduino stub). Bring-up requires explicit host `arm` with token.
