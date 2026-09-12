# HARD_EXPERIMENT_01 preregistration — Amendment 02 (Wave 1d, seed-variance restore)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this amendment: `hard_experiment_01_v4`.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

This amendment is a **hashed sibling** of Amendment 01 and of the original
preregistration. It does **not** rewrite `docs/HARD_EXPERIMENT_01_PREREG.md`
or `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md`. The campaign payload
records three digests: `prereg_digest` (original), `prereg_amendment_digest`
(Amendment 01), and `prereg_amendment_02_digest` (this file).

**Freeze time relative to outcome knowledge:** written and hashed **before**
any pilot seed 1000–1009 is re-run under the v4 overlay, and **before** any
analysis seed 11–40 is run under v4. The frozen v3 campaign
(`docs/hard_experiment_01/results_v3.json`) is known: assay valid, arm-level
sd = 0, Cohen’s \(d_z\) undefined. That knowledge motivates the amendment; it
does not authorize silent edits to Amendment 01 or post-hoc redefinition of
the confirmatory rule.

**Blocked claims (unchanged):** `intelligence`, `collective_intelligence`,
`proved_collective_intelligence`, `agi`, `tokyo_type1_passed`,
`avida_replacement`. ClaimGate is not loosened by Wave 1d.

---

## 1. Why an amendment (what v3 left undefined)

Wave 1c / Amendment 01 produced a **valid assay** (manipulation realized;
`assay_failed=false` in `results_v3.json`) but every analysis arm had
**across-seed sd = 0**. With \(s_\Delta = 0\) and \(\overline{\Delta} \neq 0\),
paired Cohen’s \(d_z = \overline{\Delta}/s_\Delta\) is **undefined** (Lakens
2013; the library already raises rather than inventing 0 or ∞). Confirmatory
inference (BCa, Holm) cannot run. The overlay was fully determined by
`index % 4` roles + `food_layout="every_cell"` +
`respawn_draws_per_tick=population`, so the campaign seed did not change the
designed energy path.

Wave 1d restores across-seed variance **without new engine semantics**,
**without** changing the estimand, arms, seeds, ticks/pop, Holm rule, dose
pattern, or ClaimGate ceiling. Roles and food remain **designed** (assigned),
not evolved; seed-varying placement is environmental stochasticity in an
overlay (Avida-style map/replicate variation), not foraging intelligence,
niche construction, or Goldsby-style evolved division of labour.

---

## 2. Preregistration deviations table (Willroth & Atherton 2024 style)

| Item | v3 (Amd 01) | v4 (this amendment) | Why | Confirmatory vs exploratory | Timing vs outcomes |
|---|---|---|---|---|---|
| Role layout | `index % 4`: 0 good emitter, 1 poor (good in oracle), 2–3 receiver | **Permute** that multiset with seed-derived official `RNGManager` (Fisher–Yates). Role **counts** unchanged; oracle still remaps poor→good before permute | Across-seed spatial / adoption variance so \(s_\Delta\) can be > 0 | Confirmatory overlay (fixed algorithm) | Before any v4 pilot/analysis run |
| Food coverage | every cell | Seed-derived coverage \(c \in [0.5, 0.8]\); \(k = \mathrm{round}(c \cdot W \cdot H)\) cells sampled without replacement | Sparse, seed-specific maps (Avida patch analog) | Confirmatory overlay | Before any v4 pilot/analysis run |
| `respawn_draws_per_tick` | `max(1, population_size)` | **`max(1, population_size // 4)`** (research pop 16 → 4; smoke pop 8 → 2) | Refill becomes stochastic under existing `RuntimeResourcePolicy`; no new policy fields | Confirmatory overlay | Before any v4 pilot/analysis run |
| RNG namespaces | (layout unused seed) | Forks: `hard_experiment_01/roles` and `hard_experiment_01/food` from campaign seed; must not steal engine respawn streams | Replay of endpoint seeds still matches | Confirmatory | Before any v4 run |
| Primary outcome | `receiver_mean_terminal_runtime_atp` | **Unchanged** | Estimand frozen | Confirmatory | — |
| Arms / contrasts / dose | Amd 01 §4 | **Unchanged** | Estimand frozen | Confirmatory | — |
| Analysis seeds | 11–40 (n=30); smoke 11–22 | **Unchanged** | Forking-paths split (Gelman & Loken) | Confirmatory | — |
| Pilot seeds | 1000–1009 | **Unchanged**; only place to verify sd / manip before 11–40 | Calibration only; not inferential | Exploratory calibration | Before analysis seeds |
| Decision rule | Amd 01 §4 (verbatim below) | **Unchanged** | Transparent amendment does not move the goalposts | Confirmatory | — |
| ClaimGate ceiling | `runtime_observation` unless full rule | **Unchanged** | Restoring variance ≠ mechanism support | Confirmatory | — |
| Schema | `hard_experiment_01_v3` | `hard_experiment_01_v4`; keep `results_v3.json` | Trail of schemas | — | — |
| Engine / Phase A–E pins | overlay only | overlay only | No new opcodes, actions, or DAG edges | — | — |

Coverage bounds and the respawn formula above are **locked at freeze**. Pilot
1000–1009 may only **pass/fail** them (sd > 0, manip 100%, recommended
\(s_\Delta > 0\) on the three primary contrasts). If calibration fails, stop;
do not peek at 11–40; change text only via a further hashed amendment before
re-piloting.

---

## 3. Locked overlay algorithms (v4)

### 3.1 Role multiset permute

1. Build the v3 role list for `i in 0..n-1` via `calibration_role_for_index`
   (oracle: slot 1 is good emitter).
2. Fisher–Yates shuffle with `RNGManager(seed=seed, namespace="hard_experiment_01/roles")`.
3. Map roles → genomes as in Amendment 01. Counts of each role class stay
   identical to the unpermuted multiset.

### 3.2 Food cells

1. Full lattice cells: all `(x, y)` for `y ∈ [0,H)`, `x ∈ [0,W)`.
2. `RNGManager(seed=seed, namespace="hard_experiment_01/food")`.
3. Draw \(c = 0.5 + 0.3 \cdot U\) with \(U \sim \mathrm{Uniform}[0,1)\) so
   \(c \in [0.5, 0.8)\); clamp upper inclusive by using
   `min(0.8, 0.5 + 0.3 * u)` then allow exact 0.8 when
   `round` hits the top cell count (coverage recorded as
   `k / (W*H)`, which must lie in **[0.5, 0.8]** inclusive).
4. \(k = \mathrm{round}(c \cdot W \cdot H)\); clamp \(k\) into
   \([\mathrm{ceil}(0.5 N), \mathrm{floor}(0.8 N)]\) with \(N=W\cdot H\).
5. Fisher–Yates shuffle all cells; take the first \(k\). Store `food_cells`,
   `food_coverage`, `initial_food_patches` in overlay metadata.

### 3.3 Respawn draws

`respawn_draws_per_tick = max(1, population_size // 4)`.
`respawn_under_organisms`, `respawn_rate`, `amount`, starvation ticks, and
ATP/basal knobs stay Amendment 01. Prefer **no new**
`RuntimeResourcePolicy` fields.

### 3.4 What stays Amendment 01

Edge e2 (`adoption_effect_action`), payloads, genomes, treatment threshold
1.5, dose ladder `{0.0, 1.5, 4.0}` + pattern test, positive control
`oracle_capsule`, manipulation check §3 of Amendment 01, primary outcome
string, analysis arms, paired-seed design, BCa 10 000, Holm over three
primary contrasts, α = 0.05, replay of first and last seeds per arm.

---

## 4. Pilot / analysis split (do not reopen)

| Use | Seeds | Allowed | Forbidden |
|---|---|---|---|
| Pilot / calibration | **1000–1009 only** | Confirm every analysis arm `sd > 0`; confirm Amendment 01 manip check 100%; record \(s_\Delta > 0\) on the three primary contrasts | Inferential \(d_z\), Holm, BCa, dose \(p\), ClaimGate request; retuning after peeking at 11–40 |
| Analysis | **11–40** (research n=30); smoke 11–22 | Frozen confirmatory campaign **after** this file is hashed and pilot gates pass | Re-tuning coverage/draws; dropping a “bad” seed |

If arm `sd > 0` but \(s_\Delta = 0\) on a primary contrast (additive-environment
trap), treat pilot as **failed**; do not run 11–40.

---

## 5. Decision rule (restated verbatim from Amendment 01 §4)

**Primary H1.** `source_bias_on` > `source_bias_off` on receiver mean
terminal runtime ATP (paired by seed).

**Auxiliary H1.** `source_bias_on` > `capsules_shuffled`, and
`capsules_shuffled` does **not** beat `capsules_off` (lower 95 % BCa bound
of the paired delta `shuffled − off` ≤ 0).

**Dose H1 (pattern).** With `FITNESS_WEIGHTED` adoption and thresholds
t ∈ {0.0, 1.5, 4.0}: outcome(1.5) > outcome(0.0) **and** outcome(1.5) >
outcome(4.0). Statistic S = (m₁.₅ − m₀) + (m₁.₅ − m₄); one-sided p from
10 000 within-seed level permutations (seed 20260911); supported if the
pattern holds descriptively and p < 0.05.

**Decision rule for `intervention_supported`** (all required):
research scale (n = 30, 40 × 16); tier `research_grade_benchmark_candidate`;
replay matched; assay valid (Amendment 01 §3); H1 vs `source_bias_off` CI
excludes 0 and Holm p < 0.05; H1 vs `capsules_shuffled` CI excludes 0 and
Holm p < 0.05; `capsules_shuffled` vs `capsules_off` lower CI bound ≤ 0;
dose pattern supported.

Wave 1d does **not** change this rule. Restoring defined \(d_z\) is
necessary for the rule to be evaluable; it is not sufficient for
`intervention_supported`. Ceiling remains `runtime_observation` unless every
clause actually passes on `results_v4.json`. Note: v3 already failed
`shuffled_better_than_capsules_off` (+0.4875 ATP); variance restore does not
repeal that clause.

---

## 6. What a positive / negative v4 result would and would not mean

**Would mean (if assay valid and variance restored):** confirmatory
statistics exist; Amd 01’s decision rule can be evaluated honestly on
seed-varying designed overlays.

**Would not mean:** intelligence, collective intelligence, knowledge
transfer, evolved DoL, Tokyo Type 1, Avida replacement, or that
`intervention_supported` is automatic. Roles and food remain designed.
Ceiling: at most `intervention_supported` (CLAIMS.md §5 level 3) and only
if every Amd 01 clause holds.

Honesty pointer (unchanged): `docs/WHY_NOT_INTELLIGENCE_YET.md` / CLAIMS.md
§4.4 / §5.

---

## 7. References

1. Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *PNAS, 115*(11), 2600–2606. https://doi.org/10.1073/pnas.1708274114
2. DeHaven, A. (2017). Preregistration: A plan, not a prison. Center for Open Science. https://www.cos.io/blog/preregistration-plan-not-prison
3. Willroth, E. C., & Atherton, O. E. (2024). Best laid plans: A guide to reporting preregistration deviations. *Advances in Methods and Practices in Psychological Science*. https://doi.org/10.1177/25152459231213802
4. Gelman, A., & Loken, E. (2013). The garden of forking paths. http://www.stat.columbia.edu/~gelman/research/unpublished/p_hacking.pdf
5. Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology. *Psychological Science, 22*, 1359–1366. https://doi.org/10.1177/0956797611417632
6. Lakens, D. (2013). Calculating and reporting effect sizes … *Frontiers in Psychology, 4*, 863. https://doi.org/10.3389/fpsyg.2013.00863
7. Lakens, D. (2017). Equivalence tests. *Social Psychological and Personality Science, 8*(4), 355–362. https://doi.org/10.1177/1948550617697177
8. Ofria, C., & Wilke, C. O. (2004). Avida: A software platform for research in computational evolutionary biology. *Artificial Life, 10*(2), 191–229. https://doi.org/10.1162/106454604773563612
9. Dolson, E., Pérez, A., Olson, R., & Ofria, C. (2017). Spatial resource heterogeneity increases diversity and evolutionary potential. *bioRxiv*. https://doi.org/10.1101/148973
10. Goldsby, H. J., Dornhaus, A., Kerr, B., & Ofria, C. (2012). Task-switching costs promote the evolution of division of labor … *PNAS, 109*, 13686–13691. https://doi.org/10.1073/pnas.1202233109
11. Okasha, S., & Otsuka, J. (2020). The Price equation and the causal analysis of evolutionary change. *Phil. Trans. R. Soc. B, 375*, 20190365.
12. Grimm, V., Railsback, S. F., et al. (2020). The ODD protocol … second update. *JASSS, 23*(2), 7. *(E6 pointer only — not part of Wave 1d.)*
13. Morris, M. D. (1991). Factorial sampling plans for preliminary computational experiments. *Technometrics, 33*(2), 161–174. *(E6 pointer only.)*

Smoke scale remains 12 seeds × 8 ticks × 8 organisms, `exploratory_only`,
ceiling `runtime_observation`.
