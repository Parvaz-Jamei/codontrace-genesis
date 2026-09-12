# HARD_EXPERIMENT_01 preregistration — Amendment 03 (Wave 1d′, roles-only variance)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this amendment: `hard_experiment_01_v5`.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

This amendment is a **hashed sibling** of Amendment 01 and Amendment 02 and of
the original preregistration. It does **not** rewrite those files. The campaign
payload records four digests: `prereg_digest`, `prereg_amendment_digest`
(Amd 01), `prereg_amendment_02_digest` (Amd 02, failed-calibration trail), and
`prereg_amendment_03_digest` (this file).

**Freeze time relative to outcome knowledge:** written after the Amd 02 pilot
(seeds 1000–1009) failed calibration and after a documented ablation
(`WAVE_1D_PILOT_DIAGNOSIS.md`), and **before** any re-pilot under v5 and
**before** any analysis seed 11–40 under v5. Amd 02 / SCHEMA v4 remains the
frozen “roles+sparse food attempted; pilot FAIL” record. `results_v3.json`
remains the frozen “assay valid, inference undefined” record.

**Blocked claims (unchanged):** `intelligence`, `collective_intelligence`,
`proved_collective_intelligence`, `agi`, `tokyo_type1_passed`,
`avida_replacement`. ClaimGate is not loosened.

---

## 1. Why an amendment (what Amd 02 got wrong)

Amd 02 (SCHEMA v4) seed-permuted roles **and** sparsified food
(coverage ∈ [0.5, 0.8], `respawn_draws_per_tick = max(1, pop // 4)`). Pilot
1000–1009 at research scale (40 × 16) failed:

1. **Positive control:** oracle mean ≈ 21.2 < `capsules_off` 28.0 →
   `assay_failed_positive_control_did_not_move_outcome`. Ablation: with v3
   every-cell food + `draws=population`, oracle ≈ 78 ≫ 28. Sparse food made
   adopted `EAT_LUMEN` frequently hit `no_lumen` while oracle’s eight good
   emitters competed for scarce patches.
2. **`capsules_off` sd = 0** is **structural** on this substrate: WAIT-only
   receivers never eat; basal 0.4 + WAIT 0.1 over 40 ticks from ATP 48 → 28
   on every seed. Food and role knobs cannot move that arm. Amd 02’s gate
   “all four ANALYSIS_ARMS sd > 0” is therefore impossible for `capsules_off`.

Wave 1d′ (this amendment) keeps **only** the role-permutation half of Amd 02
and **reverts food/respawn to Amendment 01 / v3**, so the assay ecology that
made Wave 1c valid is restored while across-seed layout variance remains on
capsule-active arms.

---

## 2. Preregistration deviations table (Willroth & Atherton 2024 style)

| Item | Amd 02 (v4, failed pilot) | Amd 03 (this file, v5) | Why | Confirmatory? | Timing vs outcomes |
|---|---|---|---|---|---|
| Role layout | seed-permuted v3 multiset | **Keep** (`RNGManager` namespace `hard_experiment_01/roles`, Fisher–Yates) | Across-seed adoption/layout variance | Yes | Before any v5 pilot/analysis |
| Food coverage | seed ∈ [0.5, 0.8] | **Revert to Amd 01:** every cell | Restore sustainable `EAT_LUMEN` for oracle/treatment | Yes | Before any v5 pilot/analysis |
| `respawn_draws_per_tick` | `max(1, pop // 4)` | **Revert to Amd 01:** `max(1, population_size)` | Same | Yes | Before any v5 pilot/analysis |
| Pilot sd gate | all four ANALYSIS_ARMS sd > 0 | sd > 0 on `source_bias_on`, `source_bias_off`, `capsules_shuffled`; **`capsules_off` sd = 0 expected** (basal plateau) | Structural impossibility under WAIT-only receivers | Yes (gate correction) | Before v5 pilot |
| Primary outcome / arms / seeds 11–40 / Amd 01 decision rule / ClaimGate | Amd 01 | **Unchanged** | Estimand frozen | Yes | — |
| Engine / Phase A–E pins | overlay only | overlay only | No new opcodes | — | — |
| Schema | `hard_experiment_01_v4` | `hard_experiment_01_v5` | Trail | — | — |

---

## 3. Locked overlay algorithms (v5)

### 3.1 Role multiset permute (unchanged from Amd 02 §3.1)

1. Build v3 role list via `calibration_role_for_index` (oracle: slot 1 → good).
2. Fisher–Yates with `RNGManager(seed=seed, namespace="hard_experiment_01/roles")`.
3. Map roles → genomes. Counts unchanged vs unpermuted multiset.

### 3.2 Food cells (revert to Amd 01)

Every cell of the lattice; ignore seed for placement. Metadata may still
record `food_coverage = 1.0` and the full `food_cells` list.

### 3.3 Respawn draws (revert to Amd 01)

`respawn_draws_per_tick = max(1, population_size)`.
No new `RuntimeResourcePolicy` fields.

### 3.4 Unchanged from Amendment 01

Edge e2, payloads, genomes, threshold 1.5, dose ladder + pattern, oracle
positive control, manipulation check (Amd 01 §3), primary outcome string,
analysis arms, paired-seed design, BCa 10 000, Holm, α = 0.05, endpoint
replay.

---

## 4. Pilot / analysis split

| Use | Seeds | Allowed | Forbidden |
|---|---|---|---|
| Pilot | **1000–1009 only** | assay valid; sd > 0 on on/off/shuffled; record `capsules_off` sd (= 0 expected); recommended primary `sd_Δ > 0` | Inferential ClaimGate; peeking at 11–40 |
| Analysis | **11–40** | After hashed Amd 03 + passing pilot | Re-tuning food/roles after peek |

If assay fails or capsule-active arms have sd = 0: **stop**; do not run 11–40.

---

## 5. Decision rule (verbatim from Amendment 01 §4)

**Primary H1.** `source_bias_on` > `source_bias_off` on receiver mean
terminal runtime ATP (paired by seed).

**Auxiliary H1.** `source_bias_on` > `capsules_shuffled`, and
`capsules_shuffled` does **not** beat `capsules_off` (lower 95 % BCa bound
of the paired delta `shuffled − off` ≤ 0).

**Dose H1 (pattern).** thresholds t ∈ {0.0, 1.5, 4.0}: outcome(1.5) >
outcome(0.0) **and** outcome(1.5) > outcome(4.0); S and permutation test as
in Amd 01.

**Decision rule for `intervention_supported`** (all required): research
scale (n = 30, 40 × 16); tier `research_grade_benchmark_candidate`; replay
matched; assay valid (Amd 01 §3); H1 vs off and vs shuffled (CI excludes 0,
Holm p < 0.05); shuffled vs off lower CI ≤ 0; dose pattern supported.

Amd 03 does not change this rule. Ceiling remains `runtime_observation`
unless every clause actually passes on a future `results_v5.json`.

---

## 6. What this would and would not mean

**Would mean (if pilot passes):** confirmatory statistics can be defined on
seed-permuted designed roles with a valid assay ecology.

**Would not mean:** intelligence, collective intelligence, evolved DoL,
Tokyo Type 1, Avida replacement, or automatic `intervention_supported`.
Roles remain assigned; food is designed every-cell.

---

## 7. References

1. Nosek et al. (2018) preregistration revolution. *PNAS*.
2. DeHaven (2017) plan not a prison. COS.
3. Willroth & Atherton (2024) reporting preregistration deviations. *AMPPS*.
4. Gelman & Loken (2013) garden of forking paths.
5. Lakens (2013) effect sizes; Lakens (2017) equivalence / non-superiority.
6. Ofria & Wilke (2004) Avida; Dolson et al. (2017) spatial heterogeneity
   (motivation for *role* stochasticity only in this amendment — food reverts).
7. Amendment 02 pilot FAIL + ablation: workspace
   `WAVE_1D_PILOT_DIAGNOSIS.md` / `WAVE_1D_PILOT_REPORT.md` (not claim evidence).

Smoke remains 12 × 8 × 8, `exploratory_only`, ceiling `runtime_observation`.
