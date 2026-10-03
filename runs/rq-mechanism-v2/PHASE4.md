# Phase 4 fitness link

Branch `rq/mechanism-v2`. Nothing was pushed, merged, or rewritten. `runs/rq-bidirectional-timeshift-01` was not modified and was not committed. `red_queen_proved` is false. Red Queen was not declared. A positive fitness link is not Red Queen. The result below is not called Red Queen.

## Commits

- Fitness-link code, before any phase-4 history: `f7f6da4a45964c552673f31eb1961860185f212b`
- Lock, also before any phase-4 history: `86f40c6bb200f89b22f650d051becce0f7741483`
- The four histories ran with `HEAD` at the lock commit. This note and the archives are a later commit. The lock commit is a descendant of the code commit and an ancestor of this note.

The lock file's sentence, in that commit, is: "No fitness number has been computed." It appears at the top and at the end of `runs/rq-mechanism-v2/PHASE4_LOCK.md`. The lock commit contains no fitness result.

## Locked settings

From `runs/rq-mechanism-v2/PHASE4_LOCK.md`, not changed after the measurement:

- Output: `runs/rq-mechanism-v2/phase4-fitness/`
- Seeds: 9501, 9502, 9503, 9504
- Hosts were not re-selected from a fitness sign
- Exemplar A: `host-A-001`, genome `101111000100000001000000`, window `000000`
- Exemplar B: `host-B-001`, genome `101111000100000001111111`, window `111111`
- Equal counts: 30 and 30, census 60
- Horizon: 7 generations
- Workers: at most 7. The run used 7 as the pool cap (`summary.json` field `workers` is 7)
- Importance is undeclared. SUPPORTED is forbidden. The minimum detectable effect is not the importance bound
- `MEASUREMENT_FLOOR` stays 12 and was not lowered
- `red_queen_proved` false
- Phase-3 source archives were read only. They were not modified

## Why seven generations

The choice was written in the lock before this contrast existed.

One engine generation is one `run_generations` step: the host life-loop, then contact, then one parasite advance. Phase 3 had already recorded a replacement time of 60/26 generations and a pre-declared multiple of 3. The horizon is the ceiling of 3 times that replacement time, which is 7. Generation-1 host births occur inside `step_generation`, before contact, so a horizon of 1 cannot be a post-contact census. The horizon was not shortened or lengthened after the sign of F.

## Code changes

### Lineage share

Prediction. A parasite conditioned while A was common reduces A's relative advantage compared with the parasite conditioned while B was common, and the converse. The score is who is alive, classed by parent id. An ATP drop is not host success.

Engine path. `lineage_share` walks `parent_id` from each living host to the installed founder class. `fitness_from_lineage` takes an optional `atp_loss` map and does not read it. `F = (L_A - L_B | common_a parasite) - (L_A - L_B | common_b parasite)`. Births and deaths are counted from lineage ids: a birth has a parent id, and a death is an id that was alive or born and is absent after the generation. Contact removal does not write `death_tick`. The archives store the parent map. `analyze_phase4` recomputes the shares from those maps.

Control. The absent branch is not an argument of `fitness_contrast`. Hand values 0.25, 0.75, 0.75, 0.25 give F = -1 by arithmetic in the test, not by copying a run. A living census of three A and two B is share 3/5 either with a large ATP loss on A or with that loss on B. An empty census is null, not 0. One unresolved id makes the share null, not the share of the remaining ids.

Source. Parent ids, births, and deaths are the life-loop lineage and the post-contact living set. Zaman et al. 2014, as already read in `PHASE1.md` (PMC4267771), is why a removed antagonist is not called reciprocal coevolution. Decaestecker et al. 2007, as already read there, is why recognition does not evolve during the score. Hall et al. 2011 full text was not read and is not quoted.

Limit. Importance is undeclared, so a complete sample cannot be SUPPORTED. `MEASUREMENT_FLOOR` remains 12. n = 4 is not support. A measured share of 0, when the other class is still alive, is a count. A missing seed is not that zero.

Estimand. F is the difference of founder-class advantages. Unmeasurable histories are dropped. They are not zeros. The absent advantage is not F.

### Assay branches

Prediction. The same locked hosts, at equal counts, face either the phase-3 common-A parasites, the phase-3 common-B parasites, or no effective infectious pressure. Recognition mutation is off. Host reproduction and its cost stay on.

Engine path. `build_arm(ARM_A)` then `install_equal_hosts` on the shared food patches at `STRUCT_BIRTH_ATP`. No host-composition hold. Adapted branches set passage `coevolve` and parasite `mutation_rate` 0, so `AntagonistPopulation.advance` does not use the frozen reseat. Host `bit_flip_rate` is set to 0 without calling `freeze_host_genotypic_inheritance`. `reproduction.enabled` stays true and `parent_atp_cost` stays the booted cost (1.0 in the archives).

Control. Passage `absent` (`PASSAGE_ABSENT`). `StructuralRQArm._apply_hp_env_contact` returns `(0, [])` before any host debit when passage is absent. Host `step_generation` still runs first. This is antagonist removal, not a pure evolution control. The absent roster is loaded only so `advance` has a population to remove. It is not a third genotype and it is not `shuffled_labels`. `shuffled_labels` is not a frozen genotype. Passage `frozen` is not used.

Source. The zero-contact return is the existing absent branch in `closed_loop_hp_arm01_structural_rq.py`. The parasite lists are the last rows of the phase-3 `common_a` and `common_b` archives for seeds 9501-9504. Those files are opened read-only. The phase-3 bytes were hashed before and after and matched.

Limit. The absent path clears the parasite roster inside `advance`. That is the existing removal, not a host-reproduction cut. Host births can still be zero if the life-loop does not reproduce inside the locked horizon. That outcome is reported below. Parameters were not changed to produce it.

Estimand. Contact pressure is `contacts` and `host_atp_paid`. It is not F. If those move while birth counts and death counts do not, the summary says so.

### Locked-seed gate

Prediction. An incomplete locked list is `BLOCKED_MEASUREMENT`, not a negative on the seeds that remain. A complete sample cannot be SUPPORTED while importance is undeclared.

Engine path. `assess_phase4` keeps a null F as missing. It refuses a lowered `MEASUREMENT_FLOOR`. The verdict is `BLOCKED_MEASUREMENT` when `n_used` is not `n_locked`, and `NOT_DECLARED` when every locked seed has a finite F.

Control. Three hand values whose mean is -0.4, with 9504 missing, do not become that mean and do not become the mean after imputing 0. Four finite values are `NOT_DECLARED`, not `SUPPORTED_IN_MODEL`.

Source. The same gate idea as phase 1 and phase 3, applied to F. This repository has no pre-declared importance bound for this estimand.

Limit. `MEASUREMENT_FLOOR` is 12 and is not this panel's sample size. The minimum detectable effect is not the importance bound.

Estimand. Dropped seeds are reported. They are not scored as zero and they are not a scientific absence of a fitness link.

## Run

Four seeds, three branches, 7 generations, worker cap 7. No history failed. No `REASON.txt`. No partial archive. Every seed has `COMPLETE` with `generations=7 red_queen_proved=false`. Each archive has generations 1 through 7. Phase-3 archive bytes were unchanged after the assay. About 644 KB under `phase4-fitness/`. Raw archives were kept.

Adapted branches recorded passage `coevolve`, host bit-flip rate 0, parasite mutation events 0, `reproduction_enabled` true, and `parent_atp_cost` 1.0. The absent branch recorded passage `absent`, 0 contacts, and the same host reproduction flags. `host_inheritance` stayed `transmit`.

## F, the absent control, and contact

Numbers are the ones in `runs/rq-mechanism-v2/phase4-fitness/summary.json`. `host_atp_paid` is contact pressure. It is not F.

| Seed | F | share A, common A | share B, common A | share A, common B | share B, common B | share A, absent | share B, absent | advantage absent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9501 | 0.0 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.0 |
| 9502 | 0.0 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.0 |
| 9503 | 0.0 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.0 |
| 9504 | 0.0 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.0 |

`F_mean` = 0.0. `n_locked` = 4. `n_used` = 4. `dropped_seeds` = []. Verdict `NOT_DECLARED`. `importance_bound` is null. `supported_forbidden` is true. `measurement_floor` is 12. `measurement_floor_lowered` is false. `red_queen_proved` is false. `red_queen_declared` is false.

Contact pressure and demography, from the same file:

| Seed | contacts common A | paid common A | contacts common B | paid common B | contacts absent | paid absent | births A/B, all branches | deaths A/B, all branches | contact without demographic change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9501 | 420 | 251.2 | 420 | 254.2 | 0 | 0.0 | 0/0 | 0/0 | true |
| 9502 | 420 | 250.2 | 420 | 245.2 | 0 | 0.0 | 0/0 | 0/0 | true |
| 9503 | 420 | 248.79999999999998 | 420 | 245.6 | 0 | 0.0 | 0/0 | 0/0 | true |
| 9504 | 420 | 251.79999999999998 | 420 | 241.39999999999998 | 0 | 0.0 | 0/0 | 0/0 | true |

Alive counts at generation 7 were 30 and 30 on every branch. No class was extinct.

Contact pressure changed without survival or reproduction changing. Seat counts on the two adapted branches were both 420, and `host_atp_paid` differed. The absent branch had 0 contacts and paid 0.0. Birth counts and death counts were 0 for both classes on every branch, including absent. `contact_without_demographic_change` is true for every seed. F is 0.0 because the living census stayed the installed 30/30. That is a result of this model on the locked horizon, not a Red Queen verdict, and the engine was not changed to create a different one.

The absent control is passage `absent`. It is not a pure evolution control. Host reproduction stayed enabled. No births were recorded on that branch either, so the lack of births is not explained by contact.

## Tests

Not stacked with pytest-xdist. Workers inside the validity file stay at 4. The phase-4 file does not open a pool. Phase-2 `MAX_WORKERS` is still 4. `PHASE3_LOCK.md` still says the measurement used 4 workers.

```
/tmp/ct-tools/bin/python -m pytest \
  tests/test_rq_mechanism_v2_phase4.py \
  tests/test_rq_mechanism_v2_validity.py \
  -o addopts='--disable-plugin-autoload --import-mode=importlib' \
  --tb=line -q
```

16 passed in 3.71s.

Ruff, on the touched files:

```
/tmp/ct-tools/bin/ruff check \
  src/codontrace/genesis/rq_mechanism_v2_phase4.py \
  tests/test_rq_mechanism_v2_phase4.py
```

All checks passed.

## What was not run

No full coevolution. No later phase. No new confirmatory. No Red Queen claim. Seeds, the horizon, virulence, steal fraction, mutation during the assay, maintenance, birth ATP, and `MEASUREMENT_FLOOR` were not changed after F. The phase-3 frequency panel was not rerun. Hall et al. 2011 full text was not read.
