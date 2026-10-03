# Phase 3 diagnostic frequency panel

Branch `rq/mechanism-v2`. Nothing was pushed, merged, or rewritten. `runs/rq-bidirectional-timeshift-01` was not modified and was not committed. `red_queen_proved` is false. Red Queen was not declared. A positive D is not Red Queen.

## Commits

- Panel code, before the selection probe and before any measurement history: `9a50ca2daca7da3c420dcff551f6e9c4531d58f7`
- Lock, also before any measurement history: `c3fbed3fabb1615d025d95d0343def7e29ce813a`
- The four histories ran with `HEAD` at the lock commit. This note and the archives are a later commit. The lock commit is an ancestor of that commit.

`c3fbed3fabb1615d025d95d0343def7e29ce813a` is a descendant of `9a50ca2daca7da3c420dcff551f6e9c4531d58f7`.

The lock file's first sentence, in that commit, is: "No measurement D has been computed." `git log -1 --format='%H %s' c3fbed3fabb1615d025d95d0343def7e29ce813a` is `c3fbed3fabb1615d025d95d0343def7e29ce813a Lock phase-3 genotypes, horizon, and seeds.` The lock commit message repeats that no measurement D has been computed. The lock text contains no `D=` result.

## Locked settings

From `runs/rq-mechanism-v2/PHASE3_LOCK.md`, not changed after the measurement:

- Output: `runs/rq-mechanism-v2/phase3-frequency/`
- Seeds: 9501, 9502, 9503, 9504
- Selection seed 9500 was not reused as a history
- Forbidden and not used: 9099, 9101-9104, 9201-9224, 9301-9304, 9401, structural pilot seeds 601, 602, 603
- Horizon: 7 generations
- Workers: 4
- Importance is undeclared. SUPPORTED is forbidden. The minimum detectable effect is not the importance bound
- `MEASUREMENT_FLOOR` stays 12 and was not lowered
- `red_queen_proved` false

## Why these two genomes

The choice is from seed 9500, recorded in `runs/rq-mechanism-v2/phase3-selection/selection.json`, not from measurement D.

The selection scored all 120 unordered pairs of the 16 structural recognition windows with `infectivity` / `replay_archived_contact`: one parasite whose window equals the first host, one host of each window, birth ATP. The largest engine gap was 1.0. Complementary pairs tied. Lexicographic order selects window A `000000` and window B `111111`.

- Exemplar id A: `host-A-001`
- Exemplar id B: `host-B-001`
- Genome A: `101111000100000001000000`
- Genome B: `101111000100000001111111`
- Shared prefix: `101111000100000001` (program, quiet kappa codon, outcross codon `001`)
- Outcross cost on both tapes: 1.0
- The last 6 bits are the only difference

Census is 60 because 64 is not divisible by 5. An exact 80/20 mix is 48 and 12, and every parasite is seated. When A is common, index modulo 5 equal to 4 is B. Virulence, steal fraction, mutation rate, maintenance, and birth ATP were not retuned.

## Why seven generations

One parasite generation is one `advance` inside one engine generation. The 9500 probe held the 80/20 mix for the pre-declared 24 generations. Mean seated newborns were 26 on a census of 60, so one replacement time is 60/26 = 2.3076923076923075 generations. The multiple 3 was in the code before the probe. The horizon is the ceiling of 3 times that replacement time, which is 7. Every probe generation had contacts above 0, and the host mix stayed 48/12. The horizon was not moved after a sign.

## Code changes

### Host-composition hold

Prediction. During conditioning the contacted host multiset stays at the locked 48/12 mix. The hold is not a reward for a parasite being common.

Engine path. `StructuralRQArm.host_composition_hold`, default `None`. When set, `run_generations` calls it before the life-loop step and again after that step, immediately before `_apply_hp_env_contact`. The hold builds `GenesisOrganism.from_bits` on the locked tapes at `STRUCT_BIRTH_ATP` and does not call parasite `advance`. Passage still runs through `_passage_update` and `AntagonistPopulation.advance`. Income is `EnergyAccount.contact_income` only. `reproduction_cost` stays 0 and the residual stays closed. There is no frequency-bonus field.

Control. With the hold unset, existing arms are unchanged. With the hold set, two generations on seed 9490 kept 48 of `000000` and 12 of `111111` at contact. A source scan rejects `be_common`, `frequency_reward`, `common_bonus`, and `host_frequency_score`.

Source. The seat rule and the debit are the structural engine. Zaman et al. 2014, as already read in `PHASE1.md` (PMC4267771), is why a frozen genotype is not called coevolution. Decaestecker et al. 2007, as already read there, is why the score itself does not evolve. Hall et al. 2011 full text was not read and is not a fitted model.

Limit. Reinstalling hosts each generation stops host death from changing the mix. It also resets host ATP to the birth reserve before contact. That is a measurement hold, not a new contact rule. It does not delete the host population.

Estimand. D is the specialization shift of the parasite, not a host-frequency drift. A constant A-versus-B gap still cancels inside D.

### Assay, D, and the locked-seed gate

Prediction. I is the engine infectivity on a copy. Empty or missing input is null, not zero. An incomplete locked list is `BLOCKED_MEASUREMENT`, not a negative on the seeds that remain. A complete sample cannot be SUPPORTED while importance is undeclared.

Engine path. After the archive is closed, `assay_archive` reads the last parasite list and calls `infectivity`, which calls `replay_archived_contact` with evolution, reproduction, and mutation off and with birth ATP. The archive bytes are compared before and after. D is `(I(A, P_commonA) - I(B, P_commonA)) - (I(A, P_commonB) - I(B, P_commonB))`. The locked branch's `I(A) - I(B)` is `control_gap`. It is not written into D. `assess_phase3` refuses a lowered `MEASUREMENT_FLOOR`.

Control. Hand values 0.80, 0.20, 0.30, 0.70 give D = 1.0 by the same arithmetic, computed in the test rather than copied from a run. `None` stays `None` and is not equal to 0. A missing 9504 with three negative D values is `BLOCKED_MEASUREMENT`, `n_locked` 4, `n_used` 3, `dropped_seeds` [9504], and `D_mean` is null rather than the mean of the three or the mean after imputing 0. Four D values of 1.0 are `NOT_DECLARED`, not `SUPPORTED_IN_MODEL`. The frozen branch on both mixes, seed 9490, three generations, keeps the founder window multiset and records 0 mutation events.

Source. The replay path is the phase-1 assay. The incomplete-list rule is the same gate idea as phase 1, applied to this estimand. Importance stays undeclared because this repository has no pre-declared importance bound for this D.

Limit. `MEASUREMENT_FLOOR` remains 12 and is not this panel's sample size. n = 4 is not support. The locked branch was conditioned on 80% A, not also on 80% B. Its assay depends on windows, and the frozen passage kept mutation at 0. A third host frequency was not added.

Estimand. Unmeasurable histories are dropped. They are not zeros. The control gap is not D.

## Run

Four seeds, three branches, 7 generations, 4 workers. No history failed. No `REASON.txt`. No partial archive. Every seed has `COMPLETE` with `generations=7 red_queen_proved=false`. Each archive has generations 1 through 7. Assay SHA-256 matches the archive bytes, so the assay did not modify the conditioning files. About 636 KB under `phase3-frequency/`. Raw archives were kept.

Contact mixes in the archives stayed 48/12. Evolving branches used passage `coevolve`. The locked branch used passage `frozen`, with 0 mutation events on every locked history. Seated newborn counts on the locked branch were not zero; the genotype multiset is what the frozen passage reseats, and mutation stayed 0.

## D and the non-evolving control

Numbers are the ones in `runs/rq-mechanism-v2/phase3-frequency/summary.json`.

| Seed | D | I(A, common A) | I(B, common A) | I(A, common B) | I(B, common B) | I(A, locked) | I(B, locked) | control gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9501 | 1.4055555555555554 | 0.8583333333333334 | 0.14166666666666666 | 0.15555555555555556 | 0.8444444444444443 | 0.5222222222222223 | 0.4777777777777778 | 0.04444444444444445 |
| 9502 | 1.6055555555555552 | 0.8833333333333332 | 0.11666666666666665 | 0.08055555555555556 | 0.9194444444444444 | 0.5222222222222223 | 0.4777777777777778 | 0.04444444444444445 |
| 9503 | 1.6222222222222222 | 0.9083333333333332 | 0.09166666666666667 | 0.09722222222222221 | 0.9027777777777778 | 0.5222222222222223 | 0.4777777777777778 | 0.04444444444444445 |
| 9504 | 1.4555555555555557 | 0.7944444444444444 | 0.20555555555555555 | 0.06666666666666667 | 0.9333333333333335 | 0.5222222222222223 | 0.4777777777777778 | 0.04444444444444445 |

`n_locked` = 4. `n_used` = 4. `dropped_seeds` = []. `D_mean` = 1.5222222222222221. Verdict `NOT_DECLARED`. `importance_bound` is null. `supported_forbidden` is true. `measurement_floor` is 12. `measurement_floor_lowered` is false. `red_queen_proved` is false. `red_queen_declared` is false.

The control gap is the same on every seed because the locked parasites are the shared founder windows. It is not substituted for D. A positive D here means the host-frequency treatment shifted the parasite's relative specialization in this panel. It does not declare Red Queen.

## Tests

Not stacked with pytest-xdist. Workers inside the validity file stay at 4, and the new file does not open a pool.

```
/tmp/ct-tools/bin/python -m pytest \
  tests/test_rq_mechanism_v2_phase3.py \
  tests/test_rq_mechanism_v2_validity.py \
  -o addopts='--disable-plugin-autoload --import-mode=importlib' \
  --tb=line -q
```

20 passed in 5.41s.

Ruff, on the touched files:

```
/tmp/ct-tools/bin/ruff check \
  src/codontrace/genesis/rq_mechanism_v2_phase3.py \
  src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py \
  tests/test_rq_mechanism_v2_phase3.py
```

All checks passed.

## What was not run

No fitness link. No full coevolution beyond this panel. No new confirmatory. No later phase. No Red Queen claim. Seeds, the horizon, virulence, steal fraction, mutation rate, maintenance, birth ATP, and `MEASUREMENT_FLOOR` were not changed after D. Hall et al. 2011 full text was not read.

## Worker cap after the run

The four histories above ran with 4 workers. That execution was not repeated. After it had finished, the protocol cap was corrected from 4 to 7 (all cores on this machine minus one). `MAX_WORKERS` in `rq_mechanism_v2_phase3.py` is now 7, and `resolve_workers(7)` is accepted. `resolve_workers(8)` is still rejected. Phase 2 and the older confirmatory module still cap at 4 and were not edited. `PHASE3_LOCK.md` still says 4 because that was the cap in force for this measurement. The raw archives were kept.
