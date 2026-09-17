# HE02 pilot report

Product: CodonTrace Genesis `0.3.0b4.dev0`.
Branch: `fix/he02-pilot-or-defer`.

## Status (strict)

- **E1 wiring completion:** Guided receivers now harvest when occupying the
  signaled active patch (`_he02_try_harvest_at_nav_target`). Adoption-side
  food-patch MI records are recorded only when `shuffle_mode=off` (aligned with
  emit), so capsules_shuffled MI stays 0.
- **Smoke (seeds 1000–1001, ticks=8, pop=8):** gates **pass**;
  `cleared_for_research=true`. Artifact: `smoke_v1.json`
  (digest `79a834d0aae0cc04b7ce0b54afc86b900686cac83de91699822e27c56e98bc98`).
- **Pilot seeds 1000–1009:** gates **pass**; `cleared_for_research=true`.
  Treatment MI≈0.510; shuffled MI=0; oracle mean 45.0 > channel_off 44.0.
  Decision-rule (Holm primary contrasts) does **not** pass on pilot
  (`no_holm_surviving_primary_contrast`). Artifact: `pilot_v1.json`
  (digest `617603f6c52f7a7513369d743f3a0662aeff50ad8eee342894acd80de04798f7`).
- **Research `results_v1.json`:** LANDED (30 seeds 2000–2029; ticks/pop locked to
  smoke-calibrated 8/8 after host OOM at 24/12 — prereg TBD after smoke).
  Assay/oracle/MI gates still pass; Holm primary contrasts still fail.
  ClaimGate ceiling remains **`runtime_observation`** (not
  `intervention_supported`). Digest
  `45741d911facd4eae0e7f000c2fcd3873280d4b344d3266c4fab9fbe28295419`.
- **Pins A–E:** `life_loop_world(seed=7,tick_count=12,population=6)` unchanged
  with knobs off.

## Honesty

No fabricated numbers. Forbidden aliases unchanged. Confirmatory HE02 claim is
**not** earned (null on Holm). HE03 research remains deferred until its own
gates clear.
