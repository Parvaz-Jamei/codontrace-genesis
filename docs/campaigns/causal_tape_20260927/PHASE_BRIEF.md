# Causal tape campaign — phase brief (stage 2)

**Date:** 2026-09-27
**Substrate:** `codontrace-genesis` life loop; local working copy at
`5a161081`; no remote writes until the accept tests pass.
**Status:** thresholds and focal sets fixed before the confirmatory runs.

## Shared protocol

* **Unit of randomisation:** the tape seed. Arms are paired on seed; ticks and
  individuals are never treated as independent replicates.
* **Intervention semantics.** A drawn substitution is suppressed by declining to
  apply it while the draw itself is still consumed, so every later draw is
  identical to the factual arm. The stream digest of both arms is asserted equal.
  Suppressing an event may not rewind or re-key the stream.
* **Ground truth.** For the additive landscape the isolated effect of flipping
  one locus on the ancestral background is exactly the corresponding weight, so
  the pipeline has a closed-form null it must reproduce.
* **Ledger.** Every energy flow is recorded. The identity
  `initial + intake - metabolism - infection - births + offspring - deaths = total`
  is asserted each generation, and a build with a deliberate leak of 1e-3 per
  host per generation must be detected.

## Question 1 — estimator benchmark

* Estimands: `ATT` (exact, on lineages that carry the mutation), `ATE`
  (never-taker convention), `naive = E[Y|m] - E[Y|m absent]`, `adjusted` = linear
  regression coefficient over the full locus vector, `tau_direct` = ancestor
  contrast, `tau_epi = ATT - tau_direct`.
* Grid: three independent coupling draws x nine epistasis levels
  `eps in {0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8}` x depths 20/40/80,
  1500 paired seeds per cell.
* Focal set: the most frequent gain substitutions, selected on pilot seeds only.
* Accept rules.
  * `A1` specification bias is zero at `eps = 0` to 1e-9 in every environment.
  * `A2` naive conditioning underestimates the effect at `eps = 0`.
  * `A3` the exact per-lineage effect has zero spread at `eps = 0` and positive
    spread at `eps = 0.8`.
  * `A4` `tau_epi` is zero at `eps = 0`.
  * `A5` the trend of specification bias against `eps` is positive; reported as
    a rank correlation with a bootstrap interval, with strict pointwise
    monotonicity descriptive only.
* Refusal conditions: any of `A1`-`A4` fails at `eps = 0`, or the trend interval
  does not exclude zero.

## Question 2 — two-fold cost of sex

* Factorial: mode (sexual/asexual) x cost (one-fold/two-fold) x antagonist
  (present/absent), plus a genotype-blind uniform tax and a recombination-off
  arm, 100 paired seeds, 400 generations, 200 founders, 10 per cent baseline
  mortality.
* Cost is charged as an energy debit; the ledger-irreducible variant adds a
  per-mating dissipation with no counterpart entry.
* Accept rules.
  * `B1` ledger identity and dissipation audit hold in every arm.
  * `B2` positive control: with no cost and an antagonist present, sexual
    frequency does not collapse.
  * `B3` negative control: with the two-fold cost and no antagonist, sexual
    frequency collapses.
  * `B4` test arm: the antagonist raises sexual frequency relative to the
    no-antagonist arm by a paired margin whose interval excludes zero.
* Refusal conditions: any control fails, or the paired margin is indistinguishable
  from zero. A refusal is reported as a negative result with the critical cost
  bracketed.

## Question 3 — biotic versus abiotic turnover

* Factorial: coevolving antagonist (present/absent) x abiotic resource pulse
  (present/absent), plus two uniform-tax cells, 100 paired seeds, 400
  generations.
* Primary statistic: temporal `F_ST(w)` on per-locus frequencies, `w` in
  `{5, 10, 20, 25, 50}`, against a closed-form Wright-Fisher drift null computed
  from the effective number of breeders `Ne(t) = (sum k)^2 / sum k^2`.
* Secondary: main effects and interaction from the four cells with paired
  bootstrap intervals, an `eta^2` decomposition, the differential infection risk
  of a genotype against a within-generation label permutation null, effective
  genotype number, and infectable-set occupancy.
* Accept rules.
  * `C1` the ordering of the two main effects is the same at every window.
  * `C2` the uniform-tax control does not reproduce the antagonist effect, so the
    factor is frequency-dependent selection rather than a uniform energy tax.
  * `C3` differential infection risk exceeds its permutation null in the
    antagonist cells and not in the tax cells.
* Refusal conditions: the ordering flips with window length, or the uniform-tax
  control reproduces the antagonist effect.

## Honest failure

A negative result that follows from a working instrument is an acceptable
outcome and is reported as such. A negative result produced by an instrument
that could not have detected the effect is not; in that case the instrument is
repaired and the run repeated.
