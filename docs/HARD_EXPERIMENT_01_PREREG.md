# HARD_EXPERIMENT_01 confirmatory preregistration

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this wave: `hard_experiment_01_v2`.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

This file is the confirmatory plan. It is frozen **before** campaign
numbers are generated. The campaign payload records `prereg_digest`
(SHA-256 of this file’s UTF-8 bytes). Results live in a later commit.

**Blocked claims (never requested, never invented):** `intelligence`,
`collective_intelligence`, `proved_collective_intelligence`, `agi`,
`tokyo_type1_passed`, `avida_replacement`, and ClaimGate aliases of those
labels. ClaimGate is not loosened.

---

## 1. Question

Does source-fitness-weighted capsule transfer raise last-tick
(terminal / next-generation) mean fitness relative to (a) the same
capsule channel with source-fitness gating ablated, (b) the capsule
channel off, and (c) the capsule channel on with content scrambled?

The question is a **mechanism** question about one wired
`CapsuleTransferConfig` intervention. It is not a question about
intelligence, communication intelligence, knowledge transfer, OEE, or
Avida replacement.

---

## 2. Hypotheses

**Directional H1 (primary).** On terminal mean fitness,
`source_bias_on` > `source_bias_off` (paired by seed).

**H0 (primary).** Mean paired delta
`source_bias_on − source_bias_off` is zero.

**Auxiliary H1 (information vs channel).** `source_bias_on` >
`capsules_shuffled` on the same outcome, **and**
`capsules_shuffled ≈ capsules_off`. This is the Goldsby-style isolation
plus the information-versus-channel negative control: a channel that is
merely present must not be treated as the treatment.

**Dose H1.** Under `FITNESS_WEIGHTED`, terminal mean fitness is
monotonically non-decreasing in
`min_source_fitness ∈ {0, 1, 2, 4}` and the Spearman trend is positive
(same direction as the primary H1).

A null or small effect is a **valid finding**. It does not unlock a
higher claim.

---

## 3. Explicit causal DAG (Okasha & Otsuka 2020)

Price / covariance identities are statistical. A causal reading requires
an explicit model (Okasha & Otsuka, *Phil. Trans. R. Soc. B*, 2020).
The confirmatory DAG is:

```
gate → which capsule is adopted → action → ATP → terminal fitness
```

Edges:

| Edge | Meaning |
|---|---|
| `e1` `gate → which capsule is adopted` | `min_source_fitness` + `adoption_policy` decide whether a read capsule is eligible and how it is weighted |
| `e2` `which capsule is adopted → action` | adopted capsule content changes the subsequent action choice |
| `e3` `action → ATP` | the chosen action changes the energy budget |
| `e4` `ATP → terminal fitness` | energy / viability enter last-tick `selection_mean_fitness` |

Which edge each arm **cuts or modulates**:

| Arm | Role | Intervention | Edge intervention |
|---|---|---|---|
| `source_bias_on` | treatment | `enabled=True`, `min_source_fitness=2.0`, `FITNESS_WEIGHTED`, `CapsuleShuffleMode.OFF` | no edge cut |
| `source_bias_off` | mechanism ablation | `enabled=True`, `min_source_fitness=0.0`, `THRESHOLD`, `CapsuleShuffleMode.OFF` | **cuts `e1`** (gate ablated; channel remains) |
| `capsules_off` | channel off | `enabled=False` | **cuts `e1` and `e2`** (no adoption) |
| `capsules_shuffled` | negative control | channel on, `CapsuleShuffleMode.CONTENT` (≠ `OFF`) | **severs informational content of `e2`** (channel present, payload scrambled) |

Dose-response (`min_source_fitness ∈ {0, 1, 2, 4}`, `FITNESS_WEIGHTED`,
shuffle off) **modulates `e1`** (stricter gate at higher threshold).
It does not cut `e2`.

`source_bias_off` is not interchangeable with dose `0`: dose `0` keeps
`FITNESS_WEIGHTED`; the ablation uses `THRESHOLD`.

---

## 4. Outcomes

**Primary outcome.** Last-tick `selection_mean_fitness`
(terminal mean fitness). Missing last-tick / generation / score vectors
are `None`. They are **dropped** from that paired comparison and
counted in `missing_outcomes_per_arm`. They are **never zero-filled**.

**Secondary outcomes (descriptive only; not claim-unlocking).**

- Births: sum of per-tick `generation_result.births`.
- Extinction rate: fraction of seeds with `final_population == 0`.
- Adoption count: `len(capsule_adoption_records)`.

Secondary outcomes are reported with the same missing-outcome rule.
They do not enter the ClaimGate decision rule.

---

## 5. Arms and dose

Four confirmatory arms (table in §3). Shared overlay knobs when the
channel is on (Wave 0 treatment template):

- `min_confidence=0.1`
- `read_radius=6`
- emission / read / adoption ATP costs `0.0`
- `adoption_requires_atp_learning=False`
- `min_atp_runtime_to_emit=0.0`
- `max_adoptions_per_organism=2`
- `max_capsules_read_per_tick=4`
- `accept_provisional_source_fitness=True`

Dose ladder (Goldsby et al. 2012 cost/dose + isolation pattern):

| Dose | `min_source_fitness` | Policy | Notes |
|---|---:|---|---|
| `dose_0` | 0.0 | `FITNESS_WEIGHTED` | not `source_bias_off` |
| `dose_1` | 1.0 | `FITNESS_WEIGHTED` | |
| `dose_2` | 2.0 | `FITNESS_WEIGHTED` | same spec as `source_bias_on`; reused |
| `dose_4` | 4.0 | `FITNESS_WEIGHTED` | |

---

## 6. Scales, seeds, n, ticks, population

Substrate: Phase A `life_loop_world` overlay. Phase A–E pins must not
change:

- `life_loop_world(seed=7, tick_count=12, population=6)` spec
  `7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac`
- snapshot
  `76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a`

Seed generator (unchanged from Wave 0): `tuple(range(11, 11 + n))`.

| Scale | n | Seeds | Ticks | Pop | Where it runs | StatisticalTestPolicy tier |
|---|---:|---|---:|---:|---|---|
| `smoke` | 12 | `11`…`22` | 6 | 4 | CI | `exploratory_only` |
| `research` | 30 | `11`…`40` | 40 | 16 | see compute rule | `research_grade_benchmark_candidate` |

Research ticks/pop follow CLAIMS.md §9 recommended benchmark baseline
(`--ticks 40 --population 16`) at research-grade n = 30
(`StatisticalTestPolicy.min_research_grade_n`).

Default `run_hard_experiment_01()` is **smoke**. Research is explicit
(`scale="research"` or explicit n/ticks/pop).

---

## 7. Analysis plan

Wave 0 helpers only. No new p-value algebra.

For each paired contrast, complete-case per-seed deltas
(treatment − baseline):

1. Cohen’s `dz` = `paired_effect_size(deltas)`.
   Undefined when `s_Δ = 0` and `mean(Δ) ≠ 0` — do not invent `dz = 0`.
2. BCa 95% CI of the mean delta: `bootstrap_ci_paired(..., method="bca",
   resamples=10000, seed=20260911)` (Wave 0 default inferential seed).
3. Two-sided sign-flip permutation p:
   `exact_sign_flip_permutation_p(deltas, seed=20260911)`.
   Exhaustive when n ≤ 20; else Monte Carlo with
   `(1 + extreme) / (1 + draws)`.
4. Wrap a `PairedComparisonResult` when `dz` is defined.
   `claim_downgraded` is true iff the BCa CI includes 0.
5. Holm step-down across the **three** primary comparisons
   (`MultipleComparisonAudit(metric_count=3)`):
   - `source_bias_on` vs `source_bias_off`
   - `source_bias_on` vs `capsules_off`
   - `source_bias_on` vs `capsules_shuffled`

α = 0.05 on Holm-adjusted p.

**Information-vs-channel auxiliary.** Same paired protocol for
`capsules_shuffled − capsules_off`. Declare `shuffled ≈ capsules_off`
iff that BCa 95% CI **includes** 0.

**Dose trend.** Complete-case seeds (all four dose outcomes present).
Statistic: Spearman ρ between
`(0, 1, 2, 4)` and the four dose-level means. Seed-fixed permutation:
within each seed, permute the four dose fitnesses (RNG namespace
`hard_experiment_01_dose_trend`, seed `20260911`); recompute means and
ρ. Monte Carlo p uses `(1 + extreme) / (1 + draws)` with 10000 draws
unless 4! exhaustive-per-seed is used for n ≤ 2. Trend is **monotonic
in the H1 direction** iff:

- consecutive dose-level means are non-decreasing, and
- Spearman ρ > 0, and
- permutation p < 0.05.

**Replay.** Independent re-run of **every arm** for `seeds[0]` and
`seeds[-1]`. Spec digest and result digest must match the campaign
records. A campaign object **must not construct** if any replay fails.

**Exclusions.** Missing primary outcomes dropped and counted. No other
pre-specified exclusions.

---

## 8. Decision rule (strict)

Request existing ClaimGate label `intervention_supported` **only** when
**all** of the following hold on the **research** campaign:

1. Scale is research (`n ≥ 30`, 40 ticks, pop 16) and
   `StatisticalTestPolicy.tier_for_n(n)` is
   `research_grade_benchmark_candidate`.
2. BCa 95% CI for `on − off` excludes 0 **and** Holm p < 0.05.
3. BCa 95% CI for `on − shuffled` excludes 0 **and** Holm p < 0.05.
4. `shuffled ≈ capsules_off` (BCa 95% CI includes 0).
5. Dose trend is monotonic in the H1 direction (§7).
6. `dz` is defined for the two CI-tested primary contrasts.
7. Replay matched for all arms × both endpoint seeds.
8. Request uses **all** existing required flags and no new ones:
   `intervention_result_artifact`,
   `intervention_result_digest`,
   `baseline_digest`,
   `treatment_digest`,
   `intervention_protocol_digest`,
   `effect_size`,
   `paired_seed_protocol_digest`,
   `claim_gate_decision_digest`.
   Flags are set true only when the corresponding digest-backed
   artifacts exist (executed `InterventionResult`, paired-seed protocol
   digest, protocol digest of this plan + DAG). The module does not
   mutate a global ClaimGate.

If ClaimGate **allows** that request → campaign ceiling =
`intervention_supported` (CLAIMS.md public level 3, mechanism support).

**Else** (any failed clause, or ClaimGate denies) → ceiling =
`runtime_observation`. Null finding is valid.

Smoke campaigns stay `runtime_observation` even if exploratory numbers
look large (`tier_for_n(12) == exploratory_only`).

Never invent a new claim label. Never claim `collective_intelligence*`.

---

## 9. Claim ceilings per outcome pattern

| Pattern | Ceiling |
|---|---|
| Research decision rule met and ClaimGate allows `intervention_supported` | `intervention_supported` |
| CI includes 0, Holm p ≥ 0.05, shuffled ≠ off, dose not monotonic, `dz` undefined, replay fail, or smoke scale | `runtime_observation` |
| Any intelligence / CI / AGI / Tokyo Type 1 passed / Avida-replacement wording | forbidden (`*_rejected`) |

CLAIMS.md §4 / §6 may be updated **only** to the ceiling ClaimGate
actually granted. Level 4–5 language stays unapproved.

---

## 10. Pineau et al. 2021 / reproducibility checklist v2

Confirmatory report must record:

| Item | Plan |
|---|---|
| Seeds | Frozen lists in §6 |
| Error bars | BCa 95% CI on paired mean deltas; arm mean ± sample SD |
| Compute | Time one research arm × one seed first. If a full research campaign (4 arms + dose + 2×4 replay) would exceed ~20 min on CI, run research **outside** CI and commit `docs/hard_experiment_01/results_v1.json` |
| Full config | Overlay knobs §5; scale table §6; digest-backed specs |
| Metrics | Primary and secondary in §4 |
| Exclusions | Missing last-tick outcomes dropped and counted; never zero-filled |
| Analysis | §7 helpers, seeds, resample counts |
| Decision rule | §8 |

---

## 11. What this will not say

- Capsule adoption is not knowledge transfer.
- Source-fitness gating is not communication intelligence.
- Last-tick fitness is not evolved instinct, OEE, or AGI.
- This is not an Avida replacement study and not Phase M+.
- A Price / covariance number without this DAG is not a causal claim
  (Okasha & Otsuka 2020).

Honesty pointer: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
