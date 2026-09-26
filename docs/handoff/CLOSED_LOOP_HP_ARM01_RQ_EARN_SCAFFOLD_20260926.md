# HP-ARM01 RQ-earn scaffold — 2026-09-26

## Status

Wave 6 patch plan **P0–P3 landed** as a measurement and runner scaffold.
`red_queen_proved` remains **false**. ClaimGate allowlist is **not** loosened
(P4 deferred). Sealed confirmatory outcomes 701–708 are untouched.

## What landed

| Patch | Content |
|---|---|
| P0 | `src/codontrace/genesis/measurements/rq_frequency_clocks.py` — `lagged_nfds_score`, dominant / per-sublocus series, `phase_lag_host_parasite`. Pure helpers; never set proved flags. |
| P1 | Dense `snap_stride` on structural RQ pilot/confirm (confirm default 25; pilot `None` = locked-windows-only). Hold clause still evaluates **only** locked windows with one **conjunctive** gate. Dense series feeds Floquet / phase / lagged NFDS only — not an OR soft-path. |
| P2 | Parasite match-class memory ring (length L, default 8) on the structural HP arm; exposed as `parasite_class_hist` / `parasite_class_hist_lag` on `window_snapshot`. HP-env / arm plugin only — **not** `engine.py`. |
| P3 | `closed_loop_hp_arm01_rq_earn.py` — Fork A scaffold wiring dense clocks, lagged NFDS, Pearl coevolve / frozen / absent stubs, optional `debit_backed_cycle` reuse. |

## Estimand and refuses

- **Fork A** (asexual clone RQD) is the default estimand.
- **Fork B / Slowinski** invasion remain deferred.
- Unpaid two-fold cost of sex ⇒ prose must **not** claim sex maintained by RQ
  (Hamilton et al. 1990; Ashby 2020 doi:10.1111/jeb.13718).
- Lag / RQ-earn scoring is **debit-active arms only** (coevolve / fixed).
  Avirulent / absent never grant RQ-earn credit.
- Seeds typed `regime_hostile_ne` are excluded from lagged NFDS pass fraction.
- `lagged_nfds_score` is a paired host↔parasite class series with explicit τ —
  never an alias of `_oscillation_on_arm`.
- Cuscore / Shewhart / CUSUM / SPC stay **observation-only** and never accept
  for RQ.
- Hold clause stays conjunctive; census is not Ne.

## Literature

- Dybdahl & Lively 1998 doi:10.1111/j.1558-5646.1998.tb01833.x — lagged NFDS.
- Ashby 2020 doi:10.1111/jeb.13718 — polymorphism / cycle ≠ RQD.
- Sasaki 2000 doi:10.1098/rspb.2000.1267 — multilocus phase-displaced cycles.
- Zaman et al. 2014 doi:10.1371/journal.pbio.1002023 — parasite memory analog.
- Buckingham & Ashby 2022 doi:10.1111/jeb.13981 — fluctuating selection.
- Phil. Trans. B doi:10.1098/rstb.2022.0006 — dense sampling / phase.

## Next step

A **separate 2-round storm** for confirmatory RQ-earn prereg after this scaffold
lands. Only a future sealed campaign that meets every conjunctive clause may
justify a ClaimGate allowlist change; until then `red_queen_proved` stays false.
