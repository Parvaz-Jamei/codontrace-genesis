# Phase design: is costly sex maintained when the antagonist tracks common host genotypes?

Design only. No experiments were run for this document.

## 1. Minimal code changes (`causal-tape-experiment/sex_arms.py`)

New constants: `ANTAG_GENS_PER_HOST = 1`, `ANTAG_FAIL_DEATH = 0.5`, `ANTAG_SAMPLE_FRAC = 1.0`.

1. **Turnover.** Wrap the parasite block (lines 260-284) in `for _ in range(antag_gens_per_host):`,
   each sub-generation infecting hosts then updating its own pool; exposure is cumulative, but charge
   `infection_cost` once per host per *host* generation. New kwarg `antag_gens_per_host`.
2. **Cost of failing to infect.** Replace `survivors = par_idx[success > 0]` with an explicit cull:
   `failed = par_idx[success == 0]`, then kill a fraction `antag_fail_death` of `failed` before
   re-tiling. `0.0` restores today's rule; the change is making culling *partial* and rate-based.
3. **Re-tiling bug.** `math.ceil(PARASITE_CAP / survivors.size)` truncates when
   `survivors.size > PARASITE_CAP`, silently dropping infecting genotypes. Use
   `rng.choice(survivors, PARASITE_CAP, replace=True)`.
4. **Mutation.** `PARASITE_MUTATION_RATE = 0.08` at `LOCI = 6` puts ~38% of offspring at distance
   >= 2, destroying the tracking it should sharpen. Grid `{0.0, 0.01, 0.02, 0.08}` via a new kwarg.
5. **Infection cost.** `infection_cost` is the right knob but uncalibrated: exposure scales with
   turnover, so at `infection_cost = 0.4` infected hosts still reproduce under high turnover. Add
   `antag_assault_frac` and mask the distance matrix by a Bernoulli draw over living hosts, so a
   plateau above the sampling floor is attributable to tracking, not universal exposure.
6. **Diagnostic.** Log mean Hamming distance from each living antagonist to its nearest host. Tracking
   is the estimand that must move when turnover moves.

## 2. Pre-registered phase diagram

Primary: the surface **`c**(turnover, infection_cost)`**, the smallest cost ratio whose persistence
fraction falls to <= 0.5, and whether `c** >= 2.0` anywhere.

- Grid: turnover `{1, 3, 6, 12}` x infection cost `{0.4, 0.9, 1.6, 2.4}` x cost ratio
  `{1.0, 1.25, 1.5, 1.75, 2.0, 3.0}`; parasite mutation fixed at `0.02`; `GENERATIONS = 400`.
  The 1.0-1.5 interval is mandatory: `c*` is already bracketed in (1.0, 1.5], so a grid of
  `{1.0, 1.5, 2.0, 3.0}` cannot locate the curve.
- Seeds: **200 paired seeds**, `range(8000, 8200)`, identical vector in every cell.
- Primary outcome: persistence fraction `P(sexual_final >= 0.05)`. Do not lead with the mean over a
  bimodal distribution (existing `A5` spans 0.12-0.82 across seeds).
- Secondary: `infected_mean`, antagonist-to-host distance, a `delta = 0.5` strip at turnover 12,
  infection cost 1.6.
- Runtime, 4 workers: 9,600 runs at an estimated 1.6-2.5 s (measured 1.11 s asex / 1.92 s sex at
  `G = 400`; the k-fold loop adds only ~48 x 16 distance evaluations per sub-generation) = 4.3-6.7 h.
  Plus 1,800 control runs (1.2 h) and 1,200 mechanism runs (0.8 h). **Budget 8 h.**

## 3. Controls and falsifiers

Positive: cost ratio 1.0 + antagonist -> persistence > 0.30 (today 0.478). Negative: cost ratio 2.0,
no antagonist -> persistence < 0.05 (today 8.6e-5). Antagonist-free cost arm at 1.5/2.0/3.0 ->
extinction. `recombine = False` -> must collapse. Uniform-tax control: `V_diff` >= 3x the permutation
null. `evolving_parasite = False` -> must fail. Ledger residual <= 1e-9; leak probe must fire.

Refuse the claim if: a control fails; the optimum sits at cost ratio 1.0; rescue survives
`recombine = False`; rescued cells have `infected_mean < 0.05` or antagonist-to-host distance that
does not fall with turnover (uniform tax); rescue vanishes under partial assault.

## 4. Honest prior

I expect a negative diagram: `c**` stays in (1.0, 1.5] at every turnover. Oswald & Kirkpatrick
concluded species interactions typically select against sex, and our single-cell runs already refused
rescue while the twofold cost was charged. A positive is news only if `c**` rises with turnover across
2.0: the timescale ratio, not parasite presence, paying for recombination. A negative is informative as
a *bounded loss*: even with a tightly tracking, heavily penalised antagonist, frequency-dependent
selection cannot clear the twofold cost here, so Oswald-Kirkpatrick is not an artifact of sluggish
antagonists.

## 5. The sentence if the diagram is entirely negative

"Across 16 (turnover, infection-cost) regimes the critical cost ratio never exceeded 1.5, so an
antagonist that tracks the currently common host genotype with a short generation time still does not
pay for recombination, and the negative result of Oswald and Kirkpatrick survives the mechanism the
literature audit recommended."
