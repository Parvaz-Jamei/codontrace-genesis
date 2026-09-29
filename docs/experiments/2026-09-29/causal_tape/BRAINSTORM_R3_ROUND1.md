# BRAINSTORM_R3_ROUND1 — monotonicity failure, novelty target, transfers

**Read:** `heavy1_results.json`, `heavy1.py`, `harness.py`, `run_benchmark.py`, `NOVELTY_VERDICT.md`, `SCALE_DESIGN.md`. **No experiments were run**; diagnostics are re-analysis of stored JSON plus closed-form arithmetic on the coupling matrix from `harness.build_env`.

## 1. The monotonicity failure is a metric artefact

`spec_bias_monotone` is a strict non-decreasing test on `median_j |specification_bias|` over **8 focal mutations** at G40 (`heavy1.py:199-205`).

| env | eps 0.2 | eps 0.3 | step | other 7 steps | paired-bootstrap P(decline) | Spearman rho (n=9) |
|---|---|---|---|---|---|---|
| 20260927 | 0.03322 | 0.22690 | +0.19368 | all + | 0.001 | 1.000 |
| **20260928** | **0.08939** | **0.08652** | **-0.00287** | all + | **0.489** | **0.983** |
| 20260929 | 0.02383 | 0.13238 | +0.10855 | all + | 0.022 | 1.000 |

| diagnostic | env 20260927 | env 20260928 | env 20260929 |
|---|---|---|---|
| `mean abs bias` monotone over 8 steps | yes | **yes** | yes |
| `max abs bias` monotone | yes | **yes** | yes |
| `q25 abs bias` monotone | yes | **yes** | yes |
| `median abs bias` monotone | yes | **no (1 dip)** | yes |
| per-mutation curves monotone (4 common to all eps) | 3/4 | **1/4** | 3/4 |
| top-8 per-bit median abs Jx | 1.5 x5, 1.0 x3 | **1.0 x7, 1.5 x1** | 1.5 x5, 1.0 x3 |
| focal-set changes across the 9 eps values | 5 | 5 | 5 |
| monotone on the 4 mutations common to all eps | yes | **no** | yes |

**Diagnosis: (c) metric flaw, small (b), no (a).** Not seed noise: bias is deterministic given the realized background and eps over 1500 seeds, so P(decline) = 0.489 reflects only an unstable n = 8 median. Not a landscape reversal: no mechanism yields a 0.003 dip (3.3% of the value it interrupts, 0.4% of the 0 -> 0.846 rise) inside a rise whose other steps are 15-70x larger, while `mean|bias|` on the identical rows is monotone (see table). Mechanism: off-diagonal couplings are exactly +/-1, so c_j = 0.5*sum_k J_jk x_k lies on a 0.5 grid; in env 20260928 the median of 8 lands **on** a mass point, so a 4th-vs-5th mutation swap flips it discretely (median carried by `13:0>1` at eps 0.2 = 0.0770, by `17:0>1` at eps 0.4 = 0.1248) — a crossover. Focal-set churn aggravates but does not cause it.

### Pre-registered replacement

Primary statistic `S(eps) = median_{m in M} |beta_hat_m(eps) - ATT_m(eps)|`, then

```
slope_hat = sum_k (eps_k - eps_bar)(S_k - S_bar) / sum_k (eps_k - eps_bar)^2,   k = 9 eps values
```

**CI:** two-level bootstrap, B = 10 000 — resample *environments* from the E coupling draws, then *mutations* from `M`, recompute `slope_hat`, report 2.5/97.5 percentiles. Environment-level resampling is mandatory: the coupling draw, not the seed, generates between-environment variation. **Secondary (reported, not gated):** Spearman rho of eps vs `S` under eps-label permutation (n = 9, one-sided critical 0.683).

**Focal set `M`:** all gain mutations with natural-arm presence >= 0.05 and >= 25 exposed lineages, capped at 32, selected **once** from the `REFERENCE_EPS` pilot and fixed across the grid. **Mutations:** n = 8 fails because the median sits on a mass point; spread ~1.0 against a 0.5 gap puts the minimum near 20 — **require n(M) >= 24** plus a sensitivity curve for n(M) in {8, 16, 24, 32}. Fallback if < 24 qualify: the **mean** of |bias|. **Environments:** between-environment variation *is* the signal, so **require E >= 10** coupling draws, each `slope_hat` one draw; the primary test becomes one-sample across those slopes. **Decision rule:** reject "no trend" iff the lower bound of the 95% CI exceeds `0.05 * S(eps_max)`, a floor stopping the near-zero eps <= 0.1 region from deciding. Report strict pointwise monotonicity as descriptive only, and pre-register that pointwise monotonicity is *not* the claim: the claim is monotone increase in expectation.

## 2. Most defensible target: C2, converted from instrument into claim

`NOVELTY_VERDICT.md` calls C3 its strongest negative and grades C1 and C4 as strongly threatened (Acosta & Zaman 2022 publish the digital biotic x abiotic factorial; Yasui publishes that resource limitation removes the realised two-fold cost). **Choose C2** — exact noise-free per-lineage bias decomposition under an RNG-stream-preserving `do()` — because its prior art constrains the *identity* and the *application*, not the *instrument*. As written, C2 is still only an instrument.

**Converting control:** a closed-form per-mutation bias multiplier plus an environment x eps interaction test. For each `(env_seed, eps)` compute `A_j(eps) = eps * E[|c_j(x)|]` with `c_j(x) = 0.5*sum_{k!=j} J_jk x_k`, backgrounds from the natural arm's own final-bit distribution — a fully specified external prediction of |specification bias|, computable without looking at the estimate. Regress observed `|bias|_j` on `A_j(eps)` (slope = 1, intercept = 0, errors clustered by environment), then fit a random-slope model grouped by environment and test the eps x environment interaction. **Claim:** the eps-slope of specification bias varies across independent coupling draws by more than sampling error. Only an exact instrument can make that claim, it needs no new simulator, and it makes environment count the inferential unit.

**Concede explicitly:** (i) `naive = ATT + selection_bias` is Heckman 1979 ([10.2307/1912352](https://doi.org/10.2307/1912352)) — cite the identity, claim none of it; (ii) selection bias in mutation-accumulation effect estimation is already quantified against a known true DFE by Wahl & Agashe 2022 ([10.1111/evo.14430](https://doi.org/10.1111/evo.14430)) — our contribution is the instrument, not the correction; (iii) conditioning on mutation absence being wrong is published (Diaz-Uriarte et al. 2026, [arXiv:2606.12597](https://arxiv.org/abs/2606.12597)) — no "new do-operator application"; (iv) noise-free paired counterfactuals are published (Klein et al. 2024, [arXiv:2409.02086](https://arxiv.org/abs/2409.02086); Buffalo et al. 2026, [arXiv:2603.11084](https://arxiv.org/abs/2603.11084)) — our `do()` differs only by preserving the draw stream, argued against Buffalo, never asserted; (v) the landscape is quadratic by construction, so the bias is analytically available — never present it as an empirical discovery. **Skip** the AIPW/ICE estimator and threshold-calibration curve of `SCALE_DESIGN.md:135` in R3: robustness, not the claim.

## 3. Interdisciplinary transfer

| tool (field) | improves | exact quantity | what it would falsify | verdict |
|---|---|---|---|---|
| AIPW / debiased ML (econometrics): orthogonal score, cross-fitting, multiplier bootstrap over the eps grid | TEST 1 trend inference | psi_m(eps) = efficient influence function for ATT_m(eps); aggregate to a *simultaneous* band for `S(eps)` over all 9 eps | A band excluding a flat line kills the median-plateau objection; a band containing one falsifies `spec_bias_monotone` as an eps-trend claim | **Adopt.** Honest variance and it fixes the multiple-comparison problem the pointwise gate creates; one estimator family, no new simulator |
| Higher-order interaction analysis (statistical genetics / Walsh-Hadamard ANOVA of the fitness map) | TEST 1 and the order arm | squared norm of the order >= 3 Walsh coefficient vector, normalised by total variance | Order >= 3 coefficients ~ 0 means every "arrival order matters" statement collapses to a parameter-free function of the pairwise matrix `J` — the quantitative form of Sailer & Harms 2017 ([10.1371/journal.pcbi.1005541](https://doi.org/10.1371/journal.pcbi.1005541)) | **Adopt as a control only.** On a quadratic landscape these coefficients are exactly 0, so it validates that the order arm samples only pairwise structure |
| G-computation (biostatistics) | TEST 1 | model-based standardisation of the mutation effect | nothing the exact paired counterfactual does not already answer | **Reject.** The tape *is* the g-formula evaluated exactly; a fitted version is strictly dominated |
| Fluctuation theorems (statistical physics): Crooks/Jarzynski on the ledger | TEST 2 ledger audit | log-ratio of forward/reverse path probabilities; exponential-average free-energy estimator | "Ledger dissipation is a path-independent constant" | **Reject.** Needs a time-reversed arm that does not exist, targets TEST 2 not the monotonicity problem, degenerate on a deterministic reversible synthetic landscape |
| Transfer entropy (information theory) | TEST 1 order arm | TE(mutation at generation t -> fitness at t+k), conditioned on genotype | "Order effects are pairwise-only", with a directional non-parametric statistic | **Reject in favour of Walsh-Hadamard.** Costlier (full generation path plus history embedding), unvalidated null, weaker question than an exact coefficient |

## 4. What would make this a FINDING rather than a benchmark

Every number in `heavy1_results.json` comes from a fitness map we wrote down, so a reviewer will correctly call it self-consistency. The finding appears only when the exact instrument is aimed at the **`agent` substrate**, where no closed form exists (`harness.agent_outcome` is a 24-step world trace, not an equation) and the answer diverges: if the agent-substrate eps-dependence of specification bias is **not** recovered by `A_j(eps)`, we have measured the failure of the linear-additive model on a landscape nobody specified, per lineage, with no simulation noise to hide behind. The publishable sentence: *on an unspecified digital landscape the additive-estimator bias is a landscape-specific function of epistasis strength that the analytic pairwise prediction does not recover, and per-lineage exactness shows which lineages it fails on.* The mirror result is equally publishable and must be preregistered as such: if `A_j(eps)` **does** recover it, the honest paper is a methods paper whose only claim is the instrument plus the landscape-dependence interaction test.
