# HARD_EXPERIMENT_01 — PREREG AMENDMENT LOCK (SCHEMA v7)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias` (**unchanged**).
Schema after this lock: **`hard_experiment_01_v7`**.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

This file is the **single locked digest** for the v7 environment-realization
fix. It does **not** rewrite `HARD_EXPERIMENT_01_PREREG.md` or Amendments
01–05. Campaign payloads record prior digests **plus**
`prereg_amendment_lock_digest` (this file). Prefer this one lock over a sixth
soft numbered amendment.

**Freeze time:** written and hashed **before** pilot seeds 1000–1009 under
SCHEMA v7 and **before** analysis seeds 11–40 under v7. Frozen trail:
`results_v1`…`results_v6` remain on disk (do not overwrite).

**Blocked claims (unchanged):** `intelligence`, `collective_intelligence`,
`proved_collective_intelligence`, `agi`, `tokyo_type1_passed`,
`avida_replacement`. ClaimGate is **not** loosened by this lock. A passing
decision rule may grant at most existing `intervention_supported`; otherwise
`assay_invalid` or honest zero / `runtime_observation`. Never inflate.

---

## 1. Why (scientific defect remaining after Amd 02–05)

| Wave / artifact | What was true |
|---|---|
| v1 | Extinction; channel silent (invalid null) |
| v2 | `assay_invalid` — arms bitwise-identical on fitness estimand |
| v3 | Manipulation realized; **sd = 0** across seeds (30 replays) |
| v4 / Amd 02 | Sparse food + reduced respawn **failed** pilot (oracle ≰ off) |
| v5 / Amd 03 | Every-cell food restored; **role Fisher–Yates** gives capsule-on variance; `capsules_off` sd=0 structural (WAIT basal) |
| v5 decision | FAIL: `shuffled_better_than_capsules_off` (peer-rotation preserves payload marginal) |
| v6 / Amd 04–05 | Confirmatory `capsules_content_null`; shuffled sensitivity-only |
| Remaining | Food layout still **seed-invariant** (every cell, fixed amount). Avida spatial-heterogeneity lesson (Dolson et al.; seed contingency Taylor 1998-style): unique seed → distinct environment realization. Food amount field must be seed-driven without repeating Amd 02 sparse-food failure. |

**Estimand unchanged:** does source-fitness-weighted capsule transfer raise
receiver terminal runtime ATP vs ablation / channel-off / confirmatory
content-null?

---

## 2. Locked change (Willroth-style deviations)

| Item | Prior (v6 / Amd 03–05) | LOCK (v7) | Why | Confirmatory? |
|---|---|---|---|---|
| Food coverage | every cell (1.0) | **Unchanged** every cell | Amd 02 sparse coverage inverted oracle>off | Yes — abundance frozen |
| Food **amount** | constant `CALIBRATION_RESOURCE_AMOUNT` | Seed RNG discrete multipliers `{0.75, 1.0, 1.25}` × base per cell (`hard_experiment_01/food_amounts`) | Distinct env realization per seed; mean multiplier = 1.0 in expectation | Yes — fixed algorithm |
| Role layout | seed Fisher–Yates multiset | **Unchanged** | Spatial role / adoption variance | Yes |
| Respawn draws | `max(1, population)` | **Unchanged** | Amd 03 | Yes |
| Confirmatory null | `capsules_content_null` (WAIT token) | **Unchanged** | Informational usefulness severed | Yes — confirmatory |
| Legacy shuffled | sensitivity | **Unchanged** | Peer-rotation may beat off by construction | Sensitivity only |
| Activity matched | exploratory | **Unchanged** | Non-blocking | Sensitivity |
| Primary H1 / arms / seeds / ticks / pop | Amd 01–05 | **Unchanged** | Estimand frozen | Yes |
| Variance gate | treatment sd>0 via roles (informal) | Assay fails if treatment outcomes are seed-invariant (`assay_failed_treatment_seed_variance_zero`) | Refuse 30 bitwise replays | Yes |
| Schema | v6 | **v7** | Trail | — |
| ClaimGate | full rule → ≤ `intervention_supported` | **Unchanged ceiling** | Lock alone never auto-grants | Yes |

---

## 3. Locked food-amount algorithm

1. Build every lattice cell `(x, y)` in row-major order (coverage = 1.0).
2. `rng = RNGManager(seed=seed, namespace="hard_experiment_01/food_amounts")`.
3. For each cell, draw `mult ∈ {0.75, 1.0, 1.25}` via `rng.randrange(3)`.
4. Place resource amount `CALIBRATION_RESOURCE_AMOUNT * mult` at that cell.
5. Respawn policy `amount` remains the base `CALIBRATION_RESOURCE_AMOUNT`
   (overlay refill knobs unchanged); **initial** map is the seed-contingent
   realization (Taylor / Avida heterogeneity lesson).

Role permute namespace stays `hard_experiment_01/roles` (Amd 02/03).

---

## 4. Negative control (confirmatory)

- **Confirmatory:** `capsules_content_null` — fixed WAIT token; must not adopt
  profitable EAT_LUMEN marginal; must not beat `capsules_off` on the primary
  ATP estimand (Amd 04 §4; lower 95% BCa of null−off ≤ 0).
- **Sensitivity only:** `capsules_shuffled` peer-rotation (may beat off;
  non-blocking).
- If treatment looks like “shuffled wins” on the confirmatory contrast, the
  decision rule fails — do not promote.

---

## 5. Pilot / analysis split

| Use | Seeds | Gate |
|---|---|---|
| Pilot | 1000–1009 only | assay valid (oracle > off); content_null EAT≈0 + content-changed; treatment across-seed sd > 0 (or ≥2 distinct outcomes); SCHEMA v7 + lock digest present |
| Analysis | 11–40 | After pilot PASS under this lock; then lock `results_v7.json` |

If pilot fails: stop; do not peek 11–40; further change only via a new
hashed lock/experiment id (estimand slide → new id).

---

## 6. ClaimGate ceiling

If research decision rule passes with healthy confirmatory null and CI
excludes 0 on required contrasts → at most **`intervention_supported`**.
Else **`assay_invalid`** or honest zero / **`runtime_observation`**.
Never invent collective intelligence / AGI / Avida replacement.

---

## 7. Explicit non-goals (this lock)

- No `population.py` / `engine.py` split
- No Phase M, E4, more QD, more robots
- No real Avida external campaign
- No fabricated numbers
- ESP32 remains engineering stub (`SimEsp32Bridge`), not a research surface
- Avida/MABE ClaimGate adapters remain **skeletons** until audited published
  `.dat` / DataFile CSV campaigns exist

---

## 8. References

1. Taylor, C. E., et al. — seed / contingency sensitivity in evolutionary
   experiments (style citation; garden of forking paths).
2. Dolson, E., et al. — Avida spatial / environmental heterogeneity;
   unique seed → distinct environment realization.
3. HE01 Wave 1d″ honesty — weak shuffled / peer-rotation controls.
4. Amendments 01–05 (hashed siblings; bytes frozen).
5. Willroth & Atherton (2024); Nosek et al. (2018); Boot et al. (2013) yoked controls.

Smoke remains `exploratory_only`; ceiling `runtime_observation` unless the
full research conjunction holds.
