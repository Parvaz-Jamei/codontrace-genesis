# Phase 5 full coevolution

Branch `rq/mechanism-v2`. Nothing was pushed, merged, or rewritten. `runs/rq-bidirectional-timeshift-01` was not modified and was not committed. Previous mechanism-v2 runs were not modified. `PHASE3_LOCK.md` was not edited. The engine was not edited after this verdict.

`red_queen_proved` is false. Red Queen was not declared. Claim A is not claim B. A positive D or a nonzero F from an earlier phase is not this confirmatory.

## Commits

- Code, before the lock and before any confirmatory history: `46c318f298e0c27f6fd636e6f37a1df61581912a`
- Lock, before any confirmatory history: `60a9a0fec9b542bd216c23d1ac6c080e3c254918`
- The twelve histories ran with `HEAD` at the lock commit. This note and the confirmatory archives are a later commit.

The lock file's sentence, in that commit, is: "No confirmatory number has been computed." It is the third line of `runs/rq-mechanism-v2/PHASE5_LOCK.md` and the last sentence of that file. The lock commit contains the seed-9600 probe and no confirmatory archive.

## Why these settings

From the lock, chosen on the seed-9600 probe plus the power calculation, not from a confirmatory sign.

The probe ran 24 generations of the coevolve arm only. Mean seated parasite newborns were 20.166666666666668 on a census of 64, so one replacement time is 3.173553719008264 generations. Primary lag is `max(1, round(replacement))`, which is 3. No other lag was scored. Horizon is the ceiling of 3 times that replacement time, which is 10, and 10 is greater than lag + 1. The turnover multiple 3 is the phase-3 multiple. It was not moved after the confirmatory sign.

Planning sigma for claim A is 0.25, the greater of the probe's infectivity dispersion and the pre-declared planning sigma. Planning sigma for claim B is 0.5. It is not a reversal rate from the probe. Precision targets, which are not importance, are 0.25 and 0.5. At n = 12 the minimum detectable effects are 0.22216378635389802 and 0.44432757270779605. Both meet those precision targets, so n stays at `MEASUREMENT_FLOOR`. n was not increased after the sign.

Seeds: 9601 through 9612. Seed 9600 is not one of them.

Importance is undeclared. SUPPORTED is forbidden. The Decaestecker gap of 0.10 was not adopted as this engine's importance bound. The minimum detectable effect is not the importance bound. `MEASUREMENT_FLOOR` stays 12.

Workers: at most 7. The run used 7.

Direction locked before the run: `I(hosts at generation 10, parasites at generation 10) - I(hosts at generation 10, parasites at generation 7) > 0`. That is the contemporary-versus-previous comparison read from Decaestecker et al. 2007 in `PHASE1.md` (contemporary infectivity 0.65, previous 0.55). It was not chosen from the probe contrast. The probe did not score a time-shift.

## Code

Births use the outcross birth chamber from phase 4b. Host bit-flip on `coevolve` and `constant_parasite` stays `STRUCT_HOST_BIT_FLIP`. It is 0 only on `adaptation_cut`. Reproduction stays enabled on every arm. `freeze_host_genotypic_inheritance` is not used. `shuffled_labels` is not used. Passage `absent` is not used.

`adaptation_cut` restores the founder host genomes before contact and holds parasite passage at `frozen`. That removes reciprocal adaptation. It is not reproduction-off.

`constant_parasite` holds parasite passage at `frozen`, so parasite genotype composition is held, while contact and the debit stay and the hosts are not deleted.

Claim A and claim B are separate gates. A census wave cannot support claim B. A null contrast is not zero. An incomplete locked seed list is `BLOCKED_MEASUREMENT`. Importance undeclared forbids `SUPPORTED`. `MEASUREMENT_FLOOR` is not lowered.

## Run

Twelve seeds, three arms, 10 generations, worker cap 7. No history failed. No `REASON.txt`. Every seed has `COMPLETE` with `generations=10 red_queen_proved=false`. Each archive has generations 1 through 10 for `coevolve`, `adaptation_cut`, and `constant_parasite`. About 9.3 MB under `phase5-coevolution/`. Raw archives were kept. Extinction and fixation were not deleted; none of the twelve focal censuses was empty.

Replay matched. Each of the 12 archives was re-scored with `replay_archived_contact` on an independent copy: 30 generations compared, 0 unmeasurable, 0 mismatches. The flags `evolution`, `reproduction`, and `mutation` were false. 360 generations in total. One-shot versus resume matched on `scientific_body` inside each history before `COMPLETE`. There was no partial stop and no invariant stop.

## Claim A

Numbers are the ones in `runs/rq-mechanism-v2/phase5-coevolution/summary.json`. The contrast is contemporary infectivity minus past infectivity on the coevolve arm. Controls are the same contrast and are not substituted into it.

| Seed | coevolve | adaptation_cut | constant_parasite |
| --- | --- | --- | --- |
| 9601 | -0.06609195402298862 | 0.0 | 0.0 |
| 9602 | -0.011299435028248483 | 0.0 | 0.0 |
| 9603 | -0.030555555555555558 | 0.0 | 0.0 |
| 9604 | 0.032258064516129004 | 0.0 | 0.0 |
| 9605 | -0.0357142857142857 | 0.0 | 0.0 |
| 9606 | 0.038011695906432774 | 0.0 | 0.0 |
| 9607 | -0.03611111111111115 | 0.0 | 0.0 |
| 9608 | -0.01881720430107514 | 0.0 | 0.0 |
| 9609 | -0.02586206896551735 | 0.0 | 0.0 |
| 9610 | -0.008333333333333415 | 0.0 | 0.0 |
| 9611 | 0.04597701149425304 | 0.0 | 0.0 |
| 9612 | 0.05913978494623662 | 0.0 | 0.0 |

`n_locked` = 12. `n_used` = 12. `dropped_seeds` = []. Mean = -0.004783199264088665. The 95% interval is [-0.029704900119957314, 0.020138501591779982]. One-sided p = 0.6595759941604089. `se_zero` is false. Verdict `INCONCLUSIVE`.

The locked direction was positive. The interval contains 0 and extends below 0, so the confirmatory does not establish that contemporary parasites outperform past parasites on the focal hosts. It is not a negative either: the upper end is above 0. Importance is undeclared, so the verdict is not `SUPPORTED`.

Both controls are 0.0 on every seed. That 0 is a measured contrast, not a missing archive. Frozen parasite composition removes the parasite time-shift. It does not get written into the coevolve mean.

## Claim B

Every locked history measured the required pieces, and none showed the reversal.

| Seed | reversal | fitness measured | contacts | ATP paid | windows in the focal census |
| --- | --- | --- | --- | --- | --- |
| 9601 | false | true | 639 | 401.47421875 | 34 |
| 9602 | false | true | 640 | 396.225 | 35 |
| 9603 | false | true | 639 | 385.92187499999994 | 34 |
| 9604 | false | true | 637 | 375.40000000000003 | 32 |
| 9605 | false | true | 640 | 384.73749999999995 | 34 |
| 9606 | false | true | 638 | 385.8421875000001 | 32 |
| 9607 | false | true | 640 | 388.2 | 30 |
| 9608 | false | true | 635 | 383.19140625 | 35 |
| 9609 | false | true | 639 | 375.25156250000003 | 36 |
| 9610 | false | true | 640 | 389.159375 | 33 |
| 9611 | false | true | 640 | 393.06874999999997 | 32 |
| 9612 | false | true | 640 | 392.2 | 27 |

`frequency_measured_n` = 12. `contact_ok_n` = 12. `fitness_measured_n` = 12. `reversal_true_n` = 0. `used_census_wave_as_estimand` is false. `n_locked` = 12. `n_used` = 12. `dropped_seeds` = []. Reversal-rate mean = 0.0. `se_zero` is true. The one-sided p-value is null, not 0. The interval is null. `criterion_met` is false. Verdict `INCONCLUSIVE`.

Genotype counts, contact pressure, and lineage fitness were measurable. The missing part of the conjunction is the rank reversal: `I(A) - I(B)` did not change sign between generation 10 and generation 7 in any history. A census wave was not used as the estimand. ATP paid is contact pressure, not fitness.

## Verdict

Claim A: `INCONCLUSIVE`. Claim B: `INCONCLUSIVE`. `importance_bound` is null. `supported_forbidden` is true. `measurement_floor` is 12. `measurement_floor_lowered` is false. `red_queen_proved` is false.

Neither mechanism was supported in this model. The locked positive time-shift was not established, and the sign reversal required for claim B did not occur. Importance was left undeclared because this engine has no pre-declared importance bound for these estimands, so `SUPPORTED` was forbidden even before the sign. The sample standard error of the reversal rate is 0, so that t statistic is undefined. That is not a proof of absence and it is not Red Queen.

## Tests

Not stacked with pytest-xdist. The validity file opens its own 4-worker pool.

```
/tmp/ct-tools/bin/python -m pytest \
  tests/test_rq_mechanism_v2_phase5.py \
  tests/test_rq_mechanism_v2_validity.py \
  -o addopts='--disable-plugin-autoload --import-mode=importlib' \
  --tb=line -q
```

20 passed in 5.48s. Ten in `test_rq_mechanism_v2_phase5.py`, ten in `test_rq_mechanism_v2_validity.py`.

Ruff, on the touched files:

```
/tmp/ct-tools/bin/ruff check \
  src/codontrace/genesis/rq_mechanism_v2_phase5.py \
  tests/test_rq_mechanism_v2_phase5.py
```

All checks passed.

## What was not done

No push, merge, or history rewrite. The engine was not changed after the verdict and was not changed to force a positive. `red_queen_proved` was not set true by hand. Seeds were not added or replaced after the sign. Raw archives were kept. Hall et al. 2011 full text was not read.

## Rejection

Phase 5 is rejected. The control zeros were an instrument failure, not a biological zero. Claim A and claim B on the coevolve arm were not rewritten. Their definitions stay `I(hosts at generation 10, parasites at generation 10) - I(hosts at generation 10, parasites at generation 7)` and the claim-B conjunction already stated above. The coevolve numbers in this file stay as recorded: claim A mean -0.004783199264088665, interval includes 0, verdict `INCONCLUSIVE`; claim B reversal rate 0, `criterion_met` false, verdict `INCONCLUSIVE`.

Verified before any control edit, on the code and on the twelve archives.

`score_arm_contrast` passes the horizon hosts to both `infectivity` calls and changes only the parasite generation. `infectivity` calls `replay_archived_contact` with the assay ATP override, so archived ATP is rewritten before the debit. `_apply_hp_env_contact` pairs parasite seat `i` with a host seat. Frozen passage calls `AntagonistPopulation._reseat_frozen`, which writes the founder window back onto each seat, and frozen mode sets mutation to 0. The two parasite inputs are therefore the same windows, the pairing matches, and the contrast cannot be nonzero. That written 0 is not a result about adaptation.

On every seed 9601 through 9612, the parasite window sequence at generations 1 through 10 is the same inside `adaptation_cut`, the same inside `constant_parasite`, and the same across those two arms. Order matches, not only the multiset. `constant_parasite` host windows at generation 10 differ from generation 7 on every seed, so host change was present and the old contrast could not see it. `adaptation_cut` host windows do not differ across those generations. The coevolve parasite windows do differ. A separate seat check, not these archives, already shows the assay moves when one window changes: 64 seats at affinity 0.5 versus the same seats with one window at affinity 0 differ by 0.5/64.

The replacement is phase 5b. It does not reuse seeds 9601 through 9612, and it does not write into `phase5-coevolution/`.
