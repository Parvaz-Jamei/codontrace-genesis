# HE02 pilot / research report

Product: CodonTrace Genesis `0.3.0b4`.

## Status (strict)

- **E1 wiring:** Guided receivers harvest on the signaled patch
  (`_he02_try_harvest_at_nav_target`). Shuffled-arm MI records only when
  `shuffle_mode=off`, so capsules_shuffled MI stays 0.
- **Smoke (1000–1001, 8/8):** gates pass. `smoke_v1.json`
  digest `79a834d0aae0cc04b7ce0b54afc86b900686cac83de91699822e27c56e98bc98`.
- **Pilot 1000–1009:** gates pass. Treatment MI≈0.510; shuffled MI=0;
  oracle 45.0 > channel_off 44.0. `pilot_v1.json`
  digest `617603f6c52f7a7513369d743f3a0662aeff50ad8eee342894acd80de04798f7`.
- **Research 2000–2029:** seed ATP frozen in `results_v1.json`
  digest `45741d911facd4eae0e7f000c2fcd3873280d4b344d3266c4fab9fbe28295419`.
  Stored contrast `dz` fields in that file are **null** (call bug).
  Corrected analysis: `analysis_v1b_contrasts.json` +
  `ANALYSIS_CORRECTION_v1b.md`.
  Holm survives vs off/null (dz≈1.13, ΔATP=+0.53 on baseline 44) and
  fails vs shuffled (dz≈0.20, p_holm≈0.37).
- ClaimGate ceiling remains **`runtime_observation`**.
- Pins A–E unchanged with knobs off.

## Honesty

No fabricated campaign. Confirmatory HE02 claim is not earned
(`information_control_not_separated`). HE03 research remains deferred.
