# PREREG_V2 — corrected host–antagonist rare-advantage campaign

**Date:** 2026-09-28
**Revision name:** `rq_redesign_20260928_v2`
**Base commit:** `7cfba3fc59b4d6dcd80895ea283eb5a69fdf7c72` (`7cfba3f`), `main`
**Status:** thresholds, seeds, outcomes, controls and stop rules fixed before any
confirmatory run; nothing in this document may be amended after the confirmatory runs begin
**Directory:** `docs/campaigns/rq_redesign_20260928/`
**Companions:** `SCIENTIFIC_QUESTION_AND_DAG.md` (question, causal graph, estimand, unit of
replication, falsification conditions), `MEASUREMENT_VALIDATION.md` (the two quantities and
the hand-computed scenarios), `STATS_AND_NULL_DESIGN.md` (interval method, null models,
attrition policy, stopping conditions)

---

## 0. Standing commitments

1. **The sealed campaign stays sealed.** The campaign `801–816`
   (`HP-ARM01-RQ-EARN-CONFIRM`) remains **`ABORT / sealed FAIL`**: 12 of 16 seeds completed,
   zero `rq_earn_seed_pass`, typed outcome `lag_fail` in all twelve, claim ceiling
   `runtime_observation`. Its seeds are not re-run, re-scored, re-labelled or re-analyzed for
   any claim in this campaign, and it is not retconned.
2. **The WAVE7 design and its failure are preserved unmodified.**
   `docs/handoff/WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md` and
   `docs/handoff/CLOSED_LOOP_HP_ARM01_RQ_EARN_CONFIRM_RESULTS_20260926.md` are not edited,
   superseded in the record, or reinterpreted. This document is a new design, not an
   amendment to WAVE7, and no result of this campaign is described as a confirmation of the
   WAVE7 design. The phrase "WAVE7 confirmed" does not appear in any output of this campaign.
3. **No threshold is chosen from the new confirmations.** Every value in section 8 is fixed
   before the confirmatory runs and is justified in that section from a mechanism argument, a
   pre-existing project lock, or a pilot estimated on its own disjoint seed range. No
   threshold may be relaxed, tightened, re-signed or re-scoped after seeing a confirmatory
   result; a result that falls on the wrong side of a fixed threshold is reported as a
   negative or as a boundary, not repaired.
4. **Signs and lags are fixed before the runs.** The sign and lag of every causal link are
   recorded in `SCIENTIFIC_QUESTION_AND_DAG.md`, section 3, and the expected sign of the
   lagged association is positive. The sign is never changed after seeing a result. In
   particular, the existing `corr <= -0.3` criterion on the composition-versus-composition
   score is not revived as a success criterion, and reversing its sign after the fact would
   not convert the sealed outcome into a pass.
5. **Claim flags stay false.** `red_queen_proved = false` and
   `biological_red_queen_proved = false` throughout. The estimand is an asexual clone
   estimand; no claim about the maintenance of sex, recombination or a two-fold cost is made
   here. A pass is at most candidate evidence and requires a separate claim decision.
6. **The campaign requires an independent mechanism gate first.** The synthetic cases P1–P3
   and the counter-samples N1–N4 of `SCIENTIFIC_QUESTION_AND_DAG.md`, section 6, must pass and
   be rejected respectively, on the mechanism-calibration block of section 2, before any
   confirmatory run is allowed. A failure there is an instrument failure and is reported as
   such.
7. **A fresh working copy is used, and the audit is separate.** The confirmatory campaign
   runs on a clean checkout of the base commit with the campaign code; the artefact set
   (design digest, document digest, per-run digests, dense histories, attrition table,
   scripts) is published with the results. An independent auditor re-runs a pre-declared
   subset and recomputes the primary statistic from the raw histories.

---

## 1. Design in one view

| Element | Lock |
|---|---|
| Estimand | **Fork A asexual clone rare-class advantage** under delayed antagonist adaptation |
| Primary outcome | `Δ`, the cell-level difference in rare-class advantage between the coevolving and frozen passage arms, paired on seed |
| Mechanism outcome | swap-signal `S` in ATP per host per contact opportunity, expected sign negative |
| Association outcome | within-run cross-covariance of past host frequency with later realised pressure on the same class, expected sign positive, peak lag 1–4 generations |
| Unit of replication | the run (one fresh seed in one factorial cell); `N` is the number of runs |
| Factorial | passage (coevolve / frozen / absent) × resource forcing (constant / aperiodic-pulse) × effective census (low / high) × contact intensity–virulence (moderate / high): 24 cells |
| Focal contrasts | 8: coevolve versus frozen at each combination of forcing × census × contact intensity, paired on seed |
| Horizon | 500 generations, burn-in 125, measurement windows 125–500 |
| Runs | 576 confirmatory (24 per cell); escalation to 48 runs per focal cell only if the pilot cannot meet the absolute target `δ_min` at 24 (section 5.3); hard cap 2,400 runs |
| Primary interval | cluster bootstrap over runs, 10,000 resamples, bootstrap seed `20260928`; moving-block bootstrap over time reported alongside |
| Multiplicity | Holm within the declared focal family of 8; everything else labelled exploratory |
| Sealed material | `801–816` sealed FAIL; WAVE7 design and results untouched |

---

## 2. Fresh seed ranges

All ranges are unused by every previous block in this repository. The reserved blocks are
`101–108`, `201–208` (both the confirmatory and the Slowinski occupants), `301–308`,
`401–408`, `501–508`, `601–603`, `701–708`, `751–758`, `801–816`, `1000–1009`, `2000–2009`,
`3100–3107`, `4100–4107`, and the mixed small blocks `{11, 22, 33}`, `{11, 22, 33, 44}`,
`{11, 22, 33, 44, 55}`, `{3, 6, 7, 8, 9, 11, 12, 13}`, `{1, 2, 4}`, `{7, 14, 21, 28, 35}`,
`{101, 202, 303, 404, 505}`, and `11–40` (`hard_experiment_01_morris`). The campaign ranges
below are disjoint from all of them.

| Block | Range | Size | Use | May contribute to the primary claim? |
|---|---|---|---|---|
| Pilot | `9001–9096` | 96 | one run in each of the 12 pilot cells (passage × forcing × census × contact, with passage in {coevolve, frozen}); estimates between-run variance and within-run autocorrelation only | no; never pooled with confirmatory runs |
| Mechanism calibration | `9101–9120` | 20 | synthetic and counter-sample cases P1–P3 / N1–N4, the exposure audit, the stride and aliasing checks, and the swap-signal floor calibration | no; instrument only |
| Confirmatory main | `10001–10576` | 576 | 24 runs in each of the 24 cells; fresh seeds, each seed assigned to every cell | yes |
| Confirmatory escalation | `11001–11384` | 384 | 24 additional runs on each of the 8 focal coevolving and frozen cells, used only if section 5.3 fires | yes, only if the escalation rule fires, and both tiers are then reported |
| Independent sensitivity | `12001–12240` | 240 | 10 runs in each of the 24 cells under the pre-declared sensitivity variations of section 9.3, analysed separately | no; sensitivity only |

The 24-run base allocation deliberately replaces the previous campaign's 16 seeds with a pass
bar of 12. That bar was an auditor floor, not a statistical sample size, and its operating
characteristic is poor: with 16 runs, a seed-level pass rate of 0.55 reaches the bar with
probability 0.085, a rate of 0.75 reaches it with probability 0.630, and a rate of 0.82 reaches
it only with probability 0.854. A mechanism that is real but partial would therefore have been
recorded as a failure in most campaigns of that size, while a rate of 0.75 would have passed
about two times in three. The corrected design reports a continuous effect with an interval
instead of a count against a bar.

Rules on use of seeds:

* A seed is assigned to **every** cell of the design. Pairing is within seed, so the paired
  contrasts are exact on the demographic and resource draws.
* No seed appears in two blocks. The confirmatory tier and the escalation tier use disjoint
  seeds; escalation adds runs, it does not replace them.
* The pilot block, the calibration block and the independent sensitivity block are analysed
  once each and reported separately. Nothing from them is merged into the confirmatory
  estimate.
* Seed policy assertions are part of the campaign code: uniqueness within a block, disjointness
  from the reserved blocks, and equality of the assigned set across cells. A campaign run that
  fails a seed assertion does not start.
* The sealed `801–816` block is not in the allocation and is not read.

---

## 3. Factorial structure

### 3.1 Factors

| Factor | Levels | Operationally |
|---|---|---|
| Passage (Pearl cut) | `coevolve`, `frozen`, `absent` | update on / update off with debit on / antagonist removed. Frozen restores the ancestral window multiset each generation; absent sets the antagonist pool empty. The three modes are distinct cuts and are not aliased to one another |
| Resource forcing | `constant`, `periodic` | constant bolus every generation; or an aperiodic bolus pulse with pre-registered mean interval 25 generations and a recorded schedule digest. The periodic schedule is aperiodic by design so that it cannot resonate with the measurement window; the schedule is written into the design artefact before the run |
| Effective census | `low`, `high` | manipulated by the resource supply level (bolus amount and number of food patches), not by reading census as a proxy. Soft carrying capacity stays at its standing locked value of 64 in both levels; a standing lock forbids treating soft carrying capacity as an effective population size, so census is manipulated through supply. The two supply levels, and the realised census bands they produced in the pilot, are recorded in the design artefact; the pilot must show a realised census separation of at least a factor of 1.5 between the low and high levels, otherwise the level pair is re-chosen from the pilot's supply grid before the confirmatory run |
| Contact intensity / virulence | `moderate`, `high` | `virulence = 4.0` and `virulence = 8.0`, with `steal_fraction = 0.15` fixed at both levels and contact policy identical, so that the factor changes damage per contact and not the number of contact opportunities |

Fixed across all cells: mutation rate of the host (`0.02` bit flip), antagonist mutation rate
(`0.25`), antagonist keep fraction (`0.5`), the six-bit three-sublocus affinity rule, the
founder slate, the contact policy, the census minimum, and the horizon.

### 3.2 Cells and contrast family

The full crossing of the four factors gives `3 × 2 × 2 × 2 = 24` cells. The declared focal
family is the **8** coevolve-versus-frozen contrasts, one per combination of forcing × census
× contact intensity. The 8 antagonist-absent cells are recorded as controls; the remaining 8
coevolving and frozen cells are the focal ones. Multiplicity is handled inside the focal
family only (section 7).

### 3.3 Declared rare and common classes

* The host classes are the joint match classes of the founder slate, i.e. the six-bit window's
  three two-bit sub-loci joined into one class label. Class identity is a property of the
  window, not of the frequency, so the same label is trackable from the founder census through
  the measurement window.
* The standing founder slate is symmetric: the distinct windows are distributed as evenly as
  64 hosts over 16 windows allows, so at generation 0 there is no most-frequent class and a
  rule that reads "the two most frequent classes" would resolve by an arbitrary tie-break.
  The designation is therefore made **before** the run, from a pre-registered founder
  assignment, not from the trajectory: two windows are drawn from the distinct-window slate by
  the pre-registered deterministic rule *the window whose bit string is numerically lowest is
  the designated common class `A`, and the window whose bit string is numerically highest is
  the designated rare class `B`*, and the generation-0 founder census is then placed so that
  `A` holds the plurality of founders and `B` holds the smallest non-zero count consistent
  with the band of T6. The assignment is written into the run record and into the design digest
  before the first run, and it is applied **identically to every arm of the design**, so the
  arms differ in passage mode and not in founder composition. That last property is what the
  paired contrast requires; the symmetry of the slate is traded away deliberately and the
  trade is disclosed here rather than repaired by a post-hoc label choice.
* If the generation-0 share of `B` is not inside the band of T6, the run is flagged
  `rare_class_out_of_band`. The band is a property of the founder assignment and is checked
  before the run; it is not a filter applied to observed trajectories.
* The same designation is used in both arms of a seed by construction. A run whose recorded
  designation differs from the design record is flagged `designation_mismatch` and its pair is
  excluded from the contrast with the count reported.

---

## 4. Primary, secondary and descriptive outcomes

### 4.1 Primary outcome

For a run `r`, with `A` the common and `B` the rare founder class,

```
RA(r) = mean over g in [125, 500] of [ λ_B(g) − λ_A(g) ],   λ_c(g) = log( n_c(g+1) / n_c(g) )
```

in log count per generation. The cell-level primary contrast is

```
Δ(cell) = mean over seeds of RA(r; passage = coevolve) − mean over seeds of RA(r; passage = frozen)
```

paired on seed. Positive `Δ` means the coevolving antagonist produces a larger growth
advantage for the class that was rare than a frozen antagonist of the same ancestry and
demography. The interval is the cluster bootstrap of section 6; the decision is `Δ > 0` with
the interval excluding zero, at the mechanism floor of section 8.

Secondary outcomes, reported for every run: the swap-signal `S` of section 4.2; the
within-run cross-covariance of section 4.3; the terminal share of the rare class; time to
first loss of a designated class; the collapse and extinction indicators of section 9;
realised census; contact rate and exposure ratio; saturation load; and the realised antagonist
class entropy.

### 4.2 Mechanism outcome (the swap-signal)

At the pre-registered swap generations 150 and 300, the host class frequencies are swapped by
symmetric intervention: the census of hosts of class `A` and class `B` is exchanged in place
while the total census, the resource state, the host genotype multiset, the contact count and
the random draws are held fixed. Within the same generation, two pressure values are recorded
for the designated class `A`: the intended and the realised value under the baseline pairing
and under the swap. Define

```
S = π_A(swap) − π_A(baseline)      units: ATP per host per contact opportunity, expected sign negative
```

The swap is applied in both directions in separate paired runs, and the two directions must
agree in magnitude and oppose in sign within the tolerance of section 8. `S` is averaged over
the two swap generations, and its interval is taken across runs. `S` is a mechanism check and
is not a substitute for `Δ`.

### 4.3 Association outcome

For each run, the within-run cross-covariance between `h_i(g)` and `π_i(g + τ)` for
`τ ∈ {0, 1, 2, 4, 8}`, with uncertainty taken across runs. The pre-registered expectation is a
positive cross-covariance peaking at a positive lag in `1–4` generations in the coevolving
cells. The retired composition score and its pooled pair count are reported descriptively
alongside, under the name `lagged_nfds_composition`, and are not a decision criterion.

### 4.4 Descriptive-only quantities

The number of pooled class-generation pairs; the number of retained classes; the number of
successive generations in which the dominant class differs from the previous generation; the
proportion of runs whose rare class ends numerically dominant; entropy-based summaries. These
are reported as descriptions with the word "descriptive" attached wherever they appear, never
as `N`, and never as evidence for the mechanism.

---

## 5. Pilot and power calculation

### 5.1 What the pilot estimates

The pilot block (`9001–9096`, 96 runs, 8 per pilot cell) yields three numbers and nothing
else:

1. `σ_pilot`, the between-run standard deviation of `RA` in the six coevolving and six frozen
   pilot cells, pooled across cells:
   `σ_pilot² = Σ_cells (n_c − 1) s_c² / Σ_cells (n_c − 1)`, with `n_c = 8`, so 7 degrees of
   freedom per cell, 42 across the six coevolving cells, 42 across the six frozen cells, and
   84 pooled across all twelve. The paired contrast inside one pilot cell uses 8 pairs and
   carries only `MDE(8) = (2.365 + 0.896)/√8 = 1.153 σ_Δ`; that number is reported to show
   why the pilot cannot decide an effect and can only estimate variance.
2. `ρ_pilot`, the run-level lag-1 autocorrelation of `RA` and of the dense pressure series,
   used to set the moving-block length and to confirm that run-level dependence is real.
3. `census_separation`, the realised low-to-high census ratio, used to accept or re-choose the
   resource-supply level pair (section 3.1).

The pilot also fixes the exposure audit's realised targets and confirms that the calibration
block's synthetic cases can be executed on the base commit.

### 5.2 Power calculation

The focal contrast is a paired comparison of two cell means over `n` seeds per cell, at
two-sided `α = 0.05` with 80 per cent power. With `n` pairs and the paired-difference
standard deviation `σ_Δ`, the minimum detectable effect is

```
MDE(n) = (t_{0.975, n−1} + t_{0.80, n−1}) · σ_Δ / √n
```

For `n = 24` pairs: `t_{0.975, 23} = 2.069`, `t_{0.80, 23} = 0.858`, so

```
MDE(24) = (2.069 + 0.858) · σ_Δ / √24 = 2.927 · σ_Δ / 4.899 = 0.597 · σ_Δ
```

A design target of `MDE ≤ 0.60 σ_Δ` is met by 24 runs per cell, which is the reason the
confirmatory tier is 24 rather than the project's auditor floor of 16. Sixteen runs would
give `MDE(16) = (2.131 + 0.866)/4 = 0.749 σ_Δ`, a 25 per cent larger detectable effect for the
same cost, and a bare floor is not a sample size argument.

The pilot sample is small, so the planning value must be conservative. Two pre-declared
corrections are applied as variance multipliers to the pilot estimate:

```
σ_plan = √(V_pilot · V_attrition) · σ_pilot
V_pilot = 1/[(k−1)/χ²_{0.20, k−1}]      one-sided 80 per cent bound at the pilot's pooled df k
V_attrition = 1/(1 − p_U)²              p_U = one-sided 80 per cent upper bound on the loss rate
```

With `k = 84` pooled degrees of freedom (12 pilot cells, 7 each) and `χ²_{0.20, 84} ≈ 97.0`,
the pilot correction is `1/0.866 = 1.155` on the variance, i.e. `√1.155 = 1.075 · σ_pilot`. With
an assumed 15 per cent loss rate and 24 planned runs, `p_U = 0.249`, so
`V_attrition = 1/(1 − 0.249)² = 1.77` and the standard-deviation factor is `√1.77 = 1.330`.
The two are applied together as a single multiplier on the variance,

```
V = (1/0.866) · 1.77 = 1.155 · 1.77 = 2.04
σ_plan = √2.04 · σ_pilot = 1.43 · σ_pilot
```

The decision rule is an absolute effect target, not a multiple of the noise. The smallest
rare-class advantage that would be worth reporting is declared in advance as

```
δ_min = 0.02 log count per generation
```

which is a sustained two per cent per-generation growth advantage for the class that was rare,
a scale at which the class share moves by roughly half of its own value over the measurement
window and which is large enough to matter for persistence in this system. The run size is then
fixed by

```
n_req = [(t_{0.975, n−1} + t_{0.80, n−1}) · σ_plan / δ_min]²   evaluated at the chosen n
```

With `n = 24` the bracket is `[2.927 · σ_plan / 0.02]² = (146.4 σ_plan)²`, so 24 runs per cell
suffice when `σ_plan ≤ 0.0335`. If `σ_plan` is larger, section 5.3 applies. This is a
self-consistent absolute criterion: the target does not move with the pilot, and the run size
is accepted or escalated against it. `δ_min` is fixed here, before the pilot is read, and is
recorded in the design digest together with `V`.

### 5.3 Escalation and refusal rule

The escalation rule is keyed to the pre-declared absolute target `δ_min`, not to a multiple of
the pilot's noise, so that the noise cannot move the goal:

* If `σ_plan ≤ 0.0335`, the design target `MDE ≤ δ_min` is met at 24 runs per focal cell and
  the confirmatory tier runs as designed.
* If `0.0335 < σ_plan ≤ 0.0489`, the focal cells move to 48 runs per cell (the escalation block
  `11001–11384`, 24 extra runs per focal cell). At `n = 48`,
  `MDE(48) = (2.014 + 0.849) · σ_Δ / √48 = 0.413 σ_Δ`, and the target is met when
  `σ_plan ≤ 0.0489`.
* If `σ_plan > 0.0489`, the campaign **does not run**. There is no second escalation and no
  expansion beyond the pre-declared cap; the pilot is reported, the target is reported as
  unattainable at the available run budget, and that is the finding.

The decision is made once, from the pilot, before any confirmatory run, and is written into the
frozen design record. There is no de-escalation and no post-hoc run-size change.

### 5.4 What the pilot may not do

The pilot may not select the primary outcome, the sign, the lag, the factor levels, the arm
contrasts, the horizon, `δ_min`, `V` or any confirmatory threshold. If the pilot reveals that a
factor level cannot be realised, the level pair is re-chosen from the pilot's supply grid and
the design digest is re-frozen before the confirmatory runs; the other thresholds do not move.
If the pilot's positive control (the calibration block's P1 case, scaled to the real engine)
does not produce a rare-class advantage at or above `δ_min`, the campaign is not run, because
the design could not detect its own positive case.

---

## 6. Uncertainty interval method

All intervals are at run level. The exact procedure is fixed in
`STATS_AND_NULL_DESIGN.md`, section 2; the campaign locks the following parameters of it.

| Parameter | Value |
|---|---|
| Primary method | cluster bootstrap over runs |
| Resampling | runs resampled with replacement within each arm, separately for coevolving and frozen |
| Statistic | recomputed cell-level `Δ` from the pooled run-level `RA` values of the resampled runs |
| Resamples | 10,000 |
| Interval | 2.5 and 97.5 percentiles |
| Bootstrap seed | `20260928`, fixed |
| Secondary method | moving-block bootstrap over time within a run, then runs resampled as above |
| Block length | the first lag at which the run-level autocorrelation of the primary statistic falls below `1/e`, determined from the pilot block and then frozen |
| Disagreement rule | if the primary and secondary intervals disagree in sign, the contrast is reported as unresolved, never as a pass |
| Rejected | any nominal interval computed from the count of pooled class-generation pairs, and any interval that resamples classes or generations as if independent |

The point estimate may pool runs; the resampling is over runs. This is the specific repair the
directive requires: dependence within a run is modelled or resampled explicitly, and the
number of pooled pairs is reported as a descriptive count.

---

## 7. Multiplicity

* **Primary family (confirmatory, corrected).** The 8 focal coevolve-versus-frozen contrasts,
  one per forcing × census × contact-intensity combination, on the primary outcome `Δ`. Holm
  correction within this family at family-wise `α = 0.05`. Adjusted and raw values are both
  reported.
* **Secondary family.** The mechanism and association outcomes (sections 4.2 and 4.3) are
  reported with their own intervals and labelled secondary; they do not create a pass on their
  own and are not Holm-corrected inside the primary family.
* **Exploratory.** Factor main effects and interactions, the absent-arm controls, the
  sensitivity variations, the retired composition score, and every subgroup comparison. These
  are labelled exploratory wherever they appear and carry no claim.
* No correction is applied to, or removed from, any family after the runs begin. If a
  confirmatory result is significant only before correction, it is reported as not surviving
  correction.

---

## 8. Thresholds and their arguments

Every value is fixed before the confirmatory runs. The column "source of the number" records
whether the value is inherited from a standing project lock, derived from the mechanism, or
estimated on the pilot block; no value is derived from a confirmatory result.

| # | Threshold | Value | Argument |
|---|---|---|---|
| T1 | Lag of the antagonist adaptation channel `τ` | 4 generations | The update copies from the realised contact set at the generation boundary and is available to contacts from the next generation onward, so the true lag is 1. Four is the search anchor inherited from the prior campaign's configuration, kept so that the association curve can be compared with the recorded one, and the campaign estimates the whole cross-covariance over `τ ∈ {0,1,2,4,8}` rather than asserting 4. The peak lag (not `τ = 4`) is the reported quantity |
| T2 | Horizon | 500 generations | Matches the prior campaign's horizon so that a difference in outcome cannot be attributed to a longer run; the measurement window 125–500 spans at least 25 lag-4 cycles and at least three persistence intervals of the class dynamics recorded in the previous structural campaign |
| T3 | Burn-in | 125 generations | Matches the first locked window of the prior design; the founder slate and the initial transient are excluded while half the horizon is retained |
| T4 | Minimum viable census | 12 | A standing project lock inherited from the structural design. It is not adjusted here, and the previous campaign is not unlocked by anything in this campaign |
| T5 | Soft carrying capacity | 64 | A standing lock. It is deliberately *not* used as an effective population size, and the two census levels are produced by manipulating resource supply instead |
| T6 | Rare-class initial share band | `[0.05, 0.35]` | A class below 5 per cent is not trackable against the minimum viable census floor of 12, and a class above 35 per cent is not meaningfully rare; the band is checked on the pre-registered founder assignment before the run |
| T7 | Exposure ratio tolerance | 0.05 relative | Equal exposure is the precondition for interpreting a class difference in pressure. Five per cent relative is tight enough that any class imbalance that could carry the effect is flagged, and loose enough to be met by the designed policy. A run outside it is invalid for the contrast and appears in the attrition table |
| T8 | Contact-opportunity floor | 1.0 contact per host per generation, window-average | The contact policy pairs one host with one antagonist per seat per generation, so a fully realised generation gives exactly 1.0 opportunity per host, and the floor is set at the policy's own value. Below it, a host class' pressure is estimated from fewer events than the design provides and the deficit is a policy failure to be reported rather than a reason to lower the bound |
| T9 | Mechanism floor on the swap-signal | 0.20 ATP per host per contact opportunity | Derived from the mechanism and from the arithmetic of the calibration scenarios in `MEASUREMENT_VALIDATION.md`, section 4: with `virulence 8.0` and `steal_fraction 0.15` the debit scale is 1.2 ATP times affinity, and a swap that moves a class from a strongly matched to a weakly matched pairing moves the per-host debit by 0.4 to 0.7 ATP in the hand-computed cases. The floor is set at 0.20, below that range and above the zero that the counter-samples N1–N4 must produce, and it is frozen in the design digest before the confirmatory seeds are touched |
| T10 | Association significance rule | interval across runs excludes zero at the peak lag, with the sign required to be positive | The mechanism predicts a signed positive association. Excluding zero is the minimum evidence; the pre-registered sign is what distinguishes the mechanism from anti-phase oscillation, which the counter-sample N1 shows can also give a large correlation of the opposite sign |
| T11 | Dominance / polymorphism bound | maximum class frequency `≤ 0.85` at each locked window, with at least two alleles retained at each of the three sub-loci | Inherited from the existing structural hold clause (`ε = 0.15`, `R_min = 3`), retained so that the new campaign's demographic conditions are comparable with the previously recorded ones; it is not a new discovery threshold |
| T12 | Genotype-loss indicator | a designated class is recorded lost at the first generation in which its census is zero | A definition, not a threshold; it feeds time-to-loss and the competing-risk analysis |
| T13 | Effective-census separation | realised low-to-high census ratio `≥ 1.5` over the pilot | Chosen so that the two levels are a real manipulation rather than label variation; if the pilot cannot produce it, the level pair is re-chosen from the supply grid and the design is re-frozen before the confirmatory runs |
| T14 | Confirmatory run size | 24 runs per cell | Set by the power calculation of section 5.2 against the absolute target `δ_min = 0.02` log count per generation: `MDE(24) = 0.597 σ_Δ ≤ δ_min` whenever `σ_plan ≤ 0.0335`. It is not the project's 16-run auditor floor |
| T15 | Absolute effect target | `δ_min = 0.02` log count per generation | The smallest rare-class advantage that would be worth reporting: a sustained two per cent per-generation growth advantage for the rare class, which moves its share substantially over the 375-generation measurement window. It is a scientific judgement fixed before the pilot is read, not a function of the observed noise |
| T16 | Escalated run size | 48 runs per focal cell | `MDE(48) = 0.413 σ_Δ`, which meets the target when `σ_plan ≤ 0.0489`; chosen as the next doubling of the base allocation so that the paired design stays balanced and no cell is dropped. If `σ_plan > 0.0489` the campaign does not run |
| T17 | Uncertainty method and resample count | cluster bootstrap over runs, 10,000 resamples | The unit of replication is the run, so resampling is over runs; 10,000 resamples make the percentile endpoints stable to three decimals in the pilot's variance range |
| T18 | Bootstrap seed | `20260928` | Fixed so that the reported interval is exactly reproducible; it is a reproducibility device with no statistical content |
| T19 | Multiplicity procedure | Holm within the 8 focal contrasts, family-wise `α = 0.05` | Holm is uniformly more powerful than the Bonferroni bound at the same family-wise error rate, and the family is declared before the runs |
| T20 | Variance inflation applied to the pilot estimate | `V = 2.04` on `σ_pilot²` before the power calculation, i.e. `σ_plan = 1.43 σ_pilot` | The product of two pre-declared factors, both derived in section 5.2: `1/0.866 = 1.155`, the inverse of the one-sided 80 per cent upper bound on the pilot's standard deviation at `k = 84` pooled degrees of freedom, and `1.77`, the inverse squared one-sided 80 per cent upper bound on the surviving proportion at an assumed 15 per cent loss rate with 24 runs. The 15 per cent loss assumption is the pilot-and-prior-campaign attrition figure and is fixed before the pilot is read |
| T21 | Campaign run cap | 2,400 runs | A resource cap declared in advance: 576 base plus 384 escalation plus 96 pilot plus 20 calibration plus 240 sensitivity is 1,316 runs, well inside the cap; the cap exists so that no post-hoc expansion is quietly possible, and if the cap is ever reached the campaign reports an incomplete record rather than a reduced sample |
| T22 | Sensitivity block size | 240 runs (10 per cell) | Large enough to detect a sign change of the primary contrast at the sensitivity settings, small enough not to compete for the resource budget reserved for the confirmatory tier; the sensitivity block never enters a primary estimate |

---

## 9. Data handling

### 9.1 Missing data and run validity

* **Every assigned run is reported.** The primary table is unconditional: each assigned run
  contributes its `RA` value if one is defined, and otherwise contributes an entry in the
  attrition table with the reason. The number of assigned runs appears in the denominator of
  every reported rate.
* **Invalidity flags are mechanical and pre-declared**: `exposure_invalid` (T7 or T8 failed),
  `designation_mismatch` (section 3.3), `rare_class_out_of_band` (T6), `horizon_incomplete`,
  and `digest_mismatch` (replay failure). Each flag removes the run from the paired contrast
  only, and the count per flag is reported.
* **Conditioning on survival is a separate, labelled table.** The primary table makes no
  survival restriction. A second table conditions on runs that retain both designated classes
  and a census at or above the minimum viable floor through the window, and is labelled a
  conditional claim. The difference between the two tables is reported as a mediation
  statement: how much of the apparent effect is carried by collapse and extinction rather than
  by the lag mechanism.
* **Censoring, not deletion, for collapsed trajectories.** If a run falls below the minimum
  viable census, the series is censored at that generation, the censoring generation is
  recorded, and the run contributes a censored `RA` value computed from the generations at or
  after the burn-in that it did complete; if the collapse occurs at or before the burn-in, the
  run contributes no contrast value and appears in the attrition table. Its subsequent
  generations are not scored.
* **No arm is dropped for being hostile, unstable or inconvenient** without the drop appearing
  in the attrition table, in the sensitivity analysis and in the conditional table.

### 9.2 Extinction policy

Extinction is treated as an outcome, not as a filter, following `STATS_AND_NULL_DESIGN.md`,
section 5.

| Event | Recorded as | Treatment |
|---|---|---|
| Antagonist pool reaches zero units | `antagonist_extinct`, with generation | Run retained; pressure series censored from that generation; the run is a competing-risk outcome |
| Host census below the minimum viable floor | `host_collapse`, with generation | Run retained as `regime_hostile`; the series is censored at that generation and a censored `RA` is used when the burn-in was completed, otherwise no contrast value; the mediation table absorbs the difference |
| A designated class census reaches zero | `class_lost`, with generation | Run retained; time-to-loss enters the competing-risk analysis |
| No designated class remains in either arm of a seed | `designation_mismatch` | Pair excluded from the paired contrast, count reported |
| Replay digest mismatch | `digest_mismatch` | Run excluded from all analysis and reported; a replay failure is an instrument defect that is repaired and disclosed, not silently dropped |

### 9.3 Pre-declared sensitivity analyses

Each is run once, on the independent sensitivity block unless stated, and reported separately:

1. **Survival-restricted versus unconditional** primary contrast (the two tables of 9.1).
2. **With and without the `regime_hostile` runs**, which is the specific sensitivity the
   directive requires, so that the filter cannot be the source of the result.
3. **Mutation-rate sensitivity**: host bit-flip rate and antagonist mutation rate each varied
   by a fixed factor of two around their locked values, on the sensitivity block only.
4. **Window-length sensitivity** for the periodic forcing arm, to detect aliasing between the
   pulse schedule and the measurement window (T-absent, but pre-declared): the contrast is
   recomputed at three window lengths that are not multiples of the mean pulse interval.
5. **Composition-score comparator**: the retired `lagged_nfds_composition` statistic and its
   pooled pair count, reported with raw and Holm-adjusted values beside the pressure-based
   outcomes, labelled descriptive.

---

## 10. Stop rule

The confirmatory campaign does **not** start, and no claim is made, while any of the following
holds. These are the stopping conditions of `STATS_AND_NULL_DESIGN.md`, section 7, with the
campaign's phase assignments attached.

| # | Stop condition | Verified by |
|---|---|---|
| S1 | The two quantities are not separated in code and in the recorded history | The separation contract of `MEASUREMENT_VALIDATION.md`, section 7, and the unit test on scenarios 4.2–4.4 |
| S2 | The sign and lag of every causal link is not fixed in writing before the run | `SCIENTIFIC_QUESTION_AND_DAG.md`, section 3, frozen in the design digest |
| S3 | The anti-phase counter-sample (N1) is not rejected, or any positive synthetic case (P1–P3) fails, or any counter-sample (N2–N4) is not handled as specified | The mechanism-calibration block of section 2 |
| S4 | The nulls do not discriminate, or a null passes for the wrong reason | `STATS_AND_NULL_DESIGN.md`, section 3 |
| S5 | The power calculation has not fixed the run size, or the pilot has not been read on its own disjoint block | Section 5, and the frozen design digest |
| S6 | Any threshold cannot be defended without reference to a result | Section 8; any value that fails this test is removed before the run |
| S7 | Replay digests do not reproduce for the calibration and pilot blocks | The digest check of section 9.2 |
| S8 | The mechanism gate of section 0.6 has not been signed off by a reviewer who did not write the test | Review log of this campaign directory |

Additional rules once the campaign is running:

* **No interim analysis of the primary outcome.** There is no look at `Δ` before the assigned
  runs complete; optional stopping is excluded by construction. Only the pilot block may be
  used to estimate variance, and it is never used to estimate the effect.
* **No threshold motion.** No value in section 8 moves after the first confirmatory run starts.
  A threshold found to be mis-specified is reported as a design limitation and the affected
  contrast is reported as unresolved, not as a pass.
* **An instrument defect halts the campaign.** If replay digests fail, or exposure auditing
  reveals an unintended class imbalance, or the pressure and frequency channels are found to
  be crossed in the artefact, the campaign stops, the defect is repaired, and the affected
  blocks are re-run on their own seeds; runs already completed under a defective instrument
  are reported as instrument failures.
* **A negative result is reported, not repaired.** If `Δ` is below the floor, or the swap-signal
  is not negative, or the association does not have the pre-registered sign, the campaign
  reports an informative negative together with the parameter region in which the effect
  disappears. Region boundaries are reported as the finding.
* **An incomplete campaign is reported as incomplete.** If the campaign stops early for any
  reason, the assigned-but-unrun runs are listed with the reason, and no rate is computed
  against a reduced denominator.

---

## 11. Recording and the claim boundary

Every run records: the base commit, the design digest, the design document digest, the seed,
the cell coordinates, the arm, the designated common and rare classes and their generation-0
shares, the full dense history of the separated quantities of
`MEASUREMENT_VALIDATION.md`, section 7, the pressure and intent series, the exposure audit
block, the swap snapshot pairs, the run digest, the replay digest, the wall time and the
termination reason. The artefact set includes the analysis scripts and the raw histories so
that the primary statistic can be recomputed without re-simulating.

The claim boundary is fixed now. A pass under this design supports a statement of the form:
*in this model, with this affinity rule, this contact policy and this update rule, a delayed
adaptation of the antagonist to the previously common host class produced a measurable
rare-class advantage over a frozen antagonist under the stated factorial conditions, with the
stated boundary*. It does not support a general biological claim, it does not generalise to
other contact rules without a separate test, it does not claim the maintenance of sex, and it
does not use the words "proved" for either the Red Queen hypothesis or its digital analogue.
`red_queen_proved` and `biological_red_queen_proved` remain false, and the sealed campaign
`801–816` remains `ABORT / sealed FAIL`.
