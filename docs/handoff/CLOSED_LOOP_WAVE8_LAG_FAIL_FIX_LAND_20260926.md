# WAVE8 lag_fail fix land — 2026-09-26

## Scope

Implements `WAVE8_FIX_PLAN_20260926.md` patches **P0→P3** (P4 ClaimGate allowlist untouched). Soft-pass forbidden. Sealed Stage 1 seeds **801–816** are **not** rewritten: they remain typed under the pre-fix clocks (`lag_fail` / FAIL campaign as recorded). `red_queen_proved` stays false.

Owner policy: `docs/handoff/OWNER_ENGINE_MODULE_UPDATE_POLICY_20260926.md` — modules + engine may update; engine stays general.

## What landed

### P0 — Emit parasite class hist (`closed_loop_hp_arm01_structural_rq.py`)

`StructuralRQArm.window_snapshot` non-empty return now includes:

- `parasite_class_hist` — frequency map from `parasite_class_hist_series[idx]` (same normalization as `joint_freq`)
- `parasite_class_hist_lag` — last `STRUCT_PARASITE_CLASS_MEMORY_L` frequency maps

**Also (wiring):** lag scoring consumed `collect_dense_snaps(..., snap_stride=25)` while `τ=4`. Generations `t` and `t+τ` never co-occur under stride 25 ⇒ `n=0` even with live hist. Added `collect_lag_clock_snaps` (every generation) and wired RQ-earn confirm to it. Floquet subsample constant `snap_stride=25` retained in design; lag clock stride = 1. **τ=4 / thr=0.3 / min_points=20 unchanged.**

### P1 — Primary lag gate = coevolve only (`closed_loop_hp_arm01_rq_earn_confirm.py`)

`classify_rq_earn_confirm_outcome` now requires `score_pearl_passage_lag(ARM_COPASSAGED).pass_prelim` for not-`lag_fail`. `score_lagged_nfds_on_debit_arms` remains **diagnostic only** (never sole accept). Pearl contrasts still required afterward (coevolve pass ∧ ¬frozen ∧ ¬absent). Avirulent never lag credit; `regime_hostile_ne` excluded; proved flags false.

### P2 — Observability

`lag_observability` + `seed_done_live_metrics` emit on seed_done / lag_fail: `corr`, `n`, `pass_prelim` for coevolve / frozen / absent, plus `parasite_hist_empty`.

### P3 — Domain-free diagnostics

- `assert_census_series_len` after `run_generations(G)` (host + parasite series length == G)
- Optional `GenerationBoundaryObserver` (engine Protocol; generation_index only)
- `bolus_sync_before_census` boolean digests (refill before census on this path)

**Forbidden:** infection / virulence / match-allele / parasite / red_queen physics strings in `engine.py`.

### P4

No ClaimGate allowlist change.

## Falsifiers

| Check | Pass condition |
|---|---|
| P0 hist | `parasite_n>0` and series length>0 ⇒ `parasite_class_hist` non-empty, freqs sum ≈1 |
| P0 lag pairs | stride-25 dense ⇒ `n=0`; lag-clock every-gen ⇒ `n≥min_points` when hist live |
| P1 gate | Coevolve lag pass + frozen/absent fail ⇒ not `lag_fail` from debit all_pass; reaches Pearl path |
| P1 fail | Coevolve lag fail ⇒ `lag_fail` |
| P2 | seed_done row carries corr/n/pass_prelim + parasite_hist_empty |
| P3 | series length ≠ G raises; engine token scan clean of HP domain physics |
| Post-fix biology | Many seeds still `lag_fail` with logged corr≈0 and `n≥min_points` ⇒ ecology (honest), not empty wiring |

## Explicit non-claims

- No SUCCESS claim on sealed **801–816**.
- No `red_queen_proved=true`.
- No τ / threshold / min_points softening.
- No packaging hold / cycle_candidate as RQ.
- Next sealed campaign only after 801–816 closure + new Storm design.

## Smoke (not sealed)

Short fixture seed (non-801–816): non-empty `parasite_class_hist`, finite logged `corr` with `n>0`, `parasite_hist_empty=false`.
