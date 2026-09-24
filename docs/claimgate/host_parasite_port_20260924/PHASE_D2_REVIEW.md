# Phase D2 review — mortality d × carrying capacity K region map

**Project:** CodonTrace Genesis  
**Branch:** `feat/detoy-d0-d1-type2-diagonal` (stacked after D0+D1)  
**Local time:** 2026-09-24 ~05:10 IRST (UTC+3:30)  
**Depends on:** D0+D1 type-II / diagonal stepper  
**Scope:** Sweep parasite mortality \(d\) and host carrying capacity \(K\); publish
digest of where `cycling_detected` appears. ClaimGate still refuses
`red_queen_proved`. No clinical prediction from region maps.

**Experts:** A (ALife ecology) · B (microbial / metabolism honesty) ·
C (ClaimGate) · D (cross-field innovator)

---

## Literature + competitor code (pre-build)

| Source | Use |
|---|---|
| Sci Rep Fig. 3 (doi:10.1038/srep10004) | RQ region mid-d / larger-K; contracts with type count; low-d proximate extinction; high-d equilibrium |
| Discrete Holling-II bifurcation literature | Region maps are standard; we publish digital qualitative labels only |
| Control / continuation thinking | Coarse grid + digest is enough; no claim of full bifurcation proof |

---

## Pre-build plan

1. Grid over `d ∈ {0.01, 0.08, 0.12, 0.20, 0.40}` and `K ∈ {0.5, 2.0, 5.0, 10.0}`.
2. Per cell: run type-II campaign on fixed seeds; record `n_cycling_seeds` / result label.
3. Prereg pattern: nonempty capable region at mid-d / high-K; empty (or near-empty) at extremes — **or** document mismatch.
4. Always `red_queen_proved=False`; refuse clinical prediction strings.

---

## موج ۱ (pre-build)

### A
1. Must reuse D1 stepper; do not invent a second dynamics core.
2. Label cells as cycling_capable / noncycling — not “RQ proved”.

### B
3. No wet chemostat or phage therapy interpretation of K.

### C
4. Pineau-style disclosure of grid + seeds in digest; BAIC pins untouched.

### D
5. **Adopt:** ecology phase-diagram / region-map reporting (Sci Rep Fig. 3 analogue).
6. **Reject:** Filippov IPM threshold switching as a “control” overlay; SIR clinical R0 mapping from (d,K).

### Fixes
- Single module `host_parasite_dk_region_map.py` calling `run_type2_campaign`.
- Explicit `clinical_prediction_refused=True` in payload.

## موج ۲ (pre-build sign-off)
A/B/C/D approve D2 coding.

---

## Build summary

- `host_parasite_dk_region_map.py` + `tests/test_host_parasite_dk_region_map.py`
- Docs: this file + `_FA.md`

---

## Post-build موج ۱

### A
1. Mid-d / K≥2 cells are cycling_capable; tiny-K mostly empty — structural signal present.

### B
2. No wet chemostat/phage language in payload; clinical_prediction_refused=True.

### C
3. Digest stable; BAIC pins intact; red_queen_proved False everywhere.

### D
4. Epoch cycling_detected is *wider* than Sci Rep visual RQ on low-d/high-d edges —
   documented mismatch (allowed by phase plan), not papered over.

### Fixes
- Pattern fields: `sci_rep_visual_exact_match`, `tiny_k_capable_count`, honest `prereg_pattern_note`.

## Post-build موج ۲ — sign-off

A/B/C/D sign-off D2. Proceed to D3+D4 (phenotype coupling + abstract metabolic channel).
