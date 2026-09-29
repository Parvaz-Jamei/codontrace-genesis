# CausalTape-1 — pre-registration

**Date:** 2026-09-27 (Asia/Tehran) · **Status:** run before any confirmatory number was inspected
**Substrate:** CodonTrace Genesis (`codontrace-genesis`, commit `5a161081`), local working copy, no remote writes.

## 1. What this study is, and what it is not

**Is.** A known-ground-truth instrument. The mutation-accumulation tape is
deterministic and the counterfactual arm advances the same RNG stream as the
factual arm, so `do(m suppressed)` is exact and `Y(0)` is computable for every
unit (lineage). That turns two quantities that are normally estimated into
*computed* quantities:

* the **exact per-lineage causal effect** of one mutation, and therefore its
  exact spread across lineages (contingency of a single substitution);

* the **exact decomposition** of the estimator everyone uses from data,
  `E[Y | m] − E[Y | ¬m] = ATT + selection_bias`, where
  `selection_bias = E[Y(0) | m] − E[Y(0) | ¬m]`.

**Is not.** A new application of Pearl's do-operator. Díaz-Uriarte, Ríos-Arroyo
& Johnston (arXiv:2606.12597) already formalise do-interventions and conditional
interventions on evolutionary accumulation models and already show that
conditioning on the absence of a mutation gives incorrect predictions. This
study does not claim that idea. It asks a narrower question that a fitted model
cannot answer: *how large is the error, exactly, and how does it scale with
epistasis and depth?* It is not a claim about biology. It is not a claim about
CodonTrace's fidelity. `red_queen_proved` and every other ClaimGate refusal stay
false and untouched by this run.

The framing follows Powell & Mariscal (Interface Focus 5:20150040): under
determinism, rewinding the tape is exact by construction, so a bit-reproducible
engine is the correct *instrument* for asking how sensitive outcomes are to
which history was realised.

## 2. Substrate

Two substrates, one run each.

* **S (synthetic, primary).** Genotype is 18 bits (6 codons × 3 bits, engine
  `SemanticGenome`). Founder is all-zero. Fitness

  `F(x) = Σ w_i x_i + ε · Σ_{i<j} J_ij x_i x_j`

  with `w_i ∈ [0.5, 1.5]` and symmetric `J_ij ∈ {−1, +1}`, diagonal zero, drawn
  once from `RNGManager(seed=20260927).fork("env")`. Because the map is
  analytic, the isolated effect of mutation `i` on the ancestor background is
  exactly `w_i`, which gives an independent check on the harness.

* **A (engine-native, secondary).** The genome is executed by the engine's
  `WhiteBoxAgent` in a fixed `World2D`; the outcome is the remaining ATP read
  from the closed `ATPAccount` after 8 deterministic steps. No analytic
  reference exists here; substrate A is reported as a portability check only.

### Tape dynamics

Each generation the tape draws one point mutation from
`RNGManager(seed).fork("tape")` using the engine's own draw order
(codon index, bit index, replacement symbol), then accepts it iff fitness
strictly improves. Every proposal is logged with generation, locus, direction
and fitness delta. The fast proposal path is proven event-identical to
`Mutation.apply` (gate C).

### Intervention semantics

`do(m := suppressed)` means: when the drawn proposal *is* `m`, it is not
applied. The RNG stream is **not** rewound or re-keyed, so every later draw is
identical to the factual arm (gate B verifies the stream digest is unchanged).
Bootstrapping a fresh stream was explicitly rejected as the intervention design;
the red-team review flagged `preserve_rng_stream` as a flag without a mechanism,
and this harness does not rely on it.

## 3. Estimands

For focal mutation `m` and outcome `Y` (fitness, and secondarily the innovation
indicator `1[F ≥ θ]`):

| symbol | definition | how obtained |
|---|---|---|
| `ATT_m` | `E[Y(1) − Y(0) | m occurs]` | exact, paired replay |
| `ATE_m` | `E[Y(1) − Y(0)]` | exact, paired replay (never-taker convention) |
| `naive_m` | `E[Y | m] − E[Y | ¬m]` | observational, same ensemble |
| `adjusted_m` | OLS coefficient on bit `i`, all 18 bits + intercept | observational |
| `τ_direct` | isolated mutation on the ancestor background = `w_i` | analytic |
| `τ_epi` | `ATT_m − τ_direct` | exact |
| `null band` | p95 of `|ATT_i − ATT_j|`, `i ≠ j` across focal loci | exact |

`selection_bias_m = naive_m − ATT_m` and is *also* computed directly as
`E[Y(0)|m] − E[Y(0)|¬m]`; the identity residual is reported and must be ≤ 1e-12.

The direct/epistatic reference is the **ancestor contrast**, never an average
over random backgrounds (averaging over backgrounds estimates the direct effect
and leaves sampler noise that can be published as fake epistasis).

## 4. Sample and seeds

* Pilot seeds `0…149`: used only to select the focal mutation set (top 8
  `0→1` mutation ids by how many pilot tapes carry them) and to fix `θ`.
  No effect size is read from pilot seeds.
* Confirmatory seeds `1000…1299` (n = 300, paired). The red-team power analysis
  rejects the older 16–30 seed standard for this design; n = 300 is well above
  the n = 48 floor, and the paired variance ratio from common random numbers is
  ~1e-5.
* Grid: `ε ∈ {0, 0.05, 0.1, 0.2, 0.4, 0.8}` × depth `G ∈ {20, 40, 80}`.
* Substrate A: 100 seeds, G = 20.
* Bootstrap: 1000 paired resamples over confirmatory seeds, percentile 95% CI.
* No seed is dropped, no run is repeated to obtain a nicer number, and the
  analysis script is fixed before the confirmatory run.

## 5. Pre-registered rules

**R1 — harness gates.** Determinism floor (re-run digest equality),
intervention minimality (stream digest unchanged, exactly one bit changed,
closed-form delta matched to 1e-12), fast-path equivalence, and perturbed-seed
digest inequality. If any gate fails, the study reports an instrument failure
and no numbers.

**R2 — additive pipeline null (`ε = 0`).** `|adjusted_m − ATT_m| ≤ 1e-9` for
every focal mutation. With an exactly linear map, OLS over the full bit vector
must recover the per-unit effect exactly. If this fails, the estimator
comparison is void and the study stops.

**R3 — conditioning is confounded even without epistasis (`ε = 0`).**
`median(selection_bias) > 1e-3`. The mutation is not randomised across
lineages, so the naive contrast must already be biased in the additive world.

**R4 — exact contingency of a single mutation.**
`ε = 0` ⇒ `sd(τ_total | exposed) = 0` for every focal mutation;
`ε = 0.8` ⇒ `median sd(τ_total | exposed) > 0`. This is a statement about the
system, not about noise: in the additive world every lineage feels exactly the
same effect.

**R5 — specification bias grows with epistasis.**
`median |adjusted_m − ATT_m|` is non-decreasing in `ε` at `G = 40` and strictly
larger at `ε = 0.8` than at `ε = 0` by more than 1e-3.

**R6 — heterogeneity is reported, never assumed away.** Median `sd(τ_total | exposed)`
by `ε`, plus the fraction of exposed seeds with a non-zero delta.

**R7 — direct equals lineage under additivity.** `ε = 0` ⇒ `|τ_epi| ≤ 1e-9`
for every focal mutation (the ancestor contrast is the whole effect).

**R8 — epistatic excess beats the cross-locus null band.**
At `ε = 0.8`, `median |τ_epi|` > the p95 cross-locus gap. A zero-width null
band from a single inert locus is explicitly rejected as a calibration source.

## 6. Honest-FAIL path

Any of the following is a publishable outcome and none of them licenses
shrinking the claim to fit the data:

* R1 fails → instrument invalid; report the gate that failed and stop.
* R2 fails → the OLS comparison is uninformative; report only the exact
  contrasts and say why.
* R4/R7 fail at `ε = 0` → the harness does not behave additively; report the
  harness, not a finding.
* R5/R8 fail → "epistasis does not make these estimators worse in this
  substrate" is the result, and it is reported as such.
* R3 fails → conditioning is unbiased in this substrate, contradicting the
  expected direction; report it.

## 7. Scope limitations (stated up front)

* One fixed environment: no niche construction, no frequency-dependent
  selection, so "contingency" here is mutation-order and background epistasis,
  not ecology.
* Substrate S uses a specified fitness map; it is an instrument calibration,
  not a model of any organism. Substrate A is the engine-anchored port.
* No environment-seed or genotype-forcing intervention in this version; only
  "the mutation is suppressed" and "the mutation occurs" are estimated. The
  red-team's five-intervention separation (genotype do-operator vs lineage
  conditioning vs RNG-stream vs environment vs mutation operator) is honoured
  by estimating exactly one of them and saying so.
* No order-permutation intervention in this version. Mutation-order contrasts
  need a matched mutation-schedule digest on every arm, or the order effect is
  inflated by the whole schedule (red-team D5); that arm is deferred rather than
  approximated.
* Population = one tape per seed. Seed is the only randomisation unit; ticks and
  individuals are not independent replicates.

## 8. References used to position this run

* Díaz-Uriarte, Ríos-Arroyo & Johnston (2026), *A structural causal framework
  for interventions on evolutionary accumulation models*, arXiv:2606.12597.
* Marshall & Galea (2015), *Am J Epidemiol* 181:92–99, doi:10.1093/aje/kwu274.
* Powell & Mariscal (2015), *Interface Focus* 5:20150040,
  doi:10.1098/rsfs.2015.0040.
* Lenski, Ofria, Pennock & Adami (2003), *Nature* 423:139–144,
  doi:10.1038/nature01568.
* Covert, Lenski, Wilke & Ofria (2013), *PNAS* 110:E3171–E3178,
  doi:10.1073/pnas.1313424110.
* Blount, Lenski & Losos (2018), *Science* 362:eaam5979,
  doi:10.1126/science.aam5979.
* Van Hofwegen, Hovde & Minnich (2016), *J Bacteriol* 198:1022–1034,
  doi:10.1128/JB.00831-15.
* Leon, D'Alton, Quandt & Barrick (2018), *PLoS Genet* 14:e1007348,
  doi:10.1371/journal.pgen.1007348.
* Turner, Blount & Lenski (2015), *PLoS ONE* 10:e0142050,
  doi:10.1371/journal.pone.0142050.
