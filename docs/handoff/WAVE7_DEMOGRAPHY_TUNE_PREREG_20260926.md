# WAVE7 Demography-only tune prereg — 2026-09-26
**Slice:** `HP-ARM01-RQ-EARN-DEMOGRAPHY-TUNE`  
**Estimand:** debit-arm **demographic readability** under antagonist load (not polymorphism, not lagged NFDS, not RQ).  
**Tip baseline:** `fa69913`. Sealed 701–708 / 601–603 untouched.

## Why
Confirm seed 702 showed `regime_hostile_ne` can burn seeds before RQ clocks speak. Owner critique: demography-only tune **before** RQ-earn confirm lock (Elena–Lenski feast–famine refill under load).

## Seeds / horizon
| Knob | Lock |
|---|---|
| Seeds | **751–758** (n=8); never reuse 601–603, 701–708, 801+ |
| Horizon / windows | **500**; **125 / 250 / 500** |
| Primary success | Both debit arms census ≥ `min_viable` (**12**) at **every** locked window |
| Campaign PASS | ≥ **6/8** seeds primary success |
| Genetics / N / κ / vir/steal | Start from structural confirm pins (64/16/0.02/3×2/κ0.5/8/0.15) |
| Bolus×patches grid (pre-reg, ≤3 cells) | **(24,20)** landed; **(28,20)**; **(24,24)** — pick **one** winner by primary count; no post-peek new cells |
| Soft K | **64** fixed (forbid raise-K as Ne fix) |
| Floor / R_min / ε | Floor **12** fixed; R_min/ε **unscored** this stage |

## Typed outcomes
`demography_ok` | `regime_hostile_ne` | `parasite_extinct` | `horizon_insufficient`

## Refuse
Drop floor; raise K; score polymorphism/lag/RQ here; reuse sealed seeds; SPC accept; infection in `engine.py`.

## Handoff
Pin winning bolus×patches (and κ/vir if left unchanged) into `WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md` **before** Stage 1 outcomes. If no cell hits ≥6/8, **honest FAIL** Stage 0 — do not open Stage 1 by cutting floor.

---
## EcoEvo fold
Agree Stage 0 as readability-only under antagonist load. Do not score polymorphism, lagged NFDS, or RQ here. If no grid cell hits ≥6/8, honest FAIL — do not cut floor to unlock Stage 1.

---
## ClaimCritic fold
Agree Stage 0 readability-only. Refuse: scoring polymorphism/lag/RQ here; dropping floor or raising K after peek; unlocking Stage 1 on Stage 0 FAIL by soft-pass. Sealed seed blocks untouched.

---
## XFieldInnov fold
Agree Stage 0 readability-only under antagonist load (Elena–Lenski feast–famine). Soft K=64 fixed; floor=12 fixed; Cuscore/SPC never accept; no polymorphism/lag/RQ scoring here. Stage 0 FAIL ⇒ honest FAIL — do not cut floor or raise K to unlock Stage 1. Grid cells pre-reg only (24×20 / 28×20 / 24×24).
