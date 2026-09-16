# HE02 pilot report

Product: CodonTrace Genesis `0.3.0b4.dev0`.
Branch: `feat/he02-e1-e2-e5`.

## Status (strict)

- **E1 MI plumbing:** Fixed. Generation-scoped `food_patch_signal_records`; emit records only when `shuffle_mode=off`; adopt records always; canonical patch ground-truth.
- **Smoke (seeds 1000–1001, tick_count=8, population=8):** manipulation MI gate **passes** (treatment MI≈1.16; shuffled MI=0). Assay gate passes. `oracle_gt_channel_off` **fails** → `cleared_for_research=false`. Artifact: `smoke_v1.json` (digest `61d31b7f7555b94fa9200711abf4bc1dcf9f40437c68d204b897153670f08aee`).
- **Pilot seeds 1000–1009 full campaign:** Not re-run end-to-end after plumbing fix in this session. Prior `pilot_v1.json` is **stale** and must not support claims.
- **Research `results_v1.json`:** ABSENT. Not fabricated. Deferred until a fresh pilot clears all gates including oracle.
- **ClaimGate ceiling:** `runtime_observation` only. `intervention_supported` is **not** granted.
- **Pins A–E:** `life_loop_world(seed=7,tick_count=12,population=6)` unchanged with knobs off.

## Honesty

HE02 is assay/pilot-incomplete for confirmatory inference. Forbidden aliases unchanged. Wave 3 / HE03 untouched.
