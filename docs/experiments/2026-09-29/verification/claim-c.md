# CLAIM C — ACCEPT

**Claim.** In `causal-tape-experiment/results/estimand_split.json` and the datasets under
`causal-tape-experiment/datasets/*.npz`, the re-routing share of the previously reported
specification bias at the highest epistasis level is **64.1 %** with a 95 % interval of
**[55.8, 73.3]**.

**Verdict: ACCEPT.** Recomputed from the raw arrays, the published estimator gives
**64.07 %** with 95 % CI **[55.78, 73.33]** — the published median and both interval
endpoints reproduced *bit-exactly*. The pooled **ratio of means** at `eps = 0.8` is
**64.82 %**, inside the 1 pp window.

## What was recomputed, from what

`test-runs/verify/claim_c_estimand.py` — own code path; it does **not** import
`estimand_split.py` and does not read any cached number before computing. Inputs are the
raw arrays of the three highest-epistasis configurations:

| config | seeds | focal mutations | distinct 18-bit genotypes |
|---|---|---|---|
| `e20260927_eps0.8_G40` | 3 000 | 16 | 1 358 |
| `e20260928_eps0.8_G40` | 3 000 | 16 | 1 195 |
| `e20260929_eps0.8_G40` | 3 000 | 16 | 1 378 |

Per-seed arrays used: `fitness`, `bits` (18 final loci), `counterfactual` (16 columns,
one per focal mutation), `present` (exposure indicator), plus `mutations` → `bit_of`.

```
beta_j - ATT_whole  =  (beta_j - ATT_onebit)  +  (ATT_onebit - ATT_whole)
                        component (i)            component (ii)
                        misspecification         re-routing
```

- `ATT_whole_j` = mean over **exposed** seeds (`present[:, j] == 1`) of `fitness - counterfactual[:, j]`
- `beta_j` = OLS slope on the 18 bits of a linear model with intercept
- `ATT_onebit_j` = mean over exposed seeds of the change in the fitted quadratic model
  (intercept + 18 main effects + all 153 pairwise products = 172 columns), fitted by `lstsq`
  on that configuration's **natural** ensemble, when locus `bit_of[j]` is set to 1 vs 0 with
  all other loci held at their observed values

### Fit health (why the one-bit quantity is exact, not a proxy)

Rank 172/172 in all three configurations, `R² = 1.000000000000000`, max |residual|
2.4e-13 / 3.3e-13 / 1.6e-13, and the identity `total − (i) − (ii)` holds to 1.1e-16. The
landscape is exactly quadratic in the final bits, so `ATT_onebit` *is* the exact one-bit
contrast and component (ii) cannot be written off as model error.

## Numbers

Point estimates (48 mutation-draw pairs pooled), Python 3.14 / numpy 2.4.4:

| quantity | value |
|---|---|
| **ratio of MEANS** `Σ|ii| / Σ|total|` | **0.648185 → 64.82 %** |
| ratio of MEDIANS `med|ii| / med|total|` | 0.629746 → 62.97 % |
| mean \|ii\| (re-routing) | 0.452686 |
| mean \|total\| (gap) | 0.698390 |
| med \|ii\| | 0.428197 |
| med \|total\| | 0.679953 |

The pooled means reproduce the published `by_eps` row exactly
(`mean_abs_component_ii_reroute` 0.4526855216…, `mean_abs_total_gap` 0.6983896947…).

Per coupling draw (these reproduce the published `per_config` entries to all printed digits):

| coupling draw | ratio of means | ratio of medians | mean \|i\| | mean \|ii\| | mean \|total\| |
|---|---|---|---|---|---|
| `e20260927_eps0.8_G40` | 0.4389 | 0.3107 | 1.0823 | 0.3302 | 0.7525 |
| `e20260928_eps0.8_G40` | 0.8326 | 0.8382 | 1.0574 | 0.4804 | 0.5770 |
| `e20260929_eps0.8_G40` | 0.7149 | 0.7635 | 1.3131 | 0.5474 | 0.7657 |

The share is strongly draw-dependent (0.44 to 0.83 on the ratio of means), as the published
note says.

## Bootstrap (500 seed resamples, rng seed 20261004, resample within each coupling draw)

Two runs of the same script differing **only** in the rank-admissibility test:

| run | rank test | redrawn | ratio-of-medians median | 95 % CI | ratio-of-means median | 95 % CI |
|---|---|---|---|---|---|---|
| primary (independent) | Cholesky of the 172×172 Gram | 4 | 0.642071 | [0.560208, 0.732508] | 0.645741 | [0.598652, 0.689475] |
| rank-tolerance matched | published `min λ/max λ ≤ 1e-8` + SVD solve | 6 | **0.640731** | **[0.557750, 0.733298]** | 0.645943 | [0.598652, 0.692299] |
| published JSON | — | 6 | 0.6407308901109312 | [0.5577497815809901, 0.7332976037688598] | 0.6459426356173571 | [0.5986521324031486, 0.6922986345929746] |

The rank-tolerance-matched run **reproduces the published median and both CI endpoints
bit-exactly** (`reproduces_published_ci_exactly: true` in `CLAIMS.json`).

The 3.12 and 3.14 runs of the primary method both redrew 4 resamples and agree to
4.2e-14 in the median (different BLAS), so the primary result is not interpreter-specific.

## Agreement with 64.1 %

| comparison | value | within 1 pp of 64.1 |
|---|---|---|
| ratio of **means**, pooled point estimate | 64.82 % | **yes** |
| bootstrap median, ratio of means | 64.57 % | yes |
| bootstrap median, ratio of medians (published estimator) | 64.07 % (matched) / 64.21 % (primary) | **yes** |
| **95 % CI for the published estimator** | **[55.78, 73.33]** vs claimed [55.8, 73.3] | **matches to 0.02 pp** |

## Discrepancies disclosed (not adjusted away)

1. **The raw pooled ratio-of-medians point estimate is 62.97 %**, and the mean over draws of
   the per-draw ratio of medians is 63.75 % — 1.1–1.4 pp below 64.1 %, i.e. *outside* the 1 pp
   window. The claimed 64.1 % is not that point estimate: it is the **bootstrap median of the
   pooled ratio of medians**. Both are reported; the stated 64.1 % is correctly attributed to
   the bootstrap estimator in the published JSON
   (`verdict.fraction_of_published_bias_that_is_rerouting`).
2. **The claimed interval [55.8, 73.3] belongs to the ratio-of-medians estimator.** The
   ratio-of-means bootstrap interval is materially narrower: [59.9, 69.2]. A reader who took
   "the ratio of means" and "[55.8, 73.3]" to be the same estimator would be wrong.
3. The primary (fully independent) bootstrap gave [56.02, 73.25] rather than [55.78, 73.33].
   I traced the cause: my Cholesky test admits 4 resamples that the published `min/max
   singular value ≤ 1e-8` test rejects as rank-deficient. Because a rejection consumes an
   extra RNG draw, the whole resample stream shifts after that point. Substituting *only* the
   published rank criterion (keeping my compressed-design algebra) restored the published
   median and CI exactly. This is a floating-point knife-edge in the admissibility test, not
   a substantive disagreement — but it means the published interval is sensitive to the rank
   tolerance, and 6 of 1 500 resamples sit on that boundary.

## Method note on the identity

The algebraic identity `total = (i) + (ii)` holds exactly by construction (residual 1.1e-16),
so it is not independent evidence; the substantive content is the *magnitudes* of the two
components and their ratio, which are reproduced above from the raw arrays.

## Artifacts

- `test-runs/verify/claim_c_estimand.py` (recompute + bootstrap), `claim_c_out.txt`, `claim_c_raw.json`
- `test-runs/verify/claim_c_rankcheck_out.txt`, `claim_c_raw_rankcheck.json`
- `test-runs/verify/claim_c_py312_out.txt`, `claim_c_raw_py312.json`
- `test-runs/verify/claim_c_inspect.py`, `claim_c_inspect_out.txt`
- `test-runs/verify/compare_c_runs.py`, `compare_c_out.txt`
