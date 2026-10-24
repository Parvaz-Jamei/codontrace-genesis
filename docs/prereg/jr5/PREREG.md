# JR5 preregistration: cost of sex and parasite-mediated maintenance of outcrossing

Status: locked at phase 1. Nothing has been run for JR5. Base commit 66f57a5.
Machine-readable constants: `jr5_prereg_constants.json`. File hashes: `record.json`, written by `python -m codontrace.preregistration hash`.
If this text and the JSON disagree, the JSON wins.

## 1. Question

When the cost of sex is paid through the production of sons, what does it cost in this engine, and does a coevolving parasite stop a uniparental mutant from invading an outcrossing host? Parasite-mediated coevolution is one candidate explanation. Mutation load and parasite-driven diversity without cycling are tested alongside it on the same footing.

## 2. Typed outcomes

The analysis returns exactly one of these. Each has a decision rule, and all are fixed now.

- `instrument_fail`: the E1 gate fails at either sex ratio, or a validity check in section 8 fails. Nothing else is scored.
- `rq_consistent`: E2 is significant at the high-virulence level after Holm correction, with copassaged lower than fixed. It must also show all of the following:
  - the uniform-tax arm does not reproduce the effect (its paired difference CI includes 0 or has the opposite sign);
  - the frozen-replay arm differs from copassaged in the same direction;
  - at least one registered time-shift window shows a host or parasite effect whose CI excludes 0.
- `diversity_without_rqd`: E2 is significant in the same direction, and the frozen-replay arm matches copassaged (paired CI includes 0), or the time-shift effects are all null.
- `load_consistent`: E2 is not significant, but in the no-parasite mutation-load arms obligate outcrossers beat obligate selfers. Specifically, the extinction or terminal-fitness contrast at the highest mutation rate has a CI excluding 0 and grows across the mutation grid (Spearman rho > 0, one-sided p < 0.05).
- `none`: none of the above.

The default ceiling is `runtime_observation`. `red_queen_proved` is no longer banned for good. There is one evidence-gated path, set out in `RED_QUEEN_CLAIM_PATH.md`: the flag is `True` only when conditions (a) to (e) there all hold, and otherwise the typed outcome above applies. Every existing diagnostics adapter keeps its refusal. The analysis code must have a test that plants each outcome in synthetic data and recovers it.

## 3. Endpoints

**E1, realised cost of sex (gate).**
- Setup: no parasite, obligate outcross plus an asexual (or obligately selfing) founder fraction of 0.2.
- Estimator, per population: the OLS slope of logit(uniparental frequency) on generation over generations 0-10, exponentiated. This is the per-generation odds ratio.
- Replicate unit: the population (one seed). 40 populations per sex ratio at N = 200.
- Interval: a one-sample t interval on the log scale, back-transformed.
- Test: TOST at alpha 0.05, that is a 90% interval.
  - Sex ratio 0.5: the interval must lie inside [1.8, 2.2].
  - Sex ratio 0.25: the interval must lie inside [1.2, 1.4667], which is ±10% of 1/(1−0.25) = 1.3333.
  - In both cases the 95% interval must also exclude 1.
- Failure at either sex ratio stops JR5 at phase 3.

**E2, invasion (primary).**
- Setup: obligate outcross residents, uniparental mutant introduced at 0.2.
- Value per seed: terminal uniparental frequency at the horizon.
- Contrast: copassaged minus fixed, paired by seed, one test per virulence level.
- Tests: paired two-sided t test, with a paired bootstrap check (10,000 draws, bootstrap seed 12345).
- Effect sizes: risk difference of persistence (frequency at least 0.05) and Hedges g_av.
- Multiplicity: Holm across four E2 tests (N = 200 and N = 50, each at high and low virulence) at family alpha 0.05. E1 is a gate, not a claim, so it is not in the Holm family.

**Secondary, all exploratory unless named here.**
- E3: the largest cost ratio, set by sex ratio, at which outcrossing persists.
- E4: the time-shift estimand and horizon rule from RQ-v2 phase 6 (`runs/rq-mechanism-v2/PHASE6_CONFIRM_LOCK.md`).
- E5: extinction of obligate selfers versus obligate outcrossers under copassage.
- Also reported: infection prevalence, nearest parasite-host Hamming distance and realised sex ratio.

## 4. Arms

- Host N: 200 primary, 50 sensitivity. N = 10 appears only in reused lock baselines and is labelled drift-dominated.
- Parasite: none, heat-killed, fixed (low, high), copassaged (low, high), frozen replay of a coevolved archive (low, high).
- Host mating: obligate outcross, mixed (invasion), obligate self, asexual.
- Alternatives:
  - Mutation load: no parasite, host mutation in {0, 0.01, 0.05}, obligate outcross versus obligate self, at N = 200 and N = 50.
  - Uniform genotype-blind tax matched to infection cost.
  - Recombination off.
  - Migration on.
  - Sex ratio 0.25 on the fixed-high and copassaged-high contrast.

Full grid sizes are in the JSON.

## 5. Seeds

- Confirmatory: 11001-11060, the same vector in every cell.
- E1 calibration: 11101-11180.
- Pilot: 11901-11930. Pilot numbers are never confirmatory.
- Sealed and never used: 101-108, 201-208, 301-308, 401-408, 501-508, 8000-8199, 9300-9899, and the timing seeds 90001-90003.
- A killed run is re-run on the same seed. It is never replaced.

## 6. Horizon

H = max(100, ceil(max(host replacement, parasite replacement, fitness delay))), measured in the phase 4 pilot with the RQ-v2 phase 6 method. The cap is 200. If H would exceed the cap, the design is refused. It is not shortened.

## 7. Power and budget

**Timings.** Measured at 66f57a5 with the closest existing harness: `LifeLoopEcologyArm` using the selfing-hold constants, soft carrying capacity = N, 16 generations, 4 concurrent jobs on 8 cores.
- N = 200: 0.44-0.45 s per generation, census 188-200.
- N = 50: 0.09-0.12 s per generation.
- N = 10: 0.03 s per generation.
- When soft K was left at 3.2N (census about 600), N = 200 took 2.7-3.0 s per generation under 12-job contention. That setting is not used.

**Power for E1.** Simulated: Wright-Fisher, cost from son allocation, 10 generations, 4,000 replicates.
- The SD of the log estimator is 0.079 at N = 200 and 0.167 at N = 50.
- 90% TOST power needs 9 populations at N = 200 and 35 at N = 50.
- 40 per sex ratio covers engine noise up to the N = 50 level.

**Power for E2.** Paired two-sided t at alpha 0.0125 (the first Holm step of four), 80% power:
- difference 0.25, SD 0.30: 20 seeds;
- difference 0.15, SD 0.30: 48 seeds;
- difference 0.10, SD 0.25: 73 seeds.
- 60 seeds per cell are used, so a difference of 0.10 is below the detectable size at this level. A null result is reported with its interval, not as evidence of absence.

**Budget.**
- 3,520 runs at H = 100.
- About 35 CPU-hours at the measured rates, 53 with a 1.5× allowance for the new sex code.
- About 9 hours wall time on 6 workers.
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
