# JR5 preregistration: cost of sex and parasite-mediated maintenance of outcrossing

Status: locked at phase 1. Nothing has been run for JR5. Base commit 66f57a5.
Machine-readable constants: `jr5_prereg_constants.json`. File hashes: `record.json`, written by `python -m codontrace.preregistration hash`.
If this text and the JSON disagree, the JSON wins.

## 1. Question

When the cost of sex is paid through the production of sons, what does it cost in this engine, and does a coevolving parasite stop a uniparental mutant from invading an outcrossing host? Parasite-mediated coevolution is one candidate explanation. Mutation load and parasite-driven diversity without cycling are tested alongside it on the same footing.

## 2. Typed outcomes

The analysis returns exactly one of these. Each has a decision rule, and all are fixed now.

- `instrument_fail`: the E1 gate fails at either sex ratio, more than the exclusion cap of E1 populations is excluded (section 3), or a validity check in section 8 fails. Nothing else is scored.
- `inconclusive`: for any test that the outcome below depends on, the paired t test and the BCa bootstrap interval (section 3) disagree, that is one is significant and the other is not, or they point in opposite directions.
- `rq_consistent`: E2 is significant at the high-virulence level after Holm correction at N = 200 and also at N = 50 (both tests, as in condition (b) of `RED_QUEEN_CLAIM_PATH.md`), with copassaged lower than fixed. It must also show all of the following:
  - the uniform-tax arm is shown not to reproduce the effect by the equivalence rule of condition (d);
  - the frozen-replay arm differs from copassaged in the same direction;
  - at least one registered time-shift window shows a host or parasite effect whose CI excludes 0.
- `diversity_without_rqd`: E2 is significant in the same direction, and either the frozen-replay arm matches copassaged (copassaged-minus-frozen 90% interval inside ±0.10), or no registered time-shift window has a 95% interval excluding 0.
- `load_consistent`: E2 is not significant, but in the no-parasite mutation-load arms obligate outcrossers beat obligate selfers. Specifically, at N = 200 the log terminal-fitness ratio (outcross over self) at host mutation 0.05 has a 95% interval above 0 and grows across the mutation grid (Spearman rho > 0, one-sided p < 0.05, over the 3 × 60 seed values).
- `none`: none of the above.

The default ceiling is `runtime_observation`. `red_queen_proved` is no longer banned for good. There is one evidence-gated path, set out in `RED_QUEEN_CLAIM_PATH.md`: the flag is `True` only when conditions (a) to (e) there all hold, and otherwise the typed outcome above applies. Every existing diagnostics adapter keeps its refusal. The analysis code must have a test that plants each outcome in synthetic data and recovers it.

## 3. Endpoints

**E1, realised cost of sex (gate).**
- Sex ratio means the male fraction m of offspring born to outcrossing parents. The all-female asexual line then has a per-generation advantage of 1/(1 − m): 2.0 at m = 0.5 and 1.3333 at m = 0.25.
- Setup: no parasite, obligate outcross plus an all-female asexual founder fraction of 0.2. Selfers are not used in E1; their expected advantage is not 1/(1 − m), so they have no bound here.
- Estimator, per population: a bias-reduced binomial GLM (the likelihood penalised by half the log determinant of the Fisher information, which removes the first-order bias of the slope) with logit link, the asexual count out of the census at each generation as the response and generation as the only predictor, fitted over all generations 0 to T. exp(slope) is the per-generation odds ratio.
- Overdispersion: drift makes counts in successive generations correlated and more variable than binomial. A quasi-binomial fit gives the same slope and only rescales its standard error. The per-population standard error is not used, because the interval is taken across populations, so no dispersion term is added.
- Horizon T: 5 generations at m = 0.5 and 11 at m = 0.25. These keep the expected asexual frequency below 0.95 even at the upper margin bound (calculation below).
- Fixation and loss:
  - generations after fixation or loss stay in the fit, since the GLM handles counts of 0 and N;
  - a population that fixes (asexual count = census) before generation 3 is excluded and counted;
  - exclusion cap: at most 20% of the populations in a cell (8 of 40). Above the cap, E1 is an instrument failure;
  - fixed and lost populations are reported separately, with their counts, next to the estimate.
- Replicate unit: the population (one seed). 40 populations per sex ratio at N = 200. The same seeds are also run at N = 50, which is reported but is not part of the gate.
- Interval: a one-sample t interval on the log scale over populations, back-transformed.
- Test: TOST at alpha 0.05, that is a 90% interval.
  - Sex ratio 0.5: the interval must lie inside [1.8, 2.2].
  - Sex ratio 0.25: the interval must lie inside [1.2, 1.4667], which is ±10% of 1/(1−0.25) = 1.3333.
  - The margin is ±10% on the linear scale. On the log scale, where the interval is built, it is −0.1054 / +0.0953 at both ratios, so slightly wider on the low side.
  - In both cases the two-sided 95% interval (same t method) must also exclude 1.
- Failure at either sex ratio stops JR5 at phase 3.

Horizon calculation. Under a constant odds ratio w, logit p(t) = logit(0.2) + t·log w, with logit(0.2) = −1.3863 and logit(0.95) = 2.9444. So p(t) < 0.95 needs t < 4.3307 / log w.
- m = 0.5, upper bound w = 2.2: log w = 0.7885, t < 5.49, so T = 5 (p(5) = 0.928; p(6) would be 0.966).
- m = 0.25, upper bound w = 1.4667: log w = 0.3830, t < 11.31, so T = 11 (p(11) = 0.944; p(12) would be 0.961).
- At the theory values, p(5) = 0.889 at m = 0.5 and p(11) = 0.855 at m = 0.25.

**E2, invasion (primary).**
- Setup: obligate outcross residents, uniparental mutant introduced at 0.2.
- Value per seed: terminal uniparental frequency at the horizon.
- Contrast: copassaged minus fixed, paired by seed, one test per virulence level.
- Tests: paired two-sided t test, and a paired BCa bootstrap interval (10,000 resamples of seeds, bootstrap seed 12345) at the matching level.
- Matching level: the BCa interval for a test is taken at 1 minus the Holm-adjusted alpha of that test's step, that is 0.05/(5 − k) at step k = 1 to 4. So 98.75% at step 1, 98.333% at step 2, 97.5% at step 3 and 95% at step 4.
- Agreement rule: a test counts as significant only when the t test and the BCa interval are both significant in the same direction. If one is significant and the other is not, or they point in opposite directions, that test is inconclusive and the outcome is `inconclusive`.
- Effect sizes: risk difference of persistence (frequency at least 0.05) and Hedges g_av.
- Multiplicity: Holm across four E2 tests (N = 200 and N = 50, each at high and low virulence) at family alpha 0.05. E1 is a gate, not a claim, so it is not in the Holm family.

**Secondary, all exploratory unless named here.**
- E3: the largest cost ratio, set by sex ratio, at which outcrossing persists.
- E4: the time-shift estimand and horizon rule from RQ-v2 phase 6 (`runs/rq-mechanism-v2/PHASE6_CONFIRM_LOCK.md`).
- E5: extinction of obligate selfers versus obligate outcrossers under copassage.
- Also reported: infection prevalence, nearest parasite-host Hamming distance and realised sex ratio.

## 4. Arms

- Host N: 200 primary, 50 sensitivity. Every arm below runs at both. N = 10 appears only in reused lock baselines and is labelled drift-dominated.
- Parasite: none, heat-killed, fixed (low, high), copassaged (low, high), frozen replay of a coevolved archive (low, high).
- Host mating: obligate outcross, mixed (invasion), obligate self, asexual.
- Alternatives:
  - Mutation load: no parasite, host mutation in {0, 0.01, 0.05}, obligate outcross versus obligate self, at N = 200 and N = 50, 60 seeds per cell.
  - Uniform genotype-blind tax matched to infection cost.
  - Recombination off.
  - Migration on.
  - Sex ratio 0.25 on the fixed-high and copassaged-high contrast.

Grid (cells × seeds), also in the JSON under `grid`:
- E1: 2 sex ratios × 2 host N × 40 = 160.
- E2: mixed invasion × 8 parasite arms × 2 host N × 60 = 960.
- E5: obligate outcross and obligate self × {fixed, copassaged} × {low, high} × 2 host N × 60 = 960.
- Mutation load: 3 mutation rates × 2 matings × 2 host N × 60 = 720.
- Uniform tax, recombination off, migration on: 3 × 2 virulence levels × 2 host N × 60 = 720.
- Sex ratio 0.25: 2 parasite arms × 2 host N × 60 = 240.
- Total 3,760 runs. The earlier 3,520 used 40 mutation-load seeds; raising them to 60 adds 240.

## 5. Seeds

| Block | Range | Use |
|---|---|---|
| Confirmatory | `13001–13060` | the same 60-seed vector in every E2, E5 and alternative cell |
| E1 calibration | `13101–13180` | m = 0.5 uses 13101-13140, m = 0.25 uses 13141-13180, at both host N |
| Pilot | `13901–13930` | horizon and timing only; never confirmatory |

- No confirmatory arm uses a subset of the vector. E1 is the only 40-seed design.
- Sealed and never used: 101-108, 201-208, 301-308, 401-408, 501-508, 601-603, 701-708, 751-758, 801-816, 1000-1009, 1000-1299, 2000-2009, 3100-3107, 4100-4107, 8000-8199, 9201-9224, 9300-9899, 9901-9922, 0-149, the timing seeds 90001-90003, and the blocks reserved by `docs/campaigns/rq_redesign_20260928/PREREG_V2.md`: 9001-9120, 10001-10576, 11001-11384 and 12001-12240.
- A test parses the seed lines of every `docs/**/*PREREG*.md` and fails on any overlap between preregistrations.
- A killed run is re-run on the same seed. It is never replaced.

## 6. Horizon

H = max(100, ceil(max(host replacement, parasite replacement, fitness delay))), measured in the phase 4 pilot with the RQ-v2 phase 6 method. The cap is 200. If H would exceed the cap, the design is refused. It is not shortened.

## 7. Power and budget

**Timings.** Measured at 66f57a5 with the closest existing harness: `LifeLoopEcologyArm` using the selfing-hold constants, soft carrying capacity = N, 16 generations, 4 concurrent jobs on 8 cores.
- N = 200: 0.44-0.45 s per generation, census 188-200.
- N = 50: 0.09-0.12 s per generation.
- N = 10: 0.03 s per generation.
- When soft K was left at 3.2N (census about 600), N = 200 took 2.7-3.0 s per generation under 12-job contention. That setting is not used.

**Power for E1.** Simulated with the estimator above. Assumptions: Wright-Fisher sampling of N each generation, a constant odds ratio, founder frequency 0.2, horizons T = 5 and 11, the early-fixation exclusion applied, and TOST on log bounds with n − 1 degrees of freedom.
- First pass (plain binomial fit, 4,000 populations per setting, true value at the theory value): SD of the log estimator 0.077 (m = 0.5) and 0.050 (m = 0.25) at N = 200; 0.165 and 0.128 at N = 50. An independent re-run at N = 50, m = 0.25 gave 0.127. 90% TOST power needs 9 and 5 populations at N = 200, and 32 and 20 at N = 50.
- No population fixed before generation 3 in any setting. At N = 50, 3.4% (m = 0.5) and 7.6% (m = 0.25) fixed later and stay in the fit; 0.3% were lost at N = 50, m = 0.25.
- The planning figure stays at 35 for N = 50, which is conservative against 32. 40 per sex ratio covers engine noise up to the N = 50 level.

**Slope bias.** The plain binomial slope is biased upward. Mean bias of the log estimator at the theory value (4,000 populations):
- m = 0.5: +0.0020 at N = 200, +0.0158 at N = 50 (17% of the +0.0953 margin);
- m = 0.25: +0.0020 at N = 200, +0.0027 at N = 50.

The bias-reduced fit removes the first-order bias of the maximum likelihood slope, so it is used instead of subtracting a simulated bias. Its mean bias (2,000 populations) is +0.0022 and +0.0047 at m = 0.5 (N = 200, 50), and +0.0012 and +0.0044 at m = 0.25. Its SDs are 0.075 and 0.153 at m = 0.5, and 0.051 and 0.126 at m = 0.25. Normal-approximation n for 90% power is 8, 27, 5 and 19, all at or below the first-pass figures.

TOST pass rate with 40 populations (pass at a bound is the type I error, nominal 0.05):

| m | N | true w | plain fit | bias-reduced fit |
|---|---|---|---|---|
| 0.5 | 200 | 2.0 / 1.8 / 2.2 | 1.000 / 0.095 / 0.016 | 1.000 / 0.056 / 0.028 |
| 0.5 | 50 | 2.0 / 1.8 / 2.2 | 0.909 / 0.088 / 0.012 | 0.965 / 0.047 / 0.021 |
| 0.25 | 200 | 1.3333 / 1.2 / 1.4667 | 1.000 / 0.024 / 0.016 | 1.000 / 0.037 / 0.016 |
| 0.25 | 50 | 1.3333 / 1.2 / 1.4667 | 0.997 / 0.009 / 0.012 | 0.988 / 0.012 / 0.008 |

The plain fit passes too often at the lower bound for m = 0.5 (0.095 at N = 200), so the bias-reduced fit is the preregistered estimator. The 0.056 at N = 200 is within Monte Carlo error of 0.05 (about ±0.007 at 4,000 draws).

**Power for E2.** Paired two-sided t at alpha 0.0125 (the first Holm step of four), 80% power:
- difference 0.25, SD 0.30: 20 seeds;
- difference 0.15, SD 0.30: 48 seeds;
- difference 0.10, SD 0.25: 73 seeds.
- 60 seeds per cell are used, so a difference of 0.10 is below the detectable size at this level. A null result is reported with its interval, not as evidence of absence.

**Minimum detectable effect and equivalence for the alternatives.** At 60 paired seeds, two-sided alpha 0.05 and 80% power, the MDE is 0.368 SD of the paired difference: 0.092 at SD 0.25 and 0.110 at SD 0.30. Equivalence (TOST, 90% interval inside ±0.10) has power 0.97 at SD 0.20, 0.84 at SD 0.25 and 0.64 at SD 0.30 when the true difference is 0. Mutation load was raised from 40 to 60 seeds for this; at 40 the power at SD 0.25 was 0.60.

**Budget.**
- 3,760 runs, all but E1 at H = 100: 1,800 at N = 200 and 1,800 at N = 50, plus 160 short E1 runs.
- At 0.45 s and 0.10 s per generation: 22.5 + 5.0 + 0.1 = 27.6 CPU-hours, 41.4 with a 1.5× allowance for the new sex code.
- About 6.9 hours wall time on 6 workers.
- The earlier figure of 35 CPU-hours could not be rebuilt from a stated grid. It is replaced by this one, which is rebuilt by a test.
- If the pilot rate exceeds the allowance, the seed count is not cut. The run is scheduled longer.

## 8. Validity checks

- ATP ledger residual at most 1e-9 on every run.
- One-shot and resumed runs give identical scientific bodies.
- With the flag off, every sealed lock replays byte-identically.
- No verdict literal appears in the analysis code. The planted-outcome test from section 2 must pass.
- The realised E1 cost is reported next to every maintenance statement.

## 9. Reused locked results

Each is re-verified by hash at run time.

**Selfing-hold** (`docs/handoff/CLOSED_LOOP_HP_ARM01_SELFING_HOLD_RESULTS_20260926.md`):
- design digest `762e778b…a6fd298`, campaign digest `73e6a528…aa94e6`;
- invasion_fail 8/8;
- N = 10, drift-dominated.

**Mating ledger:**
- design digest `f4475f69…32d80dd`, campaign digest `72f59eff…0f5`;
- selfing_nonviable 8/8.

**RQ-v2 phase 6** (`runs/rq-mechanism-v2/phase6-coevolution/summary.json`):
- `summary_sha256` 948413a3…; the file's byte sha is dec7e432…; see `SUMMARY_SHA256_NOTE.md`;
- E4 estimand and horizon rule are reused.

**Cost sweep** (`docs/experiments/2026-09-29/sex_cost/`):
- raw.jsonl.gz sha af1b447a…;
- prior only, not evidence.

## 10. Phases

- **1.** This preregistration.
- **2a.** Mating-type trait plus heritable mating policy, built on `mating_types_enabled` (see `MATING_TYPES_DESIGN_NOTE.md`). All digests and old lock replays must be byte-identical with the flag off. Its own PR and review.
- **2b.** Son production charged in the ATP ledger, plus census streams. Its own PR and review.
- **2c.** JR5 verdict adapter in claimgate, the only path that can set `red_queen_proved`. It has its own PR and review, with the tests listed in `RED_QUEEN_CLAIM_PATH.md`.
- **3.** E1 gate.
- **4.** Pilot on pilot seeds: horizon and timing only.
- **5.** Confirmatory E2 and E5 factorial.
- **6.** Alternative arms, E3 strip and E4.
- **7.** Analysis, claimgate audit, replay digests and report.

## 11. Analysis plan

- The analysis script is committed and hashed before phase 5 starts.
- It reads only the raw per-seed records.
- Every interval is reported, whether or not it is significant.
- Exploratory results are labelled exploratory.

## 12. Deviations

- Any change after this lock goes in `DEVIATIONS.md` in this folder before the affected run starts, with the reason and the new record digest.
- A deviation made after seeing confirmatory data moves the affected endpoint to exploratory.
- Thresholds, seeds, margins and alpha do not change after phase 3 starts.

References: `REFERENCES.md`.
