# Phase 4b fitness link

Branch `rq/mechanism-v2`. Nothing was pushed, merged, or rewritten. `runs/rq-bidirectional-timeshift-01` was not modified and was not committed. `red_queen_proved` is false. Red Queen was not declared. A nonzero F is not Red Queen. The result below is not called Red Queen.

The rejected phase-4 run stays at `runs/rq-mechanism-v2/phase4-fitness/` (commit `8dbcc1eba85290bc286f1512ea06eee54456373f`). It was not deleted and its seeds were not changed. Its numbers stay in `PHASE4.md`.

## Commits

- Code, before this history: `d91b88a2496c16ef55b7eb012091cdaf40751d19`
- Rejection note on the old run: `9fff5dc1bafa78fe4673e17b62e333625e98fd6c`
- Lock, before any phase-4b history: `a7c5546ccf48fab4365d683ae8ada6129519070d`
- The four histories ran with `HEAD` at the lock commit. This note and the archives are a later commit.

The lock file's sentence, in that commit, is: "No fitness number has been computed." It is the first line, it is repeated in the horizon section, and it is the last sentence of `runs/rq-mechanism-v2/PHASE4B_LOCK.md`. The only `F =` line in the lock is the definition `F = R(common_a) - R(common_b)`. It is not a number. A search for `F` followed by `=` and a digit does not match the lock.

## What was verified before the edit

Births. On the unchanged engine, `build_phase4_arm` left `SexualRecombinationConfig.enabled` false, so `uses_birth_chamber` was false, while `decode_outcross` on genome `101111000100000001000000` was true and `resolve_copy_self_mode` returned `chamber`. One generation with reproduction enabled, parent cost 1.0, and no food produced 60 `COPY_SELF` refusals, every one `outcross_chamber_required`, births 0, and no child id. The silenced program was `EAT_LUMEN` 0.8, `COPY_SELF` 8.0, `WAIT` 0.1.

Energy. Opening ATP 48. Debit cap 8.0 * 0.15 * 1 = 1.2. Basal cost 0.05 on each of 2 ticks. No food credit. The life-loop then the 1.2 debit left 2.5 after generation 7 and 0 at generation 9. Generation 7 cannot kill the host on that account. The fed path is different: the life-loop places a 20.0 bolus on each food patch, `EAT_LUMEN` credited 20 on generation 1, and the balance rose. That bolus was not removed for the assay.

## Code changes

### Birth acceptance

Prediction. A nonzero outcross locus requires a birth chamber. Turning reproduction on without the chamber rejects every birth.

Engine path. `enable_outcross_birth_chamber` sets `SexualRecombinationConfig(enabled=True, pairing_policy=birth_chamber, recombination_prob=1, two_fold_cost_sex=False)` and writes the installed host ids into `closed_loop_hp_life.role_by_id`. `COPY_SELF` then enters `_handle_chamber_copy_self`. A child organism id is added to the population. `parent_atp_cost` stays 1.0. Host `bit_flip_rate` stays 0.

Control. The same arm with sexual recombination forced back off still has `reproduction.enabled` true, still refuses with `outcross_chamber_required`, and adds no organism id.

Source. The existing chamber in `population.py` and the life-loop's sexual config. No new quotation. Hall et al. 2011 full text was not read.

Limit. Virulence, steal fraction, maintenance, birth ATP, bolus, `max_population` (64), mutation rate, and `MEASUREMENT_FLOOR` (12) were not retuned. The cap still stops births once 64 hosts are alive. That was not raised to move F.

Estimand. Births can change the living census that `L_A` and `L_B` read. The score is still that census, not ATP loss, and not a forced nonzero F.

### Horizon

Prediction. Death on the no-food maximum-debit account is generation 9, not 7, and not `ceil(3 * 60/26)`.

Engine path. `run_generations` order: passage refill, `step_generation` (basal plus codon costs), then `_apply_hp_env_contact` (debit at most 1.2, remove the host at ATP 0). The locked horizon is 9, written before the run.

Control. The test replays ledger entry amounts from a one-host fixture with bolus 0, resources cleared, and a matching parasite window. It does not call a horizon helper. The summed balance hits 0 at the same generation the host disappears, and that generation is `PHASE4B_HORIZON`. Generation 7 of that account is still alive. The turnover horizon `PHASE4_HORIZON` stays 7 for the rejected definition and is not this run.

Source. The ATP ledger on that fixture: opening 48, basal 0.05 per tick, codon costs 0.8 / 8.0 / 0.1, debit cap 1.2, no credit. The arithmetic is in `PHASE4B_LOCK.md`.

Limit. The assay still places the 20.0 bolus. Food was not turned off to create deaths. If F had stayed 0 after births and deaths could occur, that would have been reported. It did not stay 0. A nonzero F is still not Red Queen.

Estimand. The horizon is long enough that death is reachable on the no-food account. F was not an input to the horizon.

### Branch hash

Prediction. The rejected writer stored the common_a file hash on every branch.

Engine path. `branch_archive_hash` keeps the sha256 of the file a branch reads for `common_a` and `common_b`. The absent label is the sha256 of the common_a bytes plus the tag `branch:absent`, because that roster is only loaded so `advance` can remove it. `run_phase4_seed` writes `sources[branch]["archive_sha256"]` into that branch's rows.

Control. Three different byte strings produce three labels. Writing the first label onto every branch fails that comparison. On this run each seed's three archive labels differ.

Limit. The rejected `phase4-fitness` archives were not rewritten.

Estimand. None. The hash is a label, not F.

## Locked settings

From `runs/rq-mechanism-v2/PHASE4B_LOCK.md`, not changed after the measurement:

- Output: `runs/rq-mechanism-v2/phase4b-fitness/`
- Seeds: 9501, 9502, 9503, 9504
- Parasites: the phase-3 frequency archives, read only
- Hosts were not re-selected from a fitness sign
- Exemplar A: `host-A-001`, genome `101111000100000001000000`, window `000000`
- Exemplar B: `host-B-001`, genome `101111000100000001111111`, window `111111`
- Equal counts: 30 and 30
- Horizon: 9 generations, from the host energy account above
- Workers: at most 7. The run used 7 (`summary.json` field `workers` is 7)
- Importance is undeclared. SUPPORTED is forbidden
- `MEASUREMENT_FLOOR` stays 12
- `red_queen_proved` false

## Run

Four seeds, three branches, 9 generations, worker cap 7. No history failed. No `REASON.txt`. Every seed has `COMPLETE` with `generations=9 red_queen_proved=false`. Each archive has generations 1 through 9 and schema `rq-mechanism-v2-phase4b/1`. The three `source_sha256` labels inside each seed differ. Phase-3 archive bytes were unchanged (combined sha256 `d45fedec1be706ea03eb9c2a5b7c46ac227cbdcfde120092dc9c78d4531445b6` before and after). About 796 KB under `phase4b-fitness/`. Raw archives were kept.

## F, births, deaths, and the absent control

Numbers are the ones in `runs/rq-mechanism-v2/phase4b-fitness/summary.json`. `host_atp_paid` is contact pressure. It is not F.

| Seed | F | alive A/B, common A | births A/B, common A | deaths A/B, common A | alive A/B, common B | births A/B, common B | deaths A/B, common B | alive A/B, absent | births A/B, absent | deaths A/B, absent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9501 | -0.17340521114106022 | 13/29 | 4/0 | 21/1 | 21/32 | 4/2 | 13/0 | 34/30 | 4/0 | 0/0 |
| 9502 | 0.05469845722300143 | 25/21 | 10/0 | 15/9 | 32/30 | 4/0 | 2/0 | 34/30 | 4/0 | 0/0 |
| 9503 | -0.36684171042760694 | 15/28 | 6/0 | 21/2 | 33/29 | 4/0 | 1/1 | 34/30 | 4/0 | 0/0 |
| 9504 | 0.28448275862068967 | 35/21 | 12/2 | 7/11 | 28/30 | 4/0 | 6/0 | 34/30 | 4/0 | 0/0 |

`F_mean` = -0.050266426431244016. `n_locked` = 4. `n_used` = 4. `dropped_seeds` = []. Verdict `NOT_DECLARED`. `importance_bound` is null. `supported_forbidden` is true. `measurement_floor` is 12. `measurement_floor_lowered` is false. `red_queen_proved` is false. `red_queen_declared` is false.

Births occurred on every branch, including absent. Deaths occurred on every adapted branch and on no absent branch. No class was extinct. `contact_without_demographic_change` is false on every seed: contact differed and so did births or deaths. Contacts were 540 on each adapted branch and 0 on absent. Paid ATP was 322.3 and 317.8 (9501), 319.2 and 314.6 (9502), 318.0 and 312.2 (9503), 326.3 and 313.0 (9504), and 0.0 on every absent branch.

The absent advantage was 0.0625 on every seed (alive 34 and 30). It is not inside F. The absent control is passage `absent`, not a pure evolution control. Host reproduction stayed enabled, and those four A births are why the absent census is not 30/30.

F is not zero. That is not a Red Queen result. Importance is undeclared, so the verdict is `NOT_DECLARED`, not `SUPPORTED`.

## Tests

Not stacked with pytest-xdist.

```
/tmp/ct-tools/bin/python -m pytest \
  tests/test_rq_mechanism_v2_phase4.py \
  tests/test_rq_mechanism_v2_validity.py \
  -o addopts='--disable-plugin-autoload --import-mode=importlib' \
  --tb=line -q
```

19 passed in 4.32s.

Ruff, on the touched files:

```
/tmp/ct-tools/bin/ruff check \
  src/codontrace/genesis/rq_mechanism_v2_phase4.py \
  tests/test_rq_mechanism_v2_phase4.py
```

All checks passed.

Phase-2 `MAX_WORKERS` is still 4. `PHASE3_LOCK.md` was not edited.

## What was not run

No full coevolution. No push, merge, or history rewrite. `red_queen_proved` was not set true. Seeds were not replaced. Parameters were not changed after F to push it away from zero.
