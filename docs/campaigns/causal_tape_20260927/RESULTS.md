# Causal tape campaign — acceptance-test record (stage 4)

**Date:** 2026-09-27 · **Base commit:** `5a161081`
**Run host:** 8 logical cores, Python 3.14.4, NumPy 2.4.4, four worker processes per run.
**Reproducibility:** every run writes a live event log, a per-run manifest with a
configuration digest, and a resume index, so an interrupted batch continues from
the last completed configuration.

## 1. Estimator benchmark

**Scale.** Three independent coupling draws x nine epistasis levels
`eps in {0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8}` x depths 20/40/80,
1500 paired seeds per cell: 81 configurations, 121,500 paired seeds,
164.5 minutes.

**Instrument.** Suppressing a drawn substitution leaves the RNG stream digest
unchanged (asserted equal across arms), so the counterfactual differs from the
factual arm in that event alone. A neutral fast path reproduces the engine
mutation operator exactly (events, bits, fitness and stream digest identical).

**Accept rules.**

| Rule | Outcome |
|---|---|
| `A1` specification bias zero at `eps = 0` | Pass, all three environments: 4.1e-15, 3.7e-15, 4.2e-15 |
| `A2` naive conditioning underestimates at `eps = 0` | Pass, all three |
| `A3` exact per-lineage spread zero at `eps = 0`, positive at `eps = 0.8` | Pass, all three |
| `A4` `tau_epi` zero at `eps = 0` | Pass, all three |
| `A5` trend of specification bias against `eps` | Pass as a rank correlation; the strict pointwise form failed in one environment |

**The one failure, and why it is a metric artefact.** In the second coupling draw
the median absolute specification bias dips from 0.08939 at `eps = 0.2` to
0.08652 at `eps = 0.3`, a decrease of 0.00287. A paired bootstrap over the two
levels gives probability 0.489 for a decline, i.e. no evidence of a real
reversal, and the rank correlation over the nine levels is 0.983. On the same
rows the mean, maximum and lower-quartile absolute biases are all strictly
increasing in all three environments; only the median over eight focal
substitutions fails. The cause is discrete: off-diagonal couplings are exactly
plus or minus one, so the background term of a locus lies on a half-integer grid,
and in that environment the median of eight sits on a mass point. The
pre-registered rule is therefore restated as a rank correlation over the grid
with a bootstrap interval, and strict monotonicity is reported as descriptive
only. The focal set is widened so the median cannot sit on a grid point.

**Order dependence.** With the proposal multiset held fixed and only the arrival
order permuted, the schedule-adjusted order effect is exactly zero at
`eps <= 0.1` in every environment and positive above a threshold whose position
is landscape-dependent (0.10, 0.05 and 0.10 for the three draws). Normalised by
the larger endpoint fitness, the median effect is 0.0065 at `eps = 0.2`, 0.063 at
`eps = 0.4` and 0.146 at `eps = 0.8`, against reported floors of 0.01 and 0.1.
A control arm without a matched proposal multiset inflates the estimate by only
1.06 to 1.57 times here, which is reported as a measured non-effect.

**Second pass (per-seed datasets, wider focal set, third estimator).** A rerun
stores per-seed fitness, locus bits, counterfactual fitness and presence vectors
for every configuration, so estimators can be recomputed without re-simulating.
It adds a quadratic plug-in estimator under `do(locus = 1)` versus
`do(locus = 0)`, using all main effects and all pairwise products.

That comparison splits the reported quantity in two, and the split matters. The
per-seed datasets make the split computable without re-simulating: write
`beta - ATT_whole_tape` as `(beta - ATT_onebit) + (ATT_onebit - ATT_whole_tape)`,
where the first term is misspecification of a one-bit outcome model and the
second is the re-routing gap between a one-bit contrast and the whole-tape
contrast that suppression actually produces. On this substrate the quadratic
plug-in model is exactly correctly specified (rank 172, residual 6e-13), so its
one-bit prediction coincides with the exact one-bit contrast and the second term
is pure re-routing rather than further misspecification.

| epistasis level | median absolute misspecification | median absolute re-routing | re-routing share of the total |
|---|---|---|---|
| 0.0 | 1.2e-14 | 1.2e-14 | not defined (both zero) |
| 0.05 | -- | -- | 0.01 |
| 0.1 | -- | -- | 0.02 |
| 0.2 | -- | -- | 0.60 |
| 0.4 | -- | -- | 0.44 |
| 0.8 | 1.141 | 0.403 | 0.641, 95 per cent interval [0.558, 0.733] |

The re-routing share is negligible below `eps = 0.2` and dominant above it. At
`eps = 0.8` roughly two thirds of the quantity previously reported as estimator
bias is the estimand mismatch, which no better one-bit model can remove; the
remaining third is linear-model misspecification and is fixable. The two
components are separable conditional on the coupling draw (within-configuration
median correlation +0.03); the strongly negative pooled correlation is an
artefact of pooling across epistasis levels. One caveat is recorded: at
`eps = 0.8`, 5.5 per cent of exposed seeds (up to 38 per cent for one locus) had
the locus cleared by a later accepted reversal, so the one-bit proxy and the
whole-tape contrast differ in what they hold fixed there.

## 2. Two-fold cost of sex

**Scale.** Eleven arms plus an eight-arm parameter sweep and a four-cell
factorial, 100 paired seeds per arm, 400 generations, 200 founders, ten per cent
baseline mortality.

**Instrument.**

| Check | Result |
|---|---|
| Ledger identity, all arms | maximum residual 1.2e-10 |
| Per-mating dissipation audit | exact, zero error |
| Injected leak of 1e-3 per host per generation | detected, residual 17.1 |
| Positive control: no cost, antagonist present | sexual frequency 0.478 +- 0.158, no extinction |
| Negative control: two-fold cost, no antagonist | 8.6e-5, extinction in every run |

**Result.** At the classical two-fold cost the antagonist does not maintain
sexual reproduction: sexual frequency is zero with extinction in every run
(median 125 generations with the antagonist, 191 without), and the paired margin
against the no-antagonist arm is indistinguishable from zero, so the
pre-registered test rule is refused. Charging an additional irreducible
per-mating dissipation makes it worse (median extinction 80 generations). A
non-evolving antagonist leaves infection at 3 per cent and changes nothing, so
coevolution rather than mere antagonist presence is required. An arm without
recombination behaves like the cost-only arm, consistent with recombination being
the mechanism at stake.

**Critical cost.** With the antagonist present, a cost ratio of 1.0 leaves sexual
frequency at 0.478, a ratio of 1.5 leaves 0.0004, and 3.0 leaves zero, which
brackets the critical cost in (1.0, 1.5]. Across four further parameter regimes
(infection cost, host mutation rate, matching tolerance, antagonist pool) no
regime maintains costly sex, while costless sex persists in the two regimes with
strict matching.

## 3. Biotic versus abiotic turnover

**Scale.** Four factorial cells plus two uniform-tax cells, 100 paired seeds per
cell, 400 generations; a diagnostic pass adds differential-infection statistics.

**Primary statistic.** Temporal `F_ST(w)` on per-locus frequencies against a
closed-form Wright-Fisher drift null computed from the effective number of
breeders, measured at about 40 against a census of about 359 — matching the
census instead would have overstated the null by roughly a factor of nine.

| `w` | antagonist effect | abiotic effect | interaction | uniform-tax control | antagonist share |
|---|---|---|---|---|---|
| 5 | +0.00027 | +0.00007 | -0.00026 | -0.00246 | 0.788 |
| 10 | +0.00121 | +0.00019 | -0.00064 | -0.00197 | 0.866 |
| 20 | +0.00271 | +0.00026 | -0.00106 | -0.00165 | 0.913 |
| 25 | +0.00362 | +0.00034 | -0.00140 | -0.00147 | 0.914 |
| 50 | +0.00782 | +0.00048 | -0.00269 | -0.00107 | 0.942 |

**Accept rules.** `C1` passes: the antagonist leads at every window, share
0.79 to 0.94. `C2` passes: a genotype-blind uniform energy tax does not reproduce
the antagonist effect and moves turnover the other way. `C3` passes:
differential infection risk is 0.1324 against a label-permutation null of 0.0177
in the antagonist cells, and exactly 0.0264 against 0.0264 in the tax cells, so
the factor is frequency-dependent selection rather than a uniform tax. The
interaction is negative at every window and grows with `w`, as expected when a
resource pulse makes the infection cost non-binding for one generation and
raises the effective number of breeders.

Effective genotype number is about 25 of a possible 64, so the statistic is not
saturated. An `eta^2` decomposition puts the antagonist above the abiotic factor
at every window, and the minimum detectable interaction at 100 seeds is 0.00049
against an observed 0.00106 at `w = 20`.

## 4. Standing limitations

The landscape for questions 1 and 3 is written for the experiment, so those
results are statements about the instrument and the model world, not about
biology. Question 2 uses a digital antagonist with matching-allele infection; its
conclusion is restricted to that model and to the parameter regimes tested. No
engine fidelity claim, and no relaxation of any existing ClaimGate refusal, is
implied by any number here. `red_queen_proved`, `intelligence`,
`collective_intelligence` and the host–parasite refusals all remain refused.
