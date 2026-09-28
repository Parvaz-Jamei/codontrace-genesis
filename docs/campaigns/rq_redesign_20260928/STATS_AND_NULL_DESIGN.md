# Statistics, null models and the stopping rule (directive P0 items 3 and 5)

**Date:** 2026-09-28 · **Base commit:** `7cfba3f`
**Scope:** the uncertainty, multiplicity, attrition and power policy for the
corrected host–antagonist campaign. Written before any confirmatory run.

## 1. The unit of replication

A run is a seed and a run is the experimental unit. Within one run, the
frequencies of the antagonist classes in a generation are shares that sum to one
and are therefore dependent on each other, and successive generations of the same
run are autocorrelated. Neither a class-generation pair nor a generation is an
independent observation.

Consequences, all binding:

* `n` is the number of runs. The count of retained class-generation pairs is
  reported as a descriptive quantity named `pairs`, never as `N`.
* Every interval is computed at run level. The point estimate may pool pairs, but
  resampling is done over runs.
* A run contributes one summary value per arm to the primary analysis. Where a
  within-run time series is required, it is modelled with an explicit
  within-run dependence structure, not treated as independent draws.

## 2. Uncertainty

Primary method: **cluster bootstrap over runs**. Resample runs with replacement
within each arm, recompute the arm statistic from the pooled pairs of the
resampled runs, and take the 2.5 and 97.5 percentiles over 10,000 resamples. The
bootstrap seed is fixed in advance and recorded.

Secondary method, reported alongside: **moving-block bootstrap** over time within
each run, with block length chosen as the first lag at which the run-level
autocorrelation of the statistic falls below 1/e, then runs are resampled as
above. If the two intervals disagree in sign, the result is reported as
unresolved rather than as a pass.

Rejected: pooling all class-generation pairs into one correlation and quoting a
nominal interval from that correlation's sample size. This is the defect the
directive identifies; it is not repaired by increasing `n`.

## 3. Null models

Four nulls, each with the specific artefact it excludes. The primary test must
beat all four.

1. **Block-rotation null (within run).** Rotate the antagonist time series by a
   random offset that is a multiple of the block length, preserving its
   autocorrelation and marginal distribution, and recompute the lag statistic.
   Excludes "any two autocorrelated series correlate".
2. **Genotype-label permutation (sham intervention).** Permute which host class
   label is called common, leave every frequency and every contact event
   untouched, and recompute. Excludes an effect that is really a property of the
   label rather than of frequency.
3. **Matched forcing without antagonist evolution.** Same resource cycle, same
   population-size trajectory and same contacts, with the antagonist held frozen.
   Excludes an effect produced by the abiotic clock or by demography alone.
4. **Constant-loss control.** Add a fixed fitness debit of the same average
   magnitude to every host class. Excludes "any added mortality produces the
   statistic".

A fifth, adversarial null is required before the campaign is allowed to run: the
anti-phase oscillation counter-sample, in which host and antagonist frequencies
oscillate out of phase with no adaptation and no frequency-dependent loss. The
primary statistic must fail to reject on this counter-sample. If it rejects, the
statistic is measuring oscillation and the campaign is not run.

## 4. Multiplicity

The confirmatory family is declared here: the primary lag contrast across the
factorial cells of passage x forcing x population size x contact intensity. The
family size is fixed by the grid in `PREREG_V2.md` before the run. Holm
correction is applied within the family and adjusted values are reported beside
raw ones. Results outside the declared family are labelled exploratory and carry
no claim. No threshold is chosen or adjusted after seeing the confirmations.

## 5. Attrition, extinction and conditioning on survival

* All assigned runs are reported, including runs that collapsed, went extinct or
  were excluded, with the reason for each exclusion.
* The primary table is unconditional: every assigned run contributes.
* A second table conditions on survival and is labelled as a conditional claim.
  The difference between the two tables is reported as a mediation statement:
  how much of the effect is transmitted through extinction and collapse rather
  than through the lag mechanism.
* Rate of collapse and time to first genotype loss are reported beside the lag
  statistic as competing outcomes, not as filters.
* No arm is dropped for being hostile without that drop appearing in the
  attrition table and in the sensitivity analysis.

## 6. Power and sample size

A pilot on a fresh seed range, disjoint from the confirmatory range, estimates the
between-run standard deviation of the primary statistic in each arm, and the
within-run autocorrelation. The confirmatory run size is then chosen so that the
minimum detectable effect at 80 per cent power and a two-sided 5 per cent level is
no larger than the smallest effect the mechanism hypothesis predicts. The pilot
seed range is recorded in `PREREG_V2.md`; its results are never pooled with the
confirmatory results.

The previous practice of running sixteen seeds without a stated power argument is
not repeated. Sixteen is the auditor floor in this project, not a scientific
sample size.

## 7. Stopping rule

The confirmatory campaign is not run, and no claim is made, while any of the
following holds:

1. the two quantities are not separated in code and in the recorded history —
   antagonist class frequency and realised conditional pressure on a host class;
2. the sign and lag of every causal link is not fixed in writing before the run;
3. the anti-phase counter-sample is not rejected by the primary statistic;
4. the nulls in section 3 do not discriminate (a null that passes for the wrong
   reason is not a null);
5. the power calculation has not fixed the run size;
6. any threshold in `PREREG_V2.md` cannot be defended without reference to a
   result.

If the campaign runs and the effect is absent or below the pre-registered floor,
that is reported as an informative negative together with the parameter boundary
at which it disappears. The sealed campaign `801-816` remains `ABORT / sealed
FAIL`; nothing here revises it, and no test in this campaign discharges it.
