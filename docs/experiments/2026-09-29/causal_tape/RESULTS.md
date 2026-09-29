# CausalTape-1 — results

**Run date:** 2026-09-27 · **Repo under test:** `codontrace-genesis` @ `5a161081` (working tree clean, no git writes, nothing pushed)
**Python:** 3.14.4 · **numpy:** 2.4.4 · **pytest:** 9.1.1
**Artifact hashes (SHA-256 prefix):** harness `D68BC01A8EC41212`, experiment `B5FEA4E0CDC5C210`, gates `FBAC6DA845BEFB10`
**Raw output:** `results/benchmark_results.json`, `results/harness_gates.json`, `summary.txt`

## 1. What was asked and what was measured

One question, posed so that it can be answered exactly instead of estimated:

> In a mutation-accumulation process, how wrong are the two estimators people
> actually use for the causal effect of a single mutation — naive conditioning
> and regression adjustment — when the true interventional contrast is
> computable by replay?

The tape is deterministic and the counterfactual arm advances the *same* RNG
stream as the factual arm, so `Y(0)` is available for every lineage and the
comparison needs no identification assumptions. Seed is the only randomisation
unit; n = 300 paired confirmatory seeds per configuration; the focal mutation
set and every threshold were fixed in `PREREG.md` before the run.

## 2. Instrument gates (R1) — all pass

| gate | check | result |
|---|---|---|
| A | re-run digest equality (determinism floor) | PASS — identical events, bits, fitness, RNG digest |
| B | intervention minimality: stream digest unchanged, exactly one bit moved, closed-form delta matched | PASS — to 1e-12, also with selection active |
| C | fast proposal path == `Mutation.apply` engine path | PASS — events/bits/fitness/RNG identical over 12 tapes |
| D | perturbed seeds give genuinely different tapes | PASS — 6/6 unique digests |

Gate B is the load-bearing one: the do-operator does **not** rewind or re-key the
RNG stream. Suppressing an event consumes the identical draw and only declines
to apply it, so later generations are bit-identical to the factual arm.

## 3. Pre-registered rules

| rule | prediction subject | literal outcome |
|---|---|---|
| R2 | `ε = 0` ⇒ `|adjusted − ATT| ≤ 1e-9` | **PASS** — max 1.13e-14 |
| R3 | `ε = 0` ⇒ `median(selection_bias) > 1e-3` (positive) | **FAIL as signed** — sign is *negative* |
| R4 | `ε = 0` ⇒ `sd(τ_total) == 0` and `ε = 0.8` ⇒ `> 0` | **FAIL as literally worded** — see §4.2 |
| R5 | median `|specification bias|` non-decreasing in `ε` | **PASS** — monotone, 1.3e-15 → 0.79 |
| R6 | heterogeneity reported | reported (§4.1) |
| R7 | `ε = 0` ⇒ `|τ_epi| ≤ 1e-9` | **PASS** — max 6.7e-16 |
| R8 | `ε = 0.8` ⇒ `median |τ_epi|` > cross-locus null band p95 | **PASS** — 3.13 > 2.60 |

### 4.1 The three numbers that matter

At depth 40, over 300 paired seeds and 8 focal mutations

| ε | innovation | `ATT` (exact) | `sd(ATT)` (exact) | median selection bias | median `|spec bias|` | median `|τ_epi|` | null band |
|---|---|---|---|---|---|---|---|
| 0.0 | 0.997 | 1.165 | 1.2e-15 | **−0.246** | **1.3e-15** | 0.0 | 0.658 |
| 0.05 | 0.997 | 1.042 | 0.064 | −0.272 | 0.0117 | 0.178 | 0.740 |
| 0.1 | 0.997 | 1.019 | 0.128 | −0.299 | 0.0234 | 0.355 | 1.128 |
| 0.2 | 0.993 | 1.211 | 0.324 | −0.551 | 0.0709 | 0.488 | 1.463 |
| 0.4 | 0.997 | 2.376 | 0.783 | −0.542 | 0.3703 | 1.763 | 2.149 |
| 0.8 | 0.997 | 4.078 | 1.810 | −0.550 | **0.7925** | 3.128 | 2.596 |

1. **`specification bias` is exactly zero under additivity and grows
   monotonically with epistasis** (R2, R5). At ε = 0 the OLS coefficient
   reproduces the exact per-unit causal effect to 1e-14 — the estimator
   comparison is therefore valid, and its failure at ε > 0 is a property of the
   process, not of the code.
2. **Naive conditioning is biased even with no epistasis** (R3, sign aside):
   median selection bias −0.246 against an exact effect of 1.165, i.e. about
   **21 % error at ε = 0**, rising to −0.55 (≈13 % of a much larger effect) at
   ε = 0.8. Per mutation the error is far larger than the median: for
   `4:0>1` at ε = 0 the naive estimate is 0.105 where the exact effect is
   0.628 — an **83 % underestimate**.
3. **The per-lineage causal effect has exactly zero spread under additivity and
   a large spread under epistasis** (R4/R6): `sd(ATT)` goes 1.2e-15 → 1.81.
   This is not sampling error; it is the exact dispersion of the same
   substitution across different realised histories, and it is the quantity
   "how much does which-history-matters" that replicate-based studies can only
   estimate with noise. The exact decomposition identity
   `naive = ATT + selection_bias` holds to **8e-15** across every configuration,
   which validates the counterfactual machinery independently of the model.

### 4.2 Where the pre-registration was wrong

Both deviations are reported as failures, not quietly relaxed.

**R3 (wrong sign).** I predicted the naive contrast would *over*-estimate the
effect, because lineages that accumulate more mutations should have higher
fitness. It *under*-estimates. The mechanism is visible in the exact term:
`selection_bias = E[Y(0) | m] − E[Y(0) | ¬m] = −0.246`, i.e. the lineages in
which `m` occurred have a *lower* counterfactual outcome without it than the
lineages in which it never occurred. Focal mutations are near-universal
(frequency ≈ 0.9); the lineages where the event never appears are otherwise
weak accumulators, so the untreated comparison group is not the "lower-fitness"
group the intuition assumed. The substantive claim (conditioning is confounded)
survives; the directional prediction does not, and the direction is what a
theory of the confounding must explain.

**R4 (tolerance, not substance).** The rule was written as
`sd(τ_total) == 0` at ε = 0. Taken literally it fails: the largest value over
24 focal mutations is 1.565e-15, pure floating-point summation noise, not
biological or simulation variance. With a 1e-12 tolerance the rule passes. The
literal FAIL is recorded above; the corrected reading is stated here explicitly
rather than overwriting the pre-registered text after seeing the number.

## 5. Depth sweep at ε = 0.8

| G | innovation | `sd(ATT)` | `|spec bias|` | `|τ_epi|` | null band |
|---|---|---|---|---|---|
| 20 | 0.790 | 1.869 | 0.678 | 2.429 | 1.875 |
| 40 | 0.997 | 1.810 | 0.793 | 3.128 | 2.596 |
| 80 | 1.000 | 1.130 | 0.765 | 3.638 | 3.877 |

The specification bias is flat in depth; the epistatic excess grows with depth
but so does the cross-locus null band, so R8's margin does not widen
monotonically. The binary innovation outcome saturates above depth 20
(0.997 → 1.000), so it carries no information at depth 40/80; only the
continuous fitness contrast is used there.

## 6. Engine-native port (substrate A) — failed, and why

The closed-ledger port (`WhiteBoxAgent` in `World2D`, outcome = remaining ATP
after 8 deterministic steps, 100 seeds, depth 20) returned **identical outcomes
for every seed** (mean 19.20, sd 0.0000) and therefore selected no focal
mutations: not one point mutation in those tapes strictly improved the ATP
outcome, so no counterfactual contrast exists. The port is reported as
**uninformative**, not as a negative result about the engine. The most likely
causes, in order, are (a) an all-zero founder genome under
`CodonTable.default_minimal()` whose point mutations execute as no-ops in this
world, and (b) per-step ATP costs that do not depend on the executed codon.
A working port needs an outcome variable that actually responds to the genome
(e.g. resource acquisition or trace structure) before it can carry any claim.

## 7. What this establishes — and what it does not

**Establishes (benchmark level, within this model):**

* An exact, noise-free measurement of a single mutation's causal effect and of
  its dispersion across realised histories, with the do-operator implemented as
  a minimal intervention that leaves the RNG stream untouched.
* A quantified, exact decomposition of the standard observational estimator:
  the naive contrast is biased by tens of percent, the bias is *already present
  without epistasis*, and the regression estimator's bias is zero without
  epistasis and grows monotonically with it.
* A validated estimator-comparison pipeline: a known ground truth (the additive
  case) in which the observational estimator must succeed, and in which it does.

**Does not establish, and must not be claimed:**

* Any biological result. The synthetic fitness map is an instrument calibration,
  not an organism; nothing here transfers to mutation or selection in nature.
* That Pearl's do-operator is newly applied to evolution — that formalisation
  exists (Díaz-Uriarte et al. 2026) and is cited as prior art, not novelty.
* Any statement about the engine's fidelity or about CodonTrace's scientific
  claims; `red_queen_proved` and every ClaimGate refusal remain false and
  untouched.
* Any mutation-order or environment-intervention result. This run estimates
  exactly one of the five distinct intervention types (mutation suppressed vs
  occurring) and says so.

## 8. Next steps that the data actually justify

1. Fix the engine-native port so the closed-ledger outcome responds to the
   genome; without it, substrate A cannot corroborate the synthetic result.
2. Add the mutation-order arm *with a matched schedule digest per arm*, so the
   order contrast is an interaction and not the whole order contribution.
3. Repeat at a second `ENV_SEED` with a frozen analysis script to test whether
   the ε-trend is a property of the process or of this coupling draw.
4. Separately from this study: the claim-pipeline defects below.

## 9. Pipeline defect found while reviewing (not part of this experiment)

Verified by reading the source, not inferred:

* `src/codontrace/genesis/causal_validation.py:754` builds every non-empty
  report's interval as `(mean, mean)` — a zero-width interval — and
  `claim_eligible` (line 737) requires only
  `effect.sample_count == len(run_pairs)`, with no minimum n.
* `src/codontrace/claimgate/auditor.py:135-138` treats any interval with
  `low > 0` or `high < 0` as excluding zero, so a degenerate interval around a
  non-zero mean always passes.
* `src/codontrace/claimgate/auditor.py:150` returns `True` when a comparison has
  a non-zero effect and neither an interval nor a p-value.

So `build_causal_evidence_report` can mint `claim_eligible = True` from a single
run pair with an interval that cannot fail, and the auditor's rules would accept
it. **Exposure today looks small, not zero:** the only caller of that function
is `tests/science_gates/test_phase3_maximum_validation_public_api.py:129`, which
does pass exactly one pair; and the comparison-construction sites sampled
(`claimgate/domain.py:305`, `hard_experiment_01.py:2344`,
`hard_experiment_03.py:792`, `ladder_packs.py:143`,
`phase_b_scientific_maturity.py:1233`) either set `effect_size=None`, set a
zero-width interval, or set `claim_downgraded=True`, so they fail closed. The
defect is a loaded gun rather than a demonstrated false label — but it means any
future path that connects the causal-evidence report to a comparison would
auto-pass, and the n=1 test currently locks in that behaviour.
