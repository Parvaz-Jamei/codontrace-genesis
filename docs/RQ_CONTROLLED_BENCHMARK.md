# Red Queen: controlled calibration and full-engine pilot

Base commit: `26996bd74d210375347ed60442e5b5d7633ef542`. Tested against `origin/main` at PR #104, version 0.3.0b13. This patch adds a module and tests; it does not rewrite published archives or alter default Genesis physics.

## Purpose and scope

A detector must pass a known positive control and reject a drift-only negative control before its output on Genesis can be trusted. The new command supplies these controls and a separate full-engine pilot.

**A positive reference result is not a positive full-engine result.** The reference obtains its four infection cells from real Genesis contact replay, then uses an explicit clonal Wright–Fisher demographic model. The full-engine pilot runs existing Genesis life loops, reproduction, mutation and parasite passages unchanged.

This is a calibration benchmark based on established theory, not a new biological discovery, a proof of the advantage of sex, or an exact reproduction of a cited paper.

## Reference model

Two types are encoded as opposite recognition windows `000000` and `111111`. Whole-type symmetric mutation in this reference is not Genesis per-bit mutation. Each species has 128 individuals, non-overlapping generations, initial type-one counts round(0.55N) and round(0.45N). Contact matrix A is measured from the engine before the run; each cell records debit, host ATP loss, parasite credit and measurement-freeze flags.

For host frequency h and parasite frequency p:

- Host infection pressure: a_i = sum_j A_ij P_j.
- Parasite opportunity: b_j = sum_i H_i A_ij.
- Host fitness: w_Hi = exp(-s_H a_i).
- Parasite fitness: w_Pj = exp(+s_P b_j).
- Type-one reproductive probability before mutation: q = f*w_1 / ((1-f)*w_0 + f*w_1).
- Symmetric mutation: q_mut = mu + (1-2mu)*q.
- New type-one census: Binomial(N, q_mut).

Defaults: s_H=s_P=0.6, mu=0.005, 300 generations, discard 30 burn-in generations. These are benchmark design constants, not fitted biological estimates. Fitness is a declared modelling assumption, not offspring fitness measured in the full Genesis engine. Engine energy is verified within each kernel assay, not propagated through reference-model generations.

Arms: reciprocal selection; neutral drift with both selection coefficients zero; host-selection cut; parasite-selection cut. Population size, mutation, generation budget and initial conditions match. Paired arms share predetermined random uniforms; histories and species have distinct SHA256-derived streams.

## Locked measurements

For each independent history:

- Host response coupling: mean of -pressure_gap * realized change in host type-one frequency.
- Parasite response coupling: mean of opportunity_gap * realized change in parasite type-one frequency.
- Completed frequency crossings use hysteresis bands 0.4/0.6. Wiggles around 0.5 do not count.
- Reciprocal crossing score is the minimum of host and parasite crossing counts.

Five paired contrasts are fixed: host vs neutral, parasite vs neutral, host vs host-cut, parasite vs parasite-cut, reciprocal crossings vs neutral. One lower confidence bound per history-level contrast uses a paired t calculation and Bonferroni alpha 0.05/5. Time points are not counted as independent replicates. Zero sample variance leaves inference unmeasurable, not infinitely certain.

The coupling lower bounds must exceed 0.0001; the crossing contrast must exceed zero. At least half the independent histories must have two completed crossings in both species. At least twelve histories are required for a supported reference verdict. These operational thresholds are benchmark acceptance conditions, not a universal definition of Red Queen dynamics. The t assumptions and small-history approximation should be checked before publication; no parameter search or optional stopping is performed.

A pass is labelled `SUPPORTED_REFERENCE_MODEL`; `full_engine_claim` and `red_queen_proved` remain false. The drift-only calibration must fail. Raw JSONL data, the pre-execution lock, real contact witnesses, live log, assessment, source hash and archive hashes are saved. Verification replays every reference generation, reruns real contact witnesses and recomputes the assessment; altered data fail verification.

## Commands

From the repository root in the project's normal Python environment:

```bash
python -m pytest -ra tests/test_rq_controlled_benchmark.py tests/test_rq_reciprocal_validity.py tests/test_rq_mechanism_v2_phase6.py tests/test_rq_mechanism_v2_phase5.py
python -m codontrace.genesis.rq_controlled_benchmark --output runs/rq-reference-new
python -m codontrace.genesis.rq_controlled_benchmark --verify-reference --output runs/rq-reference-new
```

Every new execution refuses an existing output directory. Verification uses the recorded lock and the same source implementation. A new implementation requires a new run; preserve the old artifacts.

A moderate-budget exploratory full-engine pilot:

```bash
python -m codontrace.genesis.rq_controlled_benchmark --engine-pilot --histories 12 --generations 100 --seed-start 10301 --max-seconds 1800 --output runs/rq-engine-new
```

The engine pilot is serial to avoid nested workers and oversubscription. It checks existing engine invariants every generation, compares incremental and one-shot runs, replays actual contact debit/credit and retains partial archives on failure. The watchdog writes health at startup and every ten minutes, then requests a cooperative stop when its fixed wall-time budget expires. A currently executing generation or one-shot check can finish after the deadline. Hardware-dependent execution time is not guaranteed. Treat an incomplete budget as blocked, not as a negative or a missing-data zero.

After a complete pilot, fixed past/present/future matrices are measured at centers 25/50/75, lag 5, with eight shuffled-roster contact assays per cell. The output includes each mean and roster standard deviation. This changed ensemble-seat estimand is a diagnostic; it is not the old single-roster confirmatory estimand. Diagnostic analysis runs after the evolution budget and has a fixed number of assays.

**The full-engine output is exploratory.** It does not automatically declare RQ: a matched full-engine neutral-drift intervention and genotype-specific offspring/survival selection witnesses are still needed. Existing frozen-composition controls are not neutral drift, even when their external energy intervention is accounted for. A single contemporary infectivity peak or reference-model success cannot supply those missing witnesses.

## Acceptance and follow-up

1. Apply only to the exact base using the guarded installer, on a clean worktree.
2. Run tests, positive reference, reference verification and drift-only test. Keep all raw data.
3. Run the full-engine pilot once with the fixed budget. Inspect stopping reasons and replay results first.
4. Examine reproduction, genotype-specific survival/offspring success, seating noise, polymorphism and fixation. Implement a matched neutral-drift control as a separately documented scientific intervention before confirmatory claims.
5. Use pilot data to choose an adequate horizon and primary mechanistic criteria, lock them, then run fresh independent seeds. Do not extend or tune repeatedly until a positive result occurs.

## Primary sources

- Engelstädter & Bonhoeffer (2009), *PLOS Computational Biology*, DOI 10.1371/journal.pcbi.1000469. Antagonistic genotype interactions and fluctuating dynamics; interaction assumptions matter. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000469
- Papkou et al. (2019), *PNAS*, DOI 10.1073/pnas.1810402116. Reciprocal time-shift experiments and different selective processes on hosts/pathogens. https://www.pnas.org/doi/10.1073/pnas.1810402116
- Buckingham & Ashby, *Coevolutionary theory of hosts and parasites*, *Journal of Evolutionary Biology* 35:205–224 (2022), DOI 10.1111/jeb.13981. Alternative coevolutionary outcomes and assumptions. https://academic.oup.com/jeb/article/35/2/205/7317917

The benchmark is inspired by these mechanisms; demographic and fitness choices above are explicit additions, not claims of exact published parameter replication.
