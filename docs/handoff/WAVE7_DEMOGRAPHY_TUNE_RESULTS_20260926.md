# WAVE7 Demography-only tune RESULTS — 2026-09-26

**Slice:** `HP-ARM01-RQ-EARN-DEMOGRAPHY-TUNE`  
**Tip at run:** `ecd474978782d90f15caa2c705eb81bc1d80c6de`  
**Workers:** 6 parallel; wall ≈5786 s (≈96 min Asia/Tehran)  
**Evidence:** `/workspace/codontrace-genesis-storm/evidence_wave7_demography_20260926/`

## Grid outcomes (seeds 751–758 @ 500 gens; floor-only)

| Bolus × patches | demography_ok | regime_hostile_ne | parasite_extinct | horizon_insufficient | cell PASS (≥6/8) |
|---|---:|---:|---:|---:|---|
| 24.0 × 20 | **8/8** | 0 | 0 | 0 | YES |
| 28.0 × 20 | **8/8** | 0 | 0 | 0 | YES |
| 24.0 × 24 | **8/8** | 0 | 0 | 0 | YES |

Soft K=64 fixed. min_viable=12 fixed. Polymorphism / lag / RQ **not** scored.

## Winner

**24.0 × 20** (8/8). All three cells hit 8/8; pre-registered tie-break = lower bolus then fewer patches → **(24.0, 20)**.

Pinned into `WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md` §2 before Stage 1.

## Locks held

- `red_queen_proved` = false
- `engine.py` domain-token scan clean (no infection/HP)
- Sealed 701–708 and FAILS 214df20 / 91ab0c6 / 7171d19 untouched
- Floor not cut; K not raised

## Stage 0 verdict

**PASS** — open Stage 1 RQ-earn confirm (seeds 801–816) with bolus×patches = 24.0 × 20.
